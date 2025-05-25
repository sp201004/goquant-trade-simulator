"""
Fee calculation and maker/taker prediction models.
Handles transaction cost estimation including exchange fees and maker/taker dynamics.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

import logging

# Use standard logging for now
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create a simple OrderbookSnapshot placeholder for now
class OrderbookSnapshot:
    def __init__(self, timestamp, bids, asks):
        self.timestamp = timestamp
        self.bids = bids
        self.asks = asks

class OrderType(Enum):
    """Order execution type."""
    MAKER = "maker"
    TAKER = "taker"


@dataclass
class FeeStructure:
    """Exchange fee structure."""
    maker_fee_rate: float      # Maker fee rate (e.g., 0.0001 for 0.01%)
    taker_fee_rate: float      # Taker fee rate (e.g., 0.0004 for 0.04%)
    volume_tiers: Dict[float, Tuple[float, float]]  # Volume tiers: {min_volume: (maker_rate, taker_rate)}
    

@dataclass
class MakerTakerFeatures:
    """Features for maker/taker prediction."""
    order_size: float                 # Size of the order
    order_size_relative: float        # Order size relative to market depth
    distance_to_mid: float            # Distance from mid price
    distance_to_mid_bps: float        # Distance in basis points
    market_depth_ratio: float         # Ratio of market depth on both sides
    spread_ratio: float               # Current spread relative to recent average
    volatility_recent: float          # Recent price volatility
    order_flow_imbalance: float       # Order flow imbalance
    time_since_last_trade: float      # Time since last trade
    market_momentum: float            # Market momentum indicator
    volume_profile: float             # Current volume profile
    

@dataclass
class TradingCostBreakdown:
    """Breakdown of trading costs."""
    principal_amount: float           # Principal trade amount
    base_fee: float                  # Base exchange fee
    volume_discount: float           # Volume-based discount
    net_fee: float                   # Net fee after discounts
    maker_taker_prob: float          # Probability of maker execution
    expected_fee: float              # Expected fee considering maker/taker probability
    fee_rate_bps: float             # Effective fee rate in basis points
    

class FeeCalculator:
    """
    Calculator for exchange fees and trading costs.
    """
    
    def __init__(self, fee_structure: FeeStructure, daily_volume: float = 0.0):
        self.fee_structure = fee_structure
        self.daily_volume = daily_volume
        self.volume_history: List[float] = []
        
    def get_current_fee_rates(self, current_volume: Optional[float] = None) -> Tuple[float, float]:
        """
        Get current maker and taker fee rates based on volume.
        
        Args:
            current_volume: Current daily volume (optional)
            
        Returns:
            Tuple of (maker_rate, taker_rate)
        """
        volume = current_volume or self.daily_volume
        
        # Find applicable volume tier
        applicable_rates = (self.fee_structure.maker_fee_rate, self.fee_structure.taker_fee_rate)
        
        for min_volume, (maker_rate, taker_rate) in sorted(self.fee_structure.volume_tiers.items()):
            if volume >= min_volume:
                applicable_rates = (maker_rate, taker_rate)
            else:
                break
                
        return applicable_rates
        
    def calculate_fee(
        self, 
        trade_amount: float, 
        order_type: OrderType,
        current_volume: Optional[float] = None
    ) -> float:
        """
        Calculate fee for a trade.
        
        Args:
            trade_amount: Trade amount in quote currency
            order_type: Maker or taker order
            current_volume: Current daily volume
            
        Returns:
            Fee amount
        """
        maker_rate, taker_rate = self.get_current_fee_rates(current_volume)
        
        if order_type == OrderType.MAKER:
            return trade_amount * maker_rate
        else:
            return trade_amount * taker_rate
            
    def calculate_expected_fee(
        self, 
        trade_amount: float, 
        maker_probability: float,
        current_volume: Optional[float] = None
    ) -> TradingCostBreakdown:
        """
        Calculate expected fee considering maker/taker probability.
        
        Args:
            trade_amount: Trade amount in quote currency
            maker_probability: Probability of maker execution (0-1)
            current_volume: Current daily volume
            
        Returns:
            TradingCostBreakdown object
        """
        maker_rate, taker_rate = self.get_current_fee_rates(current_volume)
        
        # Calculate fees for both scenarios
        maker_fee = trade_amount * maker_rate
        taker_fee = trade_amount * taker_rate
        
        # Expected fee
        expected_fee = maker_probability * maker_fee + (1 - maker_probability) * taker_fee
        
        # Base fee (using taker rate as base)
        base_fee = trade_amount * self.fee_structure.taker_fee_rate
        
        # Volume discount
        volume_discount = base_fee - expected_fee
        
        # Fee rate in basis points
        fee_rate_bps = (expected_fee / trade_amount) * 10000
        
        return TradingCostBreakdown(
            principal_amount=trade_amount,
            base_fee=base_fee,
            volume_discount=volume_discount,
            net_fee=expected_fee,
            maker_taker_prob=maker_probability,
            expected_fee=expected_fee,
            fee_rate_bps=fee_rate_bps
        )
        
    def update_volume(self, new_trade_volume: float) -> None:
        """Update daily volume with new trade."""
        self.daily_volume += new_trade_volume
        self.volume_history.append(new_trade_volume)
        
    def reset_daily_volume(self) -> None:
        """Reset daily volume (call at end of day)."""
        self.daily_volume = 0.0


class MakerTakerPredictor:
    """
    Predicts whether an order will be executed as maker or taker.
    """
    
    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        
        # Models
        if model_type == "logistic":
            self.model = LogisticRegression(random_state=42)
        elif model_type == "random_forest":
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
            
        self.scaler = StandardScaler()
        
        # Model state
        self.is_trained = False
        self.feature_names = []
        self.training_stats = {}
        
        # Historical data
        self._features_history: List[MakerTakerFeatures] = []
        self._labels_history: List[int] = []  # 1 for maker, 0 for taker
        self._max_history = 10000
        
    def extract_features(
        self, 
        orderbook: OrderbookSnapshot,
        order_size: float,
        order_price: float,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> MakerTakerFeatures:
        """
        Extract features for maker/taker prediction.
        
        Args:
            orderbook: Current orderbook snapshot
            order_size: Size of the proposed order
            order_price: Price of the proposed order
            historical_data: Historical market data
            
        Returns:
            MakerTakerFeatures object
        """
        # Basic orderbook metrics
        bid_price = orderbook.bids[0][0] if orderbook.bids else 0
        ask_price = orderbook.asks[0][0] if orderbook.asks else 0
        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0
        
        # Distance calculations
        distance_to_mid = abs(order_price - mid_price)
        distance_to_mid_bps = (distance_to_mid / mid_price) * 10000 if mid_price > 0 else 0
        
        # Market depth
        bid_depth = sum(size for _, size in orderbook.bids[:5]) if orderbook.bids else 0
        ask_depth = sum(size for _, size in orderbook.asks[:5]) if orderbook.asks else 0
        total_depth = bid_depth + ask_depth
        
        order_size_relative = order_size / total_depth if total_depth > 0 else 0
        market_depth_ratio = bid_depth / ask_depth if ask_depth > 0 else 1.0
        
        # Spread metrics
        current_spread = ask_price - bid_price
        spread_ratio = 1.0  # Default, would need historical spread data
        
        # Order flow imbalance
        order_flow_imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0
        
        # Historical features (with defaults)
        volatility_recent = 0.0
        market_momentum = 0.0
        time_since_last_trade = 0.0
        volume_profile = 1.0
        
        if historical_data:
            # Calculate volatility
            prices = historical_data.get('prices', [])
            if len(prices) > 1:
                returns = np.diff(np.log(prices))
                volatility_recent = np.std(returns) if len(returns) > 0 else 0.0
                market_momentum = (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0.0
                
            # Time since last trade
            timestamps = historical_data.get('timestamps', [])
            if len(timestamps) > 0:
                time_since_last_trade = orderbook.timestamp - timestamps[-1]
                
            # Volume profile
            volumes = historical_data.get('volumes', [])
            if len(volumes) > 0:
                avg_volume = np.mean(volumes)
                current_volume = volumes[-1] if volumes else 0
                volume_profile = current_volume / avg_volume if avg_volume > 0 else 1.0
                
            # Spread ratio
            spreads = historical_data.get('spreads', [])
            if len(spreads) > 0:
                avg_spread = np.mean(spreads)
                spread_ratio = current_spread / avg_spread if avg_spread > 0 else 1.0
                
        return MakerTakerFeatures(
            order_size=order_size,
            order_size_relative=order_size_relative,
            distance_to_mid=distance_to_mid,
            distance_to_mid_bps=distance_to_mid_bps,
            market_depth_ratio=market_depth_ratio,
            spread_ratio=spread_ratio,
            volatility_recent=volatility_recent,
            order_flow_imbalance=order_flow_imbalance,
            time_since_last_trade=time_since_last_trade,
            market_momentum=market_momentum,
            volume_profile=volume_profile
        )
        
    def _features_to_array(self, features: MakerTakerFeatures) -> np.ndarray:
        """Convert MakerTakerFeatures to numpy array."""
        return np.array([
            features.order_size,
            features.order_size_relative,
            features.distance_to_mid,
            features.distance_to_mid_bps,
            features.market_depth_ratio,
            features.spread_ratio,
            features.volatility_recent,
            features.order_flow_imbalance,
            features.time_since_last_trade,
            features.market_momentum,
            features.volume_profile
        ])
        
    def train_model(
        self, 
        features_list: List[MakerTakerFeatures],
        order_types: List[OrderType]
    ) -> Dict[str, Any]:
        """
        Train the maker/taker prediction model.
        
        Args:
            features_list: List of feature objects
            order_types: List of actual order types (MAKER/TAKER)
            
        Returns:
            Training statistics
        """
        if len(features_list) != len(order_types):
            raise ValueError("Features and order types lists must have same length")
            
        if len(features_list) < 10:
            raise ValueError("Need at least 10 samples for training")
            
        logger.info(f"Training maker/taker model with {len(features_list)} samples")
        
        # Convert to arrays
        X = np.array([self._features_to_array(f) for f in features_list])
        y = np.array([1 if ot == OrderType.MAKER else 0 for ot in order_types])
        
        # Store feature names
        self.feature_names = [
            'order_size', 'order_size_relative', 'distance_to_mid', 'distance_to_mid_bps',
            'market_depth_ratio', 'spread_ratio', 'volatility_recent', 'order_flow_imbalance',
            'time_since_last_trade', 'market_momentum', 'volume_profile'
        ]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        self.training_stats = {
            'n_samples': len(features_list),
            'n_features': X.shape[1],
            'accuracy': accuracy_score(y_test, y_pred),
            'maker_ratio': np.mean(y),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        # Feature importance (if available)
        if hasattr(self.model, 'feature_importances_'):
            self.training_stats['feature_importance'] = dict(
                zip(self.feature_names, self.model.feature_importances_)
            )
        elif hasattr(self.model, 'coef_'):
            self.training_stats['feature_importance'] = dict(
                zip(self.feature_names, np.abs(self.model.coef_[0]))
            )
            
        self.is_trained = True
        logger.info(f"Model training completed. Accuracy: {self.training_stats['accuracy']:.4f}")
        
        return self.training_stats
        
    def predict_maker_probability(self, features: MakerTakerFeatures) -> float:
        """
        Predict probability of maker execution.
        
        Args:
            features: Features for prediction
            
        Returns:
            Probability of maker execution (0-1)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        # Convert features and scale
        X = self._features_to_array(features).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Get probability
        prob = self.model.predict_proba(X_scaled)[0, 1]
        return prob
        
    def add_observation(self, features: MakerTakerFeatures, actual_type: OrderType) -> None:
        """
        Add new observation for incremental learning.
        
        Args:
            features: Features of the executed order
            actual_type: Actual execution type (MAKER/TAKER)
        """
        self._features_history.append(features)
        self._labels_history.append(1 if actual_type == OrderType.MAKER else 0)
        
        # Maintain maximum history size
        if len(self._features_history) > self._max_history:
            self._features_history = self._features_history[-self._max_history:]
            self._labels_history = self._labels_history[-self._max_history:]
            
        # Retrain periodically
        if len(self._features_history) % 100 == 0 and len(self._features_history) >= 100:
            try:
                order_types = [OrderType.MAKER if label == 1 else OrderType.TAKER 
                             for label in self._labels_history]
                self.train_model(self._features_history, order_types)
                logger.info("Retrained maker/taker model with updated data")
            except Exception as e:
                logger.error(f"Failed to retrain model: {e}")


class IntegratedCostCalculator:
    """
    Integrated calculator that combines fees, slippage, and market impact.
    """
    
    def __init__(
        self, 
        fee_calculator: FeeCalculator,
        maker_taker_predictor: MakerTakerPredictor
    ):
        self.fee_calculator = fee_calculator
        self.maker_taker_predictor = maker_taker_predictor
        
    def calculate_total_cost(
        self, 
        orderbook: OrderbookSnapshot,
        trade_size: float,
        order_price: float,
        slippage_estimate: float = 0.0,
        market_impact: float = 0.0,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate total trading cost including all components.
        
        Args:
            orderbook: Current orderbook snapshot
            trade_size: Size of the trade
            order_price: Proposed order price
            slippage_estimate: Estimated slippage
            market_impact: Estimated market impact
            historical_data: Historical market data
            
        Returns:
            Dictionary with cost breakdown
        """
        trade_amount = trade_size * order_price
        
        # Predict maker/taker probability
        if self.maker_taker_predictor.is_trained:
            features = self.maker_taker_predictor.extract_features(
                orderbook, trade_size, order_price, historical_data
            )
            maker_prob = self.maker_taker_predictor.predict_maker_probability(features)
        else:
            # Default assumption
            maker_prob = 0.5
            
        # Calculate fee costs
        fee_breakdown = self.fee_calculator.calculate_expected_fee(
            trade_amount, maker_prob
        )
        
        # Calculate total costs
        total_cost = {
            'trade_amount': trade_amount,
            'exchange_fee': fee_breakdown.expected_fee,
            'slippage_cost': slippage_estimate,
            'market_impact_cost': market_impact,
            'total_cost': fee_breakdown.expected_fee + slippage_estimate + market_impact,
            'maker_probability': maker_prob,
            'fee_breakdown': fee_breakdown,
            'cost_bps': ((fee_breakdown.expected_fee + slippage_estimate + market_impact) / trade_amount) * 10000
        }
        
        return total_cost

"""
Slippage estimation models using linear and quantile regression.
Estimates transaction costs due to bid-ask spread and market impact.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
from sklearn.linear_model import LinearRegression, QuantileRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

# Use standard logging for now
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create a simple OrderbookSnapshot placeholder for now
class OrderbookSnapshot:
    def __init__(self, timestamp, bids, asks):
        self.timestamp = timestamp
        self.bids = bids
        self.asks = asks

@dataclass
class SlippageFeatures:
    """Features used for slippage prediction."""
    trade_size: float           # Size of the trade
    trade_size_relative: float  # Trade size relative to average volume
    bid_ask_spread: float       # Current bid-ask spread
    bid_ask_spread_bps: float   # Bid-ask spread in basis points
    market_depth_1: float       # Market depth at level 1
    market_depth_5: float       # Market depth at top 5 levels
    market_depth_10: float      # Market depth at top 10 levels
    volatility: float           # Recent price volatility
    momentum: float             # Price momentum
    time_of_day: float          # Time of day (0-1)
    volume_profile: float       # Current volume relative to daily average
    order_flow_imbalance: float # Order flow imbalance
    

@dataclass
class SlippagePrediction:
    """Slippage prediction result."""
    expected_slippage: float    # Expected slippage in absolute terms
    expected_slippage_bps: float # Expected slippage in basis points
    confidence_interval: Tuple[float, float]  # 95% confidence interval
    quantile_predictions: Dict[float, float]  # Quantile predictions
    

class SlippageEstimator:
    """
    Slippage estimation using machine learning regression models.
    """
    
    def __init__(self, use_quantile_regression: bool = True):
        self.use_quantile_regression = use_quantile_regression
        
        # Models
        self.linear_model = LinearRegression()
        self.quantile_models = {}
        self.scaler = StandardScaler()
        
        # Quantiles to predict
        self.quantiles = [0.05, 0.25, 0.5, 0.75, 0.95]
        
        # Model state
        self.is_trained = False
        self.feature_names = []
        self.training_stats = {}
        
        # Historical data for incremental learning
        self._features_history: List[SlippageFeatures] = []
        self._slippage_history: List[float] = []
        self._max_history = 10000
        
    def extract_features(
        self, 
        orderbook: OrderbookSnapshot, 
        trade_size: float,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> SlippageFeatures:
        """
        Extract features for slippage prediction.
        
        Args:
            orderbook: Current orderbook snapshot
            trade_size: Size of the proposed trade
            historical_data: Historical market data for volatility/momentum calc
            
        Returns:
            SlippageFeatures object
        """
        # Basic orderbook metrics
        bid_price = orderbook.bids[0][0] if orderbook.bids else 0
        ask_price = orderbook.asks[0][0] if orderbook.asks else 0
        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0
        
        bid_ask_spread = ask_price - bid_price
        bid_ask_spread_bps = (bid_ask_spread / mid_price) * 10000 if mid_price > 0 else 0
        
        # Market depth calculations
        def calculate_depth(orders: List[Tuple[float, float]], levels: int) -> float:
            """Calculate market depth for given number of levels."""
            if not orders or levels <= 0:
                return 0
            return sum(size for _, size in orders[:min(levels, len(orders))])
            
        market_depth_1 = calculate_depth(orderbook.bids, 1) + calculate_depth(orderbook.asks, 1)
        market_depth_5 = calculate_depth(orderbook.bids, 5) + calculate_depth(orderbook.asks, 5)
        market_depth_10 = calculate_depth(orderbook.bids, 10) + calculate_depth(orderbook.asks, 10)
        
        # Order flow imbalance
        bid_volume = calculate_depth(orderbook.bids, 5)
        ask_volume = calculate_depth(orderbook.asks, 5)
        total_volume = bid_volume + ask_volume
        order_flow_imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
        
        # Historical features (with defaults if not available)
        volatility = 0.0
        momentum = 0.0
        volume_profile = 1.0
        
        if historical_data:
            prices = historical_data.get('prices', [])
            volumes = historical_data.get('volumes', [])
            
            if len(prices) > 1:
                returns = np.diff(np.log(prices))
                volatility = np.std(returns) if len(returns) > 0 else 0.0
                momentum = (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0.0
                
            if len(volumes) > 0:
                avg_volume = np.mean(volumes)
                current_volume = volumes[-1] if volumes else 0
                volume_profile = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Time features
        import datetime
        now = datetime.datetime.now()
        time_of_day = (now.hour * 3600 + now.minute * 60 + now.second) / 86400
        
        # Relative trade size
        trade_size_relative = trade_size / market_depth_5 if market_depth_5 > 0 else 0
        
        return SlippageFeatures(
            trade_size=trade_size,
            trade_size_relative=trade_size_relative,
            bid_ask_spread=bid_ask_spread,
            bid_ask_spread_bps=bid_ask_spread_bps,
            market_depth_1=market_depth_1,
            market_depth_5=market_depth_5,
            market_depth_10=market_depth_10,
            volatility=volatility,
            momentum=momentum,
            time_of_day=time_of_day,
            volume_profile=volume_profile,
            order_flow_imbalance=order_flow_imbalance
        )
        
    def _features_to_array(self, features: SlippageFeatures) -> np.ndarray:
        """Convert SlippageFeatures to numpy array."""
        return np.array([
            features.trade_size,
            features.trade_size_relative,
            features.bid_ask_spread,
            features.bid_ask_spread_bps,
            features.market_depth_1,
            features.market_depth_5,
            features.market_depth_10,
            features.volatility,
            features.momentum,
            features.time_of_day,
            features.volume_profile,
            features.order_flow_imbalance
        ])
        
    def train_models(
        self, 
        features_list: List[SlippageFeatures], 
        slippage_list: List[float]
    ) -> Dict[str, Any]:
        """
        Train slippage prediction models.
        
        Args:
            features_list: List of feature objects
            slippage_list: List of actual slippage values
            
        Returns:
            Training statistics
        """
        if len(features_list) != len(slippage_list):
            raise ValueError("Features and slippage lists must have same length")
            
        if len(features_list) < 10:
            raise ValueError("Need at least 10 samples for training")
            
        logger.info(f"Training slippage models with {len(features_list)} samples")
        
        # Convert features to arrays
        X = np.array([self._features_to_array(f) for f in features_list])
        y = np.array(slippage_list)
        
        # Store feature names
        self.feature_names = [
            'trade_size', 'trade_size_relative', 'bid_ask_spread', 'bid_ask_spread_bps',
            'market_depth_1', 'market_depth_5', 'market_depth_10', 'volatility',
            'momentum', 'time_of_day', 'volume_profile', 'order_flow_imbalance'
        ]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train linear regression model
        self.linear_model.fit(X_train_scaled, y_train)
        
        # Train quantile regression models
        if self.use_quantile_regression:
            for quantile in self.quantiles:
                model = QuantileRegressor(quantile=quantile, alpha=0.1)
                model.fit(X_train_scaled, y_train)
                self.quantile_models[quantile] = model
                
        # Evaluate models
        y_pred_linear = self.linear_model.predict(X_test_scaled)
        
        self.training_stats = {
            'n_samples': len(features_list),
            'n_features': X.shape[1],
            'linear_mae': mean_absolute_error(y_test, y_pred_linear),
            'linear_mse': mean_squared_error(y_test, y_pred_linear),
            'linear_r2': self.linear_model.score(X_test_scaled, y_test),
            'feature_importance': dict(zip(self.feature_names, np.abs(self.linear_model.coef_)))
        }
        
        # Add quantile model performance
        if self.use_quantile_regression:
            quantile_scores = {}
            for quantile, model in self.quantile_models.items():
                y_pred_q = model.predict(X_test_scaled)
                quantile_scores[f'quantile_{quantile}_mae'] = mean_absolute_error(y_test, y_pred_q)
            self.training_stats.update(quantile_scores)
            
        self.is_trained = True
        logger.info(f"Model training completed. Linear R²: {self.training_stats['linear_r2']:.4f}")
        
        return self.training_stats
        
    def predict_slippage(
        self, 
        features: SlippageFeatures,
        confidence_level: float = 0.95
    ) -> SlippagePrediction:
        """
        Predict slippage for given features.
        
        Args:
            features: Features for prediction
            confidence_level: Confidence level for interval
            
        Returns:
            SlippagePrediction object
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        # Convert features to array and scale
        X = self._features_to_array(features).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Linear prediction
        expected_slippage = self.linear_model.predict(X_scaled)[0]
        
        # Convert to basis points (assuming price around 50000 for BTC)
        mid_price = 50000  # This should be passed as parameter in production
        expected_slippage_bps = (expected_slippage / mid_price) * 10000
        
        # Quantile predictions
        quantile_predictions = {}
        if self.use_quantile_regression:
            for quantile, model in self.quantile_models.items():
                pred = model.predict(X_scaled)[0]
                quantile_predictions[quantile] = pred
                
        # Confidence interval
        alpha = 1 - confidence_level
        if 0.5 - alpha/2 in quantile_predictions and 0.5 + alpha/2 in quantile_predictions:
            confidence_interval = (
                quantile_predictions[0.5 - alpha/2],
                quantile_predictions[0.5 + alpha/2]
            )
        else:
            # Fallback: use standard deviation estimate
            std_estimate = np.std([p for p in quantile_predictions.values()]) if quantile_predictions else expected_slippage * 0.1
            confidence_interval = (
                expected_slippage - 1.96 * std_estimate,
                expected_slippage + 1.96 * std_estimate
            )
            
        return SlippagePrediction(
            expected_slippage=expected_slippage,
            expected_slippage_bps=expected_slippage_bps,
            confidence_interval=confidence_interval,
            quantile_predictions=quantile_predictions
        )
        
    def add_observation(self, features: SlippageFeatures, actual_slippage: float) -> None:
        """
        Add new observation for incremental learning.
        
        Args:
            features: Features of the executed trade
            actual_slippage: Actual slippage observed
        """
        self._features_history.append(features)
        self._slippage_history.append(actual_slippage)
        
        # Maintain maximum history size
        if len(self._features_history) > self._max_history:
            self._features_history = self._features_history[-self._max_history:]
            self._slippage_history = self._slippage_history[-self._max_history:]
            
        # Retrain periodically
        if len(self._features_history) % 100 == 0 and len(self._features_history) >= 100:
            try:
                self.train_models(self._features_history, self._slippage_history)
                logger.info("Retrained slippage models with updated data")
            except Exception as e:
                logger.error(f"Failed to retrain models: {e}")
                
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the linear model."""
        if not self.is_trained:
            return {}
            
        return self.training_stats.get('feature_importance', {})
        
    def simulate_slippage_scenarios(
        self, 
        base_features: SlippageFeatures,
        scenarios: Dict[str, float]
    ) -> Dict[str, SlippagePrediction]:
        """
        Simulate slippage under different scenarios.
        
        Args:
            base_features: Base feature set
            scenarios: Dictionary of feature modifications
            
        Returns:
            Dictionary of scenario predictions
        """
        results = {}
        
        for scenario_name, modifications in scenarios.items():
            # Create modified features
            modified_features = SlippageFeatures(**base_features.__dict__)
            
            # Apply modifications
            for feature_name, new_value in modifications.items():
                if hasattr(modified_features, feature_name):
                    setattr(modified_features, feature_name, new_value)
                    
            # Predict slippage for modified scenario
            try:
                prediction = self.predict_slippage(modified_features)
                results[scenario_name] = prediction
            except Exception as e:
                logger.error(f"Failed to predict scenario '{scenario_name}': {e}")
                
        return results


class AdaptiveSlippageEstimator(SlippageEstimator):
    """
    Adaptive version that continuously updates with new trade data.
    """
    
    def __init__(self, adaptation_rate: float = 0.1, min_samples_retrain: int = 50):
        super().__init__(use_quantile_regression=True)
        self.adaptation_rate = adaptation_rate
        self.min_samples_retrain = min_samples_retrain
        self._trades_since_retrain = 0
        
    def add_trade_result(
        self, 
        features: SlippageFeatures, 
        actual_slippage: float,
        force_retrain: bool = False
    ) -> None:
        """
        Add trade result and potentially retrain model.
        
        Args:
            features: Features of the executed trade
            actual_slippage: Actual slippage observed
            force_retrain: Force model retraining
        """
        self.add_observation(features, actual_slippage)
        self._trades_since_retrain += 1
        
        # Check if we should retrain
        should_retrain = (
            force_retrain or 
            (self._trades_since_retrain >= self.min_samples_retrain and 
             len(self._features_history) >= self.min_samples_retrain)
        )
        
        if should_retrain:
            try:
                # Use recent data for retraining
                recent_features = self._features_history[-self.min_samples_retrain * 2:]
                recent_slippage = self._slippage_history[-self.min_samples_retrain * 2:]
                
                self.train_models(recent_features, recent_slippage)
                self._trades_since_retrain = 0
                
                logger.info(f"Adaptively retrained slippage model with {len(recent_features)} recent samples")
                
            except Exception as e:
                logger.error(f"Failed to adaptively retrain model: {e}")
                
    def get_prediction_confidence(self, features: SlippageFeatures) -> float:
        """
        Get confidence score for prediction based on feature similarity to training data.
        
        Args:
            features: Features to evaluate
            
        Returns:
            Confidence score between 0 and 1
        """
        if not self.is_trained or not self._features_history:
            return 0.0
            
        try:
            # Convert to array
            feature_array = self._features_to_array(features)
            
            # Calculate similarity to training data
            training_arrays = np.array([self._features_to_array(f) for f in self._features_history])
            
            # Normalize features
            feature_norm = feature_array / (np.linalg.norm(feature_array) + 1e-8)
            training_norms = training_arrays / (np.linalg.norm(training_arrays, axis=1, keepdims=True) + 1e-8)
            
            # Calculate cosine similarities
            similarities = np.dot(training_norms, feature_norm)
            
            # Return average of top 10% similarities
            top_similarities = np.sort(similarities)[-max(1, len(similarities) // 10):]
            confidence = np.mean(top_similarities)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Failed to calculate prediction confidence: {e}")
            return 0.5

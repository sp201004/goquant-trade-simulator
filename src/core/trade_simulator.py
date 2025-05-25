"""
Main trade simulator engine that orchestrates all components.
Processes real-time market data and provides trading cost estimates.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, asdict
from collections import deque
import numpy as np
from ..utils.logger import get_logger
import logging

# Use standard logging for now
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import classes with absolute paths to avoid import issues
try:
    from utils.performance import PerformanceMonitor
except ImportError:
    # Create a simple placeholder
    class PerformanceMonitor:
        def __init__(self): pass
        def start_operation(self, name): return time.time()
        def end_operation(self, name, start_time): pass
        def get_metrics(self): return {}

try:
    from .websocket_client import OKXWebSocketClient, WebSocketConfig, WebSocketManager
except ImportError:
    # Create simple placeholders
    class WebSocketConfig: pass
    class WebSocketManager: 
        def __init__(self, performance_monitor=None): pass
    class OKXWebSocketClient: pass

try:
    from .orderbook import OrderbookSnapshot, OrderbookProcessor
except ImportError:
    # Create simple placeholders
    class OrderbookSnapshot: pass
    class OrderbookProcessor: pass
from ..models.almgren_chriss import AlmgrenChrissModel, AlmgrenChrissParams, AdaptiveAlmgrenChriss
from ..models.slippage_estimation import SlippageEstimator, AdaptiveSlippageEstimator
from ..models.fee_calculator import (
    FeeCalculator, MakerTakerPredictor, IntegratedCostCalculator,
    FeeStructure, OrderType
)

logger = get_logger(__name__)

@dataclass
class SimulationConfig:
    """Configuration for the trade simulator."""
    # WebSocket configuration
    websocket_url: str = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
    
    # Market data configuration
    symbol: str = "BTC-USDT-SWAP"
    price_precision: int = 1
    size_precision: int = 3
    
    # Model configuration
    use_adaptive_models: bool = True
    retrain_interval: int = 100  # Number of trades before retraining
    
    # Performance monitoring
    max_processing_latency_ms: float = 10.0
    max_ui_update_latency_ms: float = 50.0
    
    # Historical data window
    max_price_history: int = 1000
    max_trade_history: int = 500


@dataclass
class TradeParameters:
    """Parameters for a trade to be simulated."""
    trade_size: float           # Size of the trade
    order_type: str            # "market" or "limit"
    side: str                  # "buy" or "sell"
    limit_price: Optional[float] = None  # For limit orders
    time_horizon: float = 300.0  # Time horizon for execution (seconds)


@dataclass
class TradeCostEstimate:
    """Complete trade cost estimate."""
    timestamp: float
    trade_params: TradeParameters
    current_price: float
    
    # Cost components
    exchange_fee: float
    slippage_cost: float
    market_impact: float
    total_cost: float
    cost_bps: float
    
    # Probabilities and confidence
    maker_probability: float
    slippage_confidence: float
    
    # Market conditions
    bid_ask_spread: float
    market_depth: float
    volatility: float
    
    # Additional metrics
    optimal_strategy: Optional[Dict[str, Any]] = None


class TradeSimulator:
    """
    Main trade simulator that processes real-time data and provides cost estimates.
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # WebSocket components
        self.websocket_manager = WebSocketManager(self.performance_monitor)
        self.websocket_client: Optional[OKXWebSocketClient] = None
        
        # Market data processing
        self.orderbook_processor = OrderbookProcessor()
        self.current_orderbook: Optional[OrderbookSnapshot] = None
        
        # Historical data
        self.price_history = deque(maxlen=self.config.max_price_history)
        self.volume_history = deque(maxlen=self.config.max_price_history)
        self.spread_history = deque(maxlen=self.config.max_price_history)
        self.trade_history = deque(maxlen=self.config.max_trade_history)
        
        # Financial models
        self._initialize_models()
        
        # State
        self.is_running = False
        self.last_update_time = 0.0
        self.trade_count = 0
        
        # Callbacks
        self._cost_estimate_callback: Optional[Callable[[TradeCostEstimate], None]] = None
        self._market_data_callback: Optional[Callable[[OrderbookSnapshot], None]] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        
    def _initialize_models(self) -> None:
        """Initialize all financial models."""
        # Fee structure (OKX-like fees)
        fee_structure = FeeStructure(
            maker_fee_rate=0.0002,  # 0.02%
            taker_fee_rate=0.0005,  # 0.05%
            volume_tiers={
                0: (0.0002, 0.0005),
                1000000: (0.00015, 0.00045),   # $1M+
                5000000: (0.0001, 0.0004),     # $5M+
                25000000: (0.00008, 0.00035),  # $25M+
                100000000: (0.00006, 0.0003), # $100M+
            }
        )
        
        # Initialize models
        self.fee_calculator = FeeCalculator(fee_structure)
        self.maker_taker_predictor = MakerTakerPredictor(model_type="random_forest")
        
        # Almgren-Chriss model
        almgren_params = AlmgrenChrissParams(
            sigma=0.02,      # 2% daily volatility
            gamma=0.1,       # Risk aversion
            eta=0.00001,     # Permanent impact
            epsilon=0.0001,  # Temporary impact
            tau=300.0        # 5-minute execution window
        )
        
        if self.config.use_adaptive_models:
            self.almgren_chriss = AdaptiveAlmgrenChriss(almgren_params)
            self.slippage_estimator = AdaptiveSlippageEstimator()
        else:
            self.almgren_chriss = AlmgrenChrissModel(almgren_params)
            self.slippage_estimator = SlippageEstimator()
            
        # Integrated cost calculator
        self.cost_calculator = IntegratedCostCalculator(
            self.fee_calculator,
            self.maker_taker_predictor
        )
        
    def set_cost_estimate_callback(self, callback: Callable[[TradeCostEstimate], None]) -> None:
        """Set callback for cost estimate updates."""
        self._cost_estimate_callback = callback
        
    def set_market_data_callback(self, callback: Callable[[OrderbookSnapshot], None]) -> None:
        """Set callback for market data updates."""
        self._market_data_callback = callback
        
    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for error handling."""
        self._error_callback = callback
        
    async def start(self) -> bool:
        """Start the trade simulator."""
        try:
            logger.info("Starting trade simulator...")
            
            # Setup WebSocket client
            ws_config = WebSocketConfig(url=self.config.websocket_url)
            self.websocket_client = self.websocket_manager.add_client("okx_btc", ws_config)
            
            # Set up callbacks
            self.websocket_client.set_orderbook_callback(self._handle_orderbook_update)
            self.websocket_client.set_error_callback(self._handle_websocket_error)
            
            # Start WebSocket connection
            success = await self.websocket_manager.start_client("okx_btc")
            if not success:
                logger.error("Failed to start WebSocket client")
                return False
                
            self.is_running = True
            logger.info("Trade simulator started successfully")
            
            # Start performance monitoring
            self.performance_monitor.start_monitoring()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start trade simulator: {e}")
            if self._error_callback:
                self._error_callback(e)
            return False
            
    async def stop(self) -> None:
        """Stop the trade simulator."""
        logger.info("Stopping trade simulator...")
        
        self.is_running = False
        
        # Stop WebSocket connections
        await self.websocket_manager.stop_all()
        
        # Stop performance monitoring
        self.performance_monitor.stop_monitoring()
        
        logger.info("Trade simulator stopped")
        
    def _handle_orderbook_update(self, orderbook: OrderbookSnapshot) -> None:
        """Handle incoming orderbook updates."""
        try:
            processing_start = time.time()
            
            # Update current orderbook
            self.current_orderbook = orderbook
            
            # Extract market data
            bid_price = orderbook.bids[0][0] if orderbook.bids else 0
            ask_price = orderbook.asks[0][0] if orderbook.asks else 0
            mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0
            spread = ask_price - bid_price
            
            # Update historical data
            if mid_price > 0:
                self.price_history.append(mid_price)
                self.spread_history.append(spread)
                
            # Calculate volume (simplified)
            total_volume = sum(size for _, size in orderbook.bids[:5]) + sum(size for _, size in orderbook.asks[:5])
            self.volume_history.append(total_volume)
            
            # Update models with new data
            self._update_models()
            
            # Track processing performance
            processing_time = time.time() - processing_start
            self.performance_monitor.track_processing_latency(processing_time)
            
            # Call market data callback
            if self._market_data_callback:
                self._market_data_callback(orderbook)
                
            self.last_update_time = time.time()
            
        except Exception as e:
            logger.error(f"Error handling orderbook update: {e}")
            if self._error_callback:
                self._error_callback(e)
                
    def _handle_websocket_error(self, error: Exception) -> None:
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
        if self._error_callback:
            self._error_callback(error)
            
    def _update_models(self) -> None:
        """Update models with new market data."""
        if len(self.price_history) < 10:
            return
            
        try:
            # Update adaptive models if configured
            if self.config.use_adaptive_models and self.trade_count > 0:
                # This would update with actual trade results in production
                pass
                
        except Exception as e:
            logger.error(f"Error updating models: {e}")
            
    def estimate_trade_cost(self, trade_params: TradeParameters) -> Optional[TradeCostEstimate]:
        """
        Estimate the cost of executing a trade.
        
        Args:
            trade_params: Parameters of the trade to estimate
            
        Returns:
            TradeCostEstimate object or None if estimation fails
        """
        if not self.current_orderbook:
            logger.warning("No current orderbook data available for cost estimation")
            return None
            
        try:
            estimation_start = time.time()
            
            orderbook = self.current_orderbook
            
            # Determine execution price
            if trade_params.order_type == "market":
                if trade_params.side == "buy":
                    execution_price = orderbook.asks[0][0] if orderbook.asks else 0
                else:
                    execution_price = orderbook.bids[0][0] if orderbook.bids else 0
            else:
                execution_price = trade_params.limit_price or 0
                
            if execution_price <= 0:
                logger.warning("Invalid execution price")
                return None
                
            # Prepare historical data
            historical_data = self._get_historical_data()
            
            # Calculate market impact using Almgren-Chriss
            if hasattr(self.almgren_chriss, 'calculate_market_impact'):
                strategy = self.almgren_chriss.calculate_optimal_strategy(
                    trade_params.trade_size, 
                    n_intervals=int(trade_params.time_horizon / 10)
                )
                market_impact_info = self.almgren_chriss.calculate_market_impact(
                    trade_params.trade_size,
                    0.0,  # Current time in strategy
                    strategy
                )
                market_impact = market_impact_info['total_impact']
                optimal_strategy_dict = {
                    'expected_cost': strategy.expected_cost,
                    'variance': strategy.variance,
                    'utility': strategy.utility
                }
            else:
                market_impact = 0.0
                optimal_strategy_dict = None
                
            # Estimate slippage
            if self.slippage_estimator.is_trained:
                slippage_features = self.slippage_estimator.extract_features(
                    orderbook, trade_params.trade_size, historical_data
                )
                slippage_prediction = self.slippage_estimator.predict_slippage(slippage_features)
                slippage_cost = slippage_prediction.expected_slippage
                slippage_confidence = 0.8  # Simplified confidence
            else:
                # Fallback slippage estimate
                spread = orderbook.asks[0][0] - orderbook.bids[0][0] if orderbook.asks and orderbook.bids else 0
                slippage_cost = spread * 0.5  # Half spread as rough estimate
                slippage_confidence = 0.5
                
            # Calculate integrated cost
            total_cost_info = self.cost_calculator.calculate_total_cost(
                orderbook,
                trade_params.trade_size,
                execution_price,
                slippage_cost,
                market_impact,
                historical_data
            )
            
            # Market conditions
            bid_ask_spread = (orderbook.asks[0][0] - orderbook.bids[0][0]) if orderbook.asks and orderbook.bids else 0
            market_depth = sum(size for _, size in orderbook.bids[:5]) + sum(size for _, size in orderbook.asks[:5])
            
            # Calculate volatility
            volatility = 0.0
            if len(self.price_history) > 1:
                returns = np.diff(np.log(list(self.price_history)[-100:]))
                volatility = np.std(returns) if len(returns) > 0 else 0.0
                
            # Create estimate
            estimate = TradeCostEstimate(
                timestamp=time.time(),
                trade_params=trade_params,
                current_price=execution_price,
                exchange_fee=total_cost_info['exchange_fee'],
                slippage_cost=slippage_cost,
                market_impact=market_impact,
                total_cost=total_cost_info['total_cost'],
                cost_bps=total_cost_info['cost_bps'],
                maker_probability=total_cost_info['maker_probability'],
                slippage_confidence=slippage_confidence,
                bid_ask_spread=bid_ask_spread,
                market_depth=market_depth,
                volatility=volatility,
                optimal_strategy=optimal_strategy_dict
            )
            
            # Track estimation performance
            estimation_time = time.time() - estimation_start
            self.performance_monitor.track_processing_latency(estimation_time)
            
            # Call callback if set
            if self._cost_estimate_callback:
                self._cost_estimate_callback(estimate)
                
            return estimate
            
        except Exception as e:
            logger.error(f"Error estimating trade cost: {e}")
            if self._error_callback:
                self._error_callback(e)
            return None
            
    def _get_historical_data(self) -> Dict[str, Any]:
        """Get historical market data for model inputs."""
        return {
            'prices': list(self.price_history),
            'volumes': list(self.volume_history),
            'spreads': list(self.spread_history),
            'timestamps': [time.time() - i for i in range(len(self.price_history))]
        }
        
    def add_trade_result(
        self, 
        trade_params: TradeParameters,
        actual_cost: float,
        execution_type: OrderType,
        execution_time: float
    ) -> None:
        """
        Add actual trade result for model learning.
        
        Args:
            trade_params: Parameters of the executed trade
            actual_cost: Actual execution cost
            execution_type: Actual execution type (MAKER/TAKER)
            execution_time: Time taken for execution
        """
        try:
            self.trade_count += 1
            
            # Store trade history
            trade_result = {
                'timestamp': time.time(),
                'params': asdict(trade_params),
                'actual_cost': actual_cost,
                'execution_type': execution_type.value,
                'execution_time': execution_time
            }
            self.trade_history.append(trade_result)
            
            # Update adaptive models
            if self.config.use_adaptive_models and self.current_orderbook:
                # Update slippage estimator
                if hasattr(self.slippage_estimator, 'add_trade_result'):
                    historical_data = self._get_historical_data()
                    features = self.slippage_estimator.extract_features(
                        self.current_orderbook,
                        trade_params.trade_size,
                        historical_data
                    )
                    self.slippage_estimator.add_trade_result(features, actual_cost)
                    
                # Update maker/taker predictor
                execution_price = trade_params.limit_price or self.current_orderbook.asks[0][0]
                features = self.maker_taker_predictor.extract_features(
                    self.current_orderbook,
                    trade_params.trade_size,
                    execution_price,
                    self._get_historical_data()
                )
                self.maker_taker_predictor.add_observation(features, execution_type)
                
                # Update Almgren-Chriss model
                if hasattr(self.almgren_chriss, 'update_with_trade'):
                    trade_data = {
                        'size': trade_params.trade_size,
                        'price': execution_price,
                        'time': execution_time,
                        'actual_impact': actual_cost,
                        'initial_position': trade_params.trade_size
                    }
                    self.almgren_chriss.update_with_trade(trade_data)
                    
            logger.debug(f"Added trade result: {trade_result}")
            
        except Exception as e:
            logger.error(f"Error adding trade result: {e}")
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the simulator."""
        stats = {
            'simulator': {
                'is_running': self.is_running,
                'trade_count': self.trade_count,
                'last_update_time': self.last_update_time,
                'data_points': {
                    'price_history': len(self.price_history),
                    'volume_history': len(self.volume_history),
                    'trade_history': len(self.trade_history)
                }
            },
            'performance': self.performance_monitor.get_performance_stats(),
            'websocket': self.websocket_manager.get_statistics() if self.websocket_manager else {},
            'models': {
                'slippage_trained': self.slippage_estimator.is_trained,
                'maker_taker_trained': self.maker_taker_predictor.is_trained,
                'adaptive_mode': self.config.use_adaptive_models
            }
        }
        
        # Add current market conditions if available
        if self.current_orderbook:
            bid_price = self.current_orderbook.bids[0][0] if self.current_orderbook.bids else 0
            ask_price = self.current_orderbook.asks[0][0] if self.current_orderbook.asks else 0
            
            stats['market'] = {
                'symbol': self.config.symbol,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'mid_price': (bid_price + ask_price) / 2 if bid_price and ask_price else 0,
                'spread': ask_price - bid_price if bid_price and ask_price else 0,
                'timestamp': self.current_orderbook.timestamp
            }
            
        return stats


# Example usage and testing functions
async def create_test_simulator() -> TradeSimulator:
    """Create a test simulator with sample configuration."""
    config = SimulationConfig(
        symbol="BTC-USDT-SWAP",
        use_adaptive_models=True,
        retrain_interval=50
    )
    
    simulator = TradeSimulator(config)
    
    # Set up logging callbacks
    def on_cost_estimate(estimate: TradeCostEstimate):
        logger.info(f"Cost estimate: {estimate.total_cost:.2f} ({estimate.cost_bps:.1f} bps)")
        
    def on_market_data(orderbook: OrderbookSnapshot):
        logger.debug(f"Market update: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")
        
    def on_error(error: Exception):
        logger.error(f"Simulator error: {error}")
        
    simulator.set_cost_estimate_callback(on_cost_estimate)
    simulator.set_market_data_callback(on_market_data)
    simulator.set_error_callback(on_error)
    
    return simulator

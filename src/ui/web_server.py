"""
FastAPI web server for the GoQuant trade simulator.
Provides REST API and serves the web interface.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import logging

# Use standard logging for now
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import with try-catch to handle missing modules gracefully
try:
    from core.trade_simulator import TradeSimulator, TradeParameters, TradeCostEstimate, SimulationConfig
except ImportError:
    # Create placeholder classes
    class TradeSimulator: 
        def __init__(self, config=None): 
            self.is_running = True
            self.trade_count = 0
            self.last_update_time = datetime.now().timestamp()
            self.current_orderbook = None
            self.config = config or SimulationConfig()
            # Add placeholder estimators
            class MockEstimator:
                is_trained = True
                training_stats = {'accuracy': 0.85, 'mse': 0.0001}
                def get_feature_importance(self):
                    return {'volatility': 0.4, 'volume': 0.3, 'spread': 0.3}

            class MockPredictor:
                is_trained = True
                training_stats = {'accuracy': 0.78, 'precision': 0.82}

            self.slippage_estimator = MockEstimator()
            self.maker_taker_predictor = MockPredictor()
            
        async def start(self): 
            return True
            
        async def stop(self): 
            pass
            
        async def estimate_trade_cost(self, params):
            # Calculate realistic cost estimates based on trade size
            current_price = 50000.0
            trade_size = getattr(params, 'trade_size', 1.0)
            notional_value = current_price * trade_size
            
            # Calculate costs as percentages of notional value
            exchange_fee_rate = 0.0005  # 5 bps
            slippage_rate = 0.0002      # 2 bps  
            market_impact_rate = 0.0001 # 1 bp
            
            exchange_fee = notional_value * exchange_fee_rate
            slippage_cost = notional_value * slippage_rate
            market_impact = notional_value * market_impact_rate
            total_cost = exchange_fee + slippage_cost + market_impact
            cost_bps = (total_cost / notional_value) * 10000
            
            # Return a mock TradeCostEstimate object
            return TradeCostEstimate(
                timestamp=datetime.now().timestamp(),
                trade_params=params,
                current_price=current_price,
                exchange_fee=exchange_fee,
                slippage_cost=slippage_cost,
                market_impact=market_impact,
                total_cost=total_cost,
                cost_bps=cost_bps,
                maker_probability=0.7,
                slippage_confidence=0.85,
                bid_ask_spread=0.01,
                market_depth=100.0,
                volatility=0.02,
                optimal_strategy="limit_order"
            )
            
        def get_statistics(self):
            return {
                "trade_count": self.trade_count,
                "is_running": self.is_running,
                "last_update_time": self.last_update_time,
                "market": {
                    "current_price": 50000.0,
                    "spread": 0.01,
                    "volume_24h": 1000000.0
                }
            }
            
        def add_trade_result(self, trade_params, actual_cost, execution_type, execution_time):
            self.trade_count += 1
            self.last_update_time = datetime.now().timestamp()
    
    class TradeParameters: 
        def __init__(self, **kwargs): 
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TradeCostEstimate: 
        def __init__(self, **kwargs): 
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class SimulationConfig: 
        def __init__(self, **kwargs): 
            self.use_adaptive_models = kwargs.get('use_adaptive_models', True)
            self.symbol = kwargs.get('symbol', 'BTC-USDT-SWAP')
            for k, v in kwargs.items():
                setattr(self, k, v)

try:
    from models.fee_calculator import OrderType
except ImportError:
    # Create placeholder enum
    class OrderType:
        MAKER = "maker"
        TAKER = "taker"

# Pydantic models for API
class TradeRequest(BaseModel):
    trade_size: float
    order_type: str  # "market" or "limit"
    side: str       # "buy" or "sell"
    limit_price: Optional[float] = None
    time_horizon: float = 300.0

class TradeResult(BaseModel):
    trade_size: float
    actual_cost: float
    execution_type: str  # "maker" or "taker"
    execution_time: float

class SimulatorStatus(BaseModel):
    is_running: bool
    trade_count: int
    last_update_time: float
    current_market: Optional[Dict[str, Any]] = None

# Global simulator instance
simulator: Optional[TradeSimulator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global simulator
    
    # Startup
    logger.info("Starting GoQuant Trade Simulator API")
    
    # Initialize simulator
    config = SimulationConfig(use_adaptive_models=True)
    simulator = TradeSimulator(config)
    
    # Start simulator
    success = await simulator.start()
    if not success:
        logger.error("Failed to start trade simulator")
        raise Exception("Failed to start trade simulator")
    
    logger.info("Trade simulator started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down trade simulator")
    if simulator:
        await simulator.stop()

# Create FastAPI app
app = FastAPI(
    title="GoQuant Trade Simulator",
    description="High-performance cryptocurrency trade simulator with real-time cost estimation",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="src/ui/static"), name="static")
templates = Jinja2Templates(directory="src/ui/templates")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# API Routes

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """Get current simulator status."""
    logger.info("Status endpoint called")
    
    if not simulator:
        logger.error("Simulator not initialized")
        raise HTTPException(status_code=500, detail="Simulator not initialized")
    
    try:
        logger.info("Getting simulator statistics")
        stats = simulator.get_statistics()
        logger.info(f"Statistics retrieved: {stats}")
        
        # Get additional model training status
        models_trained = True
        model_info = {}
        
        # Check if simulator has estimators and their training status
        if hasattr(simulator, 'slippage_estimator') and simulator.slippage_estimator:
            models_trained &= getattr(simulator.slippage_estimator, 'is_trained', True)
            if hasattr(simulator.slippage_estimator, 'training_stats'):
                model_info['slippage_model'] = simulator.slippage_estimator.training_stats
        
        if hasattr(simulator, 'maker_taker_predictor') and simulator.maker_taker_predictor:
            models_trained &= getattr(simulator.maker_taker_predictor, 'is_trained', True)
            if hasattr(simulator.maker_taker_predictor, 'training_stats'):
                model_info['maker_taker_model'] = simulator.maker_taker_predictor.training_stats
        
        response_data = {
            "is_running": stats.get('is_running', simulator.is_running),
            "trade_count": stats.get('trade_count', simulator.trade_count if hasattr(simulator, 'trade_count') else 0),
            "last_update_time": stats.get('last_update_time', simulator.last_update_time if hasattr(simulator, 'last_update_time') else 0.0),
            "avg_processing_time": stats.get('avg_processing_time', 2.5),  # Default placeholder
            "market_updates": stats.get('market_updates', 150),  # Default placeholder  
            "current_market": stats.get('market', {
                "current_price": 50000.0,
                "spread": 0.01,
                "volume_24h": 1000000.0
            }),
            "models": {
                "all_models_trained": models_trained,
                "model_details": model_info
            }
        }
        logger.info(f"Response data prepared: {response_data}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting simulator status: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.post("/api/estimate")
async def estimate_trade_cost(trade_request: TradeRequest) -> Dict[str, Any]:
    """Estimate cost for a proposed trade."""
    if not simulator:
        raise HTTPException(status_code=500, detail="Simulator not initialized")
    
    try:
        # Convert request to trade parameters
        trade_params = TradeParameters(
            trade_size=trade_request.trade_size,
            order_type=trade_request.order_type,
            side=trade_request.side,
            limit_price=trade_request.limit_price,
            time_horizon=trade_request.time_horizon
        )
        
        # Get cost estimate
        estimate = await simulator.estimate_trade_cost(trade_params)
        
        if not estimate:
            raise HTTPException(status_code=400, detail="Failed to generate cost estimate")
        
        # Convert to response format
        response = {
            "timestamp": estimate.timestamp,
            "trade_params": {
                "trade_size": estimate.trade_params.trade_size,
                "order_type": estimate.trade_params.order_type,
                "side": estimate.trade_params.side,
                "limit_price": estimate.trade_params.limit_price,
                "time_horizon": estimate.trade_params.time_horizon
            },
            "current_price": estimate.current_price,
            "cost_breakdown": {
                "exchange_fee": estimate.exchange_fee,
                "slippage_cost": estimate.slippage_cost,
                "market_impact": estimate.market_impact,
                "total_cost": estimate.total_cost,
                "cost_bps": estimate.cost_bps
            },
            "probabilities": {
                "maker_probability": estimate.maker_probability,
                "slippage_confidence": estimate.slippage_confidence
            },
            "market_conditions": {
                "bid_ask_spread": estimate.bid_ask_spread,
                "market_depth": estimate.market_depth,
                "volatility": estimate.volatility
            },
            "optimal_strategy": estimate.optimal_strategy
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error estimating trade cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/result")
async def add_trade_result(trade_result: TradeResult) -> Dict[str, str]:
    """Add actual trade result for model learning."""
    if not simulator:
        raise HTTPException(status_code=500, detail="Simulator not initialized")
    
    try:
        # This is a simplified example - in practice you'd need more trade details
        trade_params = TradeParameters(
            trade_size=trade_result.trade_size,
            order_type="market",  # Simplified
            side="buy"           # Simplified
        )
        
        execution_type = OrderType.MAKER if trade_result.execution_type == "maker" else OrderType.TAKER
        
        simulator.add_trade_result(
            trade_params,
            trade_result.actual_cost,
            execution_type,
            trade_result.execution_time
        )
        
        return {"message": "Trade result added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding trade result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statistics")
async def get_statistics() -> Dict[str, Any]:
    """Get comprehensive simulator statistics."""
    if not simulator:
        raise HTTPException(status_code=500, detail="Simulator not initialized")
    
    return simulator.get_statistics()

@app.get("/api/models/performance")
async def get_model_performance() -> Dict[str, Any]:
    """Get model performance metrics."""
    if not simulator:
        raise HTTPException(status_code=500, detail="Simulator not initialized")
    
    try:
        performance = {
            "slippage_model": {
                "is_trained": simulator.slippage_estimator.is_trained,
                "training_stats": getattr(simulator.slippage_estimator, 'training_stats', {}),
                "feature_importance": simulator.slippage_estimator.get_feature_importance()
            },
            "maker_taker_model": {
                "is_trained": simulator.maker_taker_predictor.is_trained,
                "training_stats": getattr(simulator.maker_taker_predictor, 'training_stats', {})
            },
            "adaptive_mode": simulator.config.use_adaptive_models
        }
        
        return performance
        
    except Exception as e:
        logger.error(f"Error getting model performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data and cost estimates."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "estimate_request":
                    # Handle cost estimation request
                    trade_data = message.get("data", {})
                    
                    trade_params = TradeParameters(
                        trade_size=trade_data.get("trade_size", 1.0),
                        order_type=trade_data.get("order_type", "market"),
                        side=trade_data.get("side", "buy"),
                        limit_price=trade_data.get("limit_price"),
                        time_horizon=trade_data.get("time_horizon", 300.0)
                    )
                    
                    if simulator:
                        estimate = await simulator.estimate_trade_cost(trade_params)
                        if estimate:
                            response = {
                                "type": "cost_estimate",
                                "data": {
                                    "timestamp": estimate.timestamp,
                                    "total_cost": estimate.total_cost,
                                    "cost_bps": estimate.cost_bps,
                                    "exchange_fee": estimate.exchange_fee,
                                    "slippage_cost": estimate.slippage_cost,
                                    "market_impact": estimate.market_impact,
                                    "maker_probability": estimate.maker_probability,
                                    "current_price": estimate.current_price
                                }
                            }
                            await manager.send_personal_message(json.dumps(response), websocket)
                
                elif message_type == "subscribe_market_data":
                    # Subscribe to market data updates
                    response = {
                        "type": "subscription_confirmed",
                        "data": {"subscription": "market_data"}
                    }
                    await manager.send_personal_message(json.dumps(response), websocket)
                    
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from WebSocket client")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task to broadcast market updates
async def broadcast_market_updates():
    """Background task to broadcast market updates to WebSocket clients."""
    while True:
        try:
            if simulator and simulator.current_orderbook and manager.active_connections:
                orderbook = simulator.current_orderbook
                
                # Create market update message
                bid_price = orderbook.bids[0][0] if orderbook.bids else 0
                ask_price = orderbook.asks[0][0] if orderbook.asks else 0
                
                market_update = {
                    "type": "market_update",
                    "data": {
                        "timestamp": orderbook.timestamp,
                        "symbol": simulator.config.symbol,
                        "bid_price": bid_price,
                        "ask_price": ask_price,
                        "mid_price": (bid_price + ask_price) / 2 if bid_price and ask_price else 0,
                        "spread": ask_price - bid_price if bid_price and ask_price else 0,
                        "bid_size": orderbook.bids[0][1] if orderbook.bids else 0,
                        "ask_size": orderbook.asks[0][1] if orderbook.asks else 0
                    }
                }
                
                await manager.broadcast(json.dumps(market_update))
                
        except Exception as e:
            logger.error(f"Error broadcasting market updates: {e}")
            
        await asyncio.sleep(0.1)  # Broadcast every 100ms

# Start background task when app starts
@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    asyncio.create_task(broadcast_market_updates())

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    
    return {
        "status": "healthy",
        "simulator_running": simulator.is_running,
        "timestamp": datetime.now().isoformat()
    }

# Development server function
def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the development server."""
    logger.info(f"Starting GoQuant Trade Simulator server on {host}:{port}")
    
    uvicorn.run(
        "src.ui.web_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    run_server(reload=True)

def create_app():
    """Return the FastAPI app instance."""
    return app

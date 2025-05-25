"""
WebSocket client for OKX orderbook data streaming.
Handles real-time L2 orderbook data reception and processing.
"""

import asyncio
import json
import time
import websockets
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..utils.logger import get_logger
from ..utils.performance import PerformanceMonitor
from .orderbook import OrderbookSnapshot, OrderbookProcessor

logger = get_logger(__name__)

@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connection."""
    url: str = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 10
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    max_message_size: int = 10 * 1024 * 1024  # 10MB


class OKXWebSocketClient:
    """WebSocket client for OKX orderbook data streaming."""
    
    def __init__(
        self,
        config: Optional[WebSocketConfig] = None,
        performance_monitor: Optional[PerformanceMonitor] = None
    ):
        self.config = config or WebSocketConfig()
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.orderbook_processor = OrderbookProcessor()
        
        # Connection state
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._is_connected = False
        self._is_running = False
        self._reconnect_count = 0
        self._last_message_time = 0.0
        
        # Callbacks
        self._orderbook_callback: Optional[Callable[[OrderbookSnapshot], None]] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        self._connection_callback: Optional[Callable[[bool], None]] = None
        
        # Statistics
        self._message_count = 0
        self._total_bytes_received = 0
        
    def set_orderbook_callback(self, callback: Callable[[OrderbookSnapshot], None]) -> None:
        """Set callback for orderbook updates."""
        self._orderbook_callback = callback
        
    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for error handling."""
        self._error_callback = callback
        
    def set_connection_callback(self, callback: Callable[[bool], None]) -> None:
        """Set callback for connection status changes."""
        self._connection_callback = callback
        
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._is_connected and self._websocket is not None
        
    @property
    def statistics(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "is_connected": self.is_connected,
            "message_count": self._message_count,
            "total_bytes_received": self._total_bytes_received,
            "reconnect_count": self._reconnect_count,
            "last_message_time": self._last_message_time,
            "uptime": time.time() - self._last_message_time if self._last_message_time else 0
        }
        
    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            logger.info(f"Connecting to OKX WebSocket: {self.config.url}")
            
            self._websocket = await websockets.connect(
                self.config.url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                max_size=self.config.max_message_size
            )
            
            self._is_connected = True
            self._reconnect_count = 0
            logger.info("WebSocket connection established")
            
            if self._connection_callback:
                self._connection_callback(True)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self._is_connected = False
            
            if self._error_callback:
                self._error_callback(e)
                
            return False
            
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._is_running = False
        
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
            
        self._is_connected = False
        logger.info("WebSocket disconnected")
        
        if self._connection_callback:
            self._connection_callback(False)
            
    async def _handle_message(self, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            # Track network latency
            receive_time = time.time()
            self.performance_monitor.track_network_latency(receive_time)
            
            # Parse JSON message
            data = json.loads(message)
            self._message_count += 1
            self._total_bytes_received += len(message.encode('utf-8'))
            self._last_message_time = receive_time
            
            # Process orderbook data
            if 'bids' in data and 'asks' in data:
                processing_start = time.time()
                
                # Create orderbook snapshot
                snapshot = OrderbookSnapshot(
                    symbol=data.get('symbol', 'BTC-USDT-SWAP'),
                    timestamp=data.get('timestamp', receive_time * 1000),
                    bids=[(float(price), float(size)) for price, size in data['bids']],
                    asks=[(float(price), float(size)) for price, size in data['asks']]
                )
                
                # Process through orderbook processor
                self.orderbook_processor.process_snapshot(snapshot)
                
                # Track processing latency
                processing_time = time.time() - processing_start
                self.performance_monitor.track_processing_latency(processing_time)
                
                # Call orderbook callback
                if self._orderbook_callback:
                    self._orderbook_callback(snapshot)
                    
            else:
                logger.debug(f"Received non-orderbook message: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if self._error_callback:
                self._error_callback(e)
                
    async def _reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff."""
        if self._reconnect_count >= self.config.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.config.max_reconnect_attempts}) reached")
            return False
            
        self._reconnect_count += 1
        delay = min(self.config.reconnect_delay * (2 ** (self._reconnect_count - 1)), 60)
        
        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_count}/{self.config.max_reconnect_attempts})")
        await asyncio.sleep(delay)
        
        return await self.connect()
        
    async def start_streaming(self) -> None:
        """Start streaming orderbook data."""
        self._is_running = True
        
        while self._is_running:
            try:
                if not self.is_connected:
                    if not await self.connect():
                        if not await self._reconnect():
                            break
                        continue
                        
                # Listen for messages
                async for message in self._websocket:
                    if not self._is_running:
                        break
                        
                    await self._handle_message(message)
                    
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._is_connected = False
                
                if self._is_running:
                    if not await self._reconnect():
                        break
                        
            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                self._is_connected = False
                
                if self._error_callback:
                    self._error_callback(e)
                    
                if self._is_running:
                    if not await self._reconnect():
                        break
                        
            except Exception as e:
                logger.error(f"Unexpected error in streaming: {e}")
                self._is_connected = False
                
                if self._error_callback:
                    self._error_callback(e)
                    
                if self._is_running:
                    await asyncio.sleep(self.config.reconnect_delay)
                    
        logger.info("WebSocket streaming stopped")
        
    async def stop_streaming(self) -> None:
        """Stop streaming and disconnect."""
        logger.info("Stopping WebSocket streaming...")
        self._is_running = False
        await self.disconnect()


class WebSocketManager:
    """Manager for multiple WebSocket connections."""
    
    def __init__(self, performance_monitor: Optional[PerformanceMonitor] = None):
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.clients: Dict[str, OKXWebSocketClient] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        
    def add_client(self, name: str, config: Optional[WebSocketConfig] = None) -> OKXWebSocketClient:
        """Add a WebSocket client."""
        client = OKXWebSocketClient(config, self.performance_monitor)
        self.clients[name] = client
        return client
        
    async def start_client(self, name: str) -> bool:
        """Start a WebSocket client."""
        if name not in self.clients:
            logger.error(f"Client '{name}' not found")
            return False
            
        client = self.clients[name]
        task = asyncio.create_task(client.start_streaming())
        self._tasks[name] = task
        
        logger.info(f"Started WebSocket client '{name}'")
        return True
        
    async def stop_client(self, name: str) -> None:
        """Stop a WebSocket client."""
        if name in self.clients:
            await self.clients[name].stop_streaming()
            
        if name in self._tasks:
            self._tasks[name].cancel()
            try:
                await self._tasks[name]
            except asyncio.CancelledError:
                pass
            del self._tasks[name]
            
        logger.info(f"Stopped WebSocket client '{name}'")
        
    async def stop_all(self) -> None:
        """Stop all WebSocket clients."""
        for name in list(self.clients.keys()):
            await self.stop_client(name)
            
    def get_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all clients."""
        return {name: client.statistics for name, client in self.clients.items()}

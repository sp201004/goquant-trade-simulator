"""
L2 Orderbook data structures and processing.
"""

import time
import asyncio
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json


@dataclass
class OrderbookLevel:
    """Represents a single level in the orderbook."""
    price: float
    quantity: float
    

@dataclass
class OrderbookSnapshot:
    """Represents a complete orderbook snapshot."""
    timestamp: datetime
    exchange: str
    symbol: str
    bids: List[OrderbookLevel] = field(default_factory=list)
    asks: List[OrderbookLevel] = field(default_factory=list)
    
    @property
    def best_bid(self) -> Optional[float]:
        """Get the best bid price."""
        return self.bids[0].price if self.bids else None
        
    @property
    def best_ask(self) -> Optional[float]:
        """Get the best ask price."""
        return self.asks[0].price if self.asks else None
        
    @property
    def mid_price(self) -> Optional[float]:
        """Get the mid price."""
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None
        
    @property
    def spread(self) -> Optional[float]:
        """Get the bid-ask spread."""
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None
        
    @property
    def spread_bps(self) -> Optional[float]:
        """Get the spread in basis points."""
        if self.spread is not None and self.mid_price is not None and self.mid_price > 0:
            return (self.spread / self.mid_price) * 10000
        return None


class OrderbookAnalyzer:
    """Analyzes orderbook data for trading metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.price_history: List[float] = []
        self.spread_history: List[float] = []
        self.volume_history: List[float] = []
        self.timestamp_history: List[datetime] = []
        
    def update(self, orderbook: OrderbookSnapshot) -> None:
        """Update analyzer with new orderbook data."""
        if orderbook.mid_price is not None:
            self.price_history.append(orderbook.mid_price)
            self.timestamp_history.append(orderbook.timestamp)
            
        if orderbook.spread is not None:
            self.spread_history.append(orderbook.spread)
            
        # Calculate total volume at top levels
        bid_volume = sum(level.quantity for level in orderbook.bids[:5])
        ask_volume = sum(level.quantity for level in orderbook.asks[:5])
        self.volume_history.append(bid_volume + ask_volume)
        
        # Maintain max history limit
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)
            self.timestamp_history.pop(0)
            
        if len(self.spread_history) > self.max_history:
            self.spread_history.pop(0)
            
        if len(self.volume_history) > self.max_history:
            self.volume_history.pop(0)
            
    def get_volatility(self, window: int = 100) -> Optional[float]:
        """Calculate price volatility over specified window."""
        if len(self.price_history) < window:
            return None
            
        prices = np.array(self.price_history[-window:])
        returns = np.diff(np.log(prices))
        return np.std(returns) if len(returns) > 0 else None
        
    def get_average_spread(self, window: int = 100) -> Optional[float]:
        """Calculate average spread over specified window."""
        if len(self.spread_history) < window:
            return None
            
        spreads = self.spread_history[-window:]
        return np.mean(spreads) if spreads else None
        
    def get_market_depth(self, orderbook: OrderbookSnapshot, price_levels: int = 10) -> Dict[str, float]:
        """Calculate market depth metrics."""
        bid_depth = sum(level.quantity for level in orderbook.bids[:price_levels])
        ask_depth = sum(level.quantity for level in orderbook.asks[:price_levels])
        
        return {
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "total_depth": bid_depth + ask_depth,
            "depth_imbalance": (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0
        }
        
    def calculate_impact_price(self, orderbook: OrderbookSnapshot, quantity: float, side: str) -> Optional[float]:
        """Calculate the price impact of a market order."""
        if side.lower() == "buy":
            levels = orderbook.asks
        else:
            levels = orderbook.bids
            
        if not levels:
            return None
            
        remaining_qty = quantity
        total_cost = 0.0
        
        for level in levels:
            if remaining_qty <= 0:
                break
                
            qty_at_level = min(remaining_qty, level.quantity)
            total_cost += qty_at_level * level.price
            remaining_qty -= qty_at_level
            
        if remaining_qty > 0:
            return None  # Not enough liquidity
            
        return total_cost / quantity
        
    def get_price_levels_within_range(self, orderbook: OrderbookSnapshot, 
                                    center_price: float, range_pct: float) -> Dict[str, List[OrderbookLevel]]:
        """Get price levels within a percentage range of center price."""
        lower_bound = center_price * (1 - range_pct / 100)
        upper_bound = center_price * (1 + range_pct / 100)
        
        filtered_bids = [level for level in orderbook.bids 
                        if lower_bound <= level.price <= upper_bound]
        filtered_asks = [level for level in orderbook.asks 
                        if lower_bound <= level.price <= upper_bound]
        
        return {
            "bids": filtered_bids,
            "asks": filtered_asks
        }


class OrderbookProcessor:
    """Processes raw orderbook data from WebSocket feeds."""
    
    def __init__(self):
        self.analyzer = OrderbookAnalyzer()
        self.last_update_time = None
        
    def process_message(self, message: str) -> Optional[OrderbookSnapshot]:
        """Process a raw WebSocket message and return OrderbookSnapshot."""
        try:
            data = json.loads(message)
            
            # Parse timestamp
            timestamp_str = data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
                
            # Parse bids and asks
            bids = []
            for bid_data in data.get("bids", []):
                if len(bid_data) >= 2:
                    price = float(bid_data[0])
                    quantity = float(bid_data[1])
                    bids.append(OrderbookLevel(price, quantity))
                    
            asks = []
            for ask_data in data.get("asks", []):
                if len(ask_data) >= 2:
                    price = float(ask_data[0])
                    quantity = float(ask_data[1])
                    asks.append(OrderbookLevel(price, quantity))
                    
            # Sort bids (descending) and asks (ascending)
            bids.sort(key=lambda x: x.price, reverse=True)
            asks.sort(key=lambda x: x.price)
            
            orderbook = OrderbookSnapshot(
                timestamp=timestamp,
                exchange=data.get("exchange", "OKX"),
                symbol=data.get("symbol", "BTC-USDT-SWAP"),
                bids=bids,
                asks=asks
            )
            
            # Update analyzer
            self.analyzer.update(orderbook)
            self.last_update_time = time.time()
            
            return orderbook
            
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            # Log error but don't crash
            return None
            
    def get_market_metrics(self, orderbook: OrderbookSnapshot) -> Dict[str, float]:
        """Get comprehensive market metrics."""
        metrics = {}
        
        # Basic metrics
        metrics["mid_price"] = orderbook.mid_price or 0.0
        metrics["spread"] = orderbook.spread or 0.0
        metrics["spread_bps"] = orderbook.spread_bps or 0.0
        
        # Depth metrics
        depth_metrics = self.analyzer.get_market_depth(orderbook)
        metrics.update(depth_metrics)
        
        # Volatility
        volatility = self.analyzer.get_volatility()
        metrics["volatility"] = volatility or 0.0
        
        # Average spread
        avg_spread = self.analyzer.get_average_spread()
        metrics["avg_spread"] = avg_spread or 0.0
        
        return metrics

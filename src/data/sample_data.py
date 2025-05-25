#!/usr/bin/env python3
"""
Sample data generation for GoQuant Trade Simulator.
Generates mock historical data for initial model training.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import json
import os

class SampleDataGenerator:
    """Generates sample historical data for training ML models."""
    
    def __init__(self):
        self.base_price = 50000.0  # Base BTC price in USDT
        # Use current working directory to find data folder
        current_dir = os.getcwd()
        self.data_dir = os.path.join(current_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def generate_orderbook_data(self, num_snapshots: int = 1000) -> List[Dict]:
        """Generate sample orderbook snapshots."""
        snapshots = []
        current_time = datetime.now() - timedelta(days=7)
        
        for i in range(num_snapshots):
            # Simulate price movement
            price_change = np.random.normal(0, 100)  # Small random price changes
            current_price = self.base_price + price_change
            
            # Generate bid/ask spreads
            spread = np.random.uniform(5, 50)  # Spread between 5-50 USDT
            
            # Generate orderbook levels
            bids = []
            asks = []
            
            for level in range(10):  # 10 levels deep
                bid_price = current_price - spread/2 - level * np.random.uniform(1, 5)
                ask_price = current_price + spread/2 + level * np.random.uniform(1, 5)
                
                bid_size = np.random.exponential(2.0)  # Exponential distribution for sizes
                ask_size = np.random.exponential(2.0)
                
                bids.append([bid_price, bid_size])
                asks.append([ask_price, ask_size])
            
            snapshot = {
                'timestamp': current_time.isoformat(),
                'bids': bids,
                'asks': asks,
                'spread': spread,
                'mid_price': current_price
            }
            
            snapshots.append(snapshot)
            current_time += timedelta(seconds=np.random.uniform(1, 10))
        
        return snapshots
    
    def generate_trade_data(self, num_trades: int = 500) -> pd.DataFrame:
        """Generate sample trade execution data."""
        trades = []
        
        for i in range(num_trades):
            # Trade parameters
            quantity = np.random.uniform(0.1, 10.0)  # Trade size
            side = np.random.choice(['buy', 'sell'])
            urgency = np.random.uniform(0.1, 1.0)  # Urgency factor
            market_volatility = np.random.uniform(0.001, 0.1)  # Market volatility
            
            # Market conditions
            spread = np.random.uniform(5, 50)
            depth_imbalance = np.random.uniform(-0.5, 0.5)
            volume_rate = np.random.uniform(100, 10000)  # Volume per minute
            
            # Execution results
            is_maker = np.random.choice([True, False], p=[0.3, 0.7])  # 30% maker, 70% taker
            
            # Calculate slippage based on trade size and market conditions
            base_slippage = quantity * 0.001 * market_volatility
            volatility_factor = market_volatility * np.random.uniform(0.5, 2.0)
            actual_slippage = base_slippage + volatility_factor + np.random.normal(0, 0.0001)
            
            # Calculate market impact (Almgren-Chriss inspired)
            participation_rate = quantity / (volume_rate / 60)  # Participation in volume
            temporary_impact = 0.5 * participation_rate * market_volatility
            permanent_impact = 0.3 * participation_rate * market_volatility
            total_impact = temporary_impact + permanent_impact
            
            trade = {
                'timestamp': datetime.now() - timedelta(minutes=np.random.uniform(0, 10080)),  # Last week
                'quantity': quantity,
                'side': side,
                'urgency': urgency,
                'market_volatility': market_volatility,
                'spread': spread,
                'depth_imbalance': depth_imbalance,
                'volume_rate': volume_rate,
                'is_maker': is_maker,
                'actual_slippage': actual_slippage,
                'market_impact': total_impact,
                'execution_time': np.random.uniform(1, 300),  # Execution time in seconds
                'participation_rate': participation_rate
            }
            
            trades.append(trade)
        
        return pd.DataFrame(trades)
    
    def generate_market_features(self, num_samples: int = 1000) -> pd.DataFrame:
        """Generate market feature data for ML training."""
        features = []
        
        for i in range(num_samples):
            # Time-based features
            hour = np.random.randint(0, 24)
            day_of_week = np.random.randint(0, 7)
            
            # Market microstructure features
            bid_ask_spread = np.random.uniform(5, 100)
            order_book_imbalance = np.random.uniform(-1, 1)
            trade_intensity = np.random.exponential(2.0)
            price_volatility = np.random.uniform(0.001, 0.1)
            
            # Volume and liquidity features
            total_volume = np.random.exponential(1000)
            avg_trade_size = np.random.uniform(0.1, 5.0)
            market_depth = np.random.uniform(10, 1000)
            
            # Price movement features
            price_trend = np.random.uniform(-0.05, 0.05)  # 5-minute price change
            momentum = np.random.uniform(-0.1, 0.1)
            
            # Target variables (what we want to predict)
            expected_slippage = (
                0.0001 * bid_ask_spread +
                0.0005 * abs(order_book_imbalance) +
                0.0002 * trade_intensity +
                0.001 * price_volatility +
                np.random.normal(0, 0.0001)
            )
            
            maker_probability = 1 / (1 + np.exp(-(
                -2.0 +
                0.1 * bid_ask_spread +
                0.5 * market_depth / 100 +
                -1.0 * trade_intensity +
                np.random.normal(0, 0.1)
            )))
            
            feature = {
                'timestamp': datetime.now() - timedelta(minutes=np.random.uniform(0, 10080)),
                'hour': hour,
                'day_of_week': day_of_week,
                'bid_ask_spread': bid_ask_spread,
                'order_book_imbalance': order_book_imbalance,
                'trade_intensity': trade_intensity,
                'price_volatility': price_volatility,
                'total_volume': total_volume,
                'avg_trade_size': avg_trade_size,
                'market_depth': market_depth,
                'price_trend': price_trend,
                'momentum': momentum,
                'expected_slippage': expected_slippage,
                'maker_probability': maker_probability
            }
            
            features.append(feature)
        
        return pd.DataFrame(features)
    
    def save_sample_data(self):
        """Generate and save all sample data files."""
        print("Generating sample data...")
        
        # Generate orderbook data
        print("- Generating orderbook snapshots...")
        orderbook_data = self.generate_orderbook_data(1000)
        with open(os.path.join(self.data_dir, 'sample_orderbook.json'), 'w') as f:
            json.dump(orderbook_data, f, indent=2)
        
        # Generate trade data
        print("- Generating trade execution data...")
        trade_data = self.generate_trade_data(500)
        trade_data.to_csv(os.path.join(self.data_dir, 'sample_trades.csv'), index=False)
        
        # Generate market features
        print("- Generating market features...")
        feature_data = self.generate_market_features(1000)
        feature_data.to_csv(os.path.join(self.data_dir, 'sample_features.csv'), index=False)
        
        print("Sample data generated successfully!")
        print(f"Files saved to: {self.data_dir}")
        return {
            'orderbook_snapshots': len(orderbook_data),
            'trade_records': len(trade_data),
            'feature_samples': len(feature_data)
        }

if __name__ == "__main__":
    generator = SampleDataGenerator()
    stats = generator.save_sample_data()
    print(f"\nGenerated data statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

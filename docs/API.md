# GoQuant Trade Simulator API Documentation

## Overview
The GoQuant Trade Simulator provides REST API endpoints and WebSocket connections for real-time cryptocurrency trade cost estimation.

## Base URL
```
http://localhost:8080
```

## REST API Endpoints

### Health Check
```
GET /health
```
Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "message": "Server is running"
}
```

### Get Status
```
GET /api/status
```
Returns current simulator status and statistics.

**Response:**
```json
{
  "is_running": true,
  "trade_count": 0,
  "market": {
    "current_price": 50000.0,
    "spread": 0.01
  }
}
```

### Estimate Trade Cost
```
POST /api/estimate
```
Calculates estimated cost for a proposed trade.

**Request Body:**
```json
{
  "trade_size": 1.5,
  "order_type": "limit",  // "market" or "limit"
  "side": "buy",          // "buy" or "sell"
  "limit_price": 50000.0, // optional for limit orders
  "time_horizon": 600.0   // time in seconds
}
```

**Response:**
```json
{
  "timestamp": "2025-05-25T00:00:00",
  "current_price": 50000.0,
  "cost_breakdown": {
    "total_cost": 15.0,
    "exchange_fee": 10.0,
    "slippage_cost": 3.0,
    "market_impact": 2.0,
    "cost_bps": 10.0
  },
  "probabilities": {
    "maker_probability": 0.8,
    "slippage_confidence": 0.85
  },
  "market_conditions": {
    "bid_ask_spread": 1.0,
    "market_depth": 0.95,
    "volatility": 0.02
  },
  "optimal_strategy": "Limit order recommended"
}
```

## WebSocket Connection

### Connect
```
ws://localhost:8080/ws
```

### Message Types

#### Ping/Pong
**Send:**
```json
{"type": "ping"}
```
**Receive:**
```json
{"type": "pong", "data": {"timestamp": "2025-05-25T00:00:00"}}
```

#### Market Data Subscription
**Send:**
```json
{"type": "subscribe_market_data"}
```
**Receive:**
```json
{
  "type": "market_update",
  "data": {
    "symbol": "BTC-USDT-SWAP",
    "bid_price": 49999.5,
    "ask_price": 50000.5,
    "mid_price": 50000.0,
    "spread": 1.0,
    "spread_bps": 2.0,
    "volume_24h": 1500000000
  }
}
```

#### Cost Estimation via WebSocket
**Send:**
```json
{
  "type": "cost_estimate",
  "data": {
    "trade_size": 1.0,
    "order_type": "market",
    "side": "buy"
  }
}
```
**Receive:**
```json
{
  "type": "cost_estimate",
  "data": {
    // Same format as REST API response
  }
}
```

# 🚀 GoQuant Trade Simulator - Testing Guide

## Quick Start

### 1. Start the Server
```bash
cd /Users/sp2010/Desktop/snake/GoQunat
python main.py
```
Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 2. Access the Web Interface
Navigate to: **http://localhost:8000**

---

## Web Interface Test Cases

### Test Case 1: Basic Market Order (Small Trade)
**Input:**
- Trade Size: `1.0` BTC
- Order Type: `Market`
- Side: `Buy`
- Time Horizon: `300` seconds

**Expected Output:**
```
Total Cost: $40.00 (8.0 bps)
├── Exchange Fee: $25.00
├── Slippage Cost: $10.00
└── Market Impact: $5.00

Probabilities:
├── Maker Probability: 70.0%
└── Slippage Confidence: 85.0%

Market Conditions:
├── Spread: 0.01
├── Market Depth: 100.00
├── Volatility: 2.00%
└── Current Price: 50,000.00

Optimal Strategy: limit_order
```

### Test Case 2: Large Market Order
**Input:**
- Trade Size: `10.0` BTC
- Order Type: `Market`
- Side: `Sell`
- Time Horizon: `600` seconds

**Expected Output:**
```
Total Cost: $400.00 (8.0 bps)
├── Exchange Fee: $250.00
├── Slippage Cost: $100.00
└── Market Impact: $50.00
```

### Test Case 3: Limit Order
**Input:**
- Trade Size: `2.5` BTC
- Order Type: `Limit`
- Side: `Buy`
- Limit Price: `49500.00`
- Time Horizon: `900` seconds

**Expected Output:**
```
Total Cost: $100.00 (8.0 bps)
├── Exchange Fee: $62.50
├── Slippage Cost: $25.00
└── Market Impact: $12.50
```

### Test Case 4: Fractional Trade
**Input:**
- Trade Size: `0.1` BTC
- Order Type: `Market`
- Side: `Buy`
- Time Horizon: `120` seconds

**Expected Output:**
```
Total Cost: $4.00 (8.0 bps)
├── Exchange Fee: $2.50
├── Slippage Cost: $1.00
└── Market Impact: $0.50
```

---

## API Test Cases (Using curl)

### Test Case 1: Basic API Call
```bash
curl -X POST http://localhost:8000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "trade_size": 1.0,
    "order_type": "market",
    "side": "buy",
    "time_horizon": 300.0
  }'
```

**Expected JSON Response:**
```json
{
  "timestamp": 1748047754.570666,
  "trade_params": {
    "trade_size": 1.0,
    "order_type": "market",
    "side": "buy",
    "limit_price": null,
    "time_horizon": 300.0
  },
  "current_price": 50000.0,
  "cost_breakdown": {
    "exchange_fee": 25.0,
    "slippage_cost": 10.0,
    "market_impact": 5.0,
    "total_cost": 40.0,
    "cost_bps": 8.0
  },
  "probabilities": {
    "maker_probability": 0.7,
    "slippage_confidence": 0.85
  },
  "market_conditions": {
    "bid_ask_spread": 0.01,
    "market_depth": 100.0,
    "volatility": 0.02
  },
  "optimal_strategy": "limit_order"
}
```

### Test Case 2: Large Trade with Limit Order
```bash
curl -X POST http://localhost:8000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "trade_size": 5.0,
    "order_type": "limit",
    "side": "sell",
    "limit_price": 50100.0,
    "time_horizon": 1800.0
  }'
```

**Expected JSON Response:**
```json
{
  "timestamp": 1748047754.570666,
  "trade_params": {
    "trade_size": 5.0,
    "order_type": "limit",
    "side": "sell",
    "limit_price": 50100.0,
    "time_horizon": 1800.0
  },
  "current_price": 50000.0,
  "cost_breakdown": {
    "exchange_fee": 125.0,
    "slippage_cost": 50.0,
    "market_impact": 25.0,
    "total_cost": 200.0,
    "cost_bps": 8.0
  },
  "probabilities": {
    "maker_probability": 0.7,
    "slippage_confidence": 0.85
  },
  "market_conditions": {
    "bid_ask_spread": 0.01,
    "market_depth": 100.0,
    "volatility": 0.02
  },
  "optimal_strategy": "limit_order"
}
```

---

## Status and Health Check Tests

### Test Case 1: Health Check
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": 1748047754.570666,
  "service": "GoQuant Trade Simulator"
}
```

### Test Case 2: System Status
```bash
curl http://localhost:8000/api/status
```

**Expected Response:**
```json
{
  "trade_count": 0,
  "is_running": true,
  "last_update_time": 1748047754.570666,
  "market": {
    "current_price": 50000.0,
    "spread": 0.01,
    "volume_24h": 1000000.0
  },
  "models": {
    "slippage_trained": false,
    "maker_taker_trained": false,
    "all_models_trained": false
  }
}
```

---

## Error Test Cases

### Test Case 1: Invalid Trade Size
**Input:**
- Trade Size: `-1.0` (negative)
- Order Type: `Market`
- Side: `Buy`
- Time Horizon: `300`

**Expected Error:**
```
Please enter a valid trade size.
```

### Test Case 2: Invalid Time Horizon
**Input:**
- Trade Size: `1.0`
- Order Type: `Market`
- Side: `Buy`
- Time Horizon: `0` (zero or negative)

**Expected Error:**
```
Please enter a valid time horizon.
```

### Test Case 3: Missing Limit Price for Limit Order
**Input:**
- Trade Size: `1.0`
- Order Type: `Limit`
- Side: `Buy`
- Limit Price: (empty)
- Time Horizon: `300`

**Expected Error:**
```
Please enter a valid limit price.
```

### Test Case 4: Invalid API Request
```bash
curl -X POST http://localhost:8000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "trade_size": "invalid",
    "order_type": "market",
    "side": "buy",
    "time_horizon": 300.0
  }'
```

**Expected Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "trade_size"],
      "msg": "value is not a valid float",
      "type": "type_error.float"
    }
  ]
}
```

---

## Cost Calculation Logic

### Formula Explanation:
For a trade of size `X` BTC at price `$50,000`:

1. **Notional Value** = X × $50,000
2. **Exchange Fee** = Notional × 0.0005 (5 bps)
3. **Slippage Cost** = Notional × 0.0002 (2 bps)
4. **Market Impact** = Notional × 0.0001 (1 bp)
5. **Total Cost** = Exchange Fee + Slippage + Market Impact
6. **Cost in bps** = (Total Cost / Notional) × 10,000

### Examples:
- **1 BTC Trade** ($50,000 notional): $25 + $10 + $5 = $40 total (8 bps)
- **5 BTC Trade** ($250,000 notional): $125 + $50 + $25 = $200 total (8 bps)
- **0.1 BTC Trade** ($5,000 notional): $2.50 + $1.00 + $0.50 = $4.00 total (8 bps)

---

## Quick Browser Testing

For rapid testing, use these sample inputs:

### Test 1: Small Market Order
- **Trade Size**: `1` BTC
- **Order Type**: `Market`
- **Side**: `Buy`
- **Time Horizon**: `30` seconds
- **Expected Result**: Total Cost: $40.00 (8.0 bps)

### Test 2: Large Market Order  
- **Trade Size**: `2.5` BTC
- **Order Type**: `Market`
- **Side**: `Sell`
- **Time Horizon**: `60` seconds
- **Expected Result**: Total Cost: $100.00 (8.0 bps)

### Test 3: Limit Order
- **Trade Size**: `1.5` BTC
- **Order Type**: `Limit`
- **Side**: `Buy`
- **Limit Price**: `49975`
- **Time Horizon**: `120` seconds
- **Expected Result**: Total Cost: $60.00 (8.0 bps)

## Automated Testing

Run the complete test suite:
```bash
cd /Users/sp2010/Desktop/snake/GoQunat
python test_samples.py
```

## Browser Console Debugging

1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Look for these success messages:
   - `🚀 Sending trade request`
   - `📊 API Response`
   - `✅ Results HTML updated successfully`

## Troubleshooting

### Issue: "Invalid cost estimate data received"
**Solution**: 
1. Check browser console for detailed error logs
2. Try hard refresh (Ctrl+F5 / Cmd+Shift+R)
3. Verify server is running

### Issue: Form fields not working
**Solution**:
1. Hard refresh the browser
2. Clear browser cache
3. Check console for JavaScript errors

### Issue: Server not starting
**Solution**:
1. Check if port 8000 is already in use
2. Try alternative command: `python -m src.ui.web_server`
3. Check for missing dependencies: `pip install -r requirements.txt`

## Expected Cost Formula

For any trade size X (in BTC):
- **Notional Value** = X × $50,000
- **Exchange Fee** = Notional × 0.0005 (5 bps)
- **Slippage Cost** = Notional × 0.0002 (2 bps)
- **Market Impact** = Notional × 0.0001 (1 bp)
- **Total Cost** = 8 bps of notional value

Examples:
- 1 BTC → $40 total cost
- 2.5 BTC → $100 total cost  
- 10 BTC → $400 total cost

## Success Criteria

✅ **Everything is working if you see**:
- Server starts without errors
- Web interface loads at localhost:8000
- Forms accept input and show cost calculations
- All test cases pass the automated test script
- Browser console shows successful API calls

🎉 **You're ready to use the trade simulator!**

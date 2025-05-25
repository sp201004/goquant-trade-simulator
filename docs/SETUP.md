# GoQuant Trade Simulator - Installation & Setup Guide

## System Requirements
- Python 3.8 or higher
- macOS, Linux, or Windows
- 4GB RAM minimum
- Internet connection for dependencies

## Installation

### 1. Clone or Download
Ensure you have the GoQuant project directory.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Verify Installation
```bash
python3 -c "import fastapi, uvicorn, websockets; print('✓ All dependencies installed')"
```

## Quick Start

### 1. Start the Server
```bash
python3 main.py
```

### 2. Access the Web Interface
Open your browser and navigate to:
```
http://localhost:8080
```

### 3. Test the API
```bash
# Health check
curl http://localhost:8080/health

# Get status
curl http://localhost:8080/api/status

# Estimate trade cost
curl -X POST "http://localhost:8080/api/estimate" \
  -H "Content-Type: application/json" \
  -d '{
    "trade_size": 1.0,
    "order_type": "market",
    "side": "buy",
    "time_horizon": 300.0
  }'
```

## Features

### ✅ Working Features
- **Web Interface**: Modern, responsive UI
- **REST API**: Complete cost estimation endpoints
- **WebSocket**: Real-time market data updates
- **Cost Calculation**: Exchange fees, slippage, market impact
- **Market Simulation**: Live BTC-USDT-SWAP price feeds
- **Strategy Recommendations**: Optimal order type suggestions

### 🔧 Configuration
All configuration is handled automatically. The server uses:
- **Port**: 8080
- **Symbol**: BTC-USDT-SWAP
- **Update Frequency**: 1 second for market data
- **Base Fees**: 0.1% (limit) / 0.15% (market)

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process using port 8080
lsof -i :8080
kill <PID>
```

### WebSocket Connection Issues
Ensure `websockets` package is installed:
```bash
pip install websockets
```

### Import Errors
Check Python path and ensure you're in the correct directory:
```bash
cd /path/to/GoQunat
python3 main.py
```

## Architecture

```
GoQuant/
├── main.py              # Main server entry point
├── requirements.txt     # Python dependencies
├── src/                 # Source code
│   ├── core/           # Core trading logic
│   ├── models/         # Financial models
│   ├── ui/             # Web interface
│   └── utils/          # Utilities
├── data/               # Sample data
├── logs/               # Server logs
└── docs/               # Documentation
```

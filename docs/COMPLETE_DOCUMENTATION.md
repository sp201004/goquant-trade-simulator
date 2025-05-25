# 📚 GoQuant Trade Simulator - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Quick Start](#quick-start)
3. [Architecture & Components](#architecture--components)
4. [API Reference](#api-reference)
5. [Technical Implementation](#technical-implementation)
6. [Deployment & Operations](#deployment--operations)
7. [Development Guide](#development-guide)
8. [Testing](#testing)

---

## 1. Project Overview

### 🎯 Purpose
GoQuant Trade Simulator is a **high-performance cryptocurrency trade cost estimation system** designed to:
- Calculate real-time trading costs (fees, slippage, market impact)
- Process live market data from OKX exchange via WebSocket
- Provide optimal trading strategy recommendations
- Offer interactive web interface with live charts

### 🏗️ Technology Stack
- **Backend**: Python 3.8+ with FastAPI framework
- **Financial Models**: Almgren-Chriss, Quantile Regression, Logistic Regression
- **Real-time Data**: WebSocket connections to OKX exchange
- **Frontend**: HTML5, CSS3, JavaScript with Chart.js
- **Data Processing**: NumPy, Pandas, SciPy
- **Web Server**: Uvicorn ASGI server

### 📊 Key Features
- **Real-time WebSocket Updates**: Live BTC-USDT-SWAP market data
- **Advanced Cost Modeling**: Exchange fees, slippage, market impact
- **Interactive Charts**: Live cost visualization and market conditions
- **RESTful API**: Complete programmatic access
- **High Performance**: Sub-5ms latency for critical calculations

---

## 2. Quick Start

### 🚀 Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd GoQunat
```

2. **Create virtual environment**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Start the server**:
```bash
python main.py
```

5. **Access the application**:
   - Web Interface: http://localhost:8080
   - API Documentation: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health

### ⚡ Quick Scripts
```bash
# Start server
./scripts/start.sh

# Stop server
./scripts/stop.sh

# Run tests
./scripts/test.sh
```

---

## 3. Architecture & Components

### 🔧 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GoQuant Trade Simulator                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Web UI    │    │  REST API   │    │  WebSocket  │     │
│  │             │    │             │    │   Server    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Trade Simulator Engine                 │   │
│  │                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │  Orderbook  │  │ Financial   │  │Performance  │  │   │
│  │  │ Processor   │  │  Models     │  │ Monitor     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Data Layer                             │   │
│  │                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ WebSocket   │  │   Sample    │  │    Logs     │  │   │
│  │  │   Client    │  │    Data     │  │             │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
└─────────────────────────────┼─────────────────────────────┘
                              │
                    ┌─────────────┐
                    │ OKX Exchange│
                    │  WebSocket  │
                    └─────────────┘
```

### 🗂️ Directory Structure

```
GoQuant/
├── main.py                    # 🚀 Application entry point
├── requirements.txt           # 📦 Python dependencies
├── README.md                  # 📖 Project overview
├── config/settings.ini        # ⚙️ Configuration
├── data/                      # 📊 Sample data
├── docs/                      # 📚 Documentation
├── logs/                      # 📝 Application logs
├── scripts/                   # 🔧 Utility scripts
├── src/                       # 💻 Source code
│   ├── core/                 # Core trading logic
│   ├── models/               # Financial models
│   ├── ui/                   # User interface
│   └── utils/                # Utilities
└── tests/                     # 🧪 Test suite
```

---

## 4. API Reference

### Base URL
```
http://localhost:8080
```

### REST Endpoints

#### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "message": "Server is running"
}
```

#### Get Status
```http
GET /api/status
```
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

#### Estimate Trade Cost
```http
POST /api/estimate
```
**Request:**
```json
{
  "trade_size": 1.5,
  "order_type": "limit",
  "side": "buy",
  "limit_price": 50000.0,
  "time_horizon": 600.0
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
    "market_impact": 2.0
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

### WebSocket Connection
```
ws://localhost:8080/ws
```

#### Market Data Updates
```json
{
  "type": "market_update",
  "data": {
    "symbol": "BTC-USDT-SWAP",
    "bid_price": 49999.5,
    "ask_price": 50000.5,
    "mid_price": 50000.0,
    "spread": 1.0
  }
}
```

---

## 5. Technical Implementation

### 🧮 Financial Models

#### Almgren-Chriss Model
**Nobel Prize-winning framework** for optimal trade execution.

**Mathematical Foundation:**
```
E[Cost] = ∫₀ᵀ η·v(t)dt + ∫₀ᵀ ε·v(t)²dt + γ·σ²·∫₀ᵀ x(t)²dt
```

**Implementation:**
```python
@dataclass
class AlmgrenChrissParams:
    sigma: float   # Volatility
    gamma: float   # Risk aversion
    eta: float     # Permanent impact
    epsilon: float # Temporary impact
    tau: float     # Trading time horizon
```

#### Slippage Estimation
**Machine Learning approach** using quantile regression:
- **Features**: Market microstructure, order characteristics, temporal patterns
- **Model**: Gradient Boosting with quantile loss
- **Output**: Distribution of expected slippage

#### Fee Calculator
**Comprehensive fee modeling** for OKX exchange:
- **Maker/Taker Prediction**: Logistic regression for fill probability
- **Volume Discounts**: Tier-based fee structure
- **Expected Fee**: Probability-weighted calculation

### 🌐 WebSocket Integration

#### OKX Exchange Connection
```python
# WebSocket URL
WS_URL = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"

# Message handling
async def on_message(self, message):
    data = json.loads(message)
    if data.get('action') == 'snapshot':
        await self.process_snapshot(data)
    elif data.get('action') == 'update':
        await self.process_update(data)
```

#### Real-time Data Flow
1. **WebSocket Reception** → Parse L2 orderbook data
2. **Orderbook Processing** → Calculate market metrics
3. **Model Inference** → Run cost estimation models
4. **UI Broadcasting** → Send updates to web clients

### 🎨 User Interface

#### Frontend Components
- **Interactive Charts**: Chart.js for real-time visualization
- **Parameter Controls**: Dynamic form validation
- **Cost Display**: Live cost breakdown and recommendations
- **Market Dashboard**: Real-time market condition monitoring

#### Chart Types
1. **Cost Breakdown** (Doughnut): Fee components
2. **Cost History** (Line): Historical cost tracking
3. **Probability** (Bar): Maker/taker probabilities
4. **Market Conditions** (Radar): Market health metrics

---

## 6. Deployment & Operations

### 🐳 Production Deployment

#### Docker Setup
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["python", "main.py"]
```

#### Environment Variables
```bash
export GOQUANT_ENV=production
export GOQUANT_LOG_LEVEL=INFO
export GOQUANT_PORT=8080
export GOQUANT_HOST=0.0.0.0
```

#### Performance Monitoring
- **Health Checks**: `/health` endpoint for load balancer
- **Metrics Collection**: Latency, throughput, error rates
- **Logging**: Structured logging with rotation
- **Alerting**: Performance threshold monitoring

### 🔧 Configuration

#### settings.ini
```ini
[websocket]
url = wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP
reconnect_interval = 5
max_reconnect_attempts = 10

[models]
almgren_chriss_gamma = 0.001
slippage_retrain_interval = 100
use_adaptive_learning = true

[performance]
max_api_latency_ms = 100
max_processing_latency_ms = 10
```

---

## 7. Development Guide

### 🛠️ Setup Development Environment

1. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

2. **Run development server**:
```bash
python main.py
```

3. **Enable hot reload**:
```bash
uvicorn main:app --reload --port 8080
```

### 🧪 Testing

#### Unit Tests
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_api.py::test_health_check

# Run with coverage
pytest --cov=src tests/
```

#### Integration Tests
```bash
# Start server first
python main.py &

# Run API tests
curl http://localhost:8080/health
curl -X POST http://localhost:8080/api/estimate \
  -H "Content-Type: application/json" \
  -d '{"trade_size": 1.0, "order_type": "market", "side": "buy"}'
```

#### WebSocket Testing
```javascript
// Browser console test
const ws = new WebSocket('ws://localhost:8080/ws');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

### 📊 Performance Optimization

#### Key Performance Metrics
- **API Latency**: < 100ms (target)
- **WebSocket Processing**: < 1ms per message
- **Model Inference**: < 5ms total
- **Memory Usage**: < 1GB under normal load

#### Optimization Techniques
- **Vectorized Operations**: NumPy for mathematical calculations
- **Caching**: LRU cache for expensive computations
- **Async Processing**: Non-blocking I/O operations
- **Memory Management**: Circular buffers for data history

---

## 8. Troubleshooting

### 🔍 Common Issues

#### WebSocket Connection Failed
```bash
# Check network connectivity
curl -I https://ws.gomarket-cpp.goquant.io

# Verify WebSocket URL
python -c "import websockets; print('WebSocket support available')"
```

#### High Memory Usage
```bash
# Monitor memory
ps aux | grep python
htop

# Check for memory leaks
python -c "import tracemalloc; tracemalloc.start()"
```

#### API Timeouts
```bash
# Check server load
curl http://localhost:8080/health

# Monitor logs
tail -f logs/goquant_*.log
```

### 📝 Logging

#### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Potential issues
- **ERROR**: Serious problems
- **CRITICAL**: System failures

#### Log Analysis
```bash
# View recent logs
tail -100 logs/goquant_$(date +%Y-%m-%d).log

# Search for errors
grep "ERROR" logs/goquant_*.log

# Monitor real-time
tail -f logs/goquant_*.log | grep "WebSocket"
```

---

## 📚 Additional Resources

### 📖 References
- [Almgren-Chriss Paper](https://www.math.nyu.edu/faculty/chriss/optliq_f.pdf)
- [OKX API Documentation](https://www.okx.com/docs-v5/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Chart.js Documentation](https://www.chartjs.org/docs/)

### 🤝 Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

---

**🚀 Ready to simulate trades? Start the server and begin exploring!**

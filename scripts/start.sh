#!/bin/bash
# GoQuant Trade Simulator - Start Script

echo "🚀 Starting GoQuant Trade Simulator..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import fastapi, uvicorn, websockets" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing required dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies. Please check your pip installation."
        exit 1
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if port 8080 is available
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null; then
    echo "⚠️  Port 8080 is already in use. Stopping existing process..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null
    sleep 2
fi

echo "✅ Starting server on http://localhost:8080"
echo "📊 Web interface: http://localhost:8080"
echo "🔌 WebSocket endpoint: ws://localhost:8080/ws"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================="

# Start the server
python3 main.py

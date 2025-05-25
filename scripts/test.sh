#!/bin/bash
# GoQuant Trade Simulator - Test Script

echo "🧪 Running GoQuant Trade Simulator Tests..."
echo ""

# Check if server is running
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "⚠️  Server is not running. Starting server first..."
    echo ""
    
    # Start server in background
    python3 main.py &
    SERVER_PID=$!
    
    echo "⏳ Waiting for server to start..."
    sleep 5
    
    # Check if server started successfully
    if ! curl -s http://localhost:8080/health > /dev/null; then
        echo "❌ Failed to start server for testing"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    echo "✅ Server started for testing"
    STARTED_SERVER=true
else
    echo "✅ Server is already running"
    STARTED_SERVER=false
fi

echo ""
echo "🚀 Running API tests..."
echo ""

# Run the comprehensive test suite
python3 tests/test_api.py

TEST_RESULT=$?

# Stop server if we started it
if [ "$STARTED_SERVER" = true ]; then
    echo ""
    echo "🛑 Stopping test server..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
fi

if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed! GoQuant is working correctly."
    exit 0
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi

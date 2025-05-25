#!/bin/bash
# GoQuant Trade Simulator - Stop Script

echo "🛑 Stopping GoQuant Trade Simulator..."

# Find and kill processes using port 8080
PIDS=$(lsof -ti:8080 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "ℹ️  No GoQuant server processes found running on port 8080"
else
    echo "🔍 Found processes: $PIDS"
    echo "$PIDS" | xargs kill -TERM 2>/dev/null
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Force kill if still running
    REMAINING=$(lsof -ti:8080 2>/dev/null)
    if [ ! -z "$REMAINING" ]; then
        echo "💀 Force stopping remaining processes..."
        echo "$REMAINING" | xargs kill -9 2>/dev/null
    fi
    
    echo "✅ GoQuant Trade Simulator stopped"
fi

# Also check for any python processes with "main.py"
PYTHON_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null)
if [ ! -z "$PYTHON_PIDS" ]; then
    echo "🔍 Found additional Python processes: $PYTHON_PIDS"
    echo "$PYTHON_PIDS" | xargs kill -TERM 2>/dev/null
    sleep 1
    # Force kill if needed
    REMAINING_PYTHON=$(pgrep -f "python.*main.py" 2>/dev/null)
    if [ ! -z "$REMAINING_PYTHON" ]; then
        echo "$REMAINING_PYTHON" | xargs kill -9 2>/dev/null
    fi
fi

echo "🏁 All GoQuant processes stopped"

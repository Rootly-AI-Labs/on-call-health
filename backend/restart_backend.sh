#!/bin/bash

echo "Checking if backend is already running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is already running!"
    curl -s http://localhost:8000/health | python3 -m json.tool
    exit 0
fi

echo "Backend not responding. Attempting to start..."

# Navigate to backend directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements if needed
pip install -r requirements.txt > /dev/null 2>&1

# Start the backend
echo "Starting backend server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Wait a moment for server to start
sleep 3

# Check if it's running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend started successfully!"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "❌ Failed to start backend. Check the logs."
fi
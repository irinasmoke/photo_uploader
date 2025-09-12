#!/bin/bash

# Local Photo Uploader Startup Script
echo "🖼️ Starting Local Photo Uploader..."

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Please run this script from the photo_uploader root directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

# Change to src directory
cd src

# Create uploads directory if it doesn't exist
mkdir -p uploads/photos

# Check if virtual environment exists
if [ ! -d "../.venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv ../.venv
    source ../.venv/bin/activate
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "📦 Activating virtual environment..."
    source ../.venv/bin/activate
fi

echo "🚀 Starting FastAPI server..."
echo "📱 Open your browser to: http://localhost:8000"
echo "📸 Gallery available at: http://localhost:8000/gallery"
echo "📚 API docs available at: http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop the server"

# Run the application
python3 main.py

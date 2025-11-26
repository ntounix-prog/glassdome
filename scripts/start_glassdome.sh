#!/bin/bash
#
# Glassdome Startup Script
#
# Activates virtual environment, initializes Glassdome session,
# and starts the API server and/or frontend
#
# Usage:
#   ./start_glassdome.sh              # Initialize session only
#   ./start_glassdome.sh --backend    # Start backend API server (port 8011)
#   ./start_glassdome.sh --frontend   # Start frontend dev server (port 5174)
#   ./start_glassdome.sh --all        # Start both backend and frontend
#   ./start_glassdome.sh --serve      # Alias for --backend (legacy)
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Parse arguments
START_BACKEND=false
START_FRONTEND=false

for arg in "$@"; do
    case $arg in
        --backend|--serve|--server)
            START_BACKEND=true
            ;;
        --frontend)
            START_FRONTEND=true
            ;;
        --all)
            START_BACKEND=true
            START_FRONTEND=true
            ;;
        --help|-h)
            echo "Glassdome Startup Script"
            echo ""
            echo "Usage:"
            echo "  ./start_glassdome.sh              # Initialize session only"
            echo "  ./start_glassdome.sh --backend    # Start backend (port 8011)"
            echo "  ./start_glassdome.sh --frontend   # Start frontend (port 5174)"
            echo "  ./start_glassdome.sh --all        # Start both"
            echo ""
            exit 0
            ;;
    esac
done

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "======================================================================"
    echo "❌ ERROR: Virtual environment not found"
    echo "======================================================================"
    echo "Please create the virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo "======================================================================"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run initialization script
echo ""
python3 scripts/glassdome_init.py
INIT_EXIT_CODE=$?

if [ $INIT_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Initialization failed. Cannot start application."
    exit $INIT_EXIT_CODE
fi

# Start frontend in background if requested
if [ "$START_FRONTEND" = true ]; then
    echo ""
    echo "======================================================================"
    echo "🎨 Starting Glassdome Frontend"
    echo "======================================================================"
    echo ""
    echo "Frontend will be available at: http://localhost:5174"
    echo ""
    
    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        echo "❌ npm not found. Please install Node.js and npm."
        exit 1
    fi
    
    # Check if node_modules exists
    if [ ! -d "frontend/node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        cd frontend && npm install && cd ..
    fi
    
    # Start frontend in background
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    echo "Frontend started (PID: $FRONTEND_PID)"
    echo ""
fi

# Start backend if requested
if [ "$START_BACKEND" = true ]; then
    echo ""
    echo "======================================================================"
    echo "🚀 Starting Glassdome Backend API"
    echo "======================================================================"
    echo ""
    echo "Backend API: http://localhost:8011"
    echo "API Docs:    http://localhost:8011/docs"
    if [ "$START_FRONTEND" = true ]; then
        echo "Frontend:    http://localhost:5174"
    fi
    echo ""
    echo "Press Ctrl+C to stop"
    echo "======================================================================"
    echo ""
    
    # Start the backend server (foreground)
    python3 -m glassdome.server
    
elif [ "$START_FRONTEND" = true ]; then
    # Frontend only - wait for it
    echo "======================================================================"
    echo "Press Ctrl+C to stop frontend"
    echo "======================================================================"
    wait $FRONTEND_PID
else
    echo ""
    echo "✅ Glassdome session initialized and ready!"
    echo ""
    echo "To start services:"
    echo "  ./glassdome_start --backend    # Backend API (port 8011)"
    echo "  ./glassdome_start --frontend   # Frontend (port 5174)"
    echo "  ./glassdome_start --all        # Both services"
    echo ""
fi

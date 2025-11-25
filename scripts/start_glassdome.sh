#!/bin/bash
#
# Glassdome Startup Script
#
# Activates virtual environment, initializes Glassdome session,
# and optionally starts the API server
#
# Usage:
#   ./start_glassdome.sh          # Initialize session only
#   ./start_glassdome.sh --serve  # Initialize and start API server
#   ./start_glassdome.sh --server # Same as --serve
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Parse arguments
START_SERVER=false
if [[ "$1" == "--serve" ]] || [[ "$1" == "--server" ]]; then
    START_SERVER=true
fi

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

# If --serve flag is set, start the API server
if [ "$START_SERVER" = true ]; then
    echo ""
    echo "======================================================================"
    echo "🚀 Starting Glassdome API Server"
    echo "======================================================================"
    echo ""
    echo "API will be available at: http://localhost:8010"
    echo "API documentation at: http://localhost:8010/docs"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo "======================================================================"
    echo ""
    
    # Start the server
    python3 -m uvicorn glassdome.server:app --host 0.0.0.0 --port 8010
else
    echo ""
    echo "✅ Glassdome session initialized and ready!"
    echo ""
    echo "To start the API server, run:"
    echo "  ./scripts/start_glassdome.sh --serve"
    echo ""
    echo "Or use the CLI:"
    echo "  glassdome serve"
    echo ""
fi


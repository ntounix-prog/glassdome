#!/bin/bash

# Quick activation script for the virtual environment

if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    echo "Python: $(which python)"
    echo "To deactivate, run: deactivate"
else
    echo "❌ Virtual environment not found. Run ./setup.sh first"
    exit 1
fi


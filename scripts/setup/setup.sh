#!/bin/bash

# Glassdome Virtual Environment Setup Script
# This script creates a virtual environment and installs dependencies

set -e  # Exit on error

VENV_DIR="venv"
PYTHON_CMD="python3"

echo "🔧 Glassdome Environment Setup"
echo "================================"

# Check if Python 3 is installed
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
echo "✓ Found: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment already exists at ./$VENV_DIR"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "📦 Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install package in editable mode
echo "📦 Installing Glassdome package..."
pip install -e .
echo "✓ Glassdome installed successfully"

# Verify installation
echo ""
echo "🧪 Verifying installation..."
python -c "import glassdome; print(f'Glassdome v{glassdome.__version__} installed')" || echo "⚠️ Import verification failed"
which glassdome > /dev/null && echo "✓ CLI command available" || echo "⚠️ CLI command not in PATH"

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate when done, run:"
echo "  deactivate"
echo "================================"


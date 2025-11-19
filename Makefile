.PHONY: setup clean install activate help

help:
	@echo "Glassdome - Available Commands"
	@echo "==============================="
	@echo "make setup     - Create virtual environment and install dependencies"
	@echo "make install   - Install/update dependencies from requirements.txt"
	@echo "make clean     - Remove virtual environment and cache files"
	@echo "make help      - Show this help message"
	@echo ""
	@echo "To activate the environment:"
	@echo "  source venv/bin/activate"

setup:
	@bash setup.sh

install:
	@if [ -d "venv" ]; then \
		. venv/bin/activate && pip install -r requirements.txt; \
	else \
		echo "❌ Virtual environment not found. Run 'make setup' first"; \
		exit 1; \
	fi

clean:
	@echo "🗑️  Cleaning up..."
	@rm -rf venv
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"


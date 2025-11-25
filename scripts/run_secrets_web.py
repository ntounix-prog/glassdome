#!/usr/bin/env python3
"""
Run the Secrets Manager Web Interface

Simple script to start the web interface for managing secrets.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.api.secrets_web import app
import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  🔐 Glassdome Secrets Manager Web Interface")
    print("=" * 70)
    print("\n  Starting server on http://localhost:8002")
    print("  Open your browser and navigate to: http://localhost:8002")
    print("\n" + "=" * 70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8002)


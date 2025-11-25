#!/usr/bin/env python3
"""
Glassdome Initialization Script

Initializes the Glassdome session, loads all secrets, and prepares
the environment for agent execution.
"""
import sys
from pathlib import Path

# Check if we're in a virtual environment or if keyring is available
try:
    import keyring
except ImportError:
    print("=" * 70)
    print("❌ ERROR: Missing dependencies")
    print("=" * 70)
    print("Please activate the virtual environment first:")
    print("  source venv/bin/activate")
    print()
    print("Or install dependencies:")
    print("  pip install keyring>=24.0.0 cryptography>=41.0.0")
    print("=" * 70)
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from glassdome.core.session import get_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize Glassdome session"""
    print("\n" + "=" * 70)
    print("GLASSDOME INITIALIZATION")
    print("=" * 70)
    print()
    
    session = get_session()
    
    # Check if already initialized
    if session.authenticated and session._is_session_valid():
        print("✅ Session already initialized and valid")
        print(f"   Authenticated at: {session.authenticated_at}")
        print(f"   Secrets loaded: {len(session.secrets)}")
        response = input("\nRe-initialize? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing session.")
            return 0
        session.logout()
    
    # Initialize
    success = session.initialize(interactive=True)
    
    if success:
        print("\n" + "=" * 70)
        print("✅ GLASSDOME READY")
        print("=" * 70)
        print(f"Session initialized successfully!")
        print(f"  - Secrets loaded: {len(session.secrets)}")
        print(f"  - Session timeout: {session.session_timeout}")
        print(f"  - Agents can now execute")
        print("=" * 70 + "\n")
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ INITIALIZATION FAILED")
        print("=" * 70)
        print("Please check your master password and try again.")
        print("=" * 70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())


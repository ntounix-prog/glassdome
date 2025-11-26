#!/usr/bin/env python3
"""
Glassdome Initialization Script

Initializes the Glassdome environment based on SECRETS_BACKEND:
- env: Just verifies .env file exists (no password needed)
- local: Prompts for master password to unlock encrypted secrets
- vault: Verifies Vault connectivity
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize Glassdome session"""
    print("\n" + "=" * 70)
    print("GLASSDOME INITIALIZATION")
    print("=" * 70)
    print()
    
    # Check backend type
    backend = os.environ.get("SECRETS_BACKEND", "env")
    print(f"Secrets backend: {backend}")
    print()
    
    if backend == "env":
        # Simple: just verify .env exists
        from glassdome.core.paths import ENV_FILE
        
        if not ENV_FILE.exists():
            print(f"❌ ERROR: .env file not found at {ENV_FILE}")
            print("Please create a .env file with your configuration.")
            return 1
        
        # Load and verify we have some secrets
        from glassdome.core.security import get_secret
        
        test_keys = ['openai_api_key', 'database_url', 'proxmox_password']
        found = sum(1 for k in test_keys if get_secret(k))
        
        print(f"✅ .env file found: {ENV_FILE}")
        print(f"✅ Secrets available: {found}/{len(test_keys)} test keys found")
        print()
        print("=" * 70)
        print("✅ GLASSDOME READY (env backend)")
        print("=" * 70)
        print("No master password required - secrets loaded from .env")
        print("=" * 70 + "\n")
        return 0
    
    elif backend == "local":
        # Legacy: encrypted local store - needs master password
        try:
            import keyring
        except ImportError:
            print("=" * 70)
            print("❌ ERROR: Missing dependencies for local backend")
            print("=" * 70)
            print("Install: pip install keyring>=24.0.0 cryptography>=41.0.0")
            print("Or use: export SECRETS_BACKEND=env")
            print("=" * 70)
            return 1
        
        from glassdome.core.session import get_session
        
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
        
        # Initialize with password prompt
        success = session.initialize(interactive=True)
        
        if success:
            print("\n" + "=" * 70)
            print("✅ GLASSDOME READY (local backend)")
            print("=" * 70)
            print(f"Session initialized successfully!")
            print(f"  - Secrets loaded: {len(session.secrets)}")
            print(f"  - Session timeout: {session.session_timeout}")
            print("=" * 70 + "\n")
            return 0
        else:
            print("\n" + "=" * 70)
            print("❌ INITIALIZATION FAILED")
            print("=" * 70)
            print("Please check your master password and try again.")
            print("=" * 70 + "\n")
            return 1
    
    elif backend == "vault":
        # Future: HashiCorp Vault
        print("=" * 70)
        print("⚠️  Vault backend not yet implemented")
        print("=" * 70)
        print("Set SECRETS_BACKEND=env to use .env file instead")
        print("=" * 70)
        return 1
    
    else:
        print(f"❌ Unknown SECRETS_BACKEND: {backend}")
        print("Valid options: env, local, vault")
        return 1


if __name__ == '__main__':
    sys.exit(main())

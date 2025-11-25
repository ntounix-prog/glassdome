#!/usr/bin/env python3
"""
Migrate network device credentials from .env to secure secrets store.

This script migrates:
- Cisco Nexus 3064 password
- Cisco 3850 password
- Ubiquiti Gateway password
- Ubiquiti API key
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
from glassdome.core.session import get_session


def read_env_file(env_path: str = "/home/nomad/glassdome/.env") -> dict:
    """Read .env file and return as dictionary."""
    config = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config


def main():
    print("=" * 60)
    print("Network Device Secrets Migration")
    print("=" * 60)
    
    # Read current .env
    env_config = read_env_file()
    
    # Secrets to migrate
    secrets_to_migrate = {
        # Cisco Nexus 3064
        'nexus_3064_password': env_config.get('NEXUS_3064_PASSWORD'),
        
        # Cisco 3850
        'cisco_3850_password': env_config.get('CISCO_3850_PASSWORD'),
        
        # Ubiquiti Gateway
        'ubiquiti_gateway_password': env_config.get('UBIQUITI_GATEWAY_PASSWORD'),
        'ubiquiti_api_key': env_config.get('UBIQUITY_KEY'),  # Note: typo in .env (UBIQUITY vs UBIQUITI)
    }
    
    print("\nSecrets found in .env:")
    for key, value in secrets_to_migrate.items():
        status = "✅ Found" if value else "❌ Not found"
        masked = f"{value[:3]}***{value[-3:]}" if value and len(value) > 6 else "***" if value else "N/A"
        print(f"  {key}: {status} ({masked})")
    
    # Initialize security context
    print("\nInitializing security context...")
    try:
        ensure_security_context()
        session = get_session()
        print(f"   Session active, {len(session.secrets)} secrets loaded")
    except RuntimeError as e:
        print(f"\n⚠️  Security context not initialized: {e}")
        print("   Please run: ./glassdome_start")
        return 1
    
    # Migrate each secret using session's secrets manager
    print("\nMigrating secrets...")
    results = {}
    
    for key, value in secrets_to_migrate.items():
        if value:
            try:
                # Use session's set_secret_via_manager method
                success = session.set_secret_via_manager(key, value)
                results[key] = "✅ Migrated" if success else "❌ Failed"
            except Exception as e:
                results[key] = f"❌ Error: {e}"
        else:
            results[key] = "⏭️  Skipped (no value)"
    
    print("\nMigration Results:")
    for key, result in results.items():
        print(f"  {key}: {result}")
    
    # Verify migration
    print("\nVerifying migration...")
    for key in secrets_to_migrate.keys():
        stored = session.get_secret(key)
        if stored:
            print(f"  {key}: ✅ Verified in store")
        else:
            print(f"  {key}: ⚠️  Not in store")
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("\nNext steps:")
    print("  1. Comment out passwords in .env (keep host/user/port)")
    print("  2. Update network discovery scripts to use Settings class")
    print("  3. Test network device connections")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


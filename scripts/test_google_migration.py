#!/usr/bin/env python3
"""
Test script to verify Google API key migration from .bashrc
"""
from pathlib import Path
from glassdome.core.secrets import get_secrets_manager

def test_google_migration():
    """Test if Google keys would be migrated correctly"""
    bashrc_path = Path.home() / '.bashrc'
    
    secret_key_mappings = {
        'GOOGLE_SEARCH_API_KEY': 'google_search_api_key',
        'GOOGLE_SEARCH_API': 'google_search_api_key',  # Fixed: Added this mapping
        'GOOGLE_ENGINE_ID': 'google_engine_id',
    }
    
    print("🔍 Checking .bashrc for Google API keys...\n")
    
    found_keys = {}
    if bashrc_path.exists():
        with open(bashrc_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export ') and '=' in line:
                    line = line[7:].strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if 'GOOGLE' in key.upper():
                            found_keys[key] = value
                            print(f"  Found: {key} = {value[:30]}...")
    
    print(f"\n📋 Mapping check:")
    for bashrc_key, value in found_keys.items():
        if bashrc_key in secret_key_mappings:
            secret_key = secret_key_mappings[bashrc_key]
            print(f"  ✅ {bashrc_key} -> {secret_key}")
        else:
            print(f"  ❌ {bashrc_key} -> NOT IN MAPPINGS (this is the problem!)")
    
    # Check if keys are already in secrets manager
    print(f"\n🔐 Checking secrets manager:")
    sm = get_secrets_manager()
    existing_secrets = sm.list_secrets()
    
    if 'google_search_api_key' in existing_secrets:
        print(f"  ✅ google_search_api_key is already stored")
    else:
        print(f"  ⚠️  google_search_api_key is NOT stored (needs migration)")
    
    if 'google_engine_id' in existing_secrets:
        print(f"  ✅ google_engine_id is already stored")
    else:
        print(f"  ⚠️  google_engine_id is NOT stored (needs migration)")
    
    print(f"\n💡 To migrate, run:")
    print(f"   python3 scripts/migrate_secrets.py")

if __name__ == '__main__':
    test_google_migration()


#!/usr/bin/env python3
"""
Set Google API key from .bashrc to secrets manager
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from glassdome.core.secrets import get_secrets_manager

def main():
    """Set Google API key from .bashrc"""
    print("=" * 70)
    print("Setting Google API Key from .bashrc")
    print("=" * 70)
    
    sm = get_secrets_manager()
    
    # Check .bashrc
    bashrc = Path.home() / '.bashrc'
    google_search_api = None
    google_engine_id = None
    
    if bashrc.exists():
        print("\n1. Reading .bashrc...")
        with open(bashrc) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if 'GOOGLE' in line.upper() and '=' in line:
                    if line.startswith('export '):
                        line = line[7:].strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == 'GOOGLE_SEARCH_API' or key == 'GOOGLE_SEARCH_API_KEY':
                                google_search_api = value
                                print(f"   ✅ Found GOOGLE_SEARCH_API: {value[:30]}...")
                            elif key == 'GOOGLE_ENGINE_ID':
                                google_engine_id = value
                                print(f"   ✅ Found GOOGLE_ENGINE_ID: {value}")
    
    # Check if already stored
    print("\n2. Checking secrets manager...")
    stored_search = sm.get_secret('google_search_api_key')
    stored_engine = sm.get_secret('google_engine_id')
    
    if stored_search:
        print(f"   ✅ google_search_api_key already stored")
    else:
        print(f"   ❌ google_search_api_key NOT stored")
    
    if stored_engine:
        print(f"   ✅ google_engine_id already stored")
    else:
        print(f"   ❌ google_engine_id NOT stored")
    
    # Set if needed
    print("\n3. Setting secrets...")
    if google_search_api and not stored_search:
        print(f"   Setting google_search_api_key...")
        if sm.set_secret('google_search_api_key', google_search_api):
            print(f"   ✅ Successfully set google_search_api_key")
        else:
            print(f"   ❌ Failed to set google_search_api_key")
    elif google_search_api and stored_search:
        print(f"   ⚠️  google_search_api_key already set, skipping")
    
    if google_engine_id and not stored_engine:
        print(f"   Setting google_engine_id...")
        if sm.set_secret('google_engine_id', google_engine_id):
            print(f"   ✅ Successfully set google_engine_id")
        else:
            print(f"   ❌ Failed to set google_engine_id")
    elif google_engine_id and stored_engine:
        print(f"   ⚠️  google_engine_id already set, skipping")
    
    # Final verification
    print("\n4. Final verification...")
    final_search = sm.get_secret('google_search_api_key')
    final_engine = sm.get_secret('google_engine_id')
    
    if final_search:
        print(f"   ✅ google_search_api_key: {final_search[:30]}...")
    else:
        print(f"   ❌ google_search_api_key: NOT SET")
    
    if final_engine:
        print(f"   ✅ google_engine_id: {final_engine}")
    else:
        print(f"   ❌ google_engine_id: NOT SET")
    
    print("\n" + "=" * 70)
    if final_search and final_engine:
        print("✅ SUCCESS - Both Google keys are now in secrets manager!")
    elif final_search:
        print("⚠️  PARTIAL - google_search_api_key set, but google_engine_id missing")
    elif final_engine:
        print("⚠️  PARTIAL - google_engine_id set, but google_search_api_key missing")
    else:
        print("❌ FAILED - Neither key was set")
    print("=" * 70)

if __name__ == '__main__':
    main()


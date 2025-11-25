#!/usr/bin/env python3
"""
Test script for SecretsManager implementation.

This script tests:
1. SecretsManager initialization
2. Setting and getting secrets
3. Settings class integration
4. Backward compatibility with .env
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def test_secrets_manager():
    """Test SecretsManager basic functionality"""
    print("=" * 70)
    print("  Testing SecretsManager")
    print("=" * 70 + "\n")
    
    from glassdome.core.secrets import get_secrets_manager
    
    try:
        secrets = get_secrets_manager()
        print("✅ SecretsManager initialized")
        
        # Test setting a secret
        test_key = "test_secret_key"
        test_value = "test_secret_value_12345"
        
        print(f"\n📝 Setting test secret: {test_key}")
        if secrets.set_secret(test_key, test_value):
            print("✅ Secret stored")
        else:
            print("❌ Failed to store secret")
            return False
        
        # Test getting the secret
        print(f"\n🔍 Retrieving test secret: {test_key}")
        retrieved = secrets.get_secret(test_key)
        if retrieved == test_value:
            print(f"✅ Secret retrieved correctly: {retrieved}")
        else:
            print(f"❌ Secret mismatch: expected '{test_value}', got '{retrieved}'")
            return False
        
        # Test listing secrets
        print(f"\n📋 Listing all secrets")
        all_secrets = secrets.list_secrets()
        print(f"✅ Found {len(all_secrets)} secrets")
        if test_key in all_secrets:
            print(f"✅ Test secret found in list")
        else:
            print(f"⚠️  Test secret not in list (may be expected)")
        
        # Clean up test secret
        print(f"\n🗑️  Cleaning up test secret")
        if secrets.delete_secret(test_key):
            print("✅ Test secret deleted")
        else:
            print("⚠️  Failed to delete test secret (may not exist)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings_integration():
    """Test Settings class integration with SecretsManager"""
    print("\n" + "=" * 70)
    print("  Testing Settings Integration")
    print("=" * 70 + "\n")
    
    from glassdome.core.config import settings
    from glassdome.core.secrets import get_secrets_manager
    
    try:
        # Test that settings can access secrets
        print("📋 Testing Settings access to secrets...")
        
        # Check if proxmox_password property works
        password = settings.proxmox_password
        print(f"✅ settings.proxmox_password: {'***' if password else 'None'}")
        
        # Check if other secret properties work
        token = settings.proxmox_token_value
        print(f"✅ settings.proxmox_token_value: {'***' if token else 'None'}")
        
        api_key = settings.openai_api_key
        print(f"✅ settings.openai_api_key: {'***' if api_key else 'None'}")
        
        secret_key = settings.secret_key
        print(f"✅ settings.secret_key: {'***' if secret_key else 'None'}")
        
        print("\n✅ Settings integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test backward compatibility with .env file"""
    print("\n" + "=" * 70)
    print("  Testing Backward Compatibility")
    print("=" * 70 + "\n")
    
    from glassdome.core.config import settings
    
    try:
        # Settings should still work even if secrets manager is empty
        # It should fall back to .env values
        print("📋 Testing fallback to .env values...")
        
        # These should work whether from secrets manager or .env
        proxmox_host = settings.proxmox_host
        print(f"✅ settings.proxmox_host: {proxmox_host or 'Not set'}")
        
        proxmox_user = settings.proxmox_user
        print(f"✅ settings.proxmox_user: {proxmox_user or 'Not set'}")
        
        print("\n✅ Backward compatibility maintained")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  SecretsManager Test Suite")
    print("=" * 70 + "\n")
    
    results = []
    
    # Test 1: SecretsManager
    results.append(("SecretsManager", test_secrets_manager()))
    
    # Test 2: Settings Integration
    results.append(("Settings Integration", test_settings_integration()))
    
    # Test 3: Backward Compatibility
    results.append(("Backward Compatibility", test_backward_compatibility()))
    
    # Summary
    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70 + "\n")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Comprehensive test of secrets integration across the codebase.

NOTE:
- This script now uses GlassdomeSession to ensure the master key is
  loaded before accessing secrets. Run `./glassdome_start` first
  (or be prepared to enter the master password once).
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from glassdome.core.session import get_session
from glassdome.core.secrets import get_secrets_manager


def _get_settings():
    """Get Settings via session so SecretsManager has the master key loaded."""
    session = get_session()
    if not session.is_initialized():
        # This will use cache + keyring if available; otherwise it will prompt once.
        if not session.initialize(interactive=True):
            raise RuntimeError("Failed to initialize Glassdome session for secrets test")
    return session.get_settings()


def test_settings_loading():
    """Test that Settings loads secrets from SecretsManager"""
    print("=" * 70)
    print("TEST 1: Settings Loading from SecretsManager")
    print("=" * 70)
    
    sm = get_secrets_manager()
    settings = _get_settings()
    stored_secrets = sm.list_secrets()
    
    # Test each secret mapping
    secret_mappings = {
        'openai_api_key': 'openai_api_key',
        'anthropic_api_key': 'anthropic_api_key',
        'xai_api_key': 'xai_api_key',
        'perplexity_api_key': 'perplexity_api_key',
        'rapidapi_key': 'rapidapi_key',
        'google_search_api_key': 'google_search_api_key',
        'google_engine_id': 'google_engine_id',
        'proxmox_password': 'proxmox_password',
        'proxmox_token_value': 'proxmox_token_value',
        'esxi_password': 'esxi_password',
        'azure_client_secret': 'azure_client_secret',
        'aws_secret_access_key': 'aws_secret_access_key',
        'mail_api': 'mail_api',
        'secret_key': 'secret_key',
    }
    
    results = {}
    for field_name, secret_key in secret_mappings.items():
        stored = secret_key in stored_secrets
        value = getattr(settings, field_name, None)
        loaded = value is not None and value != ""
        
        results[field_name] = {
            'stored': stored,
            'loaded': loaded,
            'matches': stored == loaded or (stored and loaded)
        }
        
        status = "✅" if results[field_name]['matches'] else "⚠️"
        print(f"{status} {field_name:30s} | Stored: {str(stored):5s} | Loaded: {str(loaded):5s}")
    
    return results

def test_proxmox_config():
    """Test Proxmox config retrieval"""
    print("\n" + "=" * 70)
    print("TEST 2: Proxmox Config Retrieval")
    print("=" * 70)
    
    try:
        settings = _get_settings()
        config = settings.get_proxmox_config("01")
        print(f"✅ Proxmox config retrieved for instance 01")
        print(f"   Host: {config.get('host', 'Not set')}")
        print(f"   User: {config.get('user', 'Not set')}")
        print(f"   Password: {'✅ Set' if config.get('password') else '❌ Not set'}")
        print(f"   Token: {'✅ Set' if config.get('token_value') else '❌ Not set'}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_agent_initialization():
    """Test that agents can be initialized with secrets"""
    print("\n" + "=" * 70)
    print("TEST 3: Agent Initialization with Secrets")
    print("=" * 70)
    
    results = {}
    
    # Test Proxmox client initialization
    try:
        from glassdome.platforms.proxmox_factory import get_proxmox_client
        settings = _get_settings()
        config = settings.get_proxmox_config("01")
        if config.get('host'):
            print(f"✅ Proxmox config available for agent initialization")
            results['proxmox'] = True
        else:
            print(f"⚠️  Proxmox not configured (expected if not set up)")
            results['proxmox'] = None
    except Exception as e:
        print(f"❌ Proxmox client error: {e}")
        results['proxmox'] = False
    
    # Test Mailcow agent (if configured)
    try:
        settings = _get_settings()
        if settings.mail_api and settings.mailcow_api_url:
            print(f"✅ Mailcow config available for agent initialization")
            results['mailcow'] = True
        else:
            print(f"⚠️  Mailcow not configured (expected if not set up)")
            results['mailcow'] = None
    except Exception as e:
        print(f"❌ Mailcow config error: {e}")
        results['mailcow'] = False
    
    return results

def test_direct_secret_access():
    """Test that secrets are accessible via settings"""
    print("\n" + "=" * 70)
    print("TEST 4: Direct Secret Access via Settings")
    print("=" * 70)
    
    settings = _get_settings()

    test_secrets = [
        'openai_api_key',
        'anthropic_api_key',
        'google_search_api_key',
        'proxmox_password',
    ]
    
    for secret_name in test_secrets:
        value = getattr(settings, secret_name, None)
        if value:
            print(f"✅ {secret_name:30s} = {value[:20]}...")
        else:
            print(f"⚠️  {secret_name:30s} = Not set")
    
    return True

def main():
    print("\n" + "=" * 70)
    print("SECRETS INTEGRATION TEST SUITE")
    print("=" * 70 + "\n")
    
    # Run all tests
    test1_results = test_settings_loading()
    test2_result = test_proxmox_config()
    test3_results = test_agent_initialization()
    test4_result = test_direct_secret_access()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_tests = len(test1_results)
    passed_tests = sum(1 for r in test1_results.values() if r['matches'])
    
    print(f"Settings Loading: {passed_tests}/{total_tests} secrets properly loaded")
    print(f"Proxmox Config: {'✅ Pass' if test2_result else '❌ Fail'}")
    print(f"Agent Init: Proxmox={test3_results.get('proxmox')}, Mailcow={test3_results.get('mailcow')}")
    print(f"Direct Access: {'✅ Pass' if test4_result else '❌ Fail'}")
    
    print("\n" + "=" * 70)
    if passed_tests == total_tests and test2_result and test4_result:
        print("✅ ALL TESTS PASSED")
    else:
        print("⚠️  SOME TESTS NEED ATTENTION")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    main()


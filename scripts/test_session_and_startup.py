#!/usr/bin/env python3
"""
Test Session Management and Startup Functionality

This script verifies:
1. Session initialization works
2. Secrets are loaded correctly
3. Settings integration works
4. Startup script functionality
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from glassdome.core.session import get_session, require_session
from glassdome.core.config import Settings
from glassdome.core.secrets import get_secrets_manager
import logging

# Use centralized logging
try:
    from glassdome.core.logging import setup_logging_from_settings
    setup_logging_from_settings()
except ImportError:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_session_initialization():
    """Test that session can be initialized"""
    print("\n" + "=" * 70)
    print("TEST 1: Session Initialization")
    print("=" * 70)
    
    session = get_session()
    
    # Check if already initialized
    if session.is_initialized():
        print("✅ Session already initialized")
        print(f"   Authenticated: {session.authenticated}")
        print(f"   Secrets loaded: {len(session.secrets)}")
        print(f"   Session expires at: {session.authenticated_at + session.session_timeout if session.authenticated_at else 'N/A'}")
        return True
    else:
        print("⚠️  Session not initialized in this process")
        print("   Note: Sessions are per-process. Initializing now...")
        try:
            # Try to initialize (will prompt for password)
            success = session.initialize(interactive=True)
            if success:
                print("✅ Session initialized successfully")
                print(f"   Secrets loaded: {len(session.secrets)}")
                return True
            else:
                print("❌ Failed to initialize session")
                return False
        except KeyboardInterrupt:
            print("\n⚠️  Initialization cancelled by user")
            return False
        except Exception as e:
            print(f"❌ Error initializing session: {e}")
            return False


def test_secrets_access():
    """Test that secrets can be accessed from session"""
    print("\n" + "=" * 70)
    print("TEST 2: Secrets Access via Session")
    print("=" * 70)
    
    try:
        session = get_session()
        
        # Ensure session is initialized
        if not session.is_initialized():
            print("⚠️  Session not initialized. Attempting to initialize...")
            if not session.initialize(interactive=True):
                print("❌ Failed to initialize session")
                return False
        
        # Test accessing a few common secrets
        test_secrets = [
            'proxmox_password',
            'openai_api_key',
            'anthropic_api_key',
        ]
        
        found = 0
        for secret_key in test_secrets:
            value = session.get_secret(secret_key)
            if value:
                print(f"✅ {secret_key}: Found (length: {len(value)})")
                found += 1
            else:
                print(f"⚠️  {secret_key}: Not set")
        
        print(f"\n   Found {found}/{len(test_secrets)} test secrets")
        return True
        
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️  Test cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_settings_integration():
    """Test that Settings class works with session"""
    print("\n" + "=" * 70)
    print("TEST 3: Settings Integration")
    print("=" * 70)
    
    try:
        session = get_session()
        
        # Ensure session is initialized
        if not session.is_initialized():
            print("⚠️  Session not initialized. Attempting to initialize...")
            if not session.initialize(interactive=True):
                print("❌ Failed to initialize session")
                return False
        
        settings = session.get_settings()
        
        # Test a few settings
        tests = [
            ('backend_port', settings.backend_port),
            ('proxmox_password', settings.proxmox_password),
            ('openai_api_key', settings.openai_api_key),
        ]
        
        passed = 0
        for name, value in tests:
            if value:
                print(f"✅ {name}: Set")
                passed += 1
            else:
                print(f"⚠️  {name}: Not set (may be optional)")
        
        print(f"\n   Settings loaded: {passed}/{len(tests)} have values")
        print(f"   Backend port: {settings.backend_port}")
        return True
        
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️  Test cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_secrets_manager():
    """Test secrets manager directly"""
    print("\n" + "=" * 70)
    print("TEST 4: Secrets Manager")
    print("=" * 70)
    
    try:
        secrets = get_secrets_manager()
        all_secrets = secrets.list_secrets()
        
        print(f"✅ Secrets manager initialized")
        print(f"   Total secrets stored: {len(all_secrets)}")
        
        if all_secrets:
            print(f"   Sample secrets: {', '.join(all_secrets[:5])}")
            if len(all_secrets) > 5:
                print(f"   ... and {len(all_secrets) - 5} more")
        else:
            print("   ⚠️  No secrets found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_startup_script_check():
    """Check if startup script exists and is executable"""
    print("\n" + "=" * 70)
    print("TEST 5: Startup Script")
    print("=" * 70)
    
    startup_script = project_root / "scripts" / "start_glassdome.sh"
    convenience_script = project_root / "glassdome_start"
    
    checks = [
        (startup_script, "Main startup script"),
        (convenience_script, "Convenience wrapper"),
    ]
    
    all_ok = True
    for script_path, description in checks:
        if script_path.exists():
            if script_path.stat().st_mode & 0o111:  # Check if executable
                print(f"✅ {description}: {script_path.name} (exists, executable)")
            else:
                print(f"⚠️  {description}: {script_path.name} (exists, not executable)")
                print(f"   Run: chmod +x {script_path}")
                all_ok = False
        else:
            print(f"❌ {description}: {script_path.name} (not found)")
            all_ok = False
    
    return all_ok


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("GLASSDOME SESSION & STARTUP TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Session Initialization", test_session_initialization()))
    results.append(("Secrets Access", test_secrets_access()))
    results.append(("Settings Integration", test_settings_integration()))
    results.append(("Secrets Manager", test_secrets_manager()))
    results.append(("Startup Script", test_startup_script_check()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! System is ready.")
        print("\n💡 Note: Sessions are per-process.")
        print("   Each Python process needs its own session initialization.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review output above.")
        print("\n💡 Note: Sessions are per-process.")
        print("   Each Python process needs its own session initialization.")
        print("   The test script will prompt for password if session not initialized.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


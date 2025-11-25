#!/usr/bin/env python3
"""
Migrate API keys from .bashrc to secrets store.

This script reads API keys from ~/.bashrc and stores them in the secrets manager.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.secrets import get_secrets_manager
import getpass


def main():
    """Migrate API keys from .bashrc"""
    print("\n" + "=" * 70)
    print("  Migrate API Keys from .bashrc")
    print("=" * 70 + "\n")
    
    # Get master password
    try:
        master_password = getpass.getpass("Enter master password: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1
    
    # Initialize secrets manager and load master key
    try:
        secrets = get_secrets_manager()
        
        # Load master key using password
        from pathlib import Path
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        master_key_path = Path.home() / ".glassdome" / "master_key.enc"
        if not master_key_path.exists():
            print("❌ Secrets manager not initialized")
            return 1
        
        with open(master_key_path, 'rb') as f:
            salt = f.read(16)
            encrypted_key = f.read()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        fernet = Fernet(key)
        secrets._master_key = fernet.decrypt(encrypted_key)
        
        # Run migration
        print("\n🔄 Migrating API keys from .bashrc...")
        results = secrets.migrate_from_env(include_bashrc=True, include_environment=True)
        
        if not results:
            print("⚠️  No secrets found to migrate")
            return 0
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"\n✅ Migrated {success_count}/{total_count} secrets:\n")
        for secret_key, success in sorted(results.items()):
            status = "✅" if success else "❌"
            print(f"  {status} {secret_key}")
        
        if success_count == total_count:
            print("\n✅ Migration complete!")
            return 0
        else:
            print(f"\n⚠️  {total_count - success_count} secrets failed to migrate")
            return 1
            
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


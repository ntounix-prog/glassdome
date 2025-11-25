#!/usr/bin/env python3
"""
Fix proxmox_admin_passwd -> proxmox_password migration

If proxmox_admin_passwd exists but proxmox_password doesn't, copy it over.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.secrets import get_secrets_manager
import getpass


def main():
    """Fix the proxmox password mapping"""
    print("\n" + "=" * 70)
    print("  Fix Proxmox Password Mapping")
    print("=" * 70 + "\n")
    
    try:
        master_password = getpass.getpass("Enter master password: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1
    
    try:
        secrets = get_secrets_manager()
        
        # Load master key
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
        
        # Check if proxmox_admin_passwd exists but proxmox_password doesn't
        admin_passwd = secrets.get_secret('proxmox_admin_passwd')
        proxmox_passwd = secrets.get_secret('proxmox_password')
        
        if admin_passwd and not proxmox_passwd:
            print("📝 Found proxmox_admin_passwd, copying to proxmox_password...")
            if secrets.set_secret('proxmox_password', admin_passwd):
                print("✅ Successfully copied proxmox_admin_passwd → proxmox_password")
                print("   You can now delete proxmox_admin_passwd if desired")
                return 0
            else:
                print("❌ Failed to copy")
                return 1
        elif proxmox_passwd:
            print("✅ proxmox_password already exists")
            if admin_passwd:
                print("   Note: proxmox_admin_passwd also exists (legacy)")
            return 0
        else:
            print("⚠️  Neither proxmox_password nor proxmox_admin_passwd found")
            return 0
            
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


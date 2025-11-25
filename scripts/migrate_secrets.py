#!/usr/bin/env python3
"""
Migrate secrets from .env file to secure secrets store.

This script reads secrets from .env and stores them securely using
the SecretsManager (keyring or encrypted file).
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.secrets import get_secrets_manager


def main():
    """Migrate secrets from .env to secure store."""
    print("\n" + "=" * 70)
    print("  Glassdome Secrets Migration")
    print("  Migrating secrets from .env to secure storage")
    print("=" * 70 + "\n")
    
    env_file = PROJECT_ROOT / ".env"
    
    if not env_file.exists():
        print(f"❌ .env file not found at {env_file}")
        print("\nNothing to migrate.")
        return 1
    
    print(f"📄 Found .env file: {env_file}")
    print("\nThis will migrate the following secrets to secure storage:")
    print("  • Proxmox passwords and tokens")
    print("  • ESXi passwords")
    print("  • Azure client secrets")
    print("  • AWS secret access keys")
    print("  • API keys (OpenAI, Anthropic)")
    print("  • Mailcow API tokens")
    print("  • JWT secret keys")
    print("\n⚠️  Note: Secrets will remain in .env for backward compatibility.")
    print("   You can manually remove them after verifying migration works.\n")
    
    response = input("Continue with migration? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled.")
        return 0
    
    # Get secrets manager (will prompt for master key if first time)
    try:
        secrets = get_secrets_manager()
    except Exception as e:
        print(f"❌ Failed to initialize secrets manager: {e}")
        return 1
    
    # Migrate secrets
    print("\n🔄 Migrating secrets...")
    results = secrets.migrate_from_env(env_file)
    
    # Report results
    print("\n" + "=" * 70)
    print("  Migration Results")
    print("=" * 70 + "\n")
    
    if not results:
        print("⚠️  No secrets found to migrate.")
        return 0
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"✅ Successfully migrated: {success_count}/{total_count} secrets\n")
    
    for secret_key, success in sorted(results.items()):
        status = "✅" if success else "❌"
        print(f"  {status} {secret_key}")
    
    if success_count == total_count:
        print("\n✅ All secrets migrated successfully!")
        print("\nNext steps:")
        print("  1. Test your application to ensure secrets work correctly")
        print("  2. Once verified, you can remove secrets from .env file")
        print("  3. Keep non-secret configuration in .env (hosts, ports, etc.)")
        return 0
    else:
        print(f"\n⚠️  {total_count - success_count} secrets failed to migrate.")
        print("   Check the errors above and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


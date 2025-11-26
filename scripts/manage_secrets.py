#!/usr/bin/env python3
"""
Glassdome Secrets Manager Utility

Interactive tool to manage secrets in the Glassdome secrets store.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glassdome.core.secrets import get_secrets_manager


def list_secrets():
    """List all stored secrets (keys only)."""
    sm = get_secrets_manager()
    secrets = sm.list_secrets()
    print(f"\n📋 Stored Secrets ({len(secrets)} total):")
    print("-" * 40)
    for key in secrets:
        print(f"  • {key}")
    print()


def get_secret(key: str):
    """Get a secret value."""
    sm = get_secrets_manager()
    value = sm.get_secret(key)
    if value:
        # Mask the value
        masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "****"
        print(f"✓ {key} = {masked}")
    else:
        print(f"✗ {key} not found")


def set_secret(key: str, value: str):
    """Set a secret value."""
    sm = get_secrets_manager()
    if sm.set_secret(key, value):
        print(f"✓ Secret '{key}' stored successfully")
    else:
        print(f"✗ Failed to store secret '{key}'")


def delete_secret(key: str):
    """Delete a secret."""
    sm = get_secrets_manager()
    if sm.delete_secret(key):
        print(f"✓ Secret '{key}' deleted")
    else:
        print(f"✗ Failed to delete secret '{key}'")


def show_proxmox_config():
    """Show Proxmox configuration for all instances."""
    from glassdome.core.config import settings
    
    instances = settings.list_proxmox_instances()
    print(f"\n🖥️  Proxmox Instances ({len(instances)} configured):")
    print("-" * 50)
    
    for instance_id in instances:
        config = settings.get_proxmox_config(instance_id)
        print(f"\n  pve{instance_id}:")
        print(f"    Host:       {config.get('host')}")
        print(f"    User:       {config.get('user')}")
        print(f"    Password:   {'✓ set' if config.get('password') else '✗ missing'}")
        print(f"    Token:      {'✓ set' if config.get('token_value') else '✗ missing'}")
        print(f"    Node:       {config.get('node')}")


def interactive_mode():
    """Interactive mode for managing secrets."""
    print("\n" + "=" * 50)
    print("🔐 Glassdome Secrets Manager")
    print("=" * 50)
    
    while True:
        print("\nCommands:")
        print("  1) List all secrets")
        print("  2) Get a secret")
        print("  3) Set a secret")
        print("  4) Delete a secret")
        print("  5) Show Proxmox config")
        print("  6) Add Proxmox password for instance")
        print("  q) Quit")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == '1':
            list_secrets()
        elif choice == '2':
            key = input("Secret key: ").strip()
            if key:
                get_secret(key)
        elif choice == '3':
            key = input("Secret key: ").strip()
            value = input("Secret value: ").strip()
            if key and value:
                set_secret(key, value)
        elif choice == '4':
            key = input("Secret key: ").strip()
            if key:
                confirm = input(f"Delete '{key}'? (y/n): ").strip().lower()
                if confirm == 'y':
                    delete_secret(key)
        elif choice == '5':
            show_proxmox_config()
        elif choice == '6':
            instance = input("Instance ID (01, 02, etc): ").strip()
            password = input("Password: ").strip()
            if instance and password:
                key = f"proxmox_password_{instance}" if instance != "01" else "proxmox_password"
                set_secret(key, password)
        elif choice == 'q':
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        interactive_mode()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_secrets()
    elif command == 'get' and len(sys.argv) >= 3:
        get_secret(sys.argv[2])
    elif command == 'set' and len(sys.argv) >= 4:
        set_secret(sys.argv[2], sys.argv[3])
    elif command == 'delete' and len(sys.argv) >= 3:
        delete_secret(sys.argv[2])
    elif command == 'proxmox':
        show_proxmox_config()
    elif command == 'add-proxmox-password' and len(sys.argv) >= 4:
        instance = sys.argv[2]
        password = sys.argv[3]
        key = f"proxmox_password_{instance}" if instance != "01" else "proxmox_password"
        set_secret(key, password)
    else:
        print("Usage:")
        print("  python manage_secrets.py                    # Interactive mode")
        print("  python manage_secrets.py list               # List all secrets")
        print("  python manage_secrets.py get <key>          # Get a secret")
        print("  python manage_secrets.py set <key> <value>  # Set a secret")
        print("  python manage_secrets.py delete <key>       # Delete a secret")
        print("  python manage_secrets.py proxmox            # Show Proxmox config")
        print("  python manage_secrets.py add-proxmox-password <instance> <password>")


if __name__ == "__main__":
    main()


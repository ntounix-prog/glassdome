#!/usr/bin/env python3
"""
Automatic Template Creation via Proxmox Gateway

This script uses SSH to automatically create Ubuntu templates on Proxmox.
No manual SSH required - the agent does it all!
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path (scripts/deployment -> root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

from glassdome.platforms.proxmox_gateway import ProxmoxGateway


async def main():
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Automatic Template Creation".center(68) + "║")
    print("║" + "  Agentic SSH-based Template Setup".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Get Proxmox host
    proxmox_host = os.getenv("PROXMOX_HOST")
    
    if not proxmox_host:
        print("❌ PROXMOX_HOST not set in .env file")
        return
    
    print(f"Proxmox Host: {proxmox_host}")
    print()
    
    # Ask for SSH credentials
    print("SSH credentials needed to access Proxmox host:")
    print("(Usually 'root' user)")
    print()
    
    ssh_user = input(f"SSH Username [root]: ").strip() or "root"
    
    print()
    print("Choose authentication method:")
    print("  1. Password")
    print("  2. SSH Key")
    print()
    
    auth_choice = input("Choice [1]: ").strip() or "1"
    
    if auth_choice == "1":
        import getpass
        ssh_password = getpass.getpass("SSH Password: ")
        ssh_key = None
    else:
        ssh_key = input("SSH Key Path [~/.ssh/id_rsa]: ").strip() or "~/.ssh/id_rsa"
        ssh_key = os.path.expanduser(ssh_key)
        ssh_password = None
    
    print()
    print("=" * 70)
    print("Step 1: Connecting to Proxmox via SSH")
    print("=" * 70)
    
    # Create gateway
    gateway = ProxmoxGateway(
        host=proxmox_host,
        username=ssh_user,
        password=ssh_password,
        key_filename=ssh_key
    )
    
    # Connect
    connected = await gateway.connect()
    
    if not connected:
        print("❌ Failed to connect to Proxmox via SSH")
        print()
        print("Troubleshooting:")
        print("  • Verify SSH is enabled on Proxmox")
        print("  • Check username/password")
        print("  • Try: ssh", f"{ssh_user}@{proxmox_host}")
        return
    
    print(f"✅ Connected to Proxmox via SSH")
    print()
    
    # Check existing templates
    print("=" * 70)
    print("Step 2: Checking for existing templates")
    print("=" * 70)
    
    templates = await gateway.list_templates()
    
    if templates:
        print(f"Found {len(templates)} existing template(s):")
        for t in templates:
            print(f"  • ID {t['vmid']}: {t['name']}")
        print()
    else:
        print("No templates found")
        print()
    
    # Ask which version to create
    print("=" * 70)
    print("Step 3: Select Ubuntu version to create")
    print("=" * 70)
    print()
    print("  1. Ubuntu 22.04 LTS (Jammy) - Recommended")
    print("  2. Ubuntu 20.04 LTS (Focal)")
    print("  3. Both")
    print()
    
    version_choice = input("Choice [1]: ").strip() or "1"
    
    versions_to_create = []
    if version_choice == "1":
        versions_to_create = [("22.04", 9000)]
    elif version_choice == "2":
        versions_to_create = [("20.04", 9001)]
    elif version_choice == "3":
        versions_to_create = [("22.04", 9000), ("20.04", 9001)]
    
    print()
    
    # Create templates
    for ubuntu_version, template_id in versions_to_create:
        print("=" * 70)
        print(f"Step 4: Creating Ubuntu {ubuntu_version} template (ID {template_id})")
        print("=" * 70)
        print()
        print("This will:")
        print(f"  1. Download Ubuntu {ubuntu_version} cloud image (~600MB)")
        print(f"  2. Create VM with ID {template_id}")
        print("  3. Import cloud image as disk")
        print("  4. Configure cloud-init")
        print("  5. Convert to template")
        print()
        print("⏱️  This may take 5-10 minutes (download + setup)...")
        print()
        
        result = await gateway.create_ubuntu_template(
            template_id=template_id,
            ubuntu_version=ubuntu_version
        )
        
        if result["success"]:
            print()
            print(f"✅ Template {template_id} created successfully!")
            print()
            print("Template details:")
            print(f"  • ID: {result['template_id']}")
            print(f"  • Name: {result['name']}")
            print(f"  • Version: Ubuntu {result['ubuntu_version']}")
            print(f"  • Storage: {result['storage']}")
            print()
        else:
            print()
            print(f"❌ Failed to create template {template_id}")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print()
            if result.get('output'):
                print("Output:")
                print(result['output'])
            print()
    
    # Verify templates
    print("=" * 70)
    print("Step 5: Verifying templates")
    print("=" * 70)
    print()
    
    templates = await gateway.list_templates()
    
    if templates:
        print(f"✅ Found {len(templates)} template(s):")
        for t in templates:
            print(f"  • ID {t['vmid']}: {t['name']}")
        print()
        print("🎉 Templates are ready!")
        print()
        print("Next steps:")
        print("  1. Update .env with template IDs (if different)")
        print("  2. Run: python scripts/testing/test_vm_creation.py")
        print("  3. Deploy your first VM!")
    else:
        print("⚠️  No templates found - something went wrong")
    
    # Disconnect
    await gateway.disconnect()
    
    print()
    print("=" * 70)
    print("Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())


#!/usr/bin/env python3
"""
Interactive Proxmox Setup Wizard

This script helps you configure Glassdome to connect to your Proxmox server.
It will:
1. Collect your Proxmox credentials
2. Test the connection
3. Create/verify templates
4. Save configuration to .env file
"""
import sys
import os
import asyncio
from pathlib import Path


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step, text):
    """Print a step"""
    print(f"\n{'█' * 3} Step {step}: {text}")
    print("-" * 70)


def get_input(prompt, default=None, required=True, password=False):
    """Get user input with validation"""
    while True:
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "
        
        if password:
            import getpass
            value = getpass.getpass(full_prompt)
        else:
            value = input(full_prompt).strip()
        
        if not value and default:
            return default
        
        if not value and not required:
            return None
        
        if value:
            return value
        
        print("❌ This field is required!")


def choose_option(prompt, options):
    """Let user choose from options"""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        choice = input(f"\nChoice [1-{len(options)}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx, options[idx]
        except ValueError:
            pass
        print(f"❌ Please enter a number between 1 and {len(options)}")


async def test_connection(host, user, auth_method, credentials):
    """Test Proxmox connection"""
    print("\n🔌 Testing connection to Proxmox...")
    
    try:
        # Add to path
        sys.path.insert(0, os.path.dirname(__file__))
        from glassdome.platforms.proxmox_client import ProxmoxClient
        
        # Create client
        if auth_method == "password":
            client = ProxmoxClient(
                host=host,
                user=user,
                password=credentials,
                verify_ssl=False
            )
        else:  # token
            token_name, token_value = credentials
            client = ProxmoxClient(
                host=host,
                user=user,
                token_name=token_name,
                token_value=token_value,
                verify_ssl=False
            )
        
        # Test connection
        connected = await client.test_connection()
        
        if not connected:
            print("❌ Failed to connect!")
            return None, None
        
        print("✅ Connected successfully!")
        
        # Get nodes
        nodes = await client.list_nodes()
        if not nodes:
            print("⚠️  No nodes found!")
            return client, None
        
        print(f"\n📊 Found {len(nodes)} node(s):")
        for node in nodes:
            print(f"   • {node['node']} - {node['status']}")
        
        # Choose node
        if len(nodes) == 1:
            selected_node = nodes[0]['node']
            print(f"\n✅ Using node: {selected_node}")
        else:
            node_names = [n['node'] for n in nodes]
            idx, selected_node = choose_option("Select a node:", node_names)
        
        return client, selected_node
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("\nInstall required packages:")
        print("  pip install proxmoxer requests")
        return None, None
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return None, None


async def check_templates(client, node):
    """Check for existing templates"""
    print("\n🔍 Checking for Ubuntu templates...")
    
    try:
        vms = await client.list_vms(node)
        templates = [vm for vm in vms if vm.get('template')]
        
        if not templates:
            print("❌ No templates found!")
            return []
        
        print(f"✅ Found {len(templates)} template(s):")
        for t in templates:
            print(f"   • ID {t['vmid']}: {t.get('name', 'Unnamed')}")
        
        return templates
        
    except Exception as e:
        print(f"❌ Error checking templates: {str(e)}")
        return []


def save_env_file(config):
    """Save configuration to .env file"""
    env_path = Path(__file__).parent / ".env"
    
    print(f"\n💾 Saving configuration to {env_path}")
    
    # Read existing .env if it exists
    existing = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing[key] = value
    
    # Update with new config
    existing.update(config)
    
    # Write back
    with open(env_path, 'w') as f:
        f.write("# Glassdome Configuration\n")
        f.write("# Generated by setup_proxmox.py\n\n")
        
        f.write("# Proxmox Configuration\n")
        f.write(f"PROXMOX_HOST={existing.get('PROXMOX_HOST', '')}\n")
        f.write(f"PROXMOX_USER={existing.get('PROXMOX_USER', '')}\n")
        
        if 'PROXMOX_TOKEN_NAME' in existing:
            f.write(f"PROXMOX_TOKEN_NAME={existing.get('PROXMOX_TOKEN_NAME', '')}\n")
            f.write(f"PROXMOX_TOKEN_VALUE={existing.get('PROXMOX_TOKEN_VALUE', '')}\n")
        else:
            f.write(f"PROXMOX_PASSWORD={existing.get('PROXMOX_PASSWORD', '')}\n")
        
        f.write(f"PROXMOX_VERIFY_SSL={existing.get('PROXMOX_VERIFY_SSL', 'false')}\n")
        f.write(f"PROXMOX_NODE={existing.get('PROXMOX_NODE', 'pve')}\n\n")
        
        f.write("# Template IDs\n")
        f.write(f"UBUNTU_2204_TEMPLATE_ID={existing.get('UBUNTU_2204_TEMPLATE_ID', '9000')}\n")
        f.write(f"UBUNTU_2004_TEMPLATE_ID={existing.get('UBUNTU_2004_TEMPLATE_ID', '9001')}\n\n")
        
        f.write("# Backend Configuration\n")
        f.write(f"BACKEND_PORT={existing.get('BACKEND_PORT', '8001')}\n")
        f.write(f"VITE_PORT={existing.get('VITE_PORT', '5174')}\n")
    
    print("✅ Configuration saved!")
    print(f"\n📝 You can edit {env_path} to make changes")


async def main():
    """Main setup wizard"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Glassdome Proxmox Setup Wizard".center(68) + "║")
    print("║" + "  Configure your Proxmox connection".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Step 1: Proxmox Host
    print_step(1, "Proxmox Server Information")
    print("Enter your Proxmox server hostname or IP address")
    print("Example: proxmox.local or 192.168.1.100")
    
    host = get_input("Proxmox host")
    
    # Step 2: Authentication
    print_step(2, "Authentication Method")
    
    idx, auth_method = choose_option(
        "How do you want to authenticate?",
        [
            "API Token (Recommended - more secure)",
            "Password (Simple but less secure)"
        ]
    )
    
    if idx == 0:  # API Token
        print("\n📋 To create an API token:")
        print("  1. Open Proxmox Web UI: https://{host}:8006")
        print("  2. Go to: Datacenter → Permissions → API Tokens")
        print("  3. Click 'Add'")
        print("  4. User: root@pam")
        print("  5. Token ID: glassdome-token")
        print("  6. Uncheck 'Privilege Separation'")
        print("  7. Click 'Add'")
        print("  8. Copy the secret (shown only once!)")
        print()
        
        user = get_input("Proxmox user", default="root@pam")
        token_name = get_input("Token name", default="glassdome-token")
        token_value = get_input("Token secret (paste here)", password=True)
        
        credentials = (token_name, token_value)
        auth_type = "token"
        
    else:  # Password
        user = get_input("Proxmox user", default="root@pam")
        password = get_input("Password", password=True)
        
        credentials = password
        auth_type = "password"
    
    # Step 3: Test Connection
    print_step(3, "Testing Connection")
    
    client, node = await test_connection(host, user, auth_type, credentials)
    
    if not client:
        print("\n❌ Setup failed - could not connect to Proxmox")
        print("\nTroubleshooting:")
        print("  • Is Proxmox accessible? Try: ping", host)
        print("  • Is the API port open? Try: telnet", host, "8006")
        print("  • Are credentials correct?")
        return
    
    if not node:
        print("\n❌ Setup failed - no nodes found")
        return
    
    # Step 4: Check Templates
    print_step(4, "Checking Templates")
    
    templates = await check_templates(client, node)
    
    if not templates:
        print("\n⚠️  No templates found!")
        print("\nYou need to create Ubuntu cloud-init templates.")
        print("See: docs/PROXMOX_SETUP.md for instructions")
        print("\nQuick start:")
        print(f"  ssh root@{host}")
        print("  cd /var/lib/vz/template/iso")
        print("  wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img")
        print("  # Then run template creation commands (see docs)")
    else:
        print("\n✅ Templates found - you're ready to deploy!")
    
    # Step 5: Save Configuration
    print_step(5, "Save Configuration")
    
    save = get_input("Save configuration to .env file? (yes/no)", default="yes")
    
    if save.lower() in ['yes', 'y']:
        config = {
            'PROXMOX_HOST': host,
            'PROXMOX_USER': user,
            'PROXMOX_VERIFY_SSL': 'false',
            'PROXMOX_NODE': node,
        }
        
        if auth_type == "token":
            config['PROXMOX_TOKEN_NAME'] = credentials[0]
            config['PROXMOX_TOKEN_VALUE'] = credentials[1]
        else:
            config['PROXMOX_PASSWORD'] = credentials
        
        if templates:
            # Try to find Ubuntu 22.04 template
            ubuntu_2204 = next((t for t in templates if '22' in t.get('name', '').lower()), None)
            if ubuntu_2204:
                config['UBUNTU_2204_TEMPLATE_ID'] = str(ubuntu_2204['vmid'])
        
        save_env_file(config)
    
    # Step 6: Next Steps
    print_step(6, "Next Steps")
    
    print("\n✅ Setup complete!")
    print("\nWhat you can do now:")
    print("\n1. Test VM creation:")
    print("   python3 test_vm_creation.py")
    print("\n2. Start the API server:")
    print("   glassdome serve")
    print("   # or: python -m glassdome.server")
    print("\n3. Create a VM via API:")
    print("   curl -X POST http://localhost:8001/api/agents/ubuntu/create \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"name\": \"test-vm\", \"version\": \"22.04\"}'")
    print("\n4. Start the frontend:")
    print("   cd frontend && npm install && npm run dev")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n⚠️  This wizard will help you connect Glassdome to your Proxmox server")
    print("You'll need:")
    print("  • Proxmox server hostname/IP")
    print("  • Admin credentials (root@pam)")
    print("  • Either a password OR an API token")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        asyncio.run(main())
    else:
        print("Setup cancelled")


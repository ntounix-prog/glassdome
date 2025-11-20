#!/usr/bin/env python3
"""
Test Script: Create a Real Ubuntu VM in Proxmox

This script tests the ACTUAL implementation end-to-end
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path (scripts/testing -> root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")


async def test_proxmox_connection():
    """Test Proxmox connection"""
    print("=" * 60)
    print("TEST 1: Proxmox Connection")
    print("=" * 60)
    
    # Get credentials from environment
    host = os.getenv("PROXMOX_HOST", "proxmox.local")
    user = os.getenv("PROXMOX_USER", "root@pam")
    password = os.getenv("PROXMOX_PASSWORD")
    token_name = os.getenv("PROXMOX_TOKEN_NAME")
    token_value = os.getenv("PROXMOX_TOKEN_VALUE")
    
    print(f"Host: {host}")
    print(f"User: {user}")
    print(f"Auth: {'Token' if token_name else 'Password'}")
    
    try:
        # Initialize client
        if token_name and token_value:
            client = ProxmoxClient(
                host=host,
                user=user,
                token_name=token_name,
                token_value=token_value,
                verify_ssl=False
            )
        elif password:
            client = ProxmoxClient(
                host=host,
                user=user,
                password=password,
                verify_ssl=False
            )
        else:
            print("❌ No credentials provided!")
            print("Set PROXMOX_PASSWORD or PROXMOX_TOKEN_NAME/PROXMOX_TOKEN_VALUE")
            return None
        
        # Test connection
        connected = await client.test_connection()
        
        if connected:
            print("✅ Connected to Proxmox!")
            
            # List nodes
            nodes = await client.list_nodes()
            print(f"\nNodes: {[n['node'] for n in nodes]}")
            
            # List VMs on first node
            if nodes:
                node = nodes[0]['node']
                vms = await client.list_vms(node)
                print(f"VMs on {node}: {len(vms)}")
                
                # List templates
                templates = [vm for vm in vms if vm.get('template')]
                print(f"Templates: {[t.get('name', t['vmid']) for t in templates]}")
                
                return client, node
        else:
            print("❌ Failed to connect to Proxmox")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


async def test_vm_creation(client: ProxmoxClient, node: str):
    """Test creating a VM"""
    print("\n" + "=" * 60)
    print("TEST 2: Create Ubuntu VM")
    print("=" * 60)
    
    # Initialize agent
    agent = UbuntuInstallerAgent("test-agent", client)
    
    print(f"Agent initialized: {agent.agent_id}")
    print(f"Ubuntu versions available: {list(agent.UBUNTU_VERSIONS.keys())}")
    
    # Create task
    task = {
        "task_id": "test-001",
        "element_type": "ubuntu_vm",
        "config": {
            "node": node,
            "ubuntu_version": "22.04",
            "name": "glassdome-test-vm",
            "use_template": True,  # Use template if available
            "resources": {
                "cores": 2,
                "memory": 2048,
                "disk_size": 20
            }
        }
    }
    
    print(f"\nTask configuration:")
    print(f"  Node: {node}")
    print(f"  Version: 22.04")
    print(f"  Name: glassdome-test-vm")
    print(f"  Resources: 2 cores, 2GB RAM, 20GB disk")
    
    # Validate task
    valid = await agent.validate(task)
    print(f"\nTask validation: {'✅ Valid' if valid else '❌ Invalid'}")
    
    if not valid:
        return None
    
    # Execute task
    print("\n📦 Creating VM...")
    print("This may take 1-2 minutes...")
    
    try:
        result = await agent.execute(task)
        
        print("\n" + "-" * 60)
        
        if result.get("success"):
            print("✅ VM CREATED SUCCESSFULLY!")
            print(f"\nVM Details:")
            print(f"  VM ID: {result.get('resource_id')}")
            print(f"  Name: {result.get('vm_name')}")
            print(f"  Node: {result.get('node')}")
            print(f"  Version: {result.get('ubuntu_version')}")
            print(f"  IP Address: {result.get('ip_address', 'Not yet assigned')}")
            print(f"  Status: {result.get('status')}")
            
            return result
        else:
            print(f"❌ VM Creation Failed:")
            print(f"  Error: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ Exception during VM creation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_vm_cleanup(client: ProxmoxClient, node: str, vmid: int):
    """Clean up test VM"""
    print("\n" + "=" * 60)
    print("TEST 3: Cleanup (Optional)")
    print("=" * 60)
    
    response = input(f"\nDelete test VM {vmid}? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print(f"🗑️  Deleting VM {vmid}...")
        
        # Stop VM first
        await client.stop_vm(node, vmid)
        await asyncio.sleep(5)
        
        # Delete VM
        result = await client.delete_vm(node, vmid)
        
        if result.get("success"):
            print(f"✅ VM {vmid} deleted")
        else:
            print(f"❌ Failed to delete VM: {result.get('error')}")
    else:
        print(f"VM {vmid} kept. Delete manually if needed:")
        print(f"  qm stop {vmid} && qm destroy {vmid}")


async def main():
    """Main test flow"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Glassdome VM Creation Test".center(58) + "║")
    print("║" + "  Testing REAL Proxmox Integration".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Test 1: Connection
    result = await test_proxmox_connection()
    if not result:
        print("\n❌ Cannot proceed without Proxmox connection")
        print("\nSetup instructions:")
        print("1. Create .env file with Proxmox credentials")
        print("2. Ensure Proxmox API is accessible")
        print("3. Create Ubuntu cloud-init templates (see docs/PROXMOX_SETUP.md)")
        return
    
    client, node = result
    
    # Test 2: VM Creation
    vm_result = await test_vm_creation(client, node)
    
    if vm_result:
        vmid = vm_result.get('resource_id')
        
        # Test 3: Cleanup (optional)
        if vmid:
            await test_vm_cleanup(client, node, vmid)
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n⚠️  This script will create a REAL VM in your Proxmox server")
    print("Make sure you have:")
    print("  1. Working Proxmox server")
    print("  2. Credentials in .env file")
    print("  3. Ubuntu cloud-init template (ID 9000)")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response == 'yes':
        asyncio.run(main())
    else:
        print("Test cancelled")


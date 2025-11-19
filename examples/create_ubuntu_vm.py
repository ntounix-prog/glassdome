#!/usr/bin/env python3
"""
Example: Create Ubuntu VM using the Ubuntu Installer Agent

This demonstrates how to use the Ubuntu Installer Agent programmatically
or via API calls.
"""
import asyncio
import requests
from glassdome import ProxmoxClient
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent


async def create_vm_programmatically():
    """Create Ubuntu VM using the agent directly"""
    print("Creating Ubuntu VM programmatically...")
    
    # Initialize Proxmox client
    proxmox = ProxmoxClient(
        host="your-proxmox-host",
        user="root@pam",
        password="your-password",
        verify_ssl=False
    )
    
    # Create Ubuntu installer agent
    agent = UbuntuInstallerAgent("ubuntu_agent_1", proxmox)
    
    # Define task
    task = {
        "task_id": "ubuntu_vm_001",
        "element_type": "ubuntu_vm",
        "config": {
            "name": "ubuntu-web-server",
            "node": "pve",
            "ubuntu_version": "22.04",
            "use_template": True,
            "resources": {
                "cores": 2,
                "memory": 4096,
                "disk_size": 30,
            }
        }
    }
    
    # Execute task
    result = await agent.run(task)
    
    if result.get("success"):
        print(f"✅ VM created successfully!")
        print(f"   VM ID: {result.get('resource_id')}")
        print(f"   Name: {result.get('vm_name')}")
        print(f"   IP: {result.get('ip_address')}")
    else:
        print(f"❌ Failed: {result.get('error')}")


def create_vm_via_api():
    """Create Ubuntu VM using the REST API"""
    print("Creating Ubuntu VM via API...")
    
    api_url = "http://localhost:8001/api/ubuntu/create-sync"
    
    payload = {
        "name": "ubuntu-api-test",
        "node": "pve",
        "ubuntu_version": "22.04",
        "use_template": True,
        "cores": 2,
        "memory": 2048,
        "disk_size": 20
    }
    
    response = requests.post(api_url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("✅ VM created successfully!")
            print(f"   Details: {data.get('vm_details')}")
        else:
            print(f"❌ Failed: {data.get('error')}")
    else:
        print(f"❌ API Error: {response.status_code}")
        print(response.text)


def get_ubuntu_versions():
    """Get available Ubuntu versions"""
    print("Getting available Ubuntu versions...")
    
    response = requests.get("http://localhost:8001/api/ubuntu/versions")
    
    if response.status_code == 200:
        data = response.json()
        print("Available versions:")
        for version, info in data["versions"].items():
            print(f"  - {version}: {info['name']}")
    else:
        print(f"Error: {response.status_code}")


def check_agent_status():
    """Check Ubuntu Installer Agent status"""
    print("Checking agent status...")
    
    response = requests.get("http://localhost:8001/api/ubuntu/agent/status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Agent ID: {data.get('agent_id')}")
        print(f"Status: {data.get('status')}")
        print(f"Type: {data.get('agent_type')}")
    else:
        print(f"Error: {response.status_code}")


if __name__ == "__main__":
    print("Ubuntu VM Creation Examples")
    print("=" * 50)
    
    # Example 1: Get available versions
    print("\n1. Available Ubuntu Versions:")
    print("-" * 50)
    get_ubuntu_versions()
    
    # Example 2: Check agent status
    print("\n2. Agent Status:")
    print("-" * 50)
    check_agent_status()
    
    # Example 3: Create VM via API (uncomment to use)
    # print("\n3. Create VM via API:")
    # print("-" * 50)
    # create_vm_via_api()
    
    # Example 4: Create VM programmatically (uncomment to use)
    # print("\n4. Create VM Programmatically:")
    # print("-" * 50)
    # asyncio.run(create_vm_programmatically())
    
    print("\n" + "=" * 50)
    print("Examples complete!")


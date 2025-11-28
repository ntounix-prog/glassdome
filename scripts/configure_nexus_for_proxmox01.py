#!/usr/bin/env python3
"""
Configure Nexus 3064 ports for proxmox01 SAN access
Uses the custom SSHClient designed for Cisco devices
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.ssh_client import SSHClient
from glassdome.core.security import ensure_security_context, get_secure_settings


def get_nexus_3064_config():
    """Get Nexus 3064 configuration from secure settings."""
    ensure_security_context()
    settings = get_secure_settings()
    return settings.get_nexus_3064_config()


async def configure_nexus_ports():
    """Configure Nexus ports for proxmox01 SAN access"""
    print("="*70)
    print("Configuring Nexus 3064 for proxmox01 SAN Access")
    print("="*70)
    
    # Get Nexus configuration
    config = get_nexus_3064_config()
    
    if not config.get('host') or not config.get('password'):
        print("❌ Nexus 3064 credentials not configured")
        return False
    
    host = config['host']
    username = config.get('user', 'admin')
    password = config['password']
    
    print(f"\nNexus Host: {host}")
    print(f"Username: {username}\n")
    
    # Create SSH client
    ssh = SSHClient(
        host=host,
        username=username,
        password=password,
        timeout=30
    )
    
    try:
        # Connect
        print("1. Connecting to Nexus...")
        connected = await ssh.connect()
        
        if not connected:
            print("❌ Failed to connect to Nexus")
            return False
        
        print("✅ Connected!\n")
        
        # Check current configuration
        print("2. Checking current port configuration...\n")
        
        print("   Eth1/9 (proxmox01 nic5):")
        result = await ssh.execute("show running-config interface Ethernet1/9", check=False)
        if result['success']:
            print(result['stdout'])
        
        print("\n   Eth1/10 (proxmox01 nic4):")
        result = await ssh.execute("show running-config interface Ethernet1/10", check=False)
        if result['success']:
            print(result['stdout'])
        
        # Apply configuration
        print("\n3. Applying configuration changes...\n")
        
        commands = [
            "configure terminal",
            "interface Ethernet1/9",
            "switchport mode trunk",
            "switchport trunk allowed vlan add 212",
            "description proxmox01 nic5 (10G SAN)",
            "exit",
            "interface Ethernet1/10",
            "switchport mode trunk",
            "switchport trunk allowed vlan 211,212",
            "description proxmox01 nic4 (10G SAN)",
            "exit",
            "copy running-config startup-config"
        ]
        
        for cmd in commands:
            print(f"   > {cmd}")
            result = await ssh.execute(cmd, check=False)
            
            if not result['success']:
                print(f"      ⚠️ {result['stderr']}")
            else:
                if result['stdout'].strip():
                    print(f"      {result['stdout'].strip()}")
        
        print("\n✅ Configuration applied!\n")
        
        # Verify configuration
        print("4. Verifying configuration...\n")
        
        print("   Eth1/9:")
        result = await ssh.execute("show running-config interface Ethernet1/9", check=False)
        if result['success']:
            print(result['stdout'])
        
        print("\n   Eth1/10:")
        result = await ssh.execute("show running-config interface Ethernet1/10", check=False)
        if result['success']:
            print(result['stdout'])
        
        # Show VLAN membership
        print("\n5. Verifying VLAN membership...\n")
        
        result = await ssh.execute("show vlan id 211 | include Eth1/9|Eth1/10", check=False)
        if result['success']:
            print("   VLAN 211:", result['stdout'].strip())
        
        result = await ssh.execute("show vlan id 212 | include Eth1/9|Eth1/10", check=False)
        if result['success']:
            print("   VLAN 212:", result['stdout'].strip())
        
        await ssh.disconnect()
        
        print("\n" + "="*70)
        print("✅ Nexus configuration complete!")
        print("="*70)
        print("\nNext steps:")
        print("1. Test connectivity from proxmox01:")
        print("   ssh root@192.168.215.78")
        print("   ping -c 3 192.168.211.95")
        print("   ping -c 3 192.168.212.95")
        print("\n2. Mount NFS storage")
        print("3. Create Proxmox cluster")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await ssh.disconnect()
        except:
            pass


if __name__ == "__main__":
    result = asyncio.run(configure_nexus_ports())
    sys.exit(0 if result else 1)


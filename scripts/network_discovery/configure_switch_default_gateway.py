#!/usr/bin/env python3
"""
Configure default gateway on Cisco switches to enable routing back to agentX network.

This script sets the default gateway on both switches to 192.168.2.1 (UniFi gateway)
so they can route traffic back to 192.168.3.0/24.

Uses secure secrets management for credentials.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from glassdome.core.ssh_client import SSHClient
from glassdome.core.security import ensure_security_context, get_secure_settings

async def configure_nexus_gateway(host: str, username: str, password: str, gateway: str = "192.168.2.1"):
    """Configure default gateway on Nexus 3064 (NX-OS)"""
    print(f"\n{'='*60}")
    print(f"Configuring Nexus 3064 ({host})")
    print(f"{'='*60}")
    
    ssh = SSHClient(
        host=host,
        port=22,
        username=username,
        password=password,
        timeout=30
    )
    
    if not await ssh.connect():
        print(f"❌ Failed to connect to {host}")
        return False
    
    try:
        # Check current default route
        print("\nChecking current routing configuration...")
        result = await ssh.execute("show ip route 0.0.0.0/0", check=False)
        if result['success']:
            print("Current default route:")
            print(result['stdout'])
        
        # Configure default route (NX-OS uses 'ip route' command)
        print(f"\nConfiguring default gateway: {gateway}")
        commands = [
            f"configure terminal",
            f"ip route 0.0.0.0/0 {gateway}",
            "end",
            "copy running-config startup-config"
        ]
        
        for cmd in commands:
            print(f"  Executing: {cmd}")
            result = await ssh.execute(cmd, check=False)
            if not result['success']:
                print(f"  ⚠️  Warning: {cmd} returned: {result['stderr']}")
        
        # Verify
        print("\nVerifying default route...")
        result = await ssh.execute("show ip route 0.0.0.0/0", check=False)
        if result['success']:
            print("Updated default route:")
            print(result['stdout'])
            if gateway in result['stdout']:
                print("✅ Default gateway configured successfully!")
                return True
            else:
                print("❌ Default gateway not found in routing table")
                return False
        
    except Exception as e:
        print(f"❌ Error configuring gateway: {e}")
        return False
    finally:
        await ssh.disconnect()
    
    return False

async def configure_cisco3850_gateway(host: str, username: str, password: str, gateway: str = "192.168.2.1"):
    """Configure default gateway on Cisco 3850 (IOS-XE)"""
    print(f"\n{'='*60}")
    print(f"Configuring Cisco 3850 ({host})")
    print(f"{'='*60}")
    
    ssh = SSHClient(
        host=host,
        port=22,
        username=username,
        password=password,
        timeout=30
    )
    
    if not await ssh.connect():
        print(f"❌ Failed to connect to {host}")
        return False
    
    try:
        # Check current default gateway
        print("\nChecking current default gateway...")
        result = await ssh.execute("show ip route 0.0.0.0/0", check=False)
        if result['success']:
            print("Current default route:")
            print(result['stdout'])
        
        # Configure default gateway (IOS-XE uses 'ip default-gateway' or 'ip route')
        print(f"\nConfiguring default gateway: {gateway}")
        commands = [
            "configure terminal",
            f"ip default-gateway {gateway}",
            # Also add static route as backup
            f"ip route 0.0.0.0 0.0.0.0 {gateway}",
            "end",
            "write memory"
        ]
        
        for cmd in commands:
            print(f"  Executing: {cmd}")
            result = await ssh.execute(cmd, check=False)
            if not result['success']:
                print(f"  ⚠️  Warning: {cmd} returned: {result['stderr']}")
        
        # Verify
        print("\nVerifying default gateway...")
        result = await ssh.execute("show ip route 0.0.0.0/0", check=False)
        if result['success']:
            print("Updated default route:")
            print(result['stdout'])
            if gateway in result['stdout']:
                print("✅ Default gateway configured successfully!")
                return True
            else:
                print("❌ Default gateway not found in routing table")
                return False
        
    except Exception as e:
        print(f"❌ Error configuring gateway: {e}")
        return False
    finally:
        await ssh.disconnect()
    
    return False

async def main():
    """Main function"""
    # Initialize security context
    ensure_security_context()
    settings = get_secure_settings()
    
    # Get switch credentials from secure settings
    nexus_config = settings.get_nexus_3064_config()
    cisco_config = settings.get_cisco_3850_config()
    
    nexus_host = nexus_config.get('host', '192.168.2.224')
    nexus_user = nexus_config.get('user', 'admin')
    nexus_password = nexus_config.get('password', '')
    
    cisco_host = cisco_config.get('host', '192.168.2.253')
    cisco_user = cisco_config.get('user', 'admin')
    cisco_password = cisco_config.get('password', '')
    
    gateway = "192.168.2.1"  # UniFi gateway
    
    print("="*60)
    print("Cisco Switch Default Gateway Configuration")
    print("="*60)
    print(f"Gateway IP: {gateway}")
    print(f"Nexus 3064: {nexus_host}")
    print(f"Cisco 3850: {cisco_host}")
    print("="*60)
    
    # Configure both switches
    nexus_ok = await configure_nexus_gateway(nexus_host, nexus_user, nexus_password, gateway)
    cisco_ok = await configure_cisco3850_gateway(cisco_host, cisco_user, cisco_password, gateway)
    
    print("\n" + "="*60)
    print("Configuration Summary:")
    print("="*60)
    print(f"  Nexus 3064: {'✅ Success' if nexus_ok else '❌ Failed'}")
    print(f"  Cisco 3850: {'✅ Success' if cisco_ok else '❌ Failed'}")
    print("="*60)
    
    if nexus_ok and cisco_ok:
        print("\n✅ Both switches configured! Testing connectivity...")
        # Test ping from agentX
        import subprocess
        result = subprocess.run(['ping', '-c', '2', nexus_host], capture_output=True, text=True)
        if '0% packet loss' in result.stdout:
            print(f"✅ Nexus 3064 is now reachable!")
        else:
            print(f"⚠️  Nexus 3064 ping test: {result.stdout}")
        
        result = subprocess.run(['ping', '-c', '2', cisco_host], capture_output=True, text=True)
        if '0% packet loss' in result.stdout:
            print(f"✅ Cisco 3850 is now reachable!")
        else:
            print(f"⚠️  Cisco 3850 ping test: {result.stdout}")

if __name__ == "__main__":
    asyncio.run(main())


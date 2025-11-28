#!/usr/bin/env python3
"""
Configure Nexus 3064 ports for proxmox01 SAN access
Standalone script with embedded SSH client for Cisco devices
"""

import asyncio
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException
from pathlib import Path
from typing import Optional, Dict, Any


def load_env_file(env_file):
    """Simple .env parser"""
    env_vars = {}
    if not env_file.exists():
        return env_vars
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip().strip('"').strip("'")
                env_vars[key.strip()] = value
    return env_vars


class CiscoSSHClient:
    """SSH Client optimized for Cisco devices"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 22, timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self._connected = False
        
    async def connect(self) -> bool:
        """Establish SSH connection"""
        if self._connected:
            return True
            
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # For password auth, disable agent and key lookup (helps with Cisco devices)
            # Also enable legacy algorithms for older Nexus switches
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "password": self.password,
                "timeout": self.timeout,
                "allow_agent": False,
                "look_for_keys": False,
                "disabled_algorithms": {"pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]}
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.connect(**connect_kwargs)
            )
            
            self._connected = True
            return True
            
        except Exception as e:
            print(f"   Connection failed: {e}")
            return False
    
    async def execute(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute command on remote host"""
        if not self._connected:
            await self.connect()
        
        try:
            # Execute command in thread pool
            stdin, stdout, stderr = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.exec_command(command, timeout=timeout)
            )
            
            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                "stdout": stdout_data,
                "stderr": stderr_data,
                "exit_code": exit_code,
                "success": exit_code == 0
            }
            
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }
    
    async def disconnect(self):
        """Close SSH connection"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self._connected = False


async def configure_nexus_ports():
    """Configure Nexus ports for proxmox01 SAN access"""
    print("="*70)
    print("Configuring Nexus 3064 for proxmox01 SAN Access")
    print("="*70)
    
    # Load credentials from .env
    env_path = Path(__file__).parent.parent / '.env'
    env_vars = load_env_file(env_path)
    
    host = env_vars.get('NEXUS_3064_HOST', '192.168.2.244')
    username = env_vars.get('NEXUS_3064_USER', 'admin')
    password = env_vars.get('NEXUS_3064_PASSWORD')
    
    if not password:
        print("❌ NEXUS_3064_PASSWORD not found in .env")
        return False
    
    print(f"\nNexus Host: {host}")
    print(f"Username: {username}\n")
    
    # Create SSH client
    ssh = CiscoSSHClient(
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
        result = await ssh.execute("show running-config interface Ethernet1/9")
        if result['success']:
            for line in result['stdout'].split('\n'):
                if line.strip():
                    print(f"      {line}")
        
        print("\n   Eth1/10 (proxmox01 nic4):")
        result = await ssh.execute("show running-config interface Ethernet1/10")
        if result['success']:
            for line in result['stdout'].split('\n'):
                if line.strip():
                    print(f"      {line}")
        
        # Apply configuration
        print("\n3. Applying configuration changes...\n")
        
        # NX-OS requires interactive session for config mode
        # We'll send all commands in one session
        config_script = """
configure terminal
interface Ethernet1/9
  switchport mode trunk
  switchport trunk allowed vlan add 212
  description proxmox01 nic5 (10G SAN)
interface Ethernet1/10
  switchport mode trunk
  switchport trunk allowed vlan 211,212
  description proxmox01 nic4 (10G SAN)
copy running-config startup-config
"""
        
        print("   Applying configuration commands...")
        result = await ssh.execute(config_script)
        
        if result['success']:
            print("   ✅ Configuration applied")
            print(result['stdout'])
        else:
            print(f"   ⚠️ Configuration may have failed: {result['stderr']}")
        
        # Verify configuration
        print("\n4. Verifying configuration...\n")
        
        print("   Eth1/9:")
        result = await ssh.execute("show running-config interface Ethernet1/9")
        if result['success']:
            for line in result['stdout'].split('\n'):
                if line.strip() and not line.strip().startswith('!'):
                    print(f"      {line}")
        
        print("\n   Eth1/10:")
        result = await ssh.execute("show running-config interface Ethernet1/10")
        if result['success']:
            for line in result['stdout'].split('\n'):
                if line.strip() and not line.strip().startswith('!'):
                    print(f"      {line}")
        
        # Show VLAN membership
        print("\n5. Checking VLAN membership...\n")
        
        result = await ssh.execute("show vlan id 211")
        if result['success'] and ('Eth1/9' in result['stdout'] or 'Eth1/10' in result['stdout']):
            print("   ✅ VLAN 211: Eth1/9 and/or Eth1/10 present")
        
        result = await ssh.execute("show vlan id 212")
        if result['success'] and ('Eth1/9' in result['stdout'] or 'Eth1/10' in result['stdout']):
            print("   ✅ VLAN 212: Eth1/9 and/or Eth1/10 present")
        
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
    import sys
    result = asyncio.run(configure_nexus_ports())
    sys.exit(0 if result else 1)


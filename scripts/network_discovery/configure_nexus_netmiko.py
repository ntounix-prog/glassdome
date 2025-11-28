#!/usr/bin/env python3
"""
Configure Nexus 3064 ports for proxmox01 SAN access
Uses netmiko - the proper library for network device SSH
"""

from netmiko import ConnectHandler
from pathlib import Path


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


def configure_nexus_for_proxmox01():
    """Configure Nexus ports for proxmox01 SAN access"""
    print("="*70)
    print("Configuring Nexus 3064 for proxmox01 SAN Access (netmiko)")
    print("="*70)
    
    # Load credentials from .env
    env_path = Path(__file__).parent.parent.parent / '.env'
    env_vars = load_env_file(env_path)
    
    host = env_vars.get('NEXUS_3064_HOST', '192.168.2.244')
    username = env_vars.get('NEXUS_3064_USER', 'admin')
    password = env_vars.get('NEXUS_3064_PASSWORD')
    
    if not password:
        print("❌ NEXUS_3064_PASSWORD not found in .env")
        return False
    
    print(f"\nNexus Host: {host}")
    print(f"Username: {username}\n")
    
    # Netmiko device configuration
    nexus = {
        'device_type': 'cisco_nxos',
        'host': host,
        'username': username,
        'password': password,
        'timeout': 30,
    }
    
    try:
        print("1. Connecting to Nexus...")
        connection = ConnectHandler(**nexus)
        print("✅ Connected!\n")
        
        # Check current configuration
        print("2. Current port configuration...\n")
        
        print("   Eth1/9 (proxmox01 nic5):")
        output = connection.send_command("show running-config interface Ethernet1/9")
        for line in output.split('\n'):
            if line.strip() and not line.strip().startswith('!'):
                print(f"      {line}")
        
        print("\n   Eth1/10 (proxmox01 nic4):")
        output = connection.send_command("show running-config interface Ethernet1/10")
        for line in output.split('\n'):
            if line.strip() and not line.strip().startswith('!'):
                print(f"      {line}")
        
        # Apply configuration
        print("\n3. Applying configuration changes...\n")
        
        config_commands = [
            'interface Ethernet1/9',
            '  switchport mode trunk',
            '  switchport trunk allowed vlan add 212',
            '  description proxmox01 nic5 (10G SAN)',
            'interface Ethernet1/10',
            '  switchport mode trunk',
            '  switchport trunk allowed vlan 211,212',
            '  description proxmox01 nic4 (10G SAN)',
        ]
        
        output = connection.send_config_set(config_commands)
        print(output)
        
        # Save configuration
        print("\n4. Saving configuration...")
        output = connection.save_config()
        print(output)
        
        # Verify configuration
        print("\n5. Verifying configuration...\n")
        
        print("   Eth1/9:")
        output = connection.send_command("show running-config interface Ethernet1/9")
        for line in output.split('\n'):
            if line.strip() and not line.strip().startswith('!'):
                print(f"      {line}")
        
        print("\n   Eth1/10:")
        output = connection.send_command("show running-config interface Ethernet1/10")
        for line in output.split('\n'):
            if line.strip() and not line.strip().startswith('!'):
                print(f"      {line}")
        
        # Show VLAN membership
        print("\n6. VLAN membership...\n")
        
        output = connection.send_command("show vlan id 211")
        if 'Eth1/9' in output or 'Eth1/10' in output:
            print("   ✅ VLAN 211: Eth1/9 and/or Eth1/10 present")
            for line in output.split('\n'):
                if 'Eth1/9' in line or 'Eth1/10' in line:
                    print(f"      {line}")
        
        output = connection.send_command("show vlan id 212")
        if 'Eth1/9' in output or 'Eth1/10' in output:
            print("   ✅ VLAN 212: Eth1/9 and/or Eth1/10 present")
            for line in output.split('\n'):
                if 'Eth1/9' in line or 'Eth1/10' in line:
                    print(f"      {line}")
        
        connection.disconnect()
        
        print("\n" + "="*70)
        print("✅ Nexus configuration complete!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    result = configure_nexus_for_proxmox01()
    sys.exit(0 if result else 1)


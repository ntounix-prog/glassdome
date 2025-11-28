#!/usr/bin/env python3
"""
Find proxmox01 10G interfaces on Nexus 3064 and configure VLANs
Uses the proven sshpass + subprocess method
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


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


def get_nexus_3064_config():
    """Get Nexus 3064 configuration from .env file"""
    env_path = PROJECT_ROOT / '.env'
    env_vars = load_env_file(env_path)
    
    return {
        'host': env_vars.get('NEXUS_3064_HOST', '192.168.2.244'),
        'user': env_vars.get('NEXUS_3064_USER', 'admin'),
        'password': env_vars.get('NEXUS_3064_PASSWORD')
    }


def execute_nexus_command(host: str, username: str, password: str, command: str):
    """Execute a command on Nexus switch using SSH with legacy algorithms"""
    try:
        ssh_cmd = [
            'sshpass', '-p', password,
            'ssh',
            '-o', 'HostKeyAlgorithms=+ssh-rsa',
            '-o', 'PubkeyAcceptedAlgorithms=+ssh-rsa',
            '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'UserKnownHostsFile=/dev/null',
            f'{username}@{host}',
            command
        ]
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"⚠️ Command failed: {result.stderr[:200]}")
            return ""
    except subprocess.TimeoutExpired:
        print(f"❌ Command timeout")
        return ""
    except Exception as e:
        print(f"❌ Error: {e}")
        return ""


def find_proxmox01_ports():
    """Find which Nexus ports proxmox01 10G interfaces are connected to"""
    print("="*70)
    print("Finding proxmox01 10G Ports on Nexus 3064")
    print("="*70)
    
    # Get Nexus configuration
    config = get_nexus_3064_config()
    
    if not config.get('host') or not config.get('password'):
        print("❌ Nexus 3064 credentials not configured")
        return None
    
    host = config['host']
    username = config.get('user', 'admin')
    password = config['password']
    
    print(f"\nNexus Host: {host}")
    print(f"Username: {username}\n")
    
    # proxmox01 10G MAC addresses (from previous discovery)
    proxmox01_macs = [
        '8061.5f11.ad92',  # nic4
        '8061.5f11.ad93',  # nic5
    ]
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'nexus_host': host,
        'proxmox01_macs': proxmox01_macs,
        'found_ports': []
    }
    
    # 1. Get full MAC address table
    print("1. Querying MAC address table...")
    mac_table = execute_nexus_command(host, username, password, "show mac address-table")
    
    if not mac_table:
        print("❌ Failed to retrieve MAC address table")
        return None
    
    # Parse and find proxmox01 MACs
    found_ports = {}
    for line in mac_table.split('\n'):
        line_lower = line.lower()
        for mac in proxmox01_macs:
            if mac.lower() in line_lower:
                print(f"✅ Found MAC {mac}: {line.strip()}")
                # Parse the line to extract port and VLAN
                parts = line.split()
                if len(parts) >= 4:
                    found_ports[mac] = {
                        'vlan': parts[0] if parts[0].isdigit() else 'unknown',
                        'port': parts[-1],
                        'raw_line': line.strip()
                    }
    
    if not found_ports:
        print("\n⚠️ No MAC addresses found. Let me try a specific search...")
        for mac in proxmox01_macs:
            result = execute_nexus_command(host, username, password, f"show mac address-table | include {mac}")
            if result.strip():
                print(f"Found {mac}:")
                print(result)
    
    if not found_ports:
        print("\n❌ Could not find proxmox01 MAC addresses in Nexus MAC table")
        print("\nPossible reasons:")
        print("  1. proxmox01 10G interfaces are not connected to Nexus")
        print("  2. proxmox01 10G interfaces are connected to a different switch")
        print("  3. MACs haven't been learned yet (no traffic)")
        return None
    
    results['found_ports'] = found_ports
    
    # 2. Check current VLAN configuration on those ports
    print("\n2. Checking current port configuration...")
    for mac, port_info in found_ports.items():
        port = port_info['port']
        print(f"\n   Port {port} (MAC: {mac}):")
        
        # Get port configuration
        port_config = execute_nexus_command(
            host, username, password,
            f"show running-config interface {port}"
        )
        
        if port_config:
            print(port_config)
            results[f'port_{port}_config'] = port_config
    
    # 3. Show current VLAN 211 and 212 configuration
    print("\n3. Checking VLAN 211 and 212 configuration...")
    
    print("\n   VLAN 211 (SAN A):")
    vlan211 = execute_nexus_command(host, username, password, "show vlan id 211")
    print(vlan211)
    results['vlan_211'] = vlan211
    
    print("\n   VLAN 212 (SAN B):")
    vlan212 = execute_nexus_command(host, username, password, "show vlan id 212")
    print(vlan212)
    results['vlan_212'] = vlan212
    
    # 4. Generate configuration commands
    print("\n" + "="*70)
    print("CONFIGURATION NEEDED")
    print("="*70)
    
    config_commands = []
    for mac, port_info in found_ports.items():
        port = port_info['port']
        current_vlan = port_info['vlan']
        
        print(f"\nFor {port} (MAC: {mac}):")
        print(f"  Current VLAN: {current_vlan}")
        print(f"  Required VLANs: 211, 212")
        print(f"\n  Configuration commands:")
        
        commands = [
            "config t",
            f"interface {port}",
            "  switchport mode trunk",
            "  switchport trunk allowed vlan add 211,212",
            "  exit",
            "copy run start"
        ]
        
        for cmd in commands:
            print(f"    {cmd}")
        
        config_commands.extend(commands)
    
    results['config_commands'] = config_commands
    
    # Save results
    output_file = PROJECT_ROOT / "docs" / "proxmox01_nexus_ports.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✅ Analysis complete!")
    print(f"   Results saved to: {output_file}")
    print(f"{'='*70}")
    
    return results


if __name__ == "__main__":
    find_proxmox01_ports()


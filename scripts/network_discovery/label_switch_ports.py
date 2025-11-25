#!/usr/bin/env python3
"""
Label unlabeled switch ports based on device mapping
"""

import sys
import os
import json
import subprocess
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from glassdome.core.ssh_client import SSHClient

def read_env_config():
    """Read configuration from .env file"""
    env_file = '/home/nomad/glassdome/.env'
    config = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def load_port_mapping():
    """Load port-to-device mapping"""
    mapping_file = '/home/nomad/glassdome/docs/port_device_mapping.json'
    if os.path.exists(mapping_file):
        with open(mapping_file) as f:
            return json.load(f)
    return {}

async def get_current_descriptions(ssh, switch_type):
    """Get current interface descriptions"""
    if switch_type == 'cisco_3850':
        result = await ssh.execute("show interfaces description", check=False)
    elif switch_type == 'nexus':
        result = await ssh.execute("show interface description", check=False)
    else:
        return {}
    
    descriptions = {}
    if result['success']:
        for line in result['stdout'].split('\n'):
            line = line.strip()
            if 'GigabitEthernet' in line or 'TenGigabitEthernet' in line or 'Ethernet' in line:
                parts = line.split()
                if parts:
                    port = parts[0]
                    desc = ' '.join(parts[1:]) if len(parts) > 1 else ''
                    descriptions[port] = desc
    
    return descriptions

async def label_cisco_3850_ports():
    """Label ports on Cisco 3850"""
    config = read_env_config()
    mapping = load_port_mapping()
    
    print("="*60)
    print("Labeling Cisco 3850 Ports")
    print("="*60)
    
    ssh = SSHClient(
        host=config.get('CISCO_3850_HOST', '192.168.2.253'),
        port=int(config.get('CISCO_3850_SSH_PORT', '22')),
        username=config.get('CISCO_3850_USER', 'admin'),
        password=config.get('CISCO_3850_PASSWORD', ''),
        timeout=15
    )
    
    if not await ssh.connect():
        print("❌ Failed to connect to Cisco 3850")
        return
    
    # Get current descriptions
    print("\nGetting current interface descriptions...")
    current_descriptions = await get_current_descriptions(ssh, 'cisco_3850')
    
    # Get port mappings
    cisco_ports = mapping.get('cisco_3850', {})
    
    # Identify ports that need labeling
    ports_to_label = []
    for port, entries in cisco_ports.items():
        # Skip non-physical ports
        if 'Gi' not in port and 'Te' not in port:
            continue
        
        # Get device info
        devices = [e['device'] for e in entries if e['device'].get('hostname') != 'N/A']
        current_desc = current_descriptions.get(port, '').strip()
        
        if devices and not current_desc:
            device = devices[0]
            hostname = device.get('hostname', 'Unknown')
            ip = device.get('ip', '')
            ports_to_label.append({
                'port': port,
                'description': f"{hostname} ({ip})" if ip != 'N/A' else hostname
            })
        elif devices and current_desc:
            # Port already has description, but we can verify
            device = devices[0]
            hostname = device.get('hostname', 'Unknown')
            if hostname.lower() not in current_desc.lower():
                ports_to_label.append({
                    'port': port,
                    'description': f"{hostname} ({device.get('ip', '')})" if device.get('ip') != 'N/A' else hostname,
                    'current': current_desc
                })
    
    if not ports_to_label:
        print("\n✅ All ports are already labeled!")
        await ssh.disconnect()
        return
    
    print(f"\nFound {len(ports_to_label)} ports to label:")
    print("-"*60)
    for item in ports_to_label:
        if 'current' in item:
            print(f"  {item['port']:20} Update: '{item['current']}' -> '{item['description']}'")
        else:
            print(f"  {item['port']:20} Add: '{item['description']}'")
    
    # Generate configuration commands
    print("\n" + "="*60)
    print("Configuration Commands (DRY RUN):")
    print("="*60)
    print("configure terminal")
    for item in ports_to_label:
        port = item['port']
        desc = item['description']
        # Escape quotes in description
        desc_escaped = desc.replace('"', '\\"')
        print(f"interface {port}")
        print(f"  description {desc_escaped}")
        print("end")
    print("write memory")
    print("="*60)
    
    print("\n⚠️  This is a DRY RUN. To apply these changes:")
    print("   1. Review the commands above")
    print("   2. Run them manually on the switch, or")
    print("   3. Use --apply flag to execute automatically")
    
    await ssh.disconnect()

if __name__ == "__main__":
    asyncio.run(label_cisco_3850_ports())


#!/usr/bin/env python3
"""
Map switch ports to devices using MAC address tables and DHCP leases

Uses secure secrets management for credentials.
"""

import sys
import os
import json
import re
import requests
from datetime import datetime
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.security import ensure_security_context, get_secure_settings


def get_ubiquiti_config():
    """Get Ubiquiti configuration from secure settings."""
    ensure_security_context()
    settings = get_secure_settings()
    return settings.get_ubiquiti_config()


def get_unifi_clients():
    """Get active clients from UniFi gateway"""
    config = get_ubiquiti_config()
    base_url = f"https://{config.get('host', '192.168.2.1')}"
    api_key = config.get('api_key', '')
    site_id = "default"
    
    session = requests.Session()
    session.verify = False
    
    headers = {
        'X-API-KEY': api_key,
        'Accept': 'application/json'
    }
    
    clients = []
    
    # Try active clients first
    try:
        response = session.get(
            f'{base_url}/proxy/network/api/s/{site_id}/stat/sta',
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            clients.extend(data.get('data', []))
    except Exception as e:
        print(f"Error getting active clients: {e}")
    
    # Try DHCP leases as fallback
    try:
        response = session.get(
            f'{base_url}/proxy/network/api/s/{site_id}/stat/lease',
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            clients.extend(data.get('data', []))
    except:
        pass
    
    return clients

def parse_mac_table(mac_table_text):
    """Parse MAC address table from switch output"""
    mac_entries = []
    
    for line in mac_table_text.split('\n'):
        line = line.strip()
        if not line or 'Vlan' in line or '----' in line:
            continue
        
        # Cisco format: MAC address, VLAN, Type, Port
        # Example: "  1    0011.2233.4455    dynamic    Gi1/0/5"
        parts = line.split()
        if len(parts) >= 4:
            try:
                vlan = parts[0]
                mac = parts[1].replace('.', '').replace(':', '').upper()
                # Format MAC as XX:XX:XX:XX:XX:XX
                mac_formatted = ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
                port = parts[-1]
                mac_entries.append({
                    'mac': mac_formatted,
                    'vlan': vlan,
                    'port': port
                })
            except:
                continue
    
    return mac_entries

def normalize_mac(mac):
    """Normalize MAC address format"""
    mac = mac.upper().replace('.', '').replace(':', '').replace('-', '')
    if len(mac) == 12:
        return ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
    return mac

def load_switch_data():
    """Load discovery data from both switches"""
    cisco_data = {}
    nexus_data = {}
    
    # Load Cisco 3850 data
    cisco_file = PROJECT_ROOT / "docs" / "cisco_3850_discovery.json"
    if cisco_file.exists():
        with open(cisco_file) as f:
            cisco_data = json.load(f)
    
    # Load Nexus 3064 data
    nexus_file = PROJECT_ROOT / "docs" / "nexus_3064_discovery.json"
    if nexus_file.exists():
        with open(nexus_file) as f:
            nexus_data = json.load(f)
    
    return cisco_data, nexus_data

def map_ports_to_devices():
    """Map switch ports to devices using MAC addresses"""
    print("="*60)
    print("Port-to-Device Mapping")
    print("="*60)
    
    # Get clients from UniFi
    print("\n1. Getting clients from UniFi...")
    clients = get_unifi_clients()
    print(f"   ✅ Found {len(clients)} clients")
    
    # Create MAC to device mapping
    mac_to_device = {}
    for client in clients:
        mac = normalize_mac(client.get('mac', ''))
        if mac:
            # Use hostname or name field
            hostname = client.get('hostname') or client.get('name') or 'N/A'
            mac_to_device[mac] = {
                'ip': client.get('ip', 'N/A'),
                'hostname': hostname,
                'mac': mac
            }
    
    # Load switch data
    print("\n2. Loading switch discovery data...")
    cisco_data, nexus_data = load_switch_data()
    
    # Parse MAC tables
    print("\n3. Parsing MAC address tables...")
    cisco_macs = []
    nexus_macs = []
    
    if 'mac_table' in cisco_data:
        cisco_macs = parse_mac_table(cisco_data['mac_table'])
        print(f"   ✅ Cisco 3850: {len(cisco_macs)} MAC entries")
    
    if 'mac_table' in nexus_data:
        nexus_macs = parse_mac_table(nexus_data['mac_table'])
        print(f"   ✅ Nexus 3064: {len(nexus_macs)} MAC entries")
    
    # Map ports to devices
    print("\n4. Mapping ports to devices...")
    print("="*60)
    
    cisco_port_map = {}
    for entry in cisco_macs:
        port = entry['port']
        mac = entry['mac']
        device = mac_to_device.get(mac, {})
        
        if port not in cisco_port_map:
            cisco_port_map[port] = []
        
        cisco_port_map[port].append({
            'mac': mac,
            'vlan': entry['vlan'],
            'device': device
        })
    
    nexus_port_map = {}
    for entry in nexus_macs:
        port = entry['port']
        mac = entry['mac']
        device = mac_to_device.get(mac, {})
        
        if port not in nexus_port_map:
            nexus_port_map[port] = []
        
        nexus_port_map[port].append({
            'mac': mac,
            'vlan': entry['vlan'],
            'device': device
        })
    
    # Generate report
    print("\nCISCO 3850 - Port Mappings:")
    print("-"*60)
    unmapped_count = 0
    mapped_count = 0
    
    for port in sorted(cisco_port_map.keys()):
        entries = cisco_port_map[port]
        devices_found = [e['device'] for e in entries if e['device'].get('hostname') != 'N/A']
        
        if devices_found:
            mapped_count += 1
            device_info = devices_found[0]
            print(f"  {port:20} -> {device_info.get('hostname', 'N/A'):30} ({device_info.get('ip', 'N/A')})")
        else:
            unmapped_count += 1
            macs = [e['mac'] for e in entries]
            print(f"  {port:20} -> [Unmapped] MACs: {', '.join(macs[:2])}")
    
    print(f"\n  Mapped: {mapped_count}, Unmapped: {unmapped_count}")
    
    print("\nNEXUS 3064 - Port Mappings:")
    print("-"*60)
    unmapped_count = 0
    mapped_count = 0
    
    for port in sorted(nexus_port_map.keys()):
        entries = nexus_port_map[port]
        devices_found = [e['device'] for e in entries if e['device'].get('hostname') != 'N/A']
        
        if devices_found:
            mapped_count += 1
            device_info = devices_found[0]
            print(f"  {port:20} -> {device_info.get('hostname', 'N/A'):30} ({device_info.get('ip', 'N/A')})")
        else:
            unmapped_count += 1
            macs = [e['mac'] for e in entries]
            print(f"  {port:20} -> [Unmapped] MACs: {', '.join(macs[:2])}")
    
    print(f"\n  Mapped: {mapped_count}, Unmapped: {unmapped_count}")
    
    # Save mapping
    mapping_data = {
        'timestamp': datetime.now().isoformat(),
        'cisco_3850': cisco_port_map,
        'nexus_3064': nexus_port_map,
        'clients': len(clients)
    }
    
    output_file = PROJECT_ROOT / "docs" / "port_device_mapping.json"
    with open(output_file, 'w') as f:
        json.dump(mapping_data, f, indent=2)
    
    print(f"\n✅ Mapping saved to: {output_file}")
    print("="*60)
    
    return cisco_port_map, nexus_port_map

if __name__ == "__main__":
    map_ports_to_devices()


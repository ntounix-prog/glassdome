#!/usr/bin/env python3
"""
Discover network topology and configuration on Nexus 3064 switch
Uses legacy SSH algorithms (ssh-rsa) required by older Nexus devices

Uses secure secrets management for credentials.
"""

import sys
import os
import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from glassdome.core.security import ensure_security_context, get_secure_settings


def get_nexus_3064_config():
    """Get Nexus 3064 configuration from secure settings."""
    ensure_security_context()
    settings = get_secure_settings()
    return settings.get_nexus_3064_config()

async def execute_nexus_command(host: str, username: str, password: str, command: str, description: str):
    """Execute a command on Nexus switch using SSH with legacy algorithms"""
    try:
        # Use sshpass with legacy SSH algorithms for Nexus
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
            print(f"   ✅ {description}")
            return result.stdout
        else:
            print(f"   ⚠️  {description} - {result.stderr[:100]}")
            return ""
    except subprocess.TimeoutExpired:
        print(f"   ❌ {description} - Timeout")
        return ""
    except Exception as e:
        print(f"   ❌ {description} - Error: {e}")
        return ""

async def discover_nexus_3064():
    """Discover Nexus 3064 switch configuration"""
    print("="*60)
    print("Nexus 3064 Network Discovery")
    print("="*60)
    
    # Get secure configuration
    config = get_nexus_3064_config()
    
    if not config.get('host') or not config.get('password'):
        print("❌ Nexus 3064 not configured or credentials missing")
        print("   Ensure nexus_3064_host and nexus_3064_password are set")
        return None
    
    host = config['host']
    username = config.get('user', 'admin')
    password = config['password']
    
    discovery_data = {
        "timestamp": datetime.now().isoformat(),
        "switch": "Nexus 3064",
        "host": host,
    }
    
    # Test connectivity
    print("\nTesting connectivity...")
    result = subprocess.run(['ping', '-c', '2', host], capture_output=True)
    if result.returncode != 0:
        print("❌ Nexus not reachable")
        return None
    print("✅ Nexus is reachable!\n")
    
    # 1. Basic info
    print("1. Gathering basic switch information...")
    discovery_data['hostname'] = (await execute_nexus_command(
        host, username, password, "show running-config | include hostname", "Hostname"
    )).strip().replace('hostname ', '')
    
    discovery_data['version'] = await execute_nexus_command(
        host, username, password, "show version", "Version information"
    )
    
    # 2. Interface status
    print("\n2. Gathering interface status...")
    interfaces_raw = await execute_nexus_command(
        host, username, password, "show interface status", "Interface status"
    )
    discovery_data['interfaces_raw'] = interfaces_raw
    
    # 3. MAC address table
    print("\n3. Gathering MAC address table...")
    discovery_data['mac_table'] = await execute_nexus_command(
        host, username, password, "show mac address-table", "MAC address table"
    )
    
    # 4. CDP neighbors
    print("\n4. Gathering CDP neighbors...")
    discovery_data['cdp_neighbors'] = await execute_nexus_command(
        host, username, password, "show cdp neighbors detail", "CDP neighbors"
    )
    
    # 5. LLDP neighbors
    print("\n5. Gathering LLDP neighbors...")
    discovery_data['lldp_neighbors'] = await execute_nexus_command(
        host, username, password, "show lldp neighbors detail", "LLDP neighbors"
    )
    
    # 6. VLAN configuration
    print("\n6. Gathering VLAN configuration...")
    discovery_data['vlans'] = await execute_nexus_command(
        host, username, password, "show vlan brief", "VLAN configuration"
    )
    
    # 7. Interface descriptions
    print("\n7. Gathering interface descriptions...")
    discovery_data['interface_descriptions'] = await execute_nexus_command(
        host, username, password, "show interface description", "Interface descriptions"
    )
    
    # 8. Routing information
    print("\n8. Gathering routing information...")
    discovery_data['routing_table'] = await execute_nexus_command(
        host, username, password, "show ip route", "Routing table"
    )
    
    # 9. VRF information
    print("\n9. Gathering VRF information...")
    discovery_data['vrfs'] = await execute_nexus_command(
        host, username, password, "show vrf", "VRF configuration"
    )
    
    # Save results
    output_file = PROJECT_ROOT / "docs" / "nexus_3064_discovery.json"
    with open(output_file, 'w') as f:
        json.dump(discovery_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ Discovery complete!")
    print(f"   Results saved to: {output_file}")
    print(f"{'='*60}")
    
    return discovery_data

if __name__ == "__main__":
    asyncio.run(discover_nexus_3064())


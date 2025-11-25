#!/usr/bin/env python3
"""
Discover network topology and configuration on Cisco 3850 switch

Uses secure secrets management for credentials.
"""

import sys
import os
import asyncio
import json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from glassdome.core.ssh_client import SSHClient
from glassdome.core.security import ensure_security_context, get_secure_settings


def get_cisco_3850_config():
    """Get Cisco 3850 configuration from secure settings."""
    ensure_security_context()
    settings = get_secure_settings()
    return settings.get_cisco_3850_config()

async def execute_cisco_command(ssh: SSHClient, command: str, description: str):
    """Execute a command on Cisco switch, reconnecting if needed"""
    try:
        # Reconnect for each command (Cisco devices may close connection)
        try:
            await ssh.disconnect()
        except:
            pass
        
        await ssh.connect()
        
        result = await ssh.execute(command, check=False)
        
        if result['success']:
            print(f"   ✅ {description}")
            return result['stdout']
        else:
            print(f"   ⚠️  {description} - {result['stderr'][:100]}")
            return ""
    except Exception as e:
        print(f"   ❌ {description} - Error: {e}")
        return ""

async def discover_cisco_3850():
    """Discover Cisco 3850 switch configuration"""
    print("="*60)
    print("Cisco 3850 Network Discovery")
    print("="*60)
    
    # Get secure configuration
    config = get_cisco_3850_config()
    
    if not config.get('host') or not config.get('password'):
        print("❌ Cisco 3850 not configured or credentials missing")
        print("   Ensure cisco_3850_host and cisco_3850_password are set")
        return None
    
    ssh = SSHClient(
        host=config['host'],
        port=config.get('port', 22),
        username=config.get('user', 'admin'),
        password=config['password'],
        timeout=15
    )
    
    discovery_data = {
        "timestamp": datetime.now().isoformat(),
        "switch": "Cisco 3850",
        "host": config['host'],
    }
    
    # Test connection
    print("\nTesting connection to switch...")
    try:
        await ssh.connect()
        print("✅ Connection test successful!\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return None
    
    # 1. Basic info
    print("1. Gathering basic switch information...")
    discovery_data['hostname'] = (await execute_cisco_command(
        ssh, "show running-config | include hostname", "Hostname"
    )).strip().replace('hostname ', '')
    
    discovery_data['version'] = await execute_cisco_command(
        ssh, "show version", "Version information"
    )
    
    # 2. Interface status
    print("\n2. Gathering interface status...")
    interfaces_raw = await execute_cisco_command(
        ssh, "show interfaces status", "Interface status"
    )
    discovery_data['interfaces_raw'] = interfaces_raw
    
    # 3. MAC address table
    print("\n3. Gathering MAC address table...")
    discovery_data['mac_table'] = await execute_cisco_command(
        ssh, "show mac address-table", "MAC address table"
    )
    
    # 4. CDP neighbors
    print("\n4. Gathering CDP neighbors...")
    discovery_data['cdp_neighbors'] = await execute_cisco_command(
        ssh, "show cdp neighbors detail", "CDP neighbors"
    )
    
    # 5. LLDP neighbors
    print("\n5. Gathering LLDP neighbors...")
    discovery_data['lldp_neighbors'] = await execute_cisco_command(
        ssh, "show lldp neighbors detail", "LLDP neighbors"
    )
    
    # 6. VLAN configuration
    print("\n6. Gathering VLAN configuration...")
    discovery_data['vlans'] = await execute_cisco_command(
        ssh, "show vlan brief", "VLAN configuration"
    )
    
    # 7. Interface descriptions
    print("\n7. Gathering interface descriptions...")
    discovery_data['interface_descriptions'] = await execute_cisco_command(
        ssh, "show interfaces description", "Interface descriptions"
    )
    
    # 8. Per-interface details for connected ports
    print("\n8. Gathering detailed interface information...")
    # Get list of connected interfaces from status
    connected_ports = []
    for line in interfaces_raw.split('\n'):
        if 'connected' in line.lower() and 'GigabitEthernet' in line:
            parts = line.split()
            if parts:
                port = parts[0]
                connected_ports.append(port)
    
    discovery_data['connected_ports'] = connected_ports
    discovery_data['interface_details'] = {}
    
    for port in connected_ports[:10]:  # Limit to first 10 to avoid timeout
        print(f"   Getting details for {port}...")
        details = await execute_cisco_command(
            ssh, f"show interfaces {port}", f"Interface {port} details"
        )
        discovery_data['interface_details'][port] = details
    
    # 9. Routing information
    print("\n9. Gathering routing information...")
    discovery_data['routing_table'] = await execute_cisco_command(
        ssh, "show ip route", "Routing table"
    )
    
    # Save results
    output_file = '/home/nomad/glassdome/docs/cisco_3850_discovery.json'
    with open(output_file, 'w') as f:
        json.dump(discovery_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ Discovery complete!")
    print(f"   Results saved to: {output_file}")
    print(f"   Connected ports: {len(connected_ports)}")
    print(f"{'='*60}")
    
    await ssh.disconnect()
    return discovery_data

if __name__ == "__main__":
    asyncio.run(discover_cisco_3850())


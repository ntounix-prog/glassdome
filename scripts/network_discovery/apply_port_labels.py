#!/usr/bin/env python3
"""
Apply port labels to Cisco 3850 switch
"""

import sys
import os
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

async def apply_port_labels():
    """Apply port labels to Cisco 3850"""
    config = read_env_config()
    
    print("="*60)
    print("Applying Port Labels to Cisco 3850")
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
        return False
    
    # Ports to label
    ports_to_label = [
        ('Gi1/0/5', 'MyCloud-GWHRKK (192.168.2.111)'),
        ('Gi1/0/7', 'rh01.summit.local (192.168.2.191)'),
        ('Gi1/0/11', 'hubv3-03011107833 (192.168.2.117)'),
        ('Gi1/0/23', 'Nexus-3064-core3k-mgmt'),
        ('Gi1/0/37', 'agentX (192.168.215.228)'),
        ('Te1/1/4', 'Nexus-3064-core3k-fiber-10G'),
    ]
    
    print(f"\nLabeling {len(ports_to_label)} ports...")
    print("-"*60)
    
    # Build configuration script
    config_script = "configure terminal\n"
    for port, description in ports_to_label:
        print(f"  Adding {port} -> {description}")
        config_script += f"interface {port}\n"
        config_script += f"description {description}\n"
        config_script += "exit\n"
    config_script += "end\n"
    
    # Execute all at once
    print("\nApplying all labels...")
    result = await ssh.execute(config_script, check=False)
    
    labeled_ports = []
    failed_ports = []
    
    if result['success']:
        # All commands succeeded
        for port, description in ports_to_label:
            labeled_ports.append((port, description))
            print(f"    ✅ {port} labeled successfully")
    else:
        # Try individual commands
        print("Batch failed, trying individual commands...")
        for port, description in ports_to_label:
            print(f"  Labeling {port} -> {description}")
            
            # Reconnect
            try:
                await ssh.disconnect()
            except:
                pass
            await ssh.connect()
            
            # Single command sequence
            cmd = f"configure terminal\ninterface {port}\ndescription {description}\nexit\nend"
            result = await ssh.execute(cmd, check=False)
            
            if result['success']:
                labeled_ports.append((port, description))
                print(f"    ✅ Labeled successfully")
            else:
                failed_ports.append((port, description, result.get('stderr', 'Unknown error')))
                print(f"    ⚠️  Failed")
    
    # Save configuration
    print("\nSaving configuration...")
    try:
        await ssh.disconnect()
    except:
        pass
    
    await ssh.connect()
    result = await ssh.execute("write memory", check=False)
    
    if result['success']:
        print("✅ Configuration saved!")
    else:
        print(f"⚠️  Warning: Failed to save configuration: {result.get('stderr', 'Unknown error')}")
    
    await ssh.disconnect()
    
    print("\n" + "="*60)
    print("Labeling Summary:")
    print("="*60)
    print(f"  ✅ Successfully labeled: {len(labeled_ports)}")
    print(f"  ❌ Failed: {len(failed_ports)}")
    
    if labeled_ports:
        print("\n  Labeled ports:")
        for port, desc in labeled_ports:
            print(f"    {port:20} -> {desc}")
    
    if failed_ports:
        print("\n  Failed ports:")
        for port, desc, error in failed_ports:
            print(f"    {port:20} -> {desc} (Error: {error[:50]})")
    
    print("="*60)
    
    return {
        'success': len(failed_ports) == 0,
        'labeled': labeled_ports,
        'failed': failed_ports
    }

if __name__ == "__main__":
    result = asyncio.run(apply_port_labels())
    sys.exit(0 if result.get('success', False) else 1)


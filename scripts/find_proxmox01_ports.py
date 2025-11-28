#!/usr/bin/env python3
"""
Find proxmox01 10G ports on Nexus 3064 and configure VLANs 211, 212
"""
import paramiko
import time
import os
import sys
from pathlib import Path

# Simple .env parser
def load_env_file(env_file):
    env_vars = {}
    if not env_file.exists():
        return env_vars
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip().strip('"').strip("'")
                env_vars[key.strip()] = value
    return env_vars

# Load .env
env_path = Path(__file__).parent.parent / '.env'
env_vars = load_env_file(env_path)

# Configuration
NEXUS_HOST = env_vars.get('NEXUS_3064_HOST', '192.168.2.244')
NEXUS_USER = 'admin'
NEXUS_PASS = env_vars.get('NEXUS_3064_PASSWORD')

if not NEXUS_PASS:
    print("❌ NEXUS_3064_PASSWORD not found in .env")
    sys.exit(1)

print(f"DEBUG: Host={NEXUS_HOST}, User={NEXUS_USER}, Pass length={len(NEXUS_PASS)}")

# proxmox01 10G MAC addresses
PROXMOX01_MACS = [
    '8061.5f11.ad92',  # nic4
    '8061.5f11.ad93',  # nic5
]

print("="*70)
print("Finding proxmox01 10G ports on Nexus 3064")
print("="*70)

# Connect to Nexus
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(
        NEXUS_HOST,
        username=NEXUS_USER,
        password=NEXUS_PASS,
        look_for_keys=False,
        allow_agent=False
    )
    
    print(f"✅ Connected to {NEXUS_HOST}\n")
    
    # Execute command
    stdin, stdout, stderr = ssh.exec_command('show mac address-table | include 8061.5f11.ad9')
    time.sleep(1)
    output = stdout.read().decode()
    
    print("MAC Address Table (proxmox01):")
    print(output)
    
    if not output.strip():
        print("⚠️  No MACs found, trying broader search...")
        stdin, stdout, stderr = ssh.exec_command('show mac address-table')
        time.sleep(2)
        full_output = stdout.read().decode()
        
        for line in full_output.split('\n'):
            if '8061.5f11' in line.lower():
                print(line)
    
    # Get VLAN configuration
    print("\n" + "="*70)
    print("VLAN 211 Configuration:")
    print("="*70)
    stdin, stdout, stderr = ssh.exec_command('show vlan id 211')
    time.sleep(1)
    print(stdout.read().decode())
    
    print("\n" + "="*70)
    print("VLAN 212 Configuration:")
    print("="*70)
    stdin, stdout, stderr = ssh.exec_command('show vlan id 212')
    time.sleep(1)
    print(stdout.read().decode())
    
    # Show connected interfaces
    print("\n" + "="*70)
    print("Connected Interfaces:")
    print("="*70)
    stdin, stdout, stderr = ssh.exec_command('show interface status | include connected')
    time.sleep(1)
    connected = stdout.read().decode()
    print(connected)
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    ssh.close()

print("\n" + "="*70)
print("Next Steps:")
print("="*70)
print("""
Once we identify the ports (e.g., Eth1/X), we need to configure them:

For each port connected to proxmox01 nic4/nic5:
  1. Set as trunk mode
  2. Add VLANs 211, 212 to allowed list
  3. Configure native VLAN if needed

Example NX-OS commands:
  config t
  interface Ethernet1/X
    switchport mode trunk
    switchport trunk allowed vlan add 211,212
  exit
  copy run start
""")


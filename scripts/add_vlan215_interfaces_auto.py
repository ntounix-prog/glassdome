#!/usr/bin/env python3
"""
Automatically add VLAN 215 interfaces to Proxmox and agentX VM
Uses Proxmox API to add interface, then waits for DHCP assignment
"""
import sys
import os
import asyncio
import subprocess
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Read .env directly to avoid config validation issues
env_file = Path(__file__).parent.parent / ".env"
config = {}
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

PROXMOX_HOST = config.get("PROXMOX_HOST", "10.0.0.1")
PROXMOX_USER = config.get("PROXMOX_USER", "apex@pve")
PROXMOX_TOKEN_NAME = config.get("PROXMOX_TOKEN_NAME", "glassdome-token")
PROXMOX_TOKEN_VALUE = config.get("PROXMOX_TOKEN_VALUE")
AGENTX_VMID = 100  # Default, will try to detect

print("=" * 70)
print("Add VLAN 215 Interfaces for Direct Proxmox Access")
print("=" * 70)
print(f"Proxmox Host: {PROXMOX_HOST}")
print(f"VLAN: 215")
print(f"Network: 192.168.215.0/24 (DHCP)")
print("")

# Step 1: Find bridge for 192.168.215.0/24
print("Step 1: Finding bridge for 192.168.215.0/24...")
try:
    result = subprocess.run(
        f"ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} 'ip addr show | grep -B 2 192.168.215'",
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode == 0 and result.stdout:
        # Extract bridge name from output
        lines = result.stdout.split('\n')
        for line in lines:
            if 'inet' in line and '192.168.215' in line:
                # Get interface name from previous line
                for prev_line in lines:
                    if prev_line.strip().startswith(('vmbr', 'ens', 'enp')):
                        bridge_name = prev_line.split(':')[1].split('@')[0].strip()
                        print(f"✅ Found bridge: {bridge_name}")
                        break
                break
        else:
            bridge_name = "vmbr0"  # Default
            print(f"⚠️  Could not detect bridge, using default: {bridge_name}")
    else:
        bridge_name = "vmbr0"  # Default
        print(f"⚠️  Could not detect bridge, using default: {bridge_name}")
except Exception as e:
    bridge_name = "vmbr0"  # Default
    print(f"⚠️  Error detecting bridge: {e}, using default: {bridge_name}")

# Allow bridge override via command line or use default
if "--bridge" in sys.argv:
    idx = sys.argv.index("--bridge")
    if idx + 1 < len(sys.argv):
        bridge_name = sys.argv[idx + 1]
        print(f"Using bridge from command line: {bridge_name}")
else:
    print(f"Using detected/default bridge: {bridge_name}")

print(f"\nUsing bridge: {bridge_name}")

# Step 2: Find agentX VM ID
print("\nStep 2: Finding agentX VM ID...")
try:
    result = subprocess.run(
        f"ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} 'qm list | grep -i agent'",
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode == 0 and result.stdout:
        # Extract VM ID
        for line in result.stdout.split('\n'):
            if 'agent' in line.lower():
                parts = line.split()
                if parts:
                    AGENTX_VMID = int(parts[0])
                    print(f"✅ Found agentX: VM {AGENTX_VMID}")
                    break
    else:
        print(f"⚠️  Could not find agentX, using default VM ID: {AGENTX_VMID}")
except Exception as e:
    print(f"⚠️  Error finding agentX: {e}, using default VM ID: {AGENTX_VMID}")

# Step 3: Add network interface to agentX
print(f"\nStep 3: Adding VLAN 215 interface to agentX (VM {AGENTX_VMID})...")
print(f"Command: qm set {AGENTX_VMID} --net1 virtio,bridge={bridge_name},tag=215,firewall=0")

dry_run = "--execute" not in sys.argv
if dry_run:
    print("\n⚠️  DRY RUN - Add --execute to actually run")
else:
    try:
        cmd = f"ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} 'qm set {AGENTX_VMID} --net1 virtio,bridge={bridge_name},tag=215,firewall=0'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Interface added to agentX VM")
        else:
            print(f"❌ Failed to add interface: {result.stderr}")
            print(f"   You may need to run manually:")
            print(f"   ssh root@{PROXMOX_HOST} 'qm set {AGENTX_VMID} --net1 virtio,bridge={bridge_name},tag=215,firewall=0'")
    except Exception as e:
        print(f"❌ Error: {e}")

# Step 4: Instructions for next steps
print("\n" + "=" * 70)
print("Next Steps")
print("=" * 70)
print("1. The new interface on agentX will get an IP via DHCP")
print("2. You may need to restart the VM or wait for network to initialize")
print("3. Check IP assignment:")
print(f"   ssh root@10.0.0.2 'ip addr show | grep 192.168.215'")
print("4. Test connectivity to original Proxmox:")
print("   ping 192.168.215.78")
print("   ssh root@192.168.215.78 'echo Connected'")
print("")
print("=" * 70)


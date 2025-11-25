#!/usr/bin/env python3
"""
Setup VLAN 215 interface on agentX using storage network (nic4/nic5)
Since bridges are VLAN-aware, we just need to tag the VM interface
"""
import sys
import subprocess
from pathlib import Path

# Read .env
env_file = Path(__file__).parent.parent / ".env"
config = {}
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

PROXMOX_HOST = config.get("PROXMOX_HOST", "10.0.0.1")
AGENTX_VMID = 100

print("=" * 70)
print("Setup VLAN 215 Interface on Storage Network")
print("=" * 70)
print(f"Proxmox Host: {PROXMOX_HOST}")
print(f"agentX VM ID: {AGENTX_VMID}")
print(f"VLAN: 215 (DHCP on 192.168.215.0/24)")
print("")

# Step 1: Identify bridge that uses nic4/nic5
print("Step 1: Identifying storage network bridge...")
print("")
print("To find which bridge uses nic4/nic5, run on Proxmox:")
print(f"  ssh root@{PROXMOX_HOST} 'cat /etc/network/interfaces | grep -E \"nic4|nic5\" -B 2 -A 5'")
print("")
print("Common bridges: vmbr0, vmbr1, vmbr2")
print("")

# Get bridge from command line or use default
bridge = "vmbr0"  # Default
if "--bridge" in sys.argv:
    idx = sys.argv.index("--bridge")
    if idx + 1 < len(sys.argv):
        bridge = sys.argv[idx + 1]

print(f"Using bridge: {bridge}")
print("(If incorrect, use --bridge <name> to specify)")
print("")

# Step 2: Add interface command
print("Step 2: Add VLAN 215 interface to agentX")
print("")
cmd = f"qm set {AGENTX_VMID} --net1 virtio,bridge={bridge},tag=215,firewall=0"
print(f"Command to run on Proxmox ({PROXMOX_HOST}):")
print(f"  {cmd}")
print("")

dry_run = "--execute" not in sys.argv
if dry_run:
    print("⚠️  DRY RUN - Add --execute to run the command")
    print("")
    print("Or run manually:")
    print(f"  ssh root@{PROXMOX_HOST} '{cmd}'")
else:
    print("Executing command...")
    try:
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} '{cmd}'"
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Interface added successfully!")
        else:
            print(f"❌ Failed: {result.stderr}")
            print("")
            print("Please run manually:")
            print(f"  ssh root@{PROXMOX_HOST}")
            print(f"  {cmd}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("")
        print("Please run manually:")
        print(f"  ssh root@{PROXMOX_HOST}")
        print(f"  {cmd}")

print("")
print("=" * 70)
print("Next Steps")
print("=" * 70)
print("1. Interface added to agentX VM")
print("2. Wait a few seconds for interface to initialize")
print("3. Check IP assignment on agentX:")
print("   ip addr show | grep 192.168.215")
print("4. Test connectivity:")
print("   ping 192.168.215.78")
print("   ssh root@192.168.215.78 'echo Connected'")
print("")
print("=" * 70)


#!/usr/bin/env python3
"""
Standalone Template Finder - No Dependencies

Finds template files on Proxmox server using direct API calls.
Only requires: requests (or use curl commands provided)
"""
import sys
import os
import re
import json
from pathlib import Path

def read_env():
    """Read .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return None
    
    config = {}
    for line in env_path.read_text().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()
    return config

def main():
    print("="*70)
    print("  PROXMOX TEMPLATE FINDER")
    print("="*70)
    print()
    
    config = read_env()
    if not config:
        print("❌ .env file not found")
        return 1
    
    host = config.get("PROXMOX_HOST") or config.get("PROXMOX_02_HOST")
    user = config.get("PROXMOX_USER") or "apex@pve"
    token_name = config.get("PROXMOX_TOKEN_NAME")
    token_value = config.get("PROXMOX_TOKEN_VALUE") or config.get("PROXMOX_TOKEN_VALUE_02")
    password = config.get("PROXMOX_PASSWORD")
    
    if not host:
        print("❌ PROXMOX_HOST not found")
        return 1
    
    search_path = sys.argv[1] if len(sys.argv) > 1 else "/mnt"
    
    print(f"Proxmox Host: {host}")
    print(f"Search Path: {search_path}")
    print()
    
    # Since we can't easily execute commands via API without proxmoxer,
    # provide the exact commands to run
    print("="*70)
    print("  COMMANDS TO RUN ON PROXMOX SERVER")
    print("="*70)
    print()
    print("SSH to Proxmox and run these commands:")
    print()
    print(f"# Find all template files in {search_path}:")
    print(f"find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*.qcow2' -o -name '*.raw' -o -name '*.img' -o -name '*.iso' \\) -size +100M -exec ls -lh {{}} \\; 2>/dev/null")
    print()
    print("# Or save to file for review:")
    print(f"find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*.qcow2' -o -name '*.raw' -o -name '*.img' -o -name '*.iso' \\) -size +100M -exec ls -lh {{}} \\; 2>/dev/null > /tmp/template_files.txt")
    print("cat /tmp/template_files.txt")
    print()
    print("="*70)
    print("  EXPECTED TEMPLATE FILES")
    print("="*70)
    print()
    print("Look for files like:")
    print("  - vm-9000-disk-0.raw (Ubuntu 22.04 template)")
    print("  - vm-9100-disk-0.raw (Windows Server 2022 template)")
    print("  - vm-9101-disk-0.raw (Windows 11 template)")
    print("  - vm-9102-disk-0.raw (Windows 10 template)")
    print("  - ubuntu-22.04-server-cloudimg-amd64.img")
    print("  - windows-server-2022-eval.iso")
    print("  - windows-11-enterprise-eval.iso")
    print("  - virtio-win.iso")
    print()
    print("="*70)
    print("  RELOCATION COMMANDS")
    print("="*70)
    print()
    print("# For ISOs, move to:")
    print("mv /mnt/path/to/file.iso /var/lib/vz/template/iso/")
    print()
    print("# For VM disks, import to storage:")
    print("qm importdisk <vmid> /mnt/path/to/vm-<vmid>-disk-0.raw local-lvm")
    print("qm set <vmid> --scsi0 local-lvm:vm-<vmid>-disk-0")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


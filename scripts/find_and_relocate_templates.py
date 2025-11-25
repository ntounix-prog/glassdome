#!/usr/bin/env python3
"""
Find and Relocate Proxmox Templates

After SAN rebuild, finds unlinked template files in /mnt subfolders
and helps relocate them to proper Proxmox storage locations.
"""
import sys
import os
import subprocess
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.config import settings
from glassdome.platforms.proxmox_factory import get_proxmox_client
from glassdome.core.ssh_client import SSHClient


async def find_template_files_on_proxmox(ssh_client, search_path: str = "/mnt") -> List[Dict[str, any]]:
    """
    Find template-related files in /mnt subfolders on Proxmox server via SSH.
    
    Args:
        ssh_client: SSHClient connected to Proxmox host
        search_path: Path to search on Proxmox server (default: /mnt)
    
    Returns:
        List of dicts with file info: path, size, type, vm_id (if detectable)
    """
    template_files = []
    
    print(f"🔍 Searching for template files in {search_path} on Proxmox server...")
    print()
    
    # Use find command via SSH to search for template files
    # Find VM disk images
    find_cmd = f"find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*.qcow2' -o -name '*.raw' -o -name '*.img' -o -name '*.iso' \\) -size +100M -exec ls -lh {{}} \\; 2>/dev/null"
    
    result = await ssh_client.execute(find_cmd)
    if not result.success:
        print(f"⚠️  Search command failed: {result.stderr}")
        return []
    
    # Parse find output
    for line in result.stdout.split('\n'):
        if not line.strip():
            continue
        
        # Parse ls -lh output: -rw-r--r-- 1 root root 4.7G Nov 22 10:00 /mnt/path/to/file
        parts = line.split()
        if len(parts) < 9:
            continue
        
        # Extract file path (last part)
        filepath = ' '.join(parts[8:])
        filename = os.path.basename(filepath)
        
        # Extract size (5th part, e.g., "4.7G")
        size_str = parts[4]
        # Convert size to GB
        try:
            if size_str.endswith('G'):
                size_gb = float(size_str[:-1])
            elif size_str.endswith('M'):
                size_gb = float(size_str[:-1]) / 1024
            else:
                continue  # Skip if can't parse
        except:
            continue
        
        # Check if it matches template patterns
        is_template = False
        vm_id = None
        file_type = "unknown"
        
        # Pattern 1: vm-XXXX-disk-Y format
        match = re.search(r"vm-(\d+)-disk-(\d+)", filename)
        if match:
            vm_id = int(match.group(1))
            is_template = True
            file_type = "vm_disk"
        
        # Pattern 2: Direct VM ID files
        match = re.search(r"^(\d+)\.(qcow2|raw|img|vmdk)$", filename)
        if match:
            vm_id = int(match.group(1))
            is_template = True
            file_type = "vm_disk"
        
        # Pattern 3: Ubuntu cloud images
        if "ubuntu" in filename.lower() and "cloudimg" in filename.lower():
            is_template = True
            file_type = "ubuntu_cloud_image"
        
        # Pattern 4: Windows ISOs
        if "windows" in filename.lower() and filename.endswith(".iso"):
            is_template = True
            file_type = "windows_iso"
        
        # Pattern 5: VirtIO ISOs
        if "virtio" in filename.lower() and filename.endswith(".iso"):
            is_template = True
            file_type = "virtio_iso"
        
        if is_template:
            template_files.append({
                "path": filepath,
                "size_gb": size_gb,
                "type": file_type,
                "vm_id": vm_id,
                "filename": filename
            })
    
    return sorted(template_files, key=lambda x: x["size_gb"], reverse=True)


def get_proxmox_storage_info(proxmox_client, node: str = None) -> Dict[str, any]:
    """Get Proxmox storage information"""
    try:
        if not node:
            node = proxmox_client.default_node
        
        # Get storage list
        storage_list = proxmox_client.client.nodes(node).storage.get()
        
        storage_info = {}
        for storage in storage_list:
            storage_name = storage.get("storage")
            storage_type = storage.get("type")
            storage_info[storage_name] = {
                "type": storage_type,
                "content": storage.get("content", []),
                "path": storage.get("path", ""),
            }
        
        return storage_info
    except Exception as e:
        print(f"⚠️  Could not get storage info: {e}")
        return {}


def get_proxmox_vms(proxmox_client, node: str = None) -> Dict[int, Dict]:
    """Get list of VMs and templates from Proxmox"""
    try:
        if not node:
            node = proxmox_client.default_node
        
        vms = proxmox_client.client.nodes(node).qemu.get()
        
        vm_dict = {}
        for vm in vms:
            vmid = vm.get("vmid")
            vm_dict[vmid] = {
                "name": vm.get("name"),
                "status": vm.get("status"),
                "template": vm.get("template", 0) == 1,
            }
        
        return vm_dict
    except Exception as e:
        print(f"⚠️  Could not get VM list: {e}")
        return {}


def suggest_location(file_info: Dict, storage_info: Dict, vm_info: Dict) -> Optional[str]:
    """
    Suggest where a file should be relocated.
    
    Returns:
        Suggested destination path or None
    """
    file_type = file_info["type"]
    vm_id = file_info.get("vm_id")
    
    # VM disk images
    if file_type == "vm_disk" and vm_id:
        # Check if VM exists
        if vm_id in vm_info:
            vm = vm_info[vm_id]
            if vm["template"]:
                # Template disk - should be in storage pool
                # Check for local-lvm first
                if "local-lvm" in storage_info:
                    return f"local-lvm:vm-{vm_id}-disk-0"
                # Or any LVM storage
                for storage_name, storage in storage_info.items():
                    if storage["type"] == "lvm" or storage["type"] == "lvmthin":
                        return f"{storage_name}:vm-{vm_id}-disk-0"
        else:
            # VM doesn't exist - might be orphaned
            return f"ORPHANED:vm-{vm_id}-disk-0"
    
    # Ubuntu cloud images
    if file_type == "ubuntu_cloud_image":
        return "/var/lib/vz/template/iso/"
    
    # Windows ISOs
    if file_type == "windows_iso":
        return "/var/lib/vz/template/iso/"
    
    # VirtIO ISOs
    if file_type == "virtio_iso":
        return "/var/lib/vz/template/iso/"
    
    return None


async def main_async():
    """Main async function"""
    print("="*70)
    print("  PROXMOX TEMPLATE FINDER & RELOCATOR")
    print("="*70)
    print()
    
    # Get Proxmox client
    try:
        proxmox = get_proxmox_client("01")  # Use instance 01 by default
        print(f"✅ Connected to Proxmox API: {proxmox.host}")
    except Exception as e:
        print(f"❌ Failed to connect to Proxmox: {e}")
        print("   Make sure PROXMOX_HOST and credentials are set in .env")
        return 1
    
    # Connect via SSH to Proxmox host
    print("\n🔌 Connecting to Proxmox via SSH...")
    config = settings.get_proxmox_config("01")
    ssh = SSHClient(
        host=config["host"],
        username="root",
        password=config.get("password") or settings.proxmox_password
    )
    
    connected = await ssh.connect()
    if not connected:
        print(f"❌ Failed to connect via SSH to {config['host']}")
        print("   Check PROXMOX_PASSWORD in .env")
        return 1
    
    print(f"✅ Connected via SSH to {config['host']}")
    
    # Get storage and VM info
    print("\n📊 Gathering Proxmox information...")
    storage_info = get_proxmox_storage_info(proxmox)
    vm_info = get_proxmox_vms(proxmox)
    
    print(f"   Storage pools: {', '.join(storage_info.keys())}")
    print(f"   VMs/Templates: {len(vm_info)}")
    print()
    
    # Find template files on Proxmox server
    search_path = input("Enter search path on Proxmox server (default: /mnt): ").strip() or "/mnt"
    template_files = await find_template_files_on_proxmox(ssh, search_path)
    
    if not template_files:
        print("❌ No template files found in /mnt")
        print("\n   Try:")
        print("   - Check if files are in a different location")
        print("   - Verify search path is correct")
        return 1
    
    print(f"✅ Found {len(template_files)} template-related files:")
    print()
    
    # Display found files
    for i, file_info in enumerate(template_files, 1):
        suggested = suggest_location(file_info, storage_info, vm_info)
        
        print(f"{i}. {file_info['filename']}")
        print(f"   Path: {file_info['path']}")
        print(f"   Size: {file_info['size_gb']:.2f} GB")
        print(f"   Type: {file_info['type']}")
        if file_info.get('vm_id'):
            vm = vm_info.get(file_info['vm_id'], {})
            if vm:
                template_status = "Template" if vm.get('template') else "VM"
                print(f"   VM ID: {file_info['vm_id']} ({vm.get('name', 'Unknown')} - {template_status})")
            else:
                print(f"   VM ID: {file_info['vm_id']} (NOT FOUND in Proxmox - orphaned?)")
        if suggested:
            print(f"   → Suggested location: {suggested}")
        print()
    
    # Ask user what to do
    print("="*70)
    print("  RELOCATION OPTIONS")
    print("="*70)
    print()
    print("1. Show relocation commands (copy/paste to run manually)")
    print("2. Interactive relocation (asks for each file)")
    print("3. Exit")
    print()
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == "1":
        print("\n" + "="*70)
        print("  RELOCATION COMMANDS")
        print("="*70)
        print()
        print("# Run these commands on Proxmox host (SSH as root):")
        print()
        
        for file_info in template_files:
            suggested = suggest_location(file_info, storage_info, vm_info)
            if not suggested:
                continue
            
            source = file_info['path']
            
            # For ISOs
            if file_info['type'] in ['ubuntu_cloud_image', 'windows_iso', 'virtio_iso']:
                dest = f"/var/lib/vz/template/iso/{file_info['filename']}"
                print(f"# {file_info['filename']} ({file_info['size_gb']:.2f} GB)")
                print(f"mv {source} {dest}")
                print()
            
            # For VM disks
            elif file_info['type'] == 'vm_disk' and file_info.get('vm_id'):
                vm_id = file_info['vm_id']
                # Need to import to storage pool
                print(f"# VM {vm_id} disk ({file_info['size_gb']:.2f} GB)")
                print(f"# First, check if VM {vm_id} exists:")
                print(f"ssh root@{proxmox.host} 'qm config {vm_id}'")
                print(f"# If VM exists, import disk:")
                if 'local-lvm' in storage_info:
                    print(f"ssh root@{proxmox.host} 'qm importdisk {vm_id} {source} local-lvm'")
                else:
                    storage_name = list(storage_info.keys())[0] if storage_info else "STORAGE_NAME"
                    print(f"ssh root@{proxmox.host} 'qm importdisk {vm_id} {source} {storage_name}'")
                print()
    
    elif choice == "2":
        print("\n" + "="*70)
        print("  INTERACTIVE RELOCATION")
        print("="*70)
        print()
        print("⚠️  This will move files. Make sure you have backups!")
        print()
        
        for file_info in template_files:
            suggested = suggest_location(file_info, storage_info, vm_info)
            if not suggested:
                print(f"⚠️  Skipping {file_info['filename']} (no suggested location)")
                continue
            
            print(f"\n📁 {file_info['filename']} ({file_info['size_gb']:.2f} GB)")
            print(f"   Current: {file_info['path']}")
            print(f"   Suggested: {suggested}")
            
            action = input("   Move this file? (y/n/skip): ").strip().lower()
            if action == 'y':
                # TODO: Implement actual move (requires SSH to Proxmox)
                print("   ⚠️  Manual move required - see commands above")
            elif action == 'skip':
                continue
    
    # Disconnect SSH
    await ssh.disconnect()
    
    print("\n✅ Done!")
    return 0


def main():
    """Main function wrapper"""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())


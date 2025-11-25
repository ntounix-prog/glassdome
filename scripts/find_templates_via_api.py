#!/usr/bin/env python3
"""
Find Proxmox Templates via API

Uses Proxmox API to execute find commands on the Proxmox server.
Works even if SSH isn't accessible on management network.
"""
import sys
import os
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
    from glassdome.platforms.proxmox_factory import get_proxmox_client
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Install dependencies: pip install -e .")
    sys.exit(1)


def find_files_via_api(proxmox_client, search_path="/mnt"):
    """Find template files using Proxmox API to execute commands"""
    print(f"🔍 Searching for template files in {search_path} via Proxmox API...")
    print()
    
    node = proxmox_client.default_node
    
    # Execute find command via Proxmox API
    find_cmd = f"find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*.qcow2' -o -name '*.raw' -o -name '*.img' -o -name '*.iso' \\) -size +100M -exec ls -lh {{}} \\; 2>/dev/null | head -100"
    
    try:
        # Use Proxmox API to execute command on node
        result = proxmox_client.client.nodes(node).execute.post(
            command="sh",
            args=["-c", find_cmd]
        )
        
        if result and "data" in result:
            output = result["data"].get("out", "")
            return output
        else:
            print("⚠️  Command execution returned no data")
            return None
            
    except Exception as e:
        # Try alternative method - use shell via API
        try:
            # Some Proxmox versions use different API endpoints
            result = proxmox_client.client.nodes(node).shell.post(
                command=find_cmd
            )
            if result and "data" in result:
                return result["data"].get("out", "")
        except:
            pass
        
        print(f"⚠️  API command execution failed: {e}")
        print()
        print("   Trying alternative: Direct file system query via API...")
        return None


def get_storage_content(proxmox_client):
    """Get storage content to see what's already linked"""
    try:
        node = proxmox_client.default_node
        storage_list = proxmox_client.client.nodes(node).storage.get()
        
        storage_content = {}
        for storage in storage_list:
            storage_name = storage.get("storage")
            try:
                content = proxmox_client.client.nodes(node).storage(storage_name).content.get()
                storage_content[storage_name] = content
            except:
                pass
        
        return storage_content
    except Exception as e:
        print(f"⚠️  Could not get storage content: {e}")
        return {}


def parse_files(output):
    """Parse find output and extract file information"""
    files = []
    
    if not output:
        return files
    
    for line in output.split('\n'):
        if not line.strip():
            continue
        
        # Parse ls -lh output
        parts = line.split()
        if len(parts) < 9:
            continue
        
        filepath = ' '.join(parts[8:])
        filename = os.path.basename(filepath)
        
        # Extract size
        size_str = parts[4]
        try:
            if size_str.endswith('G'):
                size_gb = float(size_str[:-1])
            elif size_str.endswith('M'):
                size_gb = float(size_str[:-1]) / 1024
            else:
                continue
        except:
            continue
        
        # Identify file type
        file_type = "unknown"
        vm_id = None
        
        # VM disk images
        match = re.search(r"vm-(\d+)-disk-(\d+)", filename)
        if match:
            vm_id = int(match.group(1))
            file_type = "vm_disk"
        
        # Direct VM ID files
        match = re.search(r"^(\d+)\.(qcow2|raw|img|vmdk)$", filename)
        if match:
            vm_id = int(match.group(1))
            file_type = "vm_disk"
        
        # Ubuntu cloud images
        if "ubuntu" in filename.lower() and "cloudimg" in filename.lower():
            file_type = "ubuntu_cloud_image"
        
        # Windows ISOs
        if "windows" in filename.lower() and filename.endswith(".iso"):
            file_type = "windows_iso"
        
        # VirtIO ISOs
        if "virtio" in filename.lower() and filename.endswith(".iso"):
            file_type = "virtio_iso"
        
        files.append({
            "path": filepath,
            "filename": filename,
            "size_gb": size_gb,
            "type": file_type,
            "vm_id": vm_id
        })
    
    return sorted(files, key=lambda x: x["size_gb"], reverse=True)


def main():
    print("="*70)
    print("  PROXMOX TEMPLATE FINDER (via API)")
    print("="*70)
    print()
    
    # Get Proxmox client
    try:
        proxmox = get_proxmox_client("01")
        print(f"✅ Connected to Proxmox API: {proxmox.host}")
    except Exception as e:
        print(f"❌ Failed to connect to Proxmox: {e}")
        return 1
    
    # Get search path
    search_path = sys.argv[1] if len(sys.argv) > 1 else "/mnt"
    print(f"Search path: {search_path}")
    print()
    
    # Try to find files via API
    output = find_files_via_api(proxmox, search_path)
    
    if output is None:
        print("⚠️  Could not execute find command via API")
        print()
        print("   Alternative: Run this command directly on Proxmox server:")
        print(f"   find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*.qcow2' -o -name '*.raw' -o -name '*.img' -o -name '*.iso' \\) -size +100M -exec ls -lh {{}} \\;")
        return 1
    
    files = parse_files(output)
    
    if not files:
        print("❌ No template files found")
        print()
        print("   This could mean:")
        print("   - Files are in a different location")
        print("   - Files are already linked/moved")
        print("   - Search path is incorrect")
        return 1
    
    print(f"✅ Found {len(files)} template-related files:")
    print()
    
    # Get VM list to check which exist
    try:
        vms = proxmox.client.nodes(proxmox.default_node).qemu.get()
        vm_dict = {vm.get("vmid"): vm for vm in vms}
    except:
        vm_dict = {}
    
    # Display files
    for i, file_info in enumerate(files, 1):
        print(f"{i}. {file_info['filename']}")
        print(f"   Path: {file_info['path']}")
        print(f"   Size: {file_info['size_gb']:.2f} GB")
        print(f"   Type: {file_info['type']}")
        if file_info.get('vm_id'):
            vm = vm_dict.get(file_info['vm_id'])
            if vm:
                template_status = "Template" if vm.get('template') else "VM"
                print(f"   VM ID: {file_info['vm_id']} ({vm.get('name', 'Unknown')} - {template_status})")
            else:
                print(f"   VM ID: {file_info['vm_id']} (NOT FOUND in Proxmox - orphaned?)")
        print()
    
    # Generate relocation commands
    print("="*70)
    print("  RELOCATION COMMANDS")
    print("="*70)
    print()
    print("# Run these commands on Proxmox host (SSH as root):")
    print()
    
    for file_info in files:
        source = file_info['path']
        filename = file_info['filename']
        
        # ISOs go to /var/lib/vz/template/iso/
        if file_info['type'] in ['ubuntu_cloud_image', 'windows_iso', 'virtio_iso']:
            dest = f"/var/lib/vz/template/iso/{filename}"
            print(f"# {filename} ({file_info['size_gb']:.2f} GB)")
            print(f"mv {source} {dest}")
            print()
        
        # VM disks need to be imported
        elif file_info['type'] == 'vm_disk' and file_info.get('vm_id'):
            vm_id = file_info['vm_id']
            print(f"# VM {vm_id} disk - {filename} ({file_info['size_gb']:.2f} GB)")
            print(f"# First, check if VM {vm_id} exists:")
            print(f"qm config {vm_id}")
            print(f"# If VM exists, import disk to local-lvm:")
            print(f"qm importdisk {vm_id} {source} local-lvm")
            print(f"# Then attach to VM:")
            print(f"qm set {vm_id} --scsi0 local-lvm:vm-{vm_id}-disk-0")
            print()
    
    print("="*70)
    print("✅ Done! Review commands above and run on Proxmox host.")
    print("="*70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


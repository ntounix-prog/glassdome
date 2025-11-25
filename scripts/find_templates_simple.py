#!/usr/bin/env python3
"""
Find Proxmox Templates in /mnt

Simple standalone script to find template files on Proxmox server.
Doesn't require glassdome package dependencies.
"""
import sys
import os
import re
import subprocess
from pathlib import Path

def read_env_file():
    """Read .env file and extract Proxmox settings"""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("❌ .env file not found")
        return None
    
    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    return config

def find_files_via_ssh(host, user, password, search_path="/mnt"):
    """Find template files on Proxmox server via SSH"""
    print(f"🔍 Searching for template files in {search_path} on {host}...")
    print()
    
    # Use sshpass if password is available, otherwise try SSH key
    # Break into simpler commands to avoid timeout
    find_cmd = f"find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*.qcow2' -o -name '*.raw' -o -name '*.img' -o -name '*.iso' \\) -size +100M -exec ls -lh {{}} \\; 2>/dev/null | head -100"
    
    if password:
        # Escape password for shell
        escaped_password = password.replace("'", "'\"'\"'")
        cmd = f"sshpass -p '{escaped_password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null {user}@{host} '{find_cmd}'"
    else:
        cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null {user}@{host} '{find_cmd}'"
    
    print(f"Running: ssh {user}@{host} 'find {search_path} ...'")
    print("(This may take a minute if /mnt is large...)")
    print()
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"⚠️  SSH command failed (exit code {result.returncode})")
            if result.stderr:
                error_msg = result.stderr[:300]
                print(f"   Error: {error_msg}")
            print()
            print("   Troubleshooting:")
            print(f"   - Test SSH manually: ssh {user}@{host}")
            print(f"   - Check if host is reachable: ping {host}")
            if not password:
                print(f"   - Try with password: sshpass -p 'PASSWORD' ssh {user}@{host} 'echo test'")
            return []
        return result.stdout
    except subprocess.TimeoutExpired:
        print("❌ SSH command timed out (180 seconds)")
        print()
        print("   The search might be taking too long.")
        print("   Try running the find command directly on Proxmox:")
        print(f"   ssh {user}@{host}")
        print(f"   find {search_path} -type f -name 'vm-*-disk-*' -size +100M -exec ls -lh {{}} \\;")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def parse_files(output):
    """Parse find output and extract file information"""
    files = []
    
    if not output:
        return files
    
    for line in output.split('\n'):
        if not line.strip():
            continue
        
        # Parse ls -lh output: -rw-r--r-- 1 root root 4.7G Nov 22 10:00 /mnt/path/to/file
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
    import sys
    
    print("="*70)
    print("  PROXMOX TEMPLATE FINDER")
    print("="*70)
    print()
    
    # Read config
    config = read_env_file()
    if not config:
        return 1
    
    # Get Proxmox settings
    host = config.get("PROXMOX_HOST") or config.get("PROXMOX_02_HOST")
    # For SSH, use root (API user like "apex@pve" is for API only)
    ssh_user = "root"
    # Check for PROXMOX_ADMIN_PASSWD (used in some configs) or PROXMOX_PASSWORD
    password = config.get("PROXMOX_ADMIN_PASSWD") or config.get("PROXMOX_PASSWORD") or config.get("PROXMOX_02_PASSWORD")
    
    if not host:
        print("❌ PROXMOX_HOST not found in .env")
        return 1
    
    print(f"Proxmox Host: {host}")
    print(f"SSH User: {ssh_user}")
    print()
    
    if not password:
        print("⚠️  PROXMOX_PASSWORD not found in .env")
        print("   Will try SSH key authentication...")
        print()
    
    # Get search path from command line or use default
    if len(sys.argv) > 1:
        search_path = sys.argv[1]
    else:
        search_path = "/mnt"
    
    print(f"Search path: {search_path}")
    print()
    
    # Find files
    output = find_files_via_ssh(host, ssh_user, password, search_path)
    if output is None:
        return 1
    
    files = parse_files(output)
    
    if not files:
        print("❌ No template files found")
        print("\n   Try:")
        print("   - Check if path is correct")
        print("   - Verify SSH access works: ssh root@<proxmox-host>")
        return 1
    
    print(f"✅ Found {len(files)} template-related files:")
    print()
    
    # Display files
    for i, file_info in enumerate(files, 1):
        print(f"{i}. {file_info['filename']}")
        print(f"   Path: {file_info['path']}")
        print(f"   Size: {file_info['size_gb']:.2f} GB")
        print(f"   Type: {file_info['type']}")
        if file_info.get('vm_id'):
            print(f"   VM ID: {file_info['vm_id']}")
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


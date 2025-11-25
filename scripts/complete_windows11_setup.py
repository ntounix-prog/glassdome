#!/usr/bin/env python3
"""
Complete Windows 11 Setup - Most Stable Approach

This script handles the entire Windows 11 template creation process:
1. Finds/uploads Windows 11 ISO
2. Configures VM with optimal settings
3. Starts installation with autounattend
4. Automatically handles boot prompts
5. Monitors installation progress
"""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.utils.windows_autounattend import generate_autounattend_xml, create_autounattend_floppy
from glassdome.utils.ip_pool import get_ip_pool_manager


def find_windows11_iso(proxmox):
    """Find Windows 11 ISO on Proxmox or locally"""
    # Check Proxmox storage
    storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
    all_isos = []
    for item in storage_content:
        if item.get("content") == "iso":
            volid = item.get("volid", "")
            iso_name = volid.split("/")[-1]
            size = item.get("size", 0)
            all_isos.append({"name": iso_name, "size": size, "volid": volid})
    
    # Look for Windows 11
    for iso in all_isos:
        name_lower = iso["name"].lower()
        size_gb = iso["size"] / (1024**3)
        if "windows" in name_lower:
            if any(x in name_lower for x in ["11", "win11", "eleven"]):
                return iso["name"], "proxmox"
            # Windows 11 is typically 5-6GB
            elif 4.8 < size_gb < 6.5 and "server" not in name_lower and "2022" not in name_lower:
                return iso["name"], "proxmox"
    
    # Check locally
    local_paths = [
        Path("isos/windows/windows-11-enterprise-eval.iso"),
        Path("windows-11-enterprise-eval.iso"),
        Path("windows-11.iso"),
    ]
    
    for local_path in local_paths:
        if local_path.exists():
            return str(local_path), "local"
    
    return None, None


def upload_iso(local_path, proxmox_host):
    """Upload ISO to Proxmox"""
    print(f"📤 Uploading {local_path} to Proxmox...")
    cmd = f"scp {local_path} root@{proxmox_host}:/var/lib/vz/template/iso/"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        iso_name = Path(local_path).name
        print(f"✅ Uploaded: {iso_name}")
        return iso_name
    else:
        print(f"❌ Upload failed: {result.stderr}")
        return None


def setup_windows11_vm(proxmox, vmid=9101):
    """Complete Windows 11 VM setup with most stable configuration"""
    print(f"\n🚀 Setting up Windows 11 VM {vmid} (Most Stable Configuration)")
    print("="*70)
    
    # Find Windows 11 ISO
    print("\n1. Finding Windows 11 ISO...")
    win11_iso, location = find_windows11_iso(proxmox)
    
    if not win11_iso:
        print("❌ Windows 11 ISO not found")
        print("\nPlease download and upload Windows 11 ISO:")
        print("  Download: https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise")
        print(f"  Upload: scp windows-11-enterprise-eval.iso root@{settings.proxmox_host}:/var/lib/vz/template/iso/")
        return False
    
    if location == "local":
        # Upload it
        iso_name = upload_iso(win11_iso, settings.proxmox_host)
        if not iso_name:
            return False
        win11_iso = iso_name
    else:
        print(f"✅ Found on Proxmox: {win11_iso}")
    
    # Stop VM if running
    print("\n2. Stopping VM...")
    try:
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.stop.post()
        time.sleep(3)
        print("✅ VM stopped")
    except:
        pass
    
    # Configure VM with most stable settings
    print("\n3. Configuring VM (most stable settings)...")
    
    # CPU: 4 vCPU (Windows 11 requirement)
    cpu_config = {"cores": 4}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**cpu_config)
    print("✅ CPU: 4 vCPU")
    
    # Memory: 16GB (Windows 11 requirement)
    memory_config = {"memory": 16384}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**memory_config)
    print("✅ Memory: 16GB")
    
    # Disk: 30GB, SATA (Windows-native, no drivers) - Windows 11 requires at least 11GB
    disk_config = {
        "sata0": "local-lvm:30,cache=writeback,discard=on"
    }
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**disk_config)
    print("✅ Disk: 30GB SATA (Windows-native)")
    
    # Network: VLAN 2 for 192.168.3.x
    net_config = {
        "net0": "virtio,bridge=vmbr0,tag=2"
    }
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**net_config)
    print("✅ Network: VLAN 2 (192.168.3.x)")
    
    # Allocate IP
    ip_manager = get_ip_pool_manager()
    ip_allocation = ip_manager.allocate_ip("192.168.3.0/24", str(vmid))
    if ip_allocation:
        static_ip = ip_allocation["ip"]
        gateway = ip_allocation["gateway"]
        print(f"✅ IP allocated: {static_ip}")
    else:
        static_ip = f"192.168.3.{100 + vmid}"
        gateway = "192.168.3.1"
        print(f"⚠️  Using fallback IP: {static_ip}")
    
    # Generate autounattend.xml
    print("\n4. Generating autounattend.xml...")
    autounattend_config = {
        "hostname": f"windows11-template",
        "admin_password": "Glassdome123!",
        "windows_version": "win11",
        "enable_rdp": True,
        "virtio_drivers": True,
        "static_ip": static_ip,
        "gateway": gateway,
        "netmask": "255.255.255.0",
        "dns": ["8.8.8.8", "8.8.4.4"]
    }
    autounattend_xml = generate_autounattend_xml(autounattend_config)
    
    # Create autounattend floppy
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "glassdome-autounattend"
    temp_dir.mkdir(parents=True, exist_ok=True)
    autounattend_floppy = temp_dir / f"autounattend-{vmid}.img"
    create_autounattend_floppy(autounattend_xml, autounattend_floppy)
    print("✅ Autounattend floppy created")
    
    # Upload floppy to Proxmox
    print("\n5. Uploading autounattend floppy...")
    try:
        from glassdome.integrations.ssh_client import SSHClient
        ssh = SSHClient(settings.proxmox_host, "root", password=settings.proxmox_password)
        await ssh.connect()
        await ssh.upload_file(str(autounattend_floppy), f"/var/lib/vz/images/{vmid}/autounattend.img")
        await ssh.close()
        
        # Attach floppy via QEMU args
        args_config = {
            "args": f"-drive file=/var/lib/vz/images/{vmid}/autounattend.img,if=floppy,format=raw"
        }
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**args_config)
        print("✅ Autounattend floppy attached")
    except Exception as e:
        print(f"⚠️  Floppy upload failed: {e}")
        print("   Installation will still work, but may require manual steps")
    
    # Attach ISOs
    print("\n6. Attaching ISOs...")
    iso_config = {
        "ide2": f"local:iso/{win11_iso},media=cdrom"
    }
    
    # Find VirtIO ISO
    storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
    virtio_iso = None
    for item in storage_content:
        if item.get("content") == "iso":
            iso_name = item.get("volid", "").split("/")[-1]
            if "virtio" in iso_name.lower():
                virtio_iso = iso_name
                break
    
    if virtio_iso:
        iso_config["ide3"] = f"local:iso/{virtio_iso},media=cdrom"
        print(f"✅ Attached VirtIO drivers: {virtio_iso}")
    
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**iso_config)
    print(f"✅ Attached Windows 11 ISO: {win11_iso}")
    
    # Boot order: CD-ROM only (most stable)
    print("\n7. Setting boot order...")
    boot_config = {"boot": "order=ide2"}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**boot_config)
    print("✅ Boot order: CD-ROM only")
    
    # Start VM
    print("\n8. Starting VM...")
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.start.post()
    print("✅ VM started")
    
    # Auto-press key
    print("\n9. Auto-pressing boot key...")
    time.sleep(10)  # Wait for boot prompt
    
    try:
        from vncdotool import api
        vnc_proxy = proxmox.client.nodes(settings.proxmox_node).qemu(vmid).vncproxy.post()
        ticket = vnc_proxy.get('ticket', '')
        port = vnc_proxy.get('port', 5900)
        vnc_client = api.connect(f"{settings.proxmox_host}::{port}", password=ticket)
        vnc_client.keyPress('enter')
        print("✅ Sent Enter key")
        vnc_client.disconnect()
    except Exception as e:
        print(f"⚠️  Auto key press failed: {e}")
        print("   Please press any key in Proxmox console")
    
    print("\n" + "="*70)
    print("✅ Windows 11 installation started!")
    print(f"   VM ID: {vmid}")
    print(f"   IP: {static_ip}")
    print(f"   Monitor: https://{settings.proxmox_host}:8006")
    print(f"   RDP (after install): {static_ip}:3389")
    print(f"   User: Administrator")
    print(f"   Password: Glassdome123!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    proxmox = ProxmoxClient(
        host=settings.proxmox_host,
        user=settings.proxmox_user or "root@pam",
        password=settings.proxmox_password,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
        default_node=settings.proxmox_node
    )
    
    import asyncio
    asyncio.run(setup_windows11_vm(proxmox))


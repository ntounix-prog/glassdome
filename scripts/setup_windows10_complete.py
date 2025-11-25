#!/usr/bin/env python3
"""
Complete Windows 10 Setup - Handles everything automatically
Finds/uploads ISO, configures VM, starts installation
"""
import sys
import time
import asyncio
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
from glassdome.core.ssh_client import SSHClient
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.utils.windows_autounattend import generate_autounattend_xml, create_autounattend_floppy
from glassdome.utils.ip_pool import get_ip_pool_manager


def find_windows10_iso():
    """Find Windows 10 ISO locally"""
    search_paths = [
        Path("isos/windows/windows-10-enterprise-eval.iso"),
        Path("windows-10-enterprise-eval.iso"),
        Path("windows-10.iso"),
        Path.home() / "Downloads" / "windows-10-enterprise-eval.iso",
        Path.home() / "Downloads" / "windows-10.iso",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    # Search more broadly
    for root_dir in [Path("."), Path.home() / "Downloads"]:
        if root_dir.exists():
            for iso_file in root_dir.rglob("windows*10*.iso"):
                if iso_file.is_file():
                    return iso_file
    
    return None


async def upload_iso_to_proxmox(local_path, proxmox_client, proxmox_host, password=None):
    """Upload ISO to Proxmox using multiple methods (API first, then SSH)"""
    iso_name = Path(local_path).name
    iso_size_gb = local_path.stat().st_size / (1024**3)
    print(f"📤 Uploading {iso_name} to Proxmox...")
    print(f"   Size: {iso_size_gb:.2f} GB")
    print(f"   This may take several minutes...")
    
    # Method 1: Try Proxmox API upload using proxmoxer's session
    print("   Trying Proxmox API upload...")
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Try to use proxmoxer's session first (handles SSL properly)
        try:
            proxmox_session = proxmox_client.client._store.get('session')
            if proxmox_session:
                print("   Using proxmoxer session...")
                upload_url = f"https://{proxmox_host}:8006/api2/json/nodes/{settings.proxmox_node}/storage/local/upload"
                
                with open(local_path, 'rb') as f:
                    files = {'filename': (iso_name, f, 'application/octet-stream')}
                    data = {'content': 'iso', 'filename': iso_name}
                    
                    response = proxmox_session.post(
                        upload_url,
                        files=files,
                        data=data,
                        timeout=3600
                    )
                    
                    if response.status_code == 200:
                        print(f"✅ Uploaded via proxmoxer session: {iso_name}")
                        return iso_name
        except Exception as e:
            print(f"   Proxmoxer session failed: {str(e)[:100]}")
        
        # Fallback: Direct requests with proper SSL handling
        print("   Trying direct API upload with SSL workaround...")
        upload_url = f"https://{proxmox_host}:8006/api2/json/nodes/{settings.proxmox_node}/storage/local/upload"
        
        # Prepare authentication
        if settings.proxmox_token_name and settings.proxmox_token_value:
            token = f"{settings.proxmox_token_name}={settings.proxmox_token_value}"
            auth = HTTPBasicAuth(settings.proxmox_user or "root@pam", token)
        elif settings.proxmox_password:
            auth = HTTPBasicAuth(settings.proxmox_user or "root@pam", settings.proxmox_password)
        else:
            raise ValueError("No Proxmox credentials available")
        
        # Create session with SSL adapter that handles self-signed certs
        session = requests.Session()
        session.verify = False  # Disable SSL verification for self-signed certs
        
        # Upload file
        print("   Uploading (this may take 10-20 minutes for 5GB)...")
        with open(local_path, 'rb') as f:
            files = {'filename': (iso_name, f, 'application/octet-stream')}
            data = {'content': 'iso', 'filename': iso_name}
            
            response = session.post(
                upload_url,
                auth=auth,
                files=files,
                data=data,
                timeout=3600
            )
            
            if response.status_code == 200:
                print(f"✅ Uploaded via API: {iso_name}")
                return iso_name
            else:
                print(f"   API upload failed: {response.status_code}")
                if response.text:
                    error_msg = response.text[:300]
                    print(f"   Response: {error_msg}")
    except Exception as e:
        error_msg = str(e)[:300]
        print(f"   API upload error: {error_msg}")
    
    # Method 2: Try SSH with root username and password from .env
    print("   Trying SSH upload...")
    
    # SSH always uses root, not the API user
    ssh_username = "root"
    
    # Use password from parameter, settings (secrets manager), or environment variable
    import os
    root_password = settings.proxmox_root_password or settings.proxmox_password
    ssh_password = (
        password or 
        root_password or
        settings.proxmox_password or 
        os.getenv('PROXMOX_PASSWORD') or 
        os.getenv('PROXMOX_ROOT_PASSWORD') or
        os.getenv('PROXMOX_SSH_PASSWORD')
    )
    
    if not ssh_password:
        print(f"   ⚠️  No SSH password found in .env")
        print(f"   Please add PROXMOX_PASSWORD=your-password to .env file")
        print(f"   Or set it as environment variable: export PROXMOX_PASSWORD=your-password")
        return None
    
    print(f"   Using SSH: root@{proxmox_host}")
    ssh = SSHClient(
        host=proxmox_host,
        username=ssh_username,
        password=ssh_password
    )
    
    try:
        # Connect
        print(f"   Connecting to root@{proxmox_host}...")
        connected = await ssh.connect()
        
        if not connected:
            print(f"❌ Failed to connect to root@{proxmox_host} via SSH")
            print("   Please check:")
            print(f"   - PROXMOX_PASSWORD in .env")
            print(f"   - Network connectivity to {proxmox_host}")
            return None
        
        # Upload to Proxmox ISO directory
        remote_path = f"/var/lib/vz/template/iso/{iso_name}"
        success = await ssh.upload_file(str(local_path), remote_path)
        
        if success:
            print(f"✅ Uploaded via SSH: {iso_name}")
            return iso_name
        else:
            print(f"❌ SSH upload failed")
            return None
            
    except Exception as e:
        print(f"❌ SSH upload error: {e}")
        return None
    finally:
        await ssh.disconnect()


async def setup_windows10_complete():
    """Complete Windows 10 setup - most stable approach"""
    print("="*70)
    print("  WINDOWS 10 COMPLETE SETUP (Most Stable)")
    print("="*70)
    print()
    
    proxmox = ProxmoxClient(
        host=settings.proxmox_host,
        user=settings.proxmox_user or "root@pam",
        password=settings.proxmox_password,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
        default_node=settings.proxmox_node
    )
    
    vmid = 9102  # Windows 10 template ID
    
    # Step 1: Find Windows 10 ISO locally or on Proxmox
    print("1. Finding Windows 10 ISO...")
    win10_local = find_windows10_iso()
    win10_iso = None
    
    # Check Proxmox storage first
    print("   Checking Proxmox storage...")
    storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
    available_isos = [item.get("volid", "").split("/")[-1] for item in storage_content if item.get("content") == "iso"]
    
    # Look for Windows 10 on Proxmox
    for iso in available_isos:
        iso_lower = iso.lower()
        if "windows" in iso_lower and any(x in iso_lower for x in ["10", "win10", "ten"]):
            win10_iso = iso
            print(f"✅ Found on Proxmox: {win10_iso}")
            break
    
    # If not on Proxmox, check locally
    if not win10_iso:
        if win10_local:
            print(f"✅ Found locally: {win10_local.name}")
            
            # Step 2: Upload to Proxmox if not already there
            print("\n2. Uploading to Proxmox...")
            win10_iso_name = win10_local.name
            if win10_iso_name in available_isos:
                print(f"✅ Already on Proxmox: {win10_iso_name}")
                win10_iso = win10_iso_name
            else:
                # Upload it using API or SSH
                print(f"📤 Uploading {win10_iso_name} to Proxmox...")
                win10_iso = await upload_iso_to_proxmox(win10_local, proxmox, settings.proxmox_host, settings.proxmox_password)
                if not win10_iso:
                    print("\n⚠️  Automated upload failed (SSL/connection issue with large files)")
                    print("   The script will continue assuming manual upload...")
                    print(f"\n   To upload manually, run:")
                    print(f"   scp {win10_local} root@{settings.proxmox_host}:/var/lib/vz/template/iso/")
                    print(f"\n   Or use Proxmox Web UI:")
                    print(f"   https://{settings.proxmox_host}:8006")
                    print(f"   → Datacenter → local → ISO Images → Upload")
                    print(f"\n   Then re-run this script to complete setup.")
                    print(f"\n   Continuing with setup (will check for ISO on Proxmox)...")
                    # Check again after potential manual upload
                    time.sleep(2)
                    storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
                    available_isos = [item.get("volid", "").split("/")[-1] for item in storage_content if item.get("content") == "iso"]
                    if win10_iso_name in available_isos:
                        print(f"✅ Found on Proxmox: {win10_iso_name}")
                        win10_iso = win10_iso_name
                    else:
                        print(f"❌ ISO still not found. Please upload manually and re-run.")
                        return False
        else:
            print("❌ Windows 10 ISO not found locally or on Proxmox")
            print("\nPlease download Windows 10 ISO:")
            print("  https://www.microsoft.com/en-us/evalcenter/download-windows-10-enterprise")
            print(f"\nOr place locally and run this script again:")
            print(f"  mv windows-10-enterprise-eval.iso isos/windows/")
            return False
    else:
        print("   (Skipping local search - found on Proxmox)")
    
    # Step 3: Stop VM
    print("\n3. Stopping VM (if running)...")
    try:
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.stop.post()
        time.sleep(3)
        print("✅ VM stopped")
    except:
        pass
    
    # Step 4: Configure VM (most stable settings)
    print("\n4. Configuring VM (most stable)...")
    
    # CPU: 4 vCPU (Windows 10 requirement)
    cpu_config = {"cores": 4}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**cpu_config)
    print("✅ CPU: 4 vCPU")
    
    # Memory: 16GB (Windows 10 requirement)
    memory_config = {"memory": 16384}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**memory_config)
    print("✅ Memory: 16GB")
    
    # Disk: 30GB SATA (Windows 10 requires at least 11GB)
    disk_config = {"sata0": "local-lvm:30,cache=writeback,discard=on"}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**disk_config)
    print("✅ Disk: 30GB SATA (Windows-native)")
    
    # Network: VLAN 2
    net_config = {"net0": "virtio,bridge=vmbr0,tag=2"}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**net_config)
    print("✅ Network: VLAN 2 (192.168.3.x)")
    
    # Allocate IP
    ip_manager = get_ip_pool_manager()
    ip_allocation = ip_manager.allocate_ip("192.168.3.0/24", str(vmid))
    if ip_allocation:
        static_ip = ip_allocation["ip"]
        gateway = ip_allocation["gateway"]
        dns = ip_allocation["dns"]
    else:
        static_ip = f"192.168.3.{100 + vmid}"
        gateway = "192.168.3.1"
        dns = ["8.8.8.8", "8.8.4.4"]
    print(f"✅ IP: {static_ip}")
    
    # Step 5: Generate autounattend.xml
    print("\n5. Generating autounattend.xml...")
    autounattend_config = {
        "hostname": "windows10-template",
        "admin_password": "Glassdome123!",
        "windows_version": "win10",
        "enable_rdp": True,
        "virtio_drivers": True,
        "static_ip": static_ip,
        "gateway": gateway,
        "netmask": "255.255.255.0",
        "dns": dns
    }
    autounattend_xml = generate_autounattend_xml(autounattend_config)
    
    # Create floppy
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "glassdome-autounattend"
    temp_dir.mkdir(parents=True, exist_ok=True)
    autounattend_floppy = temp_dir / f"autounattend-{vmid}.img"
    create_autounattend_floppy(autounattend_xml, autounattend_floppy)
    print("✅ Autounattend floppy created")
    
    # Step 6: Upload floppy via SSH
    print("\n6. Uploading autounattend floppy...")
    try:
        ssh = SSHClient(
            host=settings.proxmox_host,
            username="root",
            password=settings.proxmox_password
        )
        
        connected = await ssh.connect()
        if connected:
            # Create directory first
            await ssh.execute(f"mkdir -p /var/lib/vz/images/{vmid}")
            
            # Upload floppy
            remote_path = f"/var/lib/vz/images/{vmid}/autounattend.img"
            success = await ssh.upload_file(str(autounattend_floppy), remote_path)
            
            if success:
                # Attach floppy
                args_config = {"args": f"-drive file={remote_path},if=floppy,format=raw"}
                proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**args_config)
                print("✅ Autounattend floppy attached")
            else:
                print("⚠️  Floppy upload failed")
                print("   Installation will still work, may need manual steps")
            
            await ssh.disconnect()
        else:
            print("⚠️  Failed to connect for floppy upload")
            print("   Installation will still work, may need manual steps")
    except Exception as e:
        print(f"⚠️  Floppy upload error: {e}")
        print("   Installation will still work, may need manual steps")
    
    # Step 7: Attach ISOs
    print("\n7. Attaching ISOs...")
    iso_config = {"ide2": f"local:iso/{win10_iso},media=cdrom"}
    
    # Find VirtIO
    virtio_iso = next((iso for iso in available_isos if "virtio" in iso.lower()), None)
    if virtio_iso:
        iso_config["ide3"] = f"local:iso/{virtio_iso},media=cdrom"
        print(f"✅ VirtIO drivers: {virtio_iso}")
    
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**iso_config)
    print(f"✅ Windows 10 ISO: {win10_iso}")
    
    # Step 8: Boot order
    print("\n8. Setting boot order...")
    boot_config = {"boot": "order=ide2"}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**boot_config)
    print("✅ Boot: CD-ROM only")
    
    # Step 9: Start VM
    print("\n9. Starting VM...")
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.start.post()
    print("✅ VM started")
    
    # Step 10: Auto-press key
    print("\n10. Auto-pressing boot key...")
    time.sleep(10)
    
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
        print(f"⚠️  Auto key press: {e}")
        print("   Please press any key in Proxmox console")
    
    print("\n" + "="*70)
    print("✅ WINDOWS 10 INSTALLATION STARTED!")
    print("="*70)
    print(f"VM ID: {vmid}")
    print(f"IP: {static_ip}")
    print(f"Monitor: https://{settings.proxmox_host}:8006")
    print(f"RDP (after install): {static_ip}:3389")
    print(f"User: Administrator")
    print(f"Password: Glassdome123!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(setup_windows10_complete())
    sys.exit(0 if success else 1)





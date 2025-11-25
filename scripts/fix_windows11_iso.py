#!/usr/bin/env python3
"""
Fix Windows 11 VM (9101) to use the correct Windows 11 ISO
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
from glassdome.platforms.proxmox_client import ProxmoxClient


def fix_windows11_iso():
    """Update VM 9101 to use Windows 11 ISO and start installation"""
    import time
    from vncdotool import api
    
    proxmox = ProxmoxClient(
        host=settings.proxmox_host,
        user=settings.proxmox_user or "root@pam",
        password=settings.proxmox_password,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
        default_node=settings.proxmox_node
    )
    
    vmid = 9101
    
    # Check available ISOs
    storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
    available_isos = [item.get("volid", "").split("/")[-1] for item in storage_content if item.get("content") == "iso"]
    
    print("Available ISOs on Proxmox:")
    for iso in available_isos:
        print(f"  - {iso}")
    print()
    
    # Look for Windows 11 ISO (check various patterns)
    win11_iso = None
    for iso in available_isos:
        iso_lower = iso.lower()
        if "windows" in iso_lower:
            if any(x in iso_lower for x in ["11", "win11", "eleven"]):
                win11_iso = iso
                break
            # Also check file size - Windows 11 is typically 5-6GB
            try:
                iso_info = next(item for item in storage_content if item.get("volid", "").endswith(iso))
                size = iso_info.get("size", 0)
                if size > 4000000000 and "server" not in iso_lower and "2022" not in iso_lower:
                    win11_iso = iso
                    break
            except:
                pass
    
    if not win11_iso:
        print("❌ Windows 11 ISO not found on Proxmox storage")
        print()
        print("Please upload Windows 11 ISO:")
        print("  ./scripts/upload_windows11_iso.sh")
        print("  OR")
        print("  scp windows-11-enterprise-eval.iso root@192.168.3.2:/var/lib/vz/template/iso/")
        print()
        print("Or download from:")
        print("  https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise")
        return False
    
    print(f"✅ Found Windows 11 ISO: {win11_iso}")
    print()
    
    # Stop VM 9101 if running
    try:
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.stop.post()
        time.sleep(3)
        print("✅ Stopped VM 9101")
    except:
        pass
    
    # Ensure disk is 30GB and RAM is 16GB (check current)
    config = proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.get()
    current_disk = config.get('sata0', '')
    current_memory = config.get('memory', 0)
    
    # Update memory to 16GB if needed
    if current_memory < 16384:
        memory_config = {"memory": 16384}
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**memory_config)
        print("✅ Updated memory to 16GB")
    
    # Update disk to 30GB if needed (Windows 11 requires at least 11GB)
    if '30' not in current_disk:
        disk_config = {"sata0": f"local-lvm:30,cache=writeback,discard=on"}
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**disk_config)
        print("✅ Updated disk to 30GB")
    
    # Update VM 9101 to use Windows 11 ISO
    iso_config = {
        "ide2": f"local:iso/{win11_iso},media=cdrom"
    }
    
    # Attach VirtIO drivers if available
    virtio_iso = None
    for iso in available_isos:
        if "virtio" in iso.lower():
            virtio_iso = iso
            break
    
    if virtio_iso:
        iso_config["ide3"] = f"local:iso/{virtio_iso},media=cdrom"
        print(f"✅ Attached VirtIO drivers: {virtio_iso}")
    
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**iso_config)
    print(f"✅ Attached Windows 11 ISO: {win11_iso}")
    
    # Set boot order
    boot_config = {"boot": "order=ide2"}
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**boot_config)
    print("✅ Set boot order to CD-ROM")
    
    # Start VM
    proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.start.post()
    print("✅ Started VM 9101")
    
    # Wait and send key press
    print("\n⏳ Waiting 8 seconds for boot prompt...")
    time.sleep(8)
    
    try:
        vnc_proxy = proxmox.client.nodes(settings.proxmox_node).qemu(vmid).vncproxy.post()
        ticket = vnc_proxy.get('ticket', '')
        port = vnc_proxy.get('port', 5900)
        vnc_client = api.connect(f"{settings.proxmox_host}::{port}", password=ticket)
        vnc_client.keyPress('enter')
        print("✅ Sent Enter key to boot from CD-ROM")
        vnc_client.disconnect()
    except Exception as e:
        print(f"⚠️  Auto key press failed: {e}")
        print("   Please manually press any key in Proxmox console when prompted")
    
    print("\n✅ Windows 11 installation started!")
    print("   Monitor progress in Proxmox console")
    
    return True


if __name__ == "__main__":
    fix_windows11_iso()


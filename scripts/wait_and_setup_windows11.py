#!/usr/bin/env python3
"""
Wait for Windows 11 ISO to be uploaded, then complete setup automatically
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.config import settings
from glassdome.platforms.proxmox_client import ProxmoxClient

def wait_for_iso_and_setup():
    """Wait for Windows 11 ISO, then complete setup"""
    proxmox = ProxmoxClient(
        host=settings.proxmox_host,
        user=settings.proxmox_user or "root@pam",
        password=settings.proxmox_password,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
        default_node=settings.proxmox_node
    )
    
    iso_name = "windows-11-enterprise-eval.iso"
    
    print("="*70)
    print("  WAITING FOR WINDOWS 11 ISO")
    print("="*70)
    print()
    print(f"Waiting for: {iso_name}")
    print(f"Upload to: root@{settings.proxmox_host}:/var/lib/vz/template/iso/")
    print()
    print("Upload command:")
    print(f"  scp isos/windows/{iso_name} root@{settings.proxmox_host}:/var/lib/vz/template/iso/")
    print()
    print("Monitoring Proxmox storage (checking every 5 seconds)...")
    print()
    
    # Wait for ISO
    max_wait = 300  # 5 minutes
    waited = 0
    
    while waited < max_wait:
        storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
        available_isos = [item.get("volid", "").split("/")[-1] for item in storage_content if item.get("content") == "iso"]
        
        win11_iso = None
        for iso in available_isos:
            if iso_name in iso or (iso_name.lower().replace('-', '_') in iso.lower()):
                win11_iso = iso
                break
            if "windows" in iso.lower() and "11" in iso.lower():
                win11_iso = iso
                break
        
        if win11_iso:
            print(f"✅ Found Windows 11 ISO: {win11_iso}")
            print("\n🚀 Completing setup...")
            break
        
        if waited % 10 == 0:
            print(f"   Still waiting... ({waited}s / {max_wait}s)")
        
        time.sleep(5)
        waited += 5
    
    if not win11_iso:
        print("\n❌ Timeout waiting for ISO")
        return False
    
    # Run complete setup
    print("\n" + "="*70)
    import subprocess
    result = subprocess.run([sys.executable, "scripts/setup_windows11_complete.py"], cwd=Path(__file__).parent.parent)
    return result.returncode == 0

if __name__ == "__main__":
    wait_for_iso_and_setup()


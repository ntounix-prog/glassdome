#!/usr/bin/env python3
"""
Automatically press a key when Windows Setup shows "Press any key to boot from CD-ROM"
Uses Proxmox VNC to send keyboard input
"""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.config import settings
from glassdome.platforms.proxmox_client import ProxmoxClient


def send_key_via_vnc(proxmox_host: str, vmid: int, key: str = "enter"):
    """
    Send a key press to VM via VNC using qm terminal command
    """
    try:
        # Use qm terminal to send key press
        # Note: This requires SSH access to Proxmox host
        cmd = f"ssh root@{proxmox_host} 'qm terminal {vmid} --key {key}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to send key via SSH: {e}")
        return False


def send_key_via_qemu_monitor(proxmox_host: str, vmid: int, key: str = "ret"):
    """
    Send a key press via QEMU monitor
    """
    try:
        # Use QEMU monitor to send key press
        # Format: sendkey <key>
        cmd = f"ssh root@{proxmox_host} 'qm monitor {vmid} --command \"sendkey {key}\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to send key via QEMU monitor: {e}")
        return False


def auto_press_cdrom_key(vmid: int, wait_time: int = 10):
    """
    Wait for VM to boot, then automatically press a key to boot from CD-ROM
    
    Args:
        vmid: VM ID
        wait_time: Seconds to wait after VM start before pressing key
    """
    print(f"🔄 Auto-pressing CD-ROM boot key for VM {vmid}...")
    print(f"   Waiting {wait_time} seconds for boot prompt...")
    
    time.sleep(wait_time)
    
    # Try multiple methods to send key press
    methods = [
        ("QEMU Monitor", lambda: send_key_via_qemu_monitor(settings.proxmox_host, vmid, "ret")),
        ("VNC Terminal", lambda: send_key_via_vnc(settings.proxmox_host, vmid, "enter")),
    ]
    
    for method_name, method_func in methods:
        print(f"   Trying {method_name}...")
        if method_func():
            print(f"✅ Successfully sent key press via {method_name}")
            return True
        else:
            print(f"   ⚠️  {method_name} failed, trying next method...")
    
    print("❌ All methods failed. Please manually press a key in Proxmox console.")
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-press CD-ROM boot key for Windows VMs")
    parser.add_argument("vmid", type=int, help="VM ID")
    parser.add_argument("--wait", type=int, default=10, help="Seconds to wait before pressing key")
    
    args = parser.parse_args()
    
    auto_press_cdrom_key(args.vmid, args.wait)


#!/usr/bin/env python3
"""
Automatically press key to boot Windows VMs from CD-ROM
Uses VNC to send keyboard input
"""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.config import settings


def get_vnc_info(proxmox_host: str, vmid: int):
    """Get VNC connection info from Proxmox"""
    try:
        # Use Proxmox API to get VNC info
        from glassdome.platforms.proxmox_client import ProxmoxClient
        
        proxmox = ProxmoxClient(
            host=settings.proxmox_host,
            user=settings.proxmox_user or "root@pam",
            password=settings.proxmox_password,
            token_name=settings.proxmox_token_name,
            token_value=settings.proxmox_token_value,
            verify_ssl=settings.proxmox_verify_ssl,
            default_node=settings.proxmox_node
        )
        
        # Get VNC info via API
        vnc_info = proxmox.client.nodes(settings.proxmox_node).qemu(vmid).vncproxy.post()
        return vnc_info
    except Exception as e:
        print(f"Failed to get VNC info via API: {e}")
        return None


def send_key_via_vnc(vmid: int, wait_time: int = 8):
    """
    Send Enter key via VNC to boot from CD-ROM
    
    Args:
        vmid: VM ID
        wait_time: Seconds to wait before sending key
    """
    print(f"🔄 Auto-booting VM {vmid} from CD-ROM...")
    print(f"   Waiting {wait_time} seconds for boot prompt...")
    
    time.sleep(wait_time)
    
    try:
        from vncdotool import api
        
        # Get VNC connection info
        vnc_info = get_vnc_info(settings.proxmox_host, vmid)
        if not vnc_info:
            print(f"❌ Could not get VNC info for VM {vmid}")
            return False
        
        # Parse VNC ticket and port
        ticket = vnc_info.get('ticket', '')
        port = vnc_info.get('port', 5900)
        
        # Connect to VNC (Proxmox VNC requires ticket authentication)
        # Note: vncdotool may need special handling for Proxmox VNC
        print(f"   Connecting to VNC...")
        
        # Alternative: Use qm monitor via SSH if available
        # This is simpler and more reliable
        print(f"   Trying QEMU monitor method...")
        
        # Check if we have SSH access
        import os
        ssh_password = os.getenv('PROXMOX_PASSWORD') or os.getenv('PROXMOX_ROOT_PASSWORD')
        
        if ssh_password:
            cmd = f"sshpass -p '{ssh_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@{settings.proxmox_host} 'qm monitor {vmid} --command \"sendkey ret\"'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Successfully sent Enter key to VM {vmid}")
                return True
            else:
                print(f"⚠️  QEMU monitor failed: {result.stderr}")
        
        # Fallback: Manual instruction
        print(f"⚠️  Automatic key press failed")
        print(f"   Please manually press any key in Proxmox console for VM {vmid}")
        return False
        
    except ImportError:
        print("❌ vncdotool not installed. Install with: pip install vncdotool")
        print(f"   For now, please manually press any key in Proxmox console for VM {vmid}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   Please manually press any key in Proxmox console for VM {vmid}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-boot Windows VMs from CD-ROM")
    parser.add_argument("--vmid", type=int, help="VM ID (if not provided, processes 9100 and 9101)")
    parser.add_argument("--wait", type=int, default=8, help="Seconds to wait before sending key")
    
    args = parser.parse_args()
    
    vmids = [args.vmid] if args.vmid else [9100, 9101]
    
    for vmid in vmids:
        send_key_via_vnc(vmid, args.wait)
        time.sleep(2)  # Small delay between VMs


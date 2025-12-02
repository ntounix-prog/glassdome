#!/usr/bin/env python3
"""
Deploy Ubuntu Server on Proxmox 02

Creates a new Ubuntu 22.04 server with:
- SSH key authentication
- Password login for console access
- Configured for immediate use

Author: Glassdome Automation
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from proxmoxer import ProxmoxAPI
import urllib3
urllib3.disable_warnings()

# Configuration
PROXMOX_HOST = "192.168.215.77"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "xisxxisx"
PROXMOX_NODE = "pve02"

# VM Configuration
VM_NAME = "ubuntu-server-new"
VM_CORES = 2
VM_MEMORY = 4096  # MB
VM_DISK_SIZE = 32  # GB
TEMPLATE_ID = 9001  # Ubuntu 22.04 template with guest agent
TEMPLATE_NODE = "pve01"  # Templates are on pve01
TARGET_NODE = "pve01"  # Clone on pve01, then can migrate to pve02
STORAGE = "truenas-nfs-labs"  # TrueNAS shared storage (enables live migration)
NETWORK = "vmbr0"

# User Configuration
SSH_USER = "nomad"
SSH_PASSWORD = "glassdome2024!"  # Console/sudo password
SSH_KEY_PATH = Path.home() / ".ssh" / "ubuntu_server_key.pub"


def get_next_vmid(proxmox, node):
    """Get next available VMID"""
    return proxmox.cluster.nextid.get()


def main():
    print("=" * 60)
    print("Ubuntu Server Deployment on Proxmox 02")
    print("=" * 60)
    
    # Read SSH public key
    if SSH_KEY_PATH.exists():
        ssh_pub_key = SSH_KEY_PATH.read_text().strip()
        print(f"✓ SSH public key loaded from {SSH_KEY_PATH}")
    else:
        print(f"✗ SSH key not found at {SSH_KEY_PATH}")
        return
    
    # Connect to Proxmox
    print(f"\nConnecting to Proxmox at {PROXMOX_HOST}...")
    try:
        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=False
        )
        print(f"✓ Connected to {PROXMOX_HOST}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    # Get next available VMID
    new_vmid = get_next_vmid(proxmox, PROXMOX_NODE)
    print(f"✓ Next available VMID: {new_vmid}")
    
    # Check if template exists (templates are on pve01)
    template_id = TEMPLATE_ID
    print(f"\nChecking template {template_id} on {TEMPLATE_NODE}...")
    try:
        template_config = proxmox.nodes(TEMPLATE_NODE).qemu(template_id).config.get()
        print(f"✓ Template found: {template_config.get('name', 'unnamed')}")
    except Exception as e:
        print(f"✗ Template {template_id} not found: {e}")
        print("  Trying alternative template 9000...")
        try:
            template_config = proxmox.nodes(TEMPLATE_NODE).qemu(9000).config.get()
            template_id = 9000
            print(f"✓ Template found: {template_config.get('name', 'unnamed')}")
        except:
            print("✗ No Ubuntu template found. Please create one first.")
            return
    
    # Clone VM from template (on same node due to local storage)
    print(f"\nCloning template {template_id} on {TEMPLATE_NODE} as VM {new_vmid}...")
    try:
        clone_result = proxmox.nodes(TEMPLATE_NODE).qemu(template_id).clone.post(
            newid=new_vmid,
            name=VM_NAME,
            full=1,  # Full clone (not linked)
            storage=STORAGE
        )
        print(f"✓ Clone task started: {clone_result}")
    except Exception as e:
        print(f"✗ Clone failed: {e}")
        return
    
    # Wait for clone to complete
    print("  Waiting for clone to complete...")
    import time
    for i in range(90):  # Wait up to 3 minutes for cross-node clone
        time.sleep(2)
        try:
            vm_status = proxmox.nodes(TARGET_NODE).qemu(new_vmid).status.current.get()
            if vm_status:
                print(f"✓ Clone completed! VM {new_vmid} created on {TARGET_NODE}")
                break
        except:
            if i % 10 == 0:
                print(f"  Still cloning... ({i*2}s)")
    else:
        print("⚠ Clone may still be in progress...")
    
    # Configure VM
    print(f"\nConfiguring VM {new_vmid} on {TARGET_NODE}...")
    
    # URL-encode SSH key for cloud-init
    import urllib.parse
    ssh_key_encoded = urllib.parse.quote(ssh_pub_key, safe='')
    
    try:
        config_update = {
            "cores": VM_CORES,
            "memory": VM_MEMORY,
            "ciuser": SSH_USER,
            "cipassword": SSH_PASSWORD,
            "sshkeys": ssh_key_encoded,
            "ipconfig0": "ip=dhcp",
            "agent": "enabled=1",
        }
        
        proxmox.nodes(TARGET_NODE).qemu(new_vmid).config.put(**config_update)
        print(f"✓ VM configured:")
        print(f"    - Cores: {VM_CORES}")
        print(f"    - Memory: {VM_MEMORY}MB")
        print(f"    - User: {SSH_USER}")
        print(f"    - SSH Key: Configured")
        print(f"    - IP: DHCP")
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return
    
    # Start VM
    print(f"\nStarting VM {new_vmid} on {TARGET_NODE}...")
    try:
        proxmox.nodes(TARGET_NODE).qemu(new_vmid).status.start.post()
        print("✓ VM starting...")
    except Exception as e:
        print(f"✗ Failed to start VM: {e}")
        return
    
    # Wait for VM to get IP
    print("\nWaiting for VM to boot and get IP address...")
    ip_address = None
    for i in range(90):  # Wait up to 3 minutes
        time.sleep(2)
        try:
            agent_info = proxmox.nodes(TARGET_NODE).qemu(new_vmid).agent("network-get-interfaces").get()
            for iface in agent_info.get("result", []):
                for ip_info in iface.get("ip-addresses", []):
                    if ip_info.get("ip-address-type") == "ipv4" and not ip_info.get("ip-address", "").startswith("127."):
                        ip_address = ip_info.get("ip-address")
                        break
                if ip_address:
                    break
            if ip_address:
                break
        except:
            if i % 10 == 0:
                print(f"  Still waiting... ({i*2}s)")
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"""
VM Details:
  - VMID: {new_vmid}
  - Name: {VM_NAME}
  - Node: {TARGET_NODE}
  - Cores: {VM_CORES}
  - Memory: {VM_MEMORY}MB
  - IP Address: {ip_address or 'Pending (check Proxmox console)'}

Login Credentials:
  - Username: {SSH_USER}
  - Password: {SSH_PASSWORD}
  - SSH Key:  ~/.ssh/ubuntu_server_key

SSH Access:
  ssh -i ~/.ssh/ubuntu_server_key {SSH_USER}@{ip_address or '<IP_ADDRESS>'}

Console Access (Proxmox):
  https://{PROXMOX_HOST}:8006 → VM {new_vmid} → Console
""")
    
    # Save connection info
    info_file = Path.home() / "ubuntu_server_info.txt"
    with open(info_file, "w") as f:
        f.write(f"Ubuntu Server Connection Info\n")
        f.write(f"=" * 40 + "\n\n")
        f.write(f"VMID: {new_vmid}\n")
        f.write(f"Name: {VM_NAME}\n")
        f.write(f"IP Address: {ip_address or 'TBD'}\n")
        f.write(f"Username: {SSH_USER}\n")
        f.write(f"Password: {SSH_PASSWORD}\n")
        f.write(f"SSH Key: ~/.ssh/ubuntu_server_key\n\n")
        f.write(f"SSH Command:\n")
        f.write(f"  ssh -i ~/.ssh/ubuntu_server_key {SSH_USER}@{ip_address or '<IP>'}\n")
    print(f"✓ Connection info saved to: {info_file}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Deploy Glassdome Production Application Server
Clones Ubuntu template from pve01 to pve02 with production specs

Requires: Session must be initialized first (run ./glassdome_start)
"""

import os
import sys
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glassdome.core.security import ensure_security_context, get_secure_settings
from glassdome.platforms.proxmox_client import ProxmoxClient


def get_proxmox_config(instance_id: str) -> dict:
    """Get Proxmox config for a specific instance using secure settings"""
    settings = get_secure_settings()
    return settings.get_proxmox_config(instance_id)


async def deploy_prod_server():
    """Deploy the production application server to pve02"""
    
    # Ensure we have a valid security context (session must be initialized)
    try:
        ensure_security_context()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        print("\nRun ./glassdome_start first to initialize the session.")
        return None
    
    # Configuration
    VM_NAME = "glassdome-prod-app"
    # Deploy to pve02 where we just created the template
    TARGET_NODE = "pve02"
    SOURCE_NODE = "pve02"
    TEMPLATE_ID = 9000  # ubuntu-2204-cloudinit-template on pve02 (esxstore)
    
    # Specs: 4 vCPU, 16GB RAM, 100GB disk
    VM_SPECS = {
        "name": VM_NAME,
        "cores": 4,
        "memory": 16384,  # 16GB in MB
        "network": "vmbr0",
        "ssh_user": "ubuntu",
    }
    
    print("=" * 60)
    print("Glassdome Production Server Deployment")
    print("=" * 60)
    print(f"  Target:   {TARGET_NODE} (192.168.215.77)")
    print(f"  Template: {SOURCE_NODE}:{TEMPLATE_ID} (Ubuntu 22.04)")
    print(f"  Name:     {VM_NAME}")
    print(f"  Specs:    4 vCPU, 16GB RAM")
    print("=" * 60)
    
    # Get Proxmox client for pve02 (where template lives)
    print("\n[1/5] Connecting to Proxmox (pve02)...")
    config_01 = get_proxmox_config("02")
    if not config_01:
        print("ERROR: Could not get pve02 configuration")
        return None
    
    client_01 = ProxmoxClient(
        host=config_01["host"],
        user=config_01["user"],
        password=config_01.get("password"),
        token_name=config_01.get("token_name"),
        token_value=config_01.get("token_value"),
        verify_ssl=False,
        default_node=SOURCE_NODE
    )
    
    # Test connection
    if not await client_01.test_connection():
        print("ERROR: Could not connect to pve02")
        return None
    print("  ✓ Connected to pve02")
    
    # Get next available VMID
    print("\n[2/5] Getting next available VMID...")
    new_vmid = await client_01.get_next_vmid()
    print(f"  ✓ VMID: {new_vmid}")
    
    # Clone template from pve01 to pve02
    print(f"\n[3/5] Cloning template {TEMPLATE_ID} to {TARGET_NODE}...")
    print(f"       (This may take 2-5 minutes for cross-node clone)")
    
    clone_result = await client_01.clone_vm_raw(
        node=SOURCE_NODE,
        vmid=TEMPLATE_ID,
        newid=new_vmid,
        name=VM_NAME,
        full=True,
        target_node=TARGET_NODE,
        target_storage="esxstore"  # Using esxstore on pve02
    )
    
    if not clone_result.get("success"):
        print(f"ERROR: Clone failed: {clone_result.get('error')}")
        return None
    
    print(f"  ✓ Clone initiated (task: {clone_result.get('task', 'unknown')})")
    
    # Wait for clone task to complete
    task_upid = clone_result.get("task")
    if task_upid:
        print("       Waiting for clone to complete...")
        task_result = await client_01.wait_for_task(SOURCE_NODE, task_upid, timeout=600)
        if not task_result.get("success"):
            print(f"ERROR: Clone task failed: {task_result.get('error')}")
            return None
        print("  ✓ Clone completed")
    
    # Use same client since we're on the same node
    print("\n[4/5] Configuring VM on pve02...")
    client_02 = client_01  # Same node, reuse client
    
    # Configure VM specs
    print(f"\n[5/5] Configuring VM {new_vmid}...")
    vm_config = {
        "cores": VM_SPECS["cores"],
        "memory": VM_SPECS["memory"],
        "net0": f"virtio,bridge={VM_SPECS['network']}",
        "agent": "enabled=1",  # Enable QEMU guest agent
    }
    
    config_result = await client_02.configure_vm(TARGET_NODE, new_vmid, vm_config)
    if not config_result.get("success"):
        print(f"WARNING: Config update issue: {config_result.get('error')}")
    else:
        print("  ✓ VM configured: 4 vCPU, 16GB RAM")
    
    # Resize disk to 100GB (template is smaller)
    print("       Resizing disk to 100GB...")
    try:
        resize_result = await client_02.resize_disk(TARGET_NODE, new_vmid, "scsi0", "+80G")
        if resize_result.get("success"):
            print("  ✓ Disk resized to ~100GB")
        else:
            print(f"  ⚠ Disk resize skipped: {resize_result.get('error')}")
    except Exception as e:
        print(f"  ⚠ Disk resize skipped: {e}")
    
    # Start the VM
    print("\n[BONUS] Starting VM...")
    start_result = await client_02.start_vm(str(new_vmid))
    if start_result:
        print("  ✓ VM started")
    else:
        print("  ⚠ VM start failed - may need manual start")
    
    # Wait for IP
    print("\n       Waiting for IP address (up to 120s)...")
    ip_address = await client_02.get_vm_ip(str(new_vmid), timeout=120)
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"  VM ID:      {new_vmid}")
    print(f"  VM Name:    {VM_NAME}")
    print(f"  Node:       {TARGET_NODE}")
    print(f"  IP Address: {ip_address or 'Pending (check Proxmox)'}")
    print(f"  SSH User:   ubuntu")
    print("=" * 60)
    
    if ip_address:
        print(f"\nNext steps:")
        print(f"  1. SSH: ssh ubuntu@{ip_address}")
        print(f"  2. Run the Glassdome prod setup script")
        print(f"  3. Configure nginx + systemd")
    else:
        print(f"\nNote: IP not yet available. Check Proxmox console or wait for cloud-init.")
    
    return {
        "vmid": new_vmid,
        "name": VM_NAME,
        "node": TARGET_NODE,
        "ip_address": ip_address
    }


if __name__ == "__main__":
    result = asyncio.run(deploy_prod_server())
    if result:
        print(f"\n✓ Success! VM {result['vmid']} deployed to {result['node']}")
    else:
        print("\n✗ Deployment failed")
        sys.exit(1)


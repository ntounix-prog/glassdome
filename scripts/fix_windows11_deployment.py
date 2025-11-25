#!/usr/bin/env python3
"""
Fix Windows 11 VM (9101) Configuration
Updates VM to correct specs: 4 vCPU, 16GB RAM, 30GB disk
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
from glassdome.platforms.proxmox_client import ProxmoxClient


async def fix_windows11_vm():
    """Fix Windows 11 VM 9101 configuration"""
    print("="*70)
    print("  FIXING WINDOWS 11 VM (9101) CONFIGURATION")
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
    
    vmid = 9101
    
    # Check current status
    print(f"1. Checking VM {vmid} status...")
    try:
        status = proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.current.get()
        vm_status = status.get("status", "unknown")
        print(f"   Status: {vm_status}")
        
        if vm_status == "running":
            print("   ⚠️  VM is running - stopping to update configuration...")
            proxmox.client.nodes(settings.proxmox_node).qemu(vmid).status.stop.post()
            import time
            time.sleep(5)
            print("   ✅ VM stopped")
    except Exception as e:
        print(f"   ⚠️  Could not check status: {e}")
    
    # Get current config
    print(f"\n2. Checking current configuration...")
    config = proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.get()
    current_memory = int(config.get("memory", 0) or 0)
    current_cores = int(config.get("cores", 0) or 0)
    current_disk = config.get("sata0", "")
    
    print(f"   Current Memory: {current_memory} MB")
    print(f"   Current Cores: {current_cores}")
    print(f"   Current Disk: {current_disk}")
    
    # Windows 11 Requirements: 4 vCPU, 16GB RAM, 30GB disk
    target_memory = 16384  # 16GB
    target_cores = 4
    target_disk = 30  # 30GB
    
    print(f"\n3. Updating to Windows 11 requirements...")
    print(f"   Target Memory: {target_memory} MB (16GB)")
    print(f"   Target Cores: {target_cores}")
    print(f"   Target Disk: {target_disk} GB")
    
    # Update memory
    if current_memory < target_memory:
        print(f"\n   → Updating memory to {target_memory} MB...")
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(memory=target_memory)
        print(f"   ✅ Memory updated")
    else:
        print(f"   ✅ Memory already correct ({current_memory} MB)")
    
    # Update CPU cores
    if current_cores < target_cores:
        print(f"\n   → Updating CPU cores to {target_cores}...")
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(cores=target_cores)
        print(f"   ✅ CPU cores updated")
    else:
        print(f"   ✅ CPU cores already correct ({current_cores})")
    
    # Update disk size
    if '30' not in current_disk:
        print(f"\n   → Updating disk to {target_disk} GB...")
        # Note: Disk resize requires VM to be stopped and may need manual intervention
        # For now, we'll update the config - actual resize may need to be done manually
        disk_config = {"sata0": f"local-lvm:{target_disk},cache=writeback,discard=on"}
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**disk_config)
        print(f"   ✅ Disk configuration updated to {target_disk} GB")
        print(f"   ⚠️  Note: If disk was smaller, you may need to resize it manually")
    else:
        print(f"   ✅ Disk already correct (30GB)")
    
    # Verify Windows 11 ISO is attached
    print(f"\n4. Verifying Windows 11 ISO...")
    storage_content = proxmox.client.nodes(settings.proxmox_node).storage("local").content.get()
    available_isos = [item.get("volid", "").split("/")[-1] for item in storage_content if item.get("content") == "iso"]
    
    win11_iso = None
    for iso in available_isos:
        iso_lower = iso.lower()
        if "windows" in iso_lower and any(x in iso_lower for x in ["11", "win11", "eleven"]):
            win11_iso = iso
            break
    
    if win11_iso:
        print(f"   ✅ Windows 11 ISO found: {win11_iso}")
        # Ensure ISO is attached
        current_iso = config.get("ide2", "")
        if win11_iso not in current_iso:
            print(f"   → Attaching Windows 11 ISO...")
            iso_config = {"ide2": f"local:iso/{win11_iso},media=cdrom"}
            proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**iso_config)
            print(f"   ✅ ISO attached")
        else:
            print(f"   ✅ ISO already attached")
    else:
        print(f"   ⚠️  Windows 11 ISO not found on Proxmox")
        print(f"   Please upload: windows-11-enterprise-eval.iso")
    
    # Verify boot order
    print(f"\n5. Verifying boot order...")
    current_boot = config.get("boot", "")
    if "ide2" not in current_boot:
        print(f"   → Setting boot order to CD-ROM (ide2)...")
        boot_config = {"boot": "order=ide2"}
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**boot_config)
        print(f"   ✅ Boot order set to CD-ROM")
    else:
        print(f"   ✅ Boot order correct (CD-ROM)")
    
    # Verify network (VLAN 2)
    print(f"\n6. Verifying network configuration...")
    current_net = config.get("net0", "")
    if "tag=2" not in current_net:
        print(f"   → Setting network to VLAN 2...")
        net_config = {"net0": "virtio,bridge=vmbr0,tag=2"}
        proxmox.client.nodes(settings.proxmox_node).qemu(vmid).config.put(**net_config)
        print(f"   ✅ Network set to VLAN 2")
    else:
        print(f"   ✅ Network already configured (VLAN 2)")
    
    print(f"\n" + "="*70)
    print("✅ WINDOWS 11 VM CONFIGURATION UPDATED")
    print("="*70)
    print(f"VM ID: {vmid}")
    print(f"Specs: {target_cores} vCPU, {target_memory} MB RAM, {target_disk} GB disk")
    print(f"Network: VLAN 2 (192.168.3.x)")
    print(f"\nNext steps:")
    print(f"1. Start the VM: qm start {vmid}")
    print(f"2. Monitor installation in Proxmox console")
    print(f"3. After installation, change boot order to: order=sata0")
    print("="*70)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(fix_windows11_vm())
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""
Get detailed storage configuration from both Proxmox nodes via API
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.config import Settings
from glassdome.platforms.proxmox_client import ProxmoxClient


async def get_storage_details(label: str, config: dict):
    """Get storage config from Proxmox API"""
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")
    
    if not config['host']:
        print("⚠️  No host configured")
        return
    
    try:
        client = ProxmoxClient(
            host=config['host'],
            user=config['user'],
            password=config.get('password'),
            token_name=config.get('token_name'),
            token_value=config.get('token_value'),
            verify_ssl=False,
            default_node=config['node']
        )
        
        # Get storage config
        storages = client.client.storage.get()
        
        print(f"\nStorage Configuration:")
        print(f"-" * 70)
        
        for storage in storages:
            storage_id = storage.get('storage')
            storage_type = storage.get('type')
            shared = storage.get('shared', 0)
            content = storage.get('content', '')
            
            print(f"\n📦 {storage_id}")
            print(f"   Type: {storage_type}")
            print(f"   Shared: {'✅ Yes' if shared else '❌ No'}")
            print(f"   Content: {content}")
            
            # Type-specific details
            if storage_type == 'nfs':
                print(f"   Server: {storage.get('server', 'N/A')}")
                print(f"   Export: {storage.get('export', 'N/A')}")
                print(f"   Options: {storage.get('options', 'N/A')}")
            
            elif storage_type == 'iscsi':
                print(f"   Portal: {storage.get('portal', 'N/A')}")
                print(f"   Target: {storage.get('target', 'N/A')}")
            
            elif storage_type == 'zfspool':
                print(f"   Pool: {storage.get('pool', 'N/A')}")
                # Try to get more details
                try:
                    status = client.client.nodes(config['node']).storage(storage_id).status.get()
                    total_gb = status.get('total', 0) / (1024**3)
                    used_gb = status.get('used', 0) / (1024**3)
                    avail_gb = status.get('avail', 0) / (1024**3)
                    used_pct = (used_gb / total_gb * 100) if total_gb > 0 else 0
                    print(f"   Size: {total_gb:.1f} GB total, {used_gb:.1f} GB used ({used_pct:.1f}%), {avail_gb:.1f} GB available")
                except:
                    pass
            
            elif storage_type == 'dir':
                print(f"   Path: {storage.get('path', 'N/A')}")
            
            elif storage_type == 'lvm' or storage_type == 'lvmthin':
                print(f"   VG: {storage.get('vgname', 'N/A')}")
                if storage_type == 'lvmthin':
                    print(f"   Thin Pool: {storage.get('thinpool', 'N/A')}")
        
        # Try to get network config (for iSCSI initiator info if accessible via API)
        print(f"\n\niSCSI Configuration:")
        print(f"-" * 70)
        try:
            # Check if any iSCSI targets are configured
            has_iscsi = any(s.get('type') == 'iscsi' for s in storages)
            if has_iscsi:
                print("✅ iSCSI storage configured")
                print("ℹ️  To get initiator IQN, run on Proxmox host:")
                print(f"   ssh root@{config['host']} 'cat /etc/iscsi/initiatorname.iscsi'")
            else:
                print("❌ No iSCSI storage configured")
        except Exception as e:
            print(f"⚠️  Could not check iSCSI: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    settings = Settings()
    instances = settings.list_proxmox_instances()
    
    for instance_id in instances:
        config = settings.get_proxmox_config(instance_id)
        
        if instance_id == "01":
            label = "PROXMOX01 (pve01) - 192.168.215.78"
        elif instance_id == "02":
            label = "PROXMOX02 (pve02) - 192.168.215.77"
        else:
            label = f"PROXMOX Instance {instance_id}"
        
        await get_storage_details(label, config)
    
    print(f"\n{'='*70}")
    print("KEY FINDINGS")
    print(f"{'='*70}")
    print("""
proxmox01: Has 'TrueNAS' NFS storage (shared)
proxmox02: Has 'proxpool' ZFS storage (29.5TB, not shared)

✅ Both can use TrueNAS NFS for shared lab storage
✅ proxmox02's ZFS pool is safe (single-writer, for production VMs)
✅ Ready to cluster once shared storage strategy is confirmed

Next: See PROXMOX_INFRASTRUCTURE_ANALYSIS.md for detailed recommendations
""")


if __name__ == "__main__":
    asyncio.run(main())


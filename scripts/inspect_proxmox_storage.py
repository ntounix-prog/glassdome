#!/usr/bin/env python3
"""
Inspect Proxmox and TrueNAS storage configuration (read-only analysis)
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.config import Settings
from glassdome.platforms.proxmox_client import ProxmoxClient
import json


async def inspect_proxmox(host_label: str, config: dict):
    """Inspect a single Proxmox host"""
    print(f"\n{'='*60}")
    print(f"PROXMOX: {host_label}")
    print(f"  Host: {config['host']}")
    print(f"  Node: {config['node']}")
    print(f"{'='*60}")
    
    if not config['host']:
        print("  ⚠️  No host configured")
        return
    
    try:
        # Initialize client
        client = ProxmoxClient(
            host=config['host'],
            user=config['user'],
            password=config.get('password'),
            token_name=config.get('token_name'),
            token_value=config.get('token_value'),
            verify_ssl=config.get('verify_ssl', False),
            default_node=config['node']
        )
        
        # Test connection
        version_info = await client.get_platform_info()
        print(f"  ✅ Connected: Proxmox {version_info.get('version', 'unknown')}")
        
        # List nodes
        nodes = await client.list_nodes()
        print(f"\n  Nodes: {len(nodes)}")
        for node in nodes:
            print(f"    - {node.get('node')} (status: {node.get('status')})")
        
        # Get storage info via API
        print(f"\n  Storage (via API):")
        try:
            storages = client.client.storage.get()
            for storage in storages:
                storage_id = storage.get('storage')
                storage_type = storage.get('type')
                shared = storage.get('shared', 0)
                content = storage.get('content', '')
                
                print(f"    - {storage_id}")
                print(f"        Type: {storage_type}")
                print(f"        Shared: {'Yes' if shared else 'No'}")
                print(f"        Content: {content}")
                
                # For ZFS storage, get more details
                if storage_type == 'zfspool':
                    try:
                        # Get node-specific storage status
                        for node in nodes:
                            node_name = node.get('node')
                            try:
                                status = client.client.nodes(node_name).storage(storage_id).status.get()
                                print(f"        Status on {node_name}:")
                                print(f"          Total: {status.get('total', 0) / (1024**3):.2f} GB")
                                print(f"          Used: {status.get('used', 0) / (1024**3):.2f} GB")
                                print(f"          Avail: {status.get('avail', 0) / (1024**3):.2f} GB")
                            except:
                                pass
                    except Exception as e:
                        pass
                
                # For iSCSI, show target details
                if storage_type == 'iscsi':
                    print(f"        Portal: {storage.get('portal', 'N/A')}")
                    print(f"        Target: {storage.get('target', 'N/A')}")
        except Exception as e:
            print(f"    ⚠️  Could not list storage: {e}")
        
        # Check for iSCSI initiator name
        print(f"\n  iSCSI Initiator:")
        try:
            for node in nodes:
                node_name = node.get('node')
                try:
                    # Try to read initiator name via execute
                    result = client.client.nodes(node_name).execute.post(
                        command="cat /etc/iscsi/initiatorname.iscsi"
                    )
                    print(f"    {node_name}: (API execute not available)")
                except:
                    print(f"    {node_name}: (need SSH to read /etc/iscsi/initiatorname.iscsi)")
        except:
            print(f"    (need SSH access to read initiator names)")
        
        # List VMs
        print(f"\n  Virtual Machines:")
        for node in nodes:
            node_name = node.get('node')
            vms = await client.list_vms(node_name)
            print(f"    {node_name}: {len(vms)} VMs")
            for vm in sorted(vms, key=lambda x: x.get('vmid', 0)):
                vmid = vm.get('vmid')
                name = vm.get('name', 'unknown')
                status = vm.get('status', 'unknown')
                # Only show template and important VMs
                if vmid >= 9000 or vmid <= 109:
                    template_flag = " [TEMPLATE]" if vm.get('template') else ""
                    print(f"      {vmid}: {name} ({status}){template_flag}")
        
    except Exception as e:
        print(f"  ❌ Error connecting: {e}")


async def main():
    print("\n🔍 Glassdome Infrastructure Storage Analysis")
    print("=" * 60)
    
    # Load settings
    settings = Settings()
    
    # List all Proxmox instances
    instances = settings.list_proxmox_instances()
    print(f"\nConfigured Proxmox Instances: {instances}")
    
    # Inspect each Proxmox
    for instance_id in instances:
        config = settings.get_proxmox_config(instance_id)
        
        # Determine label
        if instance_id == "01":
            label = f"proxmox01 (pve01) - Instance {instance_id}"
        elif instance_id == "02":
            label = f"proxmox02 (pve02) - Instance {instance_id}"
        else:
            label = f"Proxmox Instance {instance_id}"
        
        await inspect_proxmox(label, config)
    
    # TrueNAS inspection (if configured)
    print(f"\n{'='*60}")
    print("TRUENAS (SAN)")
    print(f"{'='*60}")
    
    # Check for TrueNAS env vars
    import os
    truenas_host = os.getenv('TRUENAS_HOST')
    truenas_api_key = os.getenv('TRUENAS_API_KEY')
    
    if truenas_host and truenas_api_key:
        print(f"  Host: {truenas_host}")
        print(f"  API Key: {truenas_api_key[:10]}..." if len(truenas_api_key) > 10 else "  API Key: (set)")
        print(f"\n  ℹ️  TrueNAS API inspection not yet implemented")
        print(f"     Recommend: SSH to TrueNAS or use Web GUI to inspect:")
        print(f"       - iSCSI Targets")
        print(f"       - Initiators/ACLs")
        print(f"       - Extents/Zvols")
    else:
        print(f"  ⚠️  TrueNAS credentials not found in environment")
        print(f"     Set TRUENAS_HOST and TRUENAS_API_KEY if available")
    
    print(f"\n{'='*60}")
    print("SUMMARY & RECOMMENDATIONS")
    print(f"{'='*60}")
    print("\nNext steps to inspect manually (SSH or GUI):")
    print("\n1. Proxmox Storage Details:")
    print("   - GUI: Datacenter → Storage")
    print("   - CLI: pvesm status")
    print("   - Config: cat /etc/pve/storage.cfg")
    print("\n2. Proxmox iSCSI Initiator Names:")
    print("   - SSH to each Proxmox: cat /etc/iscsi/initiatorname.iscsi")
    print("\n3. TrueNAS Configuration:")
    print("   - GUI: Sharing → Block (iSCSI)")
    print("   - Check: Portals, Targets, Extents, Initiators")
    print("\n4. Clustering Check:")
    print("   - Proxmox GUI: Check if nodes are clustered (Datacenter view)")
    print("   - CLI: pvecm status")


if __name__ == "__main__":
    asyncio.run(main())


#!/usr/bin/env python3
"""
Proxmox Template Migration from Original Server

Migrates template disks from original Proxmox (10.0.0.3) to current Proxmox server
via VLAN 10 network without disrupting operations.
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.platforms.proxmox_factory import get_proxmox_client
from glassdome.core.config import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Template IDs to migrate
TEMPLATE_IDS = {
    9000: "Ubuntu 22.04",
    9100: "Windows Server 2022",
    9101: "Windows 11"
}


def verify_network_access(ip: str, timeout: int = 5) -> bool:
    """Test network connectivity to Proxmox server"""
    logger.info(f"Testing connectivity to {ip}...")
    try:
        result = subprocess.run(
            ["ping", "-c", "2", "-W", str(timeout), ip],
            capture_output=True,
            timeout=timeout + 2
        )
        if result.returncode == 0:
            logger.info(f"✅ Successfully connected to {ip}")
            return True
        else:
            logger.warning(f"⚠️  Cannot ping {ip}: {result.stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing connectivity: {e}")
        return False


async def discover_templates_via_api(proxmox_client, node: str = "pve") -> List[Dict[str, Any]]:
    """Discover template VMs using Proxmox API"""
    templates = []
    
    try:
        # Get all VMs
        vms = proxmox_client.client.nodes(node).qemu.get()
        logger.info(f"Found {len(vms)} VMs on node {node}")
        
        for vm in vms:
            vmid = vm.get("vmid")
            if vmid in TEMPLATE_IDS:
                # Get VM config to check if it's a template
                try:
                    config = proxmox_client.client.nodes(node).qemu(vmid).config.get()
                    is_template = config.get("template", 0) == 1
                    
                    template_info = {
                        "vmid": vmid,
                        "name": vm.get("name", f"vm-{vmid}"),
                        "status": vm.get("status", "unknown"),
                        "is_template": is_template,
                        "template_type": TEMPLATE_IDS[vmid],
                        "config": config
                    }
                    
                    # Get disk information
                    disks = []
                    for key, value in config.items():
                        if key.startswith(("scsi", "sata", "virtio", "ide")) and "=" in str(value):
                            disks.append({key: value})
                    
                    template_info["disks"] = disks
                    templates.append(template_info)
                    logger.info(f"Found template {vmid} ({TEMPLATE_IDS[vmid]}): {vm.get('name')}")
                    
                except Exception as e:
                    logger.warning(f"Could not get config for VM {vmid}: {e}")
        
        return templates
        
    except Exception as e:
        logger.error(f"Error discovering templates via API: {e}")
        return []


async def discover_templates_via_filesystem(proxmox_host: str, search_paths: List[str]) -> List[Dict[str, Any]]:
    """Discover template disk images in filesystem via SSH"""
    import re
    import subprocess
    
    found_disks = []
    
    for search_path in search_paths:
        logger.info(f"Searching for template disks in {search_path}...")
        
        # Build find command
        find_cmd = f"find {search_path} -type f \\( -name 'vm-*-disk-*' -o -name '*9000*' -o -name '*9100*' -o -name '*9101*' \\) -size +100M -exec ls -lh {{}} \\; 2>/dev/null"
        
        try:
            # Execute via SSH
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{proxmox_host} '{find_cmd}'"
            result = subprocess.run(
                ssh_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    
                    # Parse ls -lh output
                    parts = line.split()
                    if len(parts) < 9:
                        continue
                    
                    filepath = ' '.join(parts[8:])
                    filename = os.path.basename(filepath)
                    
                    # Extract VM ID
                    vm_id = None
                    match = re.search(r"vm-(\d+)-disk", filename)
                    if match:
                        vm_id = int(match.group(1))
                    else:
                        # Try direct VM ID in filename
                        match = re.search(r"(\d{4})", filename)
                        if match:
                            vm_id = int(match.group(1))
                    
                    if vm_id and vm_id in TEMPLATE_IDS:
                        size_str = parts[4]
                        found_disks.append({
                            "vmid": vm_id,
                            "path": filepath,
                            "filename": filename,
                            "size": size_str,
                            "template_type": TEMPLATE_IDS[vm_id]
                        })
                        logger.info(f"Found disk: {filename} (VM {vm_id})")
        except Exception as e:
            logger.warning(f"Error searching {search_path}: {e}")
    
    return found_disks


async def get_storage_pools(proxmox_client, node: str = "pve") -> List[Dict[str, Any]]:
    """Get list of storage pools"""
    try:
        storage_list = proxmox_client.client.storage.get()
        logger.info(f"Found {len(storage_list)} storage pools")
        return storage_list
    except Exception as e:
        logger.error(f"Error getting storage pools: {e}")
        return []


async def find_template_disks_in_storage(proxmox_client, node: str, storage: str, vm_id: int) -> List[Dict[str, Any]]:
    """Find template disk files in a storage pool"""
    try:
        # List volumes in storage
        volumes = proxmox_client.client.storage(storage).content.get()
        
        disk_files = []
        for volume in volumes:
            volid = volume.get("volid", "")
            content_type = volume.get("content", "")
            
            # Look for disk images for this VM
            if (f"vm-{vm_id}-disk" in volid or f"{vm_id}/" in volid) and content_type in ["images", "rootdir"]:
                disk_info = {
                    "volid": volid,
                    "storage": storage,
                    "size": volume.get("size", 0),
                    "format": volume.get("format", "unknown"),
                    "content": content_type
                }
                disk_files.append(disk_info)
                logger.info(f"Found disk in storage: {volid} ({storage})")
        
        return disk_files
    except Exception as e:
        logger.error(f"Error searching storage {storage} for VM {vm_id}: {e}")
        return []


async def download_template_disk(proxmox_host: str, disk_path: str, 
                                 output_path: str, use_scp: bool = True, 
                                 ssh_password: Optional[str] = None) -> bool:
    """Download template disk from Proxmox server via SCP or qemu-img"""
    try:
        logger.info(f"Downloading {disk_path} from {proxmox_host}...")
        
        if use_scp:
            # Check if this is a storage pool path (e.g., "local-lvm:vm-9100-disk-1")
            if ':' in disk_path and not disk_path.startswith('/'):
                # Storage pool path - need to find actual device path
                storage, volume = disk_path.split(':', 1)
                logger.info(f"Detected storage pool path: {storage}:{volume}")
                
                # Determine actual path based on storage type
                if storage == 'local-lvm':
                    # LVM thin volume - path is /dev/pve/{volume}
                    actual_path = f"/dev/pve/{volume}"
                elif storage.startswith('TrueNAS') or storage.startswith('nfs'):
                    # NFS storage - path is /mnt/pve/{storage}/{volume}
                    actual_path = f"/mnt/pve/{storage}/{volume}"
                else:
                    # Try common paths
                    actual_path = f"/mnt/pve/{storage}/{volume}"
                
                logger.info(f"Using actual path: {actual_path}")
                
                # Use qemu-img convert via SSH to export the disk
                if ssh_password:
                    qemu_cmd = f"qemu-img convert -f raw -O raw {actual_path} -"
                    ssh_cmd = f"sshpass -p '{ssh_password}' ssh -o StrictHostKeyChecking=no root@{proxmox_host} '{qemu_cmd}'"
                else:
                    qemu_cmd = f"qemu-img convert -f raw -O raw {actual_path} -"
                    ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{proxmox_host} '{qemu_cmd}'"
                
                logger.info(f"Exporting disk via qemu-img convert...")
                try:
                    with open(output_path, 'wb') as f:
                        result = subprocess.run(
                            ssh_cmd,
                            shell=True,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            timeout=7200  # 2 hour timeout for large disks
                        )
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Successfully exported disk to {output_path}")
                        return True
                    else:
                        logger.error(f"❌ qemu-img convert failed: {result.stderr.decode()}")
                        return False
                except subprocess.TimeoutExpired:
                    logger.error(f"❌ Export timed out (disk may be very large)")
                    return False
            else:
                # Direct file path - use SCP
                if ssh_password:
                    scp_cmd = f"sshpass -p '{ssh_password}' scp -o StrictHostKeyChecking=no root@{proxmox_host}:{disk_path} {output_path}"
                else:
                    scp_cmd = f"scp -o StrictHostKeyChecking=no root@{proxmox_host}:{disk_path} {output_path}"
                
                logger.info(f"Downloading file via SCP...")
                result = subprocess.run(
                    scp_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout for large files
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ Successfully downloaded to {output_path}")
                    return True
                else:
                    logger.error(f"❌ SCP failed: {result.stderr}")
                    return False
        else:
            # Alternative: Use qemu-img convert via SSH (for storage pool volumes)
            logger.warning("qemu-img convert method not yet implemented")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Download timed out (file may be very large)")
        return False
    except Exception as e:
        logger.error(f"❌ Error downloading disk: {e}")
        return False


async def import_template_disk(target_proxmox_host: str, vm_id: int, disk_path: str, 
                               storage: str = "local-lvm", node: str = "pve") -> bool:
    """Import template disk to target Proxmox using qm importdisk via SSH"""
    try:
        logger.info(f"Importing disk {disk_path} to VM {vm_id} on {target_proxmox_host}...")
        
        # Use qm importdisk via SSH
        import_cmd = f"qm importdisk {vm_id} {disk_path} {storage}"
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{target_proxmox_host} '{import_cmd}'"
        
        logger.info(f"Running: {ssh_cmd}")
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout for large imports
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully imported disk to VM {vm_id}")
            logger.debug(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ Import failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Import timed out (disk may be very large)")
        return False
    except Exception as e:
        logger.error(f"❌ Error importing disk: {e}")
        return False


async def verify_template(target_proxmox, vm_id: int, node: str = "pve") -> Dict[str, Any]:
    """Verify template exists and is accessible on target Proxmox"""
    try:
        config = target_proxmox.client.nodes(node).qemu(vm_id).config.get()
        is_template = config.get("template", 0) == 1
        status = target_proxmox.client.nodes(node).qemu(vm_id).status.current.get()
        vm_status = status.get("status", "unknown")
        
        # Check for attached disks
        disks = []
        for key, value in config.items():
            if key.startswith(("scsi", "sata", "virtio", "ide")) and "=" in str(value):
                disks.append({key: value})
        
        result = {
            "exists": True,
            "is_template": is_template,
            "status": vm_status,
            "disks": disks,
            "config": config
        }
        
        if is_template:
            logger.info(f"✅ Template {vm_id} verified on target Proxmox (status: {vm_status})")
        else:
            logger.warning(f"⚠️  VM {vm_id} exists but is not marked as template (status: {vm_status})")
        
        return result
    except Exception as e:
        logger.error(f"❌ Template {vm_id} not found on target Proxmox: {e}")
        return {"exists": False, "error": str(e)}


async def main():
    """Main migration process"""
    settings = Settings()
    
    # Parse arguments
    dry_run = "--execute" not in sys.argv
    original_proxmox_ip = "192.168.215.78"  # Default to direct network
    
    if "--original-ip" in sys.argv:
        idx = sys.argv.index("--original-ip")
        if idx + 1 < len(sys.argv):
            original_proxmox_ip = sys.argv[idx + 1]
    
    if dry_run:
        logger.info("=" * 70)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 70)
        logger.info("Add --execute flag to perform actual migration")
        logger.info("")
    
    # Original Proxmox configuration
    # Support both VLAN 10 (10.0.0.3) and direct network (192.168.215.78)
    original_proxmox_instance = "01"  # Assuming original is instance 01
    
    # Current Proxmox configuration
    current_proxmox_instance = "02"  # Assuming current is instance 02
    
    logger.info("=" * 70)
    logger.info("Proxmox Template Migration")
    logger.info("=" * 70)
    logger.info(f"Original Proxmox: {original_proxmox_ip}")
    logger.info(f"Templates to migrate: {list(TEMPLATE_IDS.keys())}")
    logger.info("")
    
    # Step 1: Verify network connectivity
    logger.info("Phase 1: Network Verification")
    logger.info("-" * 70)
    if not verify_network_access(original_proxmox_ip):
        logger.error("❌ Cannot reach original Proxmox. Please configure VLAN 10 network first.")
        logger.error("   Run: scripts/configure_proxmox_vlan10.sh")
        return 1
    
    # Step 2: Connect to original Proxmox
    logger.info("")
    logger.info("Phase 2: Template Discovery")
    logger.info("-" * 70)
    logger.info("Connecting to original Proxmox...")
    
    try:
        original_proxmox = get_proxmox_client(instance_id=original_proxmox_instance)
        # Get node name from config
        from glassdome.core.config import settings
        original_config = settings.get_proxmox_config(original_proxmox_instance)
        original_node = original_config.get("node", "pve01")
        logger.info(f"✅ Connected to original Proxmox (node: {original_node})")
    except Exception as e:
        logger.error(f"❌ Failed to connect to original Proxmox: {e}")
        logger.error("   Check Proxmox credentials in .env")
        return 1
    
    # Step 3: Discover templates
    logger.info("")
    logger.info("Discovering templates on original Proxmox...")
    templates = await discover_templates_via_api(original_proxmox, node=original_node)
    
    # Also search filesystem for orphaned disks
    logger.info("")
    logger.info("Searching filesystem for template disks...")
    filesystem_disks = await discover_templates_via_filesystem(
        original_proxmox_ip,
        ["/mnt/esxstore", "/var/lib/vz/images"]
    )
    
    # Search storage pools for template disks
    logger.info("")
    logger.info("Searching storage pools for template disks...")
    storage_pools = await get_storage_pools(original_proxmox, node=original_node)
    
    storage_disks = []
    for pool in storage_pools:
        pool_name = pool.get("storage")
        pool_type = pool.get("type")
        logger.info(f"   Searching storage: {pool_name} ({pool_type})")
        
        for vm_id in TEMPLATE_IDS.keys():
            disks = await find_template_disks_in_storage(original_proxmox, original_node, pool_name, vm_id)
            storage_disks.extend(disks)
    
    # Combine all findings
    logger.info("")
    logger.info(f"Discovery Summary:")
    logger.info(f"  Templates via API: {len(templates)}")
    logger.info(f"  Disks in filesystem: {len(filesystem_disks)}")
    logger.info(f"  Disks in storage pools: {len(storage_disks)}")
    logger.info("")
    
    if templates:
        logger.info(f"Found {len(templates)} template VM(s):")
        for template in templates:
            logger.info(f"  - VM {template['vmid']}: {template['template_type']} ({template['name']})")
            logger.info(f"    Status: {template['status']}, Template: {template['is_template']}")
            logger.info(f"    Disks: {len(template['disks'])}")
    
    if filesystem_disks:
        logger.info(f"Found {len(filesystem_disks)} disk file(s) in filesystem:")
        for disk in filesystem_disks:
            logger.info(f"  - {disk['filename']} (VM {disk['vmid']}, {disk['size']})")
    
    if storage_disks:
        logger.info(f"Found {len(storage_disks)} disk(s) in storage pools:")
        for disk in storage_disks:
            logger.info(f"  - {disk['volid']} ({disk['storage']}, {disk.get('size', 'unknown')} bytes)")
    
    # Step 4: Connect to current Proxmox
    logger.info("")
    logger.info("Phase 3: Template Migration")
    logger.info("-" * 70)
    logger.info("Connecting to current Proxmox...")
    
    try:
        current_proxmox = get_proxmox_client(instance_id=current_proxmox_instance)
        # Get node name from config
        from glassdome.core.config import settings
        current_config = settings.get_proxmox_config(current_proxmox_instance)
        current_node = current_config.get("node", "pve02")
        logger.info(f"✅ Connected to current Proxmox (node: {current_node})")
    except Exception as e:
        logger.error(f"❌ Failed to connect to current Proxmox: {e}")
        return 1
    
    # Step 5: Migration process (if not dry run)
    if not dry_run:
        logger.info("")
        logger.info("Starting migration process...")
        
        # Create temporary directory for downloads
        temp_dir = Path("/tmp/proxmox_template_migration")
        temp_dir.mkdir(exist_ok=True)
        logger.info(f"Using temporary directory: {temp_dir}")
        
        # Migrate each template
        migration_results = []
        
        for vm_id in TEMPLATE_IDS.keys():
            logger.info("")
            logger.info(f"Migrating template {vm_id} ({TEMPLATE_IDS[vm_id]})...")
            
            # Find disk to migrate - check templates found via API first
            disk_to_migrate = None
            template_info = None
            
            # Check templates discovered via API
            for template in templates:
                if template['vmid'] == vm_id:
                    template_info = template
                    # Extract disk path from config - skip CD-ROMs and ISOs
                    for disk_config in template.get('disks', []):
                        for key, value in disk_config.items():
                            if '=' in str(value):
                                disk_str = str(value)
                                # Skip CD-ROMs and ISO files
                                if 'media=cdrom' in disk_str or '.iso' in disk_str.lower():
                                    continue
                                # Parse disk path (e.g., "local-lvm:vm-9100-disk-1,cache=writeback")
                                disk_path = disk_str.split(',')[0]
                                disk_to_migrate = {
                                    'vmid': vm_id,
                                    'path': disk_path,
                                    'type': 'api_discovered'
                                }
                                break
                        if disk_to_migrate:
                            break
                    break
            
            # Fallback to filesystem disks
            if not disk_to_migrate:
                for disk in filesystem_disks:
                    if disk['vmid'] == vm_id:
                        disk_to_migrate = disk
                        break
            
            # Fallback to storage pool disks
            if not disk_to_migrate:
                for disk in storage_disks:
                    if f"vm-{vm_id}-disk" in disk.get('volid', ''):
                        disk_to_migrate = disk
                        break
            
            if not disk_to_migrate:
                logger.warning(f"⚠️  No disk found for template {vm_id}")
                continue
            
            # Download disk
            if 'path' in disk_to_migrate:
                # Filesystem disk or storage pool path
                source_path = disk_to_migrate['path']
                output_file = temp_dir / f"vm-{vm_id}-disk-0.raw"
                
                # Get SSH password from config
                original_config = settings.get_proxmox_config(original_proxmox_instance)
                ssh_password = original_config.get("password") or settings.proxmox_admin_passwd
                
                if await download_template_disk(original_proxmox_ip, source_path, str(output_file), ssh_password=ssh_password):
                    # Import to current Proxmox
                    current_config = settings.get_proxmox_config(current_proxmox_instance)
                    current_proxmox_host = current_config.get("host") or "192.168.215.77"
                    if await import_template_disk(current_proxmox_host, vm_id, str(output_file)):
                        # Verify template exists
                        verification = await verify_template(current_proxmox, vm_id, node=current_node)
                        if verification.get("exists"):
                            migration_results.append({
                                "vmid": vm_id,
                                "status": "success",
                                "verification": verification
                            })
                        else:
                            migration_results.append({
                                "vmid": vm_id,
                                "status": "imported_but_not_verified"
                            })
                    else:
                        migration_results.append({
                            "vmid": vm_id,
                            "status": "import_failed"
                        })
                else:
                    migration_results.append({
                        "vmid": vm_id,
                        "status": "download_failed"
                    })
            else:
                logger.warning(f"⚠️  Storage pool disk migration not yet implemented for {disk_to_migrate}")
        
        # Summary
        logger.info("")
        logger.info("Migration Summary:")
        for result in migration_results:
            logger.info(f"  VM {result['vmid']}: {result['status']}")
        
    else:
        logger.info("")
        logger.info("Dry run complete. Review above and run with --execute to migrate.")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Migration Process Complete")
    logger.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


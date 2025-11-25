"""
Cloudbase-Init Template Builder

Creates Windows templates with Cloudbase-Init pre-installed and configured
for Proxmox cloud-init deployment.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import subprocess

from glassdome.utils.cloudbase_init_config import create_cloudbase_init_config_files
from glassdome.utils.windows_autounattend import generate_autounattend_xml, create_autounattend_floppy

logger = logging.getLogger(__name__)


class CloudbaseInitBuilder:
    """
    Builds Windows templates with Cloudbase-Init for Proxmox
    """
    
    def __init__(
        self,
        proxmox_client,
        cloudbase_init_installer_url: str = "https://www.cloudbase.it/downloads/CloudbaseInitSetup_Stable_x64.msi"
    ):
        """
        Initialize Cloudbase-Init builder
        
        Args:
            proxmox_client: ProxmoxClient instance
            cloudbase_init_installer_url: URL to download Cloudbase-Init installer
        """
        self.proxmox_client = proxmox_client
        self.cloudbase_init_installer_url = cloudbase_init_installer_url
        self.working_dir = Path(tempfile.gettempdir()) / "cloudbase-init-builder"
        self.working_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_windows_template_with_cloudbase_init(
        self,
        template_id: int,
        windows_version: str = "server2022",
        node: str = "pve01",
        storage: str = "local-lvm",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Windows template with Cloudbase-Init installed
        
        This is a multi-step process:
        1. Create Windows VM from ISO with autounattend
        2. Install Cloudbase-Init (manual step or via autounattend)
        3. Configure Cloudbase-Init
        4. Install QEMU guest agent
        5. Run sysprep
        6. Convert to template
        
        Args:
            template_id: Template VM ID
            windows_version: "server2022" or "win11"
            node: Proxmox node name
            storage: Storage name
            config: Additional configuration
        
        Returns:
            Result dictionary with template information
        """
        if config is None:
            config = {}
        
        logger.info(f"Creating Windows {windows_version} template {template_id} with Cloudbase-Init")
        
        # Step 1: Create Windows VM from ISO
        logger.info("Step 1: Creating Windows VM from ISO...")
        # Different defaults based on Windows version
        if windows_version == "server2022":
            # Windows Server 2022: 8 vCPU, 80GB disk, 16GB RAM
            default_memory = 16384  # 16GB RAM
            default_cores = 8  # 8 vCPU
            default_disk = 80  # 80GB disk
        else:
            # Windows 11: 4 vCPU, 30GB disk, 16GB RAM
            default_memory = 16384  # 16GB RAM
            default_cores = 4  # 4 vCPU
            default_disk = 30  # 30GB disk
        
        vm_config = {
            "name": f"windows-{windows_version}-template",
            "windows_version": windows_version,
            "memory_mb": config.get("memory_mb", default_memory),
            "cpu_cores": config.get("cpu_cores", default_cores),
            "disk_size_gb": config.get("disk_size_gb", default_disk),
            "admin_password": config.get("admin_password", "Glassdome123!"),
            "enable_rdp": True,
            "vlan_tag": 2,  # VLAN 2 for 192.168.3.x network
            **config
        }
        
        # Create VM using autounattend (initial installation)
        try:
            result = await self.proxmox_client.create_windows_vm_from_iso(
                node=node,
                vmid=template_id,
                config=vm_config
            )
            
            # Check if result indicates success (has vm_id)
            if not result or not result.get("vm_id"):
                return {
                    "success": False,
                    "error": f"Failed to create Windows VM: {result}",
                    "step": "vm_creation"
                }
        except Exception as e:
            logger.error(f"Exception creating Windows VM: {e}")
            return {
                "success": False,
                "error": f"Failed to create Windows VM: {str(e)}",
                "step": "vm_creation"
            }
        
        logger.info(f"Windows VM {template_id} created, waiting for installation to complete...")
        logger.warning("⚠️  Manual steps required:")
        logger.warning("  1. Wait for Windows installation to complete (~15-20 minutes)")
        logger.warning("  2. RDP into the VM")
        logger.warning("  3. Install Cloudbase-Init (download from cloudbase.it)")
        logger.warning("  4. Install QEMU guest agent")
        logger.warning("  5. Run sysprep")
        logger.warning("  6. Convert to template")
        
        # Generate Cloudbase-Init configuration files for reference
        cloudbase_config = {
            "hostname": f"windows-{windows_version}-template",
            "enable_rdp": True,
            "disable_firewall": True,
            "username": "Administrator",
            "instance_id": f"template-{template_id}"
        }
        
        config_dir = self.working_dir / f"template-{template_id}"
        files = create_cloudbase_init_config_files(config_dir, cloudbase_config)
        
        logger.info(f"Cloudbase-Init configuration files generated in: {config_dir}")
        logger.info("Copy these files to the VM after Cloudbase-Init installation:")
        for name, path in files.items():
            logger.info(f"  - {name}: {path}")
        
        return {
            "success": True,
            "template_id": template_id,
            "vm_id": template_id,
            "status": "awaiting_manual_setup",
            "next_steps": [
                "Wait for Windows installation to complete",
                "RDP into the VM",
                "Download and install Cloudbase-Init",
                "Copy configuration files to C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\conf\\",
                "Install QEMU guest agent",
                "Run sysprep: C:\\Windows\\System32\\Sysprep\\sysprep.exe /generalize /oobe /shutdown",
                "Convert to template: qm template {template_id}"
            ],
            "config_files": {name: str(path) for name, path in files.items()}
        }
    
    async def install_cloudbase_init_via_autounattend(
        self,
        template_id: int,
        node: str = "pve01"
    ) -> Dict[str, Any]:
        """
        Attempt to install Cloudbase-Init via autounattend FirstLogonCommands
        
        Note: This requires downloading the installer during Windows installation,
        which may not work if network access is restricted.
        
        Args:
            template_id: VM ID
            node: Proxmox node name
        
        Returns:
            Result dictionary
        """
        logger.info("Attempting to install Cloudbase-Init via autounattend...")
        
        # This would require modifying autounattend.xml to download and install
        # Cloudbase-Init during FirstLogonCommands
        # For now, this is a placeholder for future automation
        
        return {
            "success": False,
            "error": "Automatic Cloudbase-Init installation not yet implemented",
            "note": "Manual installation required for now"
        }


async def create_windows_template_workflow(
    proxmox_client,
    template_id: int,
    windows_version: str,
    node: str = "pve01",
    storage: str = "local-lvm"
) -> Dict[str, Any]:
    """
    Convenience function to create Windows template with Cloudbase-Init
    
    Args:
        proxmox_client: ProxmoxClient instance
        template_id: Template VM ID
        windows_version: "server2022" or "win11"
        node: Proxmox node name
        storage: Storage name
    
    Returns:
        Result dictionary
    """
    builder = CloudbaseInitBuilder(proxmox_client)
    
    return await builder.create_windows_template_with_cloudbase_init(
        template_id=template_id,
        windows_version=windows_version,
        node=node,
        storage=storage
    )


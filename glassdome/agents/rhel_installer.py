"""
Rhel Installer module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import logging
from typing import Dict, Any, Optional
from glassdome.agents.base import DeploymentAgent, AgentStatus
from glassdome.platforms.base import PlatformClient

logger = logging.getLogger(__name__)


class RHELInstallerAgent(DeploymentAgent):
    """
    Agent specialized in creating base RHEL installation images
    Listens for API calls and autonomously creates RHEL VMs
    
    Note: RHEL requires subscription management. This agent assumes
    subscription is handled via cloud-init or pre-configured templates.
    """
    
    RHEL_VERSIONS = {
        "9": {
            "name": "Red Hat Enterprise Linux 9",
            "cloud_image": "rhel-9-cloud-base-x86_64.qcow2",
            "iso": "rhel-9.3-x86_64-dvd.iso",
            "template_id": 9500,
        },
        "8": {
            "name": "Red Hat Enterprise Linux 8",
            "cloud_image": "rhel-8-cloud-base-x86_64.qcow2",
            "iso": "rhel-8.9-x86_64-dvd.iso",
            "template_id": 9501,
        }
    }
    
    DEFAULT_CONFIG = {
        "cores": 2,
        "memory": 2048,  # MB
        "disk_size": 20,  # GB
        "network": "vmbr0",
        "storage": "local-lvm",
    }
    
    def __init__(self, agent_id: str, platform_client: PlatformClient):
        """
        Initialize RHEL Installer Agent
        
        This agent is PLATFORM-AGNOSTIC - it accepts any platform client
        that implements the PlatformClient interface.
        
        Args:
            agent_id: Unique agent identifier
            platform_client: Platform client (Proxmox, AWS, Azure, etc.)
        """
        super().__init__(agent_id, platform_client)
        self.platform = platform_client
        logger.info(f"RHEL Installer Agent {agent_id} initialized with platform: {type(platform_client).__name__}")
        logger.warning("RHEL requires valid subscription. Ensure subscription is configured in templates or cloud-init.")
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate RHEL installation task
        
        Args:
            task: Task definition
            
        Returns:
            True if task is valid
        """
        # Check required fields
        if task.get("element_type") != "rhel_vm":
            return False
        
        config = task.get("config", {})
        
        # Validate RHEL version
        version = config.get("rhel_version", "9")
        if version not in self.RHEL_VERSIONS:
            logger.error(f"Unsupported RHEL version: {version}")
            return False
        
        return True
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy RHEL VM (PLATFORM-AGNOSTIC)
        
        Uses standardized PlatformClient interface to deploy to any platform.
        This method prepares RHEL-specific configuration and delegates deployment.
        
        Args:
            element_type: Should be "rhel_vm"
            config: VM configuration with keys:
                - name: VM name
                - rhel_version: RHEL version (default: "9")
                - cores: CPU cores (default: 2)
                - memory: RAM in MB (default: 2048)
                - disk_size: Disk size in GB (default: 20)
                - network: Network identifier
                - ssh_user: SSH username (default: "cloud-user")
                - packages: List of packages to install
                - users: List of user accounts
                - subscription_user: RHEL subscription username (optional)
                - subscription_password: RHEL subscription password (optional)
            
        Returns:
            Deployment result with VM details
        """
        logger.info(f"Starting RHEL VM deployment with config: {config}")
        
        # Extract RHEL-specific configuration
        rhel_version = config.get("rhel_version", "9")
        vm_name = config.get("name", f"rhel-{rhel_version}-{self.agent_id}")
        
        # Validate RHEL version
        if rhel_version not in self.RHEL_VERSIONS:
            raise ValueError(f"Unsupported RHEL version: {rhel_version}")
        
        rhel_info = self.RHEL_VERSIONS[rhel_version]
        
        # Build platform-agnostic VM configuration
        vm_config = {
            "name": vm_name,
            "cores": config.get("cores", self.DEFAULT_CONFIG["cores"]),
            "memory": config.get("memory", self.DEFAULT_CONFIG["memory"]),
            "disk_size": config.get("disk_size", self.DEFAULT_CONFIG["disk_size"]),
            "network": config.get("network", self.DEFAULT_CONFIG["network"]),
            "storage": config.get("storage", self.DEFAULT_CONFIG["storage"]),
            
            # RHEL-specific metadata
            "os_type": "rhel",
            "os_version": rhel_version,
            "os_name": rhel_info["name"],
            
            # SSH configuration
            "ssh_user": config.get("ssh_user", "cloud-user"),
            "ssh_key_path": config.get("ssh_key_path"),
            
            # Cloud-init / provisioning
            "packages": config.get("packages", ["openssh-server", "qemu-guest-agent"]),
            "users": config.get("users", [{"name": "cloud-user", "sudo": True}]),
            
            # RHEL subscription (if provided)
            "subscription_user": config.get("subscription_user"),
            "subscription_password": config.get("subscription_password"),
            
            # Template or ISO
            "template_id": config.get("template_id", rhel_info.get("template_id")),
            "iso_path": rhel_info.get("iso"),
            "cloud_image": rhel_info.get("cloud_image"),
            
            # Platform-specific overrides (pass-through)
            "node": config.get("node"),
            "vmid": config.get("vmid"),
        }
        
        try:
            # Delegate to platform client (platform-agnostic!)
            result = await self.platform.create_vm(vm_config)
            
            # Return standardized result
            return {
                "success": True,
                "resource_id": result["vm_id"],
                "vm_name": vm_name,
                "rhel_version": rhel_version,
                "ip_address": result.get("ip_address"),
                "platform": result.get("platform"),
                "status": result.get("status"),
                "ansible_connection": result.get("ansible_connection"),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy RHEL VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "rhel_version": rhel_version
            }


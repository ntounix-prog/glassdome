"""
Parrot Installer module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
import logging
from typing import Dict, Any, Optional
from glassdome.agents.base import DeploymentAgent, AgentStatus
from glassdome.platforms.base import PlatformClient

logger = logging.getLogger(__name__)


class ParrotInstallerAgent(DeploymentAgent):
    """
    Agent specialized in creating base Parrot Security installation images
    Listens for API calls and autonomously creates Parrot Security VMs
    """
    
    PARROT_VERSIONS = {
        "6.0": {
            "name": "Parrot Security 6.0",
            "cloud_image": "parrot-security-6.0-cloud-amd64.img",
            "iso": "parrot-security-6.0_amd64.iso",
            "template_id": 9400,
        },
        "5.3": {
            "name": "Parrot Security 5.3",
            "cloud_image": "parrot-security-5.3-cloud-amd64.img",
            "iso": "parrot-security-5.3_amd64.iso",
            "template_id": 9401,
        }
    }
    
    DEFAULT_CONFIG = {
        "cores": 4,  # Parrot needs more CPU for tools
        "memory": 4096,  # MB - Parrot needs more RAM
        "disk_size": 40,  # GB - Parrot is larger than Ubuntu
        "network": "vmbr0",
        "storage": "local-lvm",
    }
    
    def __init__(self, agent_id: str, platform_client: PlatformClient):
        """
        Initialize Parrot Security Installer Agent
        
        This agent is PLATFORM-AGNOSTIC - it accepts any platform client
        that implements the PlatformClient interface.
        
        Args:
            agent_id: Unique agent identifier
            platform_client: Platform client (Proxmox, AWS, Azure, etc.)
        """
        super().__init__(agent_id, platform_client)
        self.platform = platform_client
        logger.info(f"Parrot Security Installer Agent {agent_id} initialized with platform: {type(platform_client).__name__}")
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate Parrot Security installation task
        
        Args:
            task: Task definition
            
        Returns:
            True if task is valid
        """
        # Check required fields
        if task.get("element_type") != "parrot_vm":
            return False
        
        config = task.get("config", {})
        
        # Validate Parrot version
        version = config.get("parrot_version", "6.0")
        if version not in self.PARROT_VERSIONS:
            logger.error(f"Unsupported Parrot Security version: {version}")
            return False
        
        return True
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy Parrot Security VM (PLATFORM-AGNOSTIC)
        
        Uses standardized PlatformClient interface to deploy to any platform.
        This method prepares Parrot Security-specific configuration and delegates deployment.
        
        Args:
            element_type: Should be "parrot_vm"
            config: VM configuration with keys:
                - name: VM name
                - parrot_version: Parrot version (default: "6.0")
                - cores: CPU cores (default: 4)
                - memory: RAM in MB (default: 4096)
                - disk_size: Disk size in GB (default: 40)
                - network: Network identifier
                - ssh_user: SSH username (default: "parrot")
                - packages: List of packages to install
                - users: List of user accounts
            
        Returns:
            Deployment result with VM details
        """
        logger.info(f"Starting Parrot Security VM deployment with config: {config}")
        
        # Extract Parrot Security-specific configuration
        parrot_version = config.get("parrot_version", "6.0")
        vm_name = config.get("name", f"parrot-{parrot_version}-{self.agent_id}")
        
        # Validate Parrot version
        if parrot_version not in self.PARROT_VERSIONS:
            raise ValueError(f"Unsupported Parrot Security version: {parrot_version}")
        
        parrot_info = self.PARROT_VERSIONS[parrot_version]
        
        # Build platform-agnostic VM configuration
        vm_config = {
            "name": vm_name,
            "cores": config.get("cores", self.DEFAULT_CONFIG["cores"]),
            "memory": config.get("memory", self.DEFAULT_CONFIG["memory"]),
            "disk_size": config.get("disk_size", self.DEFAULT_CONFIG["disk_size"]),
            "network": config.get("network", self.DEFAULT_CONFIG["network"]),
            "storage": config.get("storage", self.DEFAULT_CONFIG["storage"]),
            
            # Parrot Security-specific metadata
            "os_type": "parrot",
            "os_version": parrot_version,
            "os_name": parrot_info["name"],
            
            # SSH configuration
            "ssh_user": config.get("ssh_user", "parrot"),
            "ssh_key_path": config.get("ssh_key_path"),
            
            # Cloud-init / provisioning
            "packages": config.get("packages", ["openssh-server", "qemu-guest-agent"]),
            "users": config.get("users", [{"name": "parrot", "sudo": True}]),
            
            # Template or ISO
            "template_id": config.get("template_id", parrot_info.get("template_id")),
            "iso_path": parrot_info.get("iso"),
            "cloud_image": parrot_info.get("cloud_image"),
            
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
                "parrot_version": parrot_version,
                "ip_address": result.get("ip_address"),
                "platform": result.get("platform"),
                "status": result.get("status"),
                "ansible_connection": result.get("ansible_connection"),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy Parrot Security VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "parrot_version": parrot_version
            }


"""
Kali Installer module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
import logging
from typing import Dict, Any, Optional
from glassdome.agents.base import DeploymentAgent, AgentStatus
from glassdome.platforms.base import PlatformClient

logger = logging.getLogger(__name__)


class KaliInstallerAgent(DeploymentAgent):
    """
    Agent specialized in creating base Kali Linux installation images
    Listens for API calls and autonomously creates Kali Linux VMs
    """
    
    KALI_VERSIONS = {
        "2024.1": {
            "name": "Kali Linux 2024.1",
            "cloud_image": "kali-linux-2024.1-cloud-amd64.img",
            "iso": "kali-linux-2024.1-installer-amd64.iso",
            "template_id": 9300,
        },
        "2024.2": {
            "name": "Kali Linux 2024.2",
            "cloud_image": "kali-linux-2024.2-cloud-amd64.img",
            "iso": "kali-linux-2024.2-installer-amd64.iso",
            "template_id": 9301,
        },
        "2023.4": {
            "name": "Kali Linux 2023.4",
            "cloud_image": "kali-linux-2023.4-cloud-amd64.img",
            "iso": "kali-linux-2023.4-installer-amd64.iso",
            "template_id": 9302,
        }
    }
    
    DEFAULT_CONFIG = {
        "cores": 4,  # Kali needs more CPU for tools
        "memory": 4096,  # MB - Kali needs more RAM
        "disk_size": 50,  # GB - Kali is larger
        "network": "vmbr0",
        "storage": "local-lvm",
    }
    
    def __init__(self, agent_id: str, platform_client: PlatformClient):
        """
        Initialize Kali Linux Installer Agent
        
        This agent is PLATFORM-AGNOSTIC - it accepts any platform client
        that implements the PlatformClient interface.
        
        Args:
            agent_id: Unique agent identifier
            platform_client: Platform client (Proxmox, AWS, Azure, etc.)
        """
        super().__init__(agent_id, platform_client)
        self.platform = platform_client
        logger.info(f"Kali Linux Installer Agent {agent_id} initialized with platform: {type(platform_client).__name__}")
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate Kali Linux installation task
        
        Args:
            task: Task definition
            
        Returns:
            True if task is valid
        """
        # Check required fields
        if task.get("element_type") != "kali_vm":
            return False
        
        config = task.get("config", {})
        
        # Validate Kali version
        version = config.get("kali_version", "2024.1")
        if version not in self.KALI_VERSIONS:
            logger.error(f"Unsupported Kali Linux version: {version}")
            return False
        
        return True
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy Kali Linux VM (PLATFORM-AGNOSTIC)
        
        Uses standardized PlatformClient interface to deploy to any platform.
        This method prepares Kali Linux-specific configuration and delegates deployment.
        
        Args:
            element_type: Should be "kali_vm"
            config: VM configuration with keys:
                - name: VM name
                - kali_version: Kali version (default: "2024.1")
                - cores: CPU cores (default: 4)
                - memory: RAM in MB (default: 4096)
                - disk_size: Disk size in GB (default: 50)
                - network: Network identifier
                - ssh_user: SSH username (default: "kali")
                - packages: List of packages to install
                - users: List of user accounts
            
        Returns:
            Deployment result with VM details
        """
        logger.info(f"Starting Kali Linux VM deployment with config: {config}")
        
        # Extract Kali Linux-specific configuration
        kali_version = config.get("kali_version", "2024.1")
        vm_name = config.get("name", f"kali-{kali_version}-{self.agent_id}")
        
        # Validate Kali version
        if kali_version not in self.KALI_VERSIONS:
            raise ValueError(f"Unsupported Kali Linux version: {kali_version}")
        
        kali_info = self.KALI_VERSIONS[kali_version]
        
        # Build platform-agnostic VM configuration
        vm_config = {
            "name": vm_name,
            "cores": config.get("cores", self.DEFAULT_CONFIG["cores"]),
            "memory": config.get("memory", self.DEFAULT_CONFIG["memory"]),
            "disk_size": config.get("disk_size", self.DEFAULT_CONFIG["disk_size"]),
            "network": config.get("network", self.DEFAULT_CONFIG["network"]),
            "storage": config.get("storage", self.DEFAULT_CONFIG["storage"]),
            
            # Kali Linux-specific metadata
            "os_type": "kali",
            "os_version": kali_version,
            "os_name": kali_info["name"],
            
            # SSH configuration
            "ssh_user": config.get("ssh_user", "kali"),
            "ssh_key_path": config.get("ssh_key_path"),
            
            # Cloud-init / provisioning
            "packages": config.get("packages", ["openssh-server", "qemu-guest-agent"]),
            "users": config.get("users", [{"name": "kali", "sudo": True}]),
            
            # Template or ISO
            "template_id": config.get("template_id", kali_info.get("template_id")),
            "iso_path": kali_info.get("iso"),
            "cloud_image": kali_info.get("cloud_image"),
            
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
                "kali_version": kali_version,
                "ip_address": result.get("ip_address"),
                "platform": result.get("platform"),
                "status": result.get("status"),
                "ansible_connection": result.get("ansible_connection"),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy Kali Linux VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "kali_version": kali_version
            }


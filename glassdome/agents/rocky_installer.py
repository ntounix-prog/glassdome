"""
Rocky Linux Installer Agent
Autonomous agent for creating base Rocky Linux installation images

PLATFORM-AGNOSTIC: Works with any platform (Proxmox, AWS, Azure, etc.)
This agent knows HOW to configure Rocky Linux, not WHERE to deploy it.
"""
import logging
from typing import Dict, Any, Optional
from glassdome.agents.base import DeploymentAgent, AgentStatus
from glassdome.platforms.base import PlatformClient

logger = logging.getLogger(__name__)


class RockyInstallerAgent(DeploymentAgent):
    """
    Agent specialized in creating base Rocky Linux installation images
    Listens for API calls and autonomously creates Rocky Linux VMs
    """
    
    ROCKY_VERSIONS = {
        "9": {
            "name": "Rocky Linux 9",
            "cloud_image": "Rocky-9-GenericCloud-Base.latest.x86_64.qcow2",
            "iso": "Rocky-9.3-x86_64-minimal.iso",
            "template_id": 9200,
        },
        "8": {
            "name": "Rocky Linux 8",
            "cloud_image": "Rocky-8-GenericCloud-Base.latest.x86_64.qcow2",
            "iso": "Rocky-8.9-x86_64-minimal.iso",
            "template_id": 9201,
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
        Initialize Rocky Linux Installer Agent
        
        This agent is PLATFORM-AGNOSTIC - it accepts any platform client
        that implements the PlatformClient interface.
        
        Args:
            agent_id: Unique agent identifier
            platform_client: Platform client (Proxmox, AWS, Azure, etc.)
        """
        super().__init__(agent_id, platform_client)
        self.platform = platform_client
        logger.info(f"Rocky Linux Installer Agent {agent_id} initialized with platform: {type(platform_client).__name__}")
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate Rocky Linux installation task
        
        Args:
            task: Task definition
            
        Returns:
            True if task is valid
        """
        # Check required fields
        if task.get("element_type") != "rocky_vm":
            return False
        
        config = task.get("config", {})
        
        # Validate Rocky version
        version = config.get("rocky_version", "9")
        if version not in self.ROCKY_VERSIONS:
            logger.error(f"Unsupported Rocky Linux version: {version}")
            return False
        
        return True
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy Rocky Linux VM (PLATFORM-AGNOSTIC)
        
        Uses standardized PlatformClient interface to deploy to any platform.
        This method prepares Rocky Linux-specific configuration and delegates deployment.
        
        Args:
            element_type: Should be "rocky_vm"
            config: VM configuration with keys:
                - name: VM name
                - rocky_version: Rocky version (default: "9")
                - cores: CPU cores (default: 2)
                - memory: RAM in MB (default: 2048)
                - disk_size: Disk size in GB (default: 20)
                - network: Network identifier
                - ssh_user: SSH username (default: "rocky")
                - packages: List of packages to install
                - users: List of user accounts
            
        Returns:
            Deployment result with VM details
        """
        logger.info(f"Starting Rocky Linux VM deployment with config: {config}")
        
        # Extract Rocky Linux-specific configuration
        rocky_version = config.get("rocky_version", "9")
        vm_name = config.get("name", f"rocky-{rocky_version}-{self.agent_id}")
        
        # Validate Rocky version
        if rocky_version not in self.ROCKY_VERSIONS:
            raise ValueError(f"Unsupported Rocky Linux version: {rocky_version}")
        
        rocky_info = self.ROCKY_VERSIONS[rocky_version]
        
        # Build platform-agnostic VM configuration
        vm_config = {
            "name": vm_name,
            "cores": config.get("cores", self.DEFAULT_CONFIG["cores"]),
            "memory": config.get("memory", self.DEFAULT_CONFIG["memory"]),
            "disk_size": config.get("disk_size", self.DEFAULT_CONFIG["disk_size"]),
            "network": config.get("network", self.DEFAULT_CONFIG["network"]),
            "storage": config.get("storage", self.DEFAULT_CONFIG["storage"]),
            
            # Rocky Linux-specific metadata
            "os_type": "rocky",
            "os_version": rocky_version,
            "os_name": rocky_info["name"],
            
            # SSH configuration
            "ssh_user": config.get("ssh_user", "rocky"),
            "ssh_key_path": config.get("ssh_key_path"),
            
            # Cloud-init / provisioning
            "packages": config.get("packages", ["openssh-server", "qemu-guest-agent"]),
            "users": config.get("users", [{"name": "rocky", "sudo": True}]),
            
            # Template or ISO
            "template_id": config.get("template_id", rocky_info.get("template_id")),
            "iso_path": rocky_info.get("iso"),
            "cloud_image": rocky_info.get("cloud_image"),
            
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
                "rocky_version": rocky_version,
                "ip_address": result.get("ip_address"),
                "platform": result.get("platform"),
                "status": result.get("status"),
                "ansible_connection": result.get("ansible_connection"),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy Rocky Linux VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "rocky_version": rocky_version
            }


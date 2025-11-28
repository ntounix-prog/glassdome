"""
Base OS Installer Agent
Abstract base class for all OS installation agents with shared logic
"""
from abc import abstractmethod
from typing import Dict, Any, Optional
import logging
from glassdome.agents.base import DeploymentAgent

logger = logging.getLogger(__name__)


class OSInstallerAgent(DeploymentAgent):
    """
    Base class for OS installation agents
    
    Provides common functionality for all OS installers:
    - Template management
    - VM configuration
    - IP detection
    - Resource allocation
    
    Subclasses implement OS-specific logic
    """
    
    # Subclasses define their OS configurations
    OS_VERSIONS: Dict[str, Dict[str, Any]] = {}
    DEFAULT_CONFIG: Dict[str, Any] = {
        "cores": 2,
        "memory": 2048,
        "disk_size": 20,
        "network": "vmbr0",
        "storage": "local-lvm",
    }
    
    def __init__(self, agent_id: str, platform_client: Any, os_type: str):
        """
        Initialize OS Installer Agent
        
        Args:
            agent_id: Unique agent identifier
            platform_client: Platform client (Proxmox, Azure, AWS)
            os_type: OS type (ubuntu, kali, windows, etc.)
        """
        super().__init__(agent_id, platform_client)
        self.platform = platform_client
        self.os_type = os_type
        logger.info(f"{os_type.title()} Installer Agent {agent_id} initialized")
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate OS installation task (common validation)
        
        Args:
            task: Task definition
            
        Returns:
            True if task is valid
        """
        # Check element type matches OS type
        expected_type = f"{self.os_type}_vm"
        if task.get("element_type") != expected_type:
            return False
        
        config = task.get("config", {})
        
        # Validate version
        version = config.get("version", self.get_default_version())
        if version not in self.OS_VERSIONS:
            logger.error(f"Unsupported {self.os_type} version: {version}")
            return False
        
        # Validate required fields
        if not self.validate_config(config):
            return False
        
        return True
    
    @abstractmethod
    def get_default_version(self) -> str:
        """Get default OS version"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate OS-specific configuration"""
        pass
    
    @abstractmethod
    async def prepare_os_config(self, version: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare OS-specific configuration
        
        Args:
            version: OS version
            config: User configuration
            
        Returns:
            Platform-specific configuration
        """
        pass
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy OS VM (common flow)
        
        Args:
            element_type: Should be "{os_type}_vm"
            config: VM configuration
            
        Returns:
            Deployment result
        """
        logger.info(f"Starting {self.os_type} VM deployment: {config.get('name')}")
        
        version = config.get("version", self.get_default_version())
        use_template = config.get("use_template", True)
        
        # Merge with defaults
        vm_config = {**self.DEFAULT_CONFIG, **config.get("resources", {})}
        
        # Get OS-specific configuration
        os_config = await self.prepare_os_config(version, config)
        
        try:
            if use_template:
                result = await self._clone_from_template(
                    config.get("node"),
                    os_config,
                    vm_config
                )
            else:
                result = await self._create_from_iso(
                    config.get("node"),
                    os_config,
                    vm_config
                )
            
            return {
                "success": True,
                "resource_id": result["vmid"],
                "vm_name": config.get("name"),
                "os_type": self.os_type,
                "version": version,
                "node": config.get("node"),
                "ip_address": result.get("ip_address"),
                "status": "created",
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy {self.os_type} VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "os_type": self.os_type
            }
    
    async def _clone_from_template(
        self,
        node: str,
        os_config: Dict[str, Any],
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Clone from template (common logic)
        Can be overridden for platform-specific behavior
        """
        logger.info(f"Cloning {self.os_type} from template {os_config['template_id']}")
        
        # Get next VM ID
        new_vmid = await self.platform.get_next_vmid()
        
        # Clone template
        clone_result = await self.platform.clone_vm(
            node=node,
            vmid=os_config["template_id"],
            newid=new_vmid,
            name=os_config["name"],
            full=True
        )
        
        if not clone_result.get("success"):
            raise Exception(f"Clone failed: {clone_result.get('error')}")
        
        # Configure resources
        await self._configure_vm(node, new_vmid, vm_config)
        
        # Start VM
        await self.platform.start_vm(node, new_vmid)
        
        # Wait for IP
        ip_address = await self._wait_for_ip(node, new_vmid)
        
        return {
            "vmid": new_vmid,
            "name": os_config["name"],
            "ip_address": ip_address,
            "method": "template_clone"
        }
    
    @abstractmethod
    async def _create_from_iso(
        self,
        node: str,
        os_config: Dict[str, Any],
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create from ISO (OS-specific)
        Each OS has different ISO configuration
        """
        pass
    
    async def _configure_vm(self, node: str, vmid: int, config: Dict[str, Any]) -> None:
        """Configure VM resources (common)"""
        logger.info(f"Configuring VM {vmid}")
        # Implementation depends on platform
        pass
    
    async def _wait_for_ip(self, node: str, vmid: int, timeout: int = 60) -> Optional[str]:
        """Wait for VM to get IP (common)"""
        logger.info(f"Waiting for IP for VM {vmid}")
        # Common IP detection logic
        return None
    
    async def create_template(
        self,
        node: str,
        version: str,
        template_vmid: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create OS template (common flow)
        
        Args:
            node: Target node
            version: OS version
            template_vmid: Specific template ID
            
        Returns:
            Template creation result
        """
        logger.info(f"Creating {self.os_type} {version} template")
        
        os_info = self.OS_VERSIONS.get(version)
        if not os_info:
            return {"success": False, "error": f"Unsupported version: {version}"}
        
        # Subclasses can override template creation logic
        return await self._create_template_impl(node, version, os_info, template_vmid)
    
    @abstractmethod
    async def _create_template_impl(
        self,
        node: str,
        version: str,
        os_info: Dict[str, Any],
        template_vmid: Optional[int]
    ) -> Dict[str, Any]:
        """OS-specific template creation"""
        pass


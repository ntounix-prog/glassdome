"""
Windows Installer module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from glassdome.agents.base import BaseAgent, AgentType, AgentStatus
from glassdome.platforms.base import PlatformClient

logger = logging.getLogger(__name__)


class WindowsInstallerAgent(BaseAgent):
    """
    Agent for deploying Windows VMs (Server 2022 and Windows 11).
    
    Works across all platforms: Proxmox, ESXi, AWS, Azure
    """
    
    def __init__(self, platform_client: PlatformClient, agent_id: Optional[str] = None):
        """
        Initialize the Windows installer agent.
        
        Args:
            platform_client: Platform-specific client implementing PlatformClient interface
            agent_id: Optional unique identifier for the agent
        """
        super().__init__(
            agent_id=agent_id or f"windows-installer-{uuid.uuid4().hex[:8]}",
            agent_type=AgentType.DEPLOYMENT
        )
        self.platform_client = platform_client
        self.name = "windows_installer"
        logger.info(f"WindowsInstallerAgent initialized with {type(platform_client).__name__}")
    
    async def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate the Windows VM configuration.
        
        Args:
            config: VM configuration dictionary
            
        Returns:
            True if configuration is valid
        """
        required_fields = ["name"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate Windows version
        windows_version = config.get("windows_version", "server2022")
        valid_versions = ["server2022", "win11"]
        if windows_version not in valid_versions:
            logger.error(f"Invalid windows_version: {windows_version}. Must be one of {valid_versions}")
            return False
        
        # Validate memory (Windows needs more than Linux)
        memory_mb = config.get("memory_mb", 4096)
        if memory_mb < 2048:
            logger.warning(f"Memory {memory_mb}MB is low for Windows. Recommended: 4096MB+")
        
        logger.info(f"Configuration validated for Windows VM: {config['name']}")
        return True
    
    async def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy a Windows VM.
        
        Args:
            config: VM configuration dictionary
                - name: VM name
                - windows_version: "server2022" or "win11" (default: server2022)
                - memory_mb: Memory in MB (default: 4096)
                - cpu_cores: Number of CPU cores (default: 2)
                - disk_size_gb: Disk size in GB (default: 80)
                - admin_password: Administrator password (default: auto-generated)
                - enable_rdp: Enable RDP access (default: True)
                - install_packages: List of packages/features to install (optional)
                
        Returns:
            Dict with deployment results including vm_id, ip_address, credentials
        """
        try:
            self.status = AgentStatus.RUNNING
            
            if not await self.validate(config):
                self.status = AgentStatus.FAILED
                self.error = "Invalid configuration"
                raise ValueError("Invalid configuration")
            
            logger.info(f"Deploying Windows VM: {config['name']}")
            
            # Set Windows-specific defaults based on version
            windows_version = config.get("windows_version", "server2022")
            
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
            
            windows_config = {
                **config,
                "os_type": "windows",
                "windows_version": windows_version,
                "memory_mb": config.get("memory_mb", default_memory),
                "cpu_cores": config.get("cpu_cores", default_cores),
                "disk_size_gb": config.get("disk_size_gb", default_disk),
                "admin_password": config.get("admin_password", "Glassdome123!"),
                "enable_rdp": config.get("enable_rdp", True),
            }
            
            # Use template-based deployment if template_id provided (RECOMMENDED)
            # Otherwise fall back to ISO-based (unreliable)
            if not windows_config.get("template_id"):
                # Try to get from session-aware config if available
                from glassdome.core.security import get_secure_settings
                settings = get_secure_settings()
                if settings.windows_server2022_template_id:
                    windows_config["template_id"] = settings.windows_server2022_template_id
                    logger.info(f"Using Windows template ID from config: {settings.windows_server2022_template_id}")
                else:
                    logger.warning("No Windows template_id provided. Will attempt ISO-based deployment (unreliable).")
                    logger.warning("RECOMMENDED: Create Windows template and set WINDOWS_SERVER2022_TEMPLATE_ID in .env")
            
            # Create VM using platform client
            result = await self.platform_client.create_vm(windows_config)
            
            logger.info(f"Windows VM deployed successfully: {result['vm_id']}")
            
            # Add Windows-specific connection info
            result["windows_connection"] = {
                "rdp_host": result.get("ip_address"),
                "rdp_port": 3389,
                "username": "Administrator",
                "password": windows_config["admin_password"],
            }
            
            self.status = AgentStatus.COMPLETED
            return result
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.error = str(e)
            raise
    
    async def cleanup(self, vm_id: str) -> bool:
        """
        Clean up a deployed Windows VM.
        
        Args:
            vm_id: VM identifier
            
        Returns:
            True if cleanup successful
        """
        logger.info(f"Cleaning up Windows VM: {vm_id}")
        success = await self.platform_client.delete_vm(vm_id)
        
        if success:
            logger.info(f"Windows VM {vm_id} cleaned up successfully")
        else:
            logger.error(f"Failed to clean up Windows VM {vm_id}")
        
        return success


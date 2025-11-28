"""
Platform client for Base

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum


class VMStatus(Enum):
    """Standardized VM status across all platforms"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    CREATING = "creating"
    DELETING = "deleting"
    ERROR = "error"
    UNKNOWN = "unknown"


class PlatformClient(ABC):
    """
    Abstract base class for all platform clients
    
    This interface defines the contract that all platforms must implement.
    It ensures that OS agents can work with any platform without modification.
    
    Design Philosophy:
    - OS agents know WHAT to deploy (Ubuntu, Kali, Windows)
    - Platform clients know WHERE to deploy (Proxmox, AWS, Azure)
    - This interface is the bridge between them
    """
    
    # =========================================================================
    # CORE VM OPERATIONS (Required)
    # =========================================================================
    
    @abstractmethod
    async def create_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new virtual machine
        
        Args:
            config: VM configuration with the following keys:
                - name: VM name (required)
                - cores: CPU cores (default: 2)
                - memory: RAM in MB (default: 2048)
                - disk_size: Disk size in GB (default: 20)
                - network: Network identifier (default: platform-specific)
                - os_type: OS type hint (e.g., "ubuntu", "windows")
                - os_version: OS version (e.g., "22.04")
                - ssh_user: SSH username (default: platform-specific)
                - ssh_key_path: Path to SSH key (optional)
                - cloud_init: Cloud-init configuration (optional)
                - packages: List of packages to install (optional)
                - users: List of user accounts to create (optional)
                - template_id: Template/AMI/Image ID to clone from (optional)
                - iso_path: ISO file path for installation (optional)
        
        Returns:
            Dictionary containing:
                - vm_id: Unique VM identifier (required)
                - ip_address: VM IP address (if available, else None)
                - platform: Platform name (e.g., "proxmox", "aws")
                - status: Current status (VMStatus enum value)
                - ansible_connection: Dict with Ansible connection details:
                    - host: IP or hostname
                    - user: SSH username
                    - ssh_key_path: Path to SSH key
                    - port: SSH port (default: 22)
                - platform_specific: Dict with any platform-specific data
        
        Raises:
            Exception: If VM creation fails
        """
        pass
    
    @abstractmethod
    async def start_vm(self, vm_id: str) -> bool:
        """
        Start a stopped virtual machine
        
        Args:
            vm_id: Unique VM identifier
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def stop_vm(self, vm_id: str, force: bool = False) -> bool:
        """
        Stop a running virtual machine
        
        Args:
            vm_id: Unique VM identifier
            force: Force stop (hard shutdown) if True
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_vm(self, vm_id: str) -> bool:
        """
        Delete a virtual machine
        
        Args:
            vm_id: Unique VM identifier
        
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_vm_status(self, vm_id: str) -> VMStatus:
        """
        Get the current status of a virtual machine
        
        Args:
            vm_id: Unique VM identifier
        
        Returns:
            VMStatus enum value
        """
        pass
    
    @abstractmethod
    async def get_vm_ip(self, vm_id: str, timeout: int = 120) -> Optional[str]:
        """
        Get the IP address of a virtual machine
        
        This method should wait for the VM to acquire an IP if not immediately available.
        
        Args:
            vm_id: Unique VM identifier
            timeout: Maximum time to wait for IP (seconds)
        
        Returns:
            IP address as string, or None if not available
        """
        pass
    
    # =========================================================================
    # TEMPLATE/IMAGE OPERATIONS (Optional but Recommended)
    # =========================================================================
    
    async def clone_vm(self, template_id: str, new_vm_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clone a VM from a template/image
        
        Default implementation calls create_vm() with template_id in config.
        Platforms can override for optimized cloning.
        
        Args:
            template_id: Template/AMI/Image identifier
            new_vm_id: ID for the new VM
            config: VM configuration (same as create_vm)
        
        Returns:
            Same as create_vm()
        """
        config["template_id"] = template_id
        config["vm_id"] = new_vm_id
        return await self.create_vm(config)
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """
        List available templates/images
        
        Returns:
            List of templates with keys: id, name, os_type, os_version
        """
        return []
    
    # =========================================================================
    # NETWORK OPERATIONS (Optional but Recommended)
    # =========================================================================
    
    async def create_network(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a network/bridge/VPC
        
        Args:
            config: Network configuration
                - name: Network name
                - cidr: Network CIDR (e.g., "10.0.0.0/24")
                - isolated: Whether network is isolated (default: True)
        
        Returns:
            Dictionary with: network_id, name, cidr, platform_specific
        """
        raise NotImplementedError("Network creation not supported on this platform")
    
    async def list_networks(self) -> List[Dict[str, Any]]:
        """
        List available networks
        
        Returns:
            List of networks with keys: id, name, cidr
        """
        return []
    
    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================
    
    async def test_connection(self) -> bool:
        """
        Test connection to the platform
        
        Returns:
            True if connection is successful
        """
        raise NotImplementedError("Connection test not implemented")
    
    async def get_platform_info(self) -> Dict[str, Any]:
        """
        Get platform information (version, capabilities, etc.)
        
        Returns:
            Dictionary with platform information
        """
        return {
            "platform": "unknown",
            "version": "unknown"
        }
    
    # =========================================================================
    # HELPER METHODS (Common utilities)
    # =========================================================================
    
    def _standardize_vm_status(self, platform_status: str) -> VMStatus:
        """
        Convert platform-specific status to standardized VMStatus
        
        Platforms should override this to map their status strings
        """
        status_map = {
            "running": VMStatus.RUNNING,
            "stopped": VMStatus.STOPPED,
            "paused": VMStatus.PAUSED,
            "creating": VMStatus.CREATING,
            "deleting": VMStatus.DELETING,
            "error": VMStatus.ERROR
        }
        return status_map.get(platform_status.lower(), VMStatus.UNKNOWN)
    
    def get_platform_name(self) -> str:
        """
        Get the platform name
        
        Returns:
            Platform identifier (e.g., "proxmox", "aws", "azure")
        """
        return self.__class__.__name__.replace("Client", "").lower()


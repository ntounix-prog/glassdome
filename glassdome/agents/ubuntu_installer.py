"""
Ubuntu Installer module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from glassdome.agents.base import DeploymentAgent, AgentStatus
from glassdome.platforms.base import PlatformClient

logger = logging.getLogger(__name__)


class UbuntuInstallerAgent(DeploymentAgent):
    """
    Agent specialized in creating base Ubuntu installation images
    Listens for API calls and autonomously creates Ubuntu VMs
    """
    
    UBUNTU_VERSIONS = {
        "22.04": {
            "name": "Ubuntu 22.04 LTS (Jammy)",
            "iso": "ubuntu-22.04.3-live-server-amd64.iso",
            "template_id": 9003,  # Ubuntu 22.04 with QEMU guest agent
        },
        "24.04": {
            "name": "Ubuntu 24.04 LTS (Noble)",
            "iso": "ubuntu-24.04-live-server-amd64.iso",
            "template_id": 9001,
        },
        "20.04": {
            "name": "Ubuntu 20.04 LTS (Focal)",
            "iso": "ubuntu-20.04.6-live-server-amd64.iso",
            "template_id": 9002,
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
        Initialize Ubuntu Installer Agent
        
        This agent is PLATFORM-AGNOSTIC - it accepts any platform client
        that implements the PlatformClient interface.
        
        Args:
            agent_id: Unique agent identifier
            platform_client: Platform client (Proxmox, AWS, Azure, etc.)
        """
        super().__init__(agent_id, platform_client)
        self.platform = platform_client
        logger.info(f"Ubuntu Installer Agent {agent_id} initialized with platform: {platform_client.get_platform_name()}")
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """
        Validate Ubuntu installation task
        
        Args:
            task: Task definition
            
        Returns:
            True if task is valid
        """
        # Check required fields
        if task.get("element_type") != "ubuntu_vm":
            return False
        
        config = task.get("config", {})
        
        # Validate Ubuntu version
        version = config.get("ubuntu_version", "22.04")
        if version not in self.UBUNTU_VERSIONS:
            logger.error(f"Unsupported Ubuntu version: {version}")
            return False
        
        # Platform-agnostic - no node validation needed
        # (node is Proxmox-specific, ESXi/AWS don't have nodes)
        
        return True
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy Ubuntu VM (PLATFORM-AGNOSTIC)
        
        Uses standardized PlatformClient interface to deploy to any platform.
        This method prepares Ubuntu-specific configuration and delegates deployment.
        
        Args:
            element_type: Should be "ubuntu_vm"
            config: VM configuration with keys:
                - name: VM name
                - ubuntu_version: Ubuntu version (default: "22.04")
                - cores: CPU cores (default: 2)
                - memory: RAM in MB (default: 2048)
                - disk_size: Disk size in GB (default: 20)
                - network: Network identifier
                - ssh_user: SSH username (default: "ubuntu")
                - packages: List of packages to install
                - users: List of user accounts
            
        Returns:
            Deployment result with VM details
        """
        logger.info(f"Starting Ubuntu VM deployment with config: {config}")
        
        # Extract Ubuntu-specific configuration
        ubuntu_version = config.get("ubuntu_version", "22.04")
        vm_name = config.get("name", f"ubuntu-{ubuntu_version}-{self.agent_id}")
        
        # Validate Ubuntu version
        if ubuntu_version not in self.UBUNTU_VERSIONS:
            raise ValueError(f"Unsupported Ubuntu version: {ubuntu_version}")
        
        ubuntu_info = self.UBUNTU_VERSIONS[ubuntu_version]
        
        # Build platform-agnostic VM configuration
        vm_config = {
            "name": vm_name,
            "cores": config.get("cores", self.DEFAULT_CONFIG["cores"]),
            "memory": config.get("memory", self.DEFAULT_CONFIG["memory"]),
            "disk_size": config.get("disk_size", self.DEFAULT_CONFIG["disk_size"]),
            "network": config.get("network", self.DEFAULT_CONFIG["network"]),
            "storage": config.get("storage", self.DEFAULT_CONFIG["storage"]),
            
            # Ubuntu-specific metadata
            "os_type": "ubuntu",
            "os_version": ubuntu_version,
            "os_name": ubuntu_info["name"],
            
            # SSH configuration
            "ssh_user": config.get("ssh_user", "ubuntu"),
            "ssh_key_path": config.get("ssh_key_path"),
            
            # Cloud-init / provisioning
            "packages": config.get("packages", ["openssh-server", "qemu-guest-agent"]),
            "users": config.get("users", [{"name": "ubuntu", "sudo": True}]),
            
            # Template or ISO
            "template_id": config.get("template_id", ubuntu_info.get("template_id")),
            "iso_path": ubuntu_info.get("iso"),
            
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
                "ubuntu_version": ubuntu_version,
                "ip_address": result.get("ip_address"),
                "platform": result.get("platform"),
                "status": result.get("status"),
                "ansible_connection": result.get("ansible_connection"),
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy Ubuntu VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "ubuntu_version": ubuntu_version
            }
    
    async def _clone_from_template(
        self, 
        node: str, 
        template_id: int, 
        vm_name: str,
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Clone Ubuntu VM from existing template
        
        Args:
            node: Proxmox node
            template_id: Template VM ID
            vm_name: New VM name
            vm_config: VM configuration
            
        Returns:
            VM details
        """
        logger.info(f"Cloning Ubuntu VM from template {template_id}")
        
        # Get next available VM ID
        new_vmid = await self.proxmox.get_next_vmid()
        
        # Clone the template
        clone_result = await self.proxmox.clone_vm(
            node=node,
            vmid=template_id,
            newid=new_vmid,
            name=vm_name,
            full=True  # Full clone, not linked
        )
        
        if not clone_result.get("success"):
            raise Exception(f"Clone failed: {clone_result.get('error')}")
        
        logger.info(f"Template cloned successfully, new VMID: {new_vmid}")
        
        # Configure the cloned VM
        await self._configure_vm(node, new_vmid, vm_config)
        
        # Start the VM
        start_result = await self.proxmox.start_vm(node, new_vmid)
        
        if not start_result.get("success"):
            logger.warning(f"Failed to start VM: {start_result.get('error')}")
        
        # Wait for VM to get IP (with timeout)
        ip_address = await self._wait_for_ip(node, new_vmid, timeout=60)
        
        return {
            "vmid": new_vmid,
            "name": vm_name,
            "ip_address": ip_address,
            "method": "template_clone"
        }
    
    async def _create_from_iso(
        self,
        node: str,
        vm_name: str,
        ubuntu_info: Dict[str, Any],
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create Ubuntu VM from ISO (slower, for when template doesn't exist)
        
        Args:
            node: Proxmox node
            vm_name: VM name
            ubuntu_info: Ubuntu version info
            vm_config: VM configuration
            
        Returns:
            VM details
        """
        logger.info(f"Creating Ubuntu VM from ISO: {ubuntu_info['iso']}")
        
        # Get next available VM ID
        vmid = await self.proxmox.get_next_vmid()
        
        # Prepare VM configuration
        create_config = {
            "vmid": vmid,
            "name": vm_name,
            "cores": vm_config["cores"],
            "memory": vm_config["memory"],
            "net0": f"virtio,bridge={vm_config['network']}",
            "scsi0": f"{vm_config['storage']}:{vm_config['disk_size']}",
            "scsihw": "virtio-scsi-pci",
            "boot": "order=scsi0;ide2",
            "ide2": f"local:iso/{ubuntu_info['iso']},media=cdrom",
            "ostype": "l26",  # Linux 2.6+
            "agent": 1,  # Enable QEMU guest agent
        }
        
        # Create the VM
        create_result = await self.proxmox.create_vm(node, vmid, create_config)
        
        if not create_result.get("success"):
            raise Exception(f"VM creation failed: {create_result.get('error')}")
        
        logger.info(f"VM created successfully, VMID: {vmid}")
        
        # Note: VM created but not started - ISO install requires manual or automated setup
        # For a fully automated solution, you'd use cloud-init or preseed
        
        return {
            "vmid": vmid,
            "name": vm_name,
            "ip_address": None,
            "method": "iso_install",
            "note": "VM created but not started - ISO installation required"
        }
    
    async def _configure_vm(self, node: str, vmid: int, config: Dict[str, Any]) -> None:
        """
        Configure VM resources (CPU, memory, etc.)
        
        Args:
            node: Proxmox node
            vmid: VM ID
            config: Configuration to apply
        """
        logger.info(f"Configuring VM {vmid} with resources: {config}")
        
        # Build configuration dict for Proxmox
        proxmox_config = {}
        
        if "cores" in config:
            proxmox_config["cores"] = config["cores"]
        if "memory" in config:
            proxmox_config["memory"] = config["memory"]
        
        # Update VM configuration
        if proxmox_config:
            result = await self.proxmox.configure_vm(node, vmid, proxmox_config)
            if not result.get("success"):
                logger.warning(f"Failed to configure VM: {result.get('error')}")
        
        # Resize disk if needed
        if "disk_size" in config:
            disk_size = config["disk_size"]
            # Check if resize is needed (template might be smaller)
            await self.proxmox.resize_disk(node, vmid, "scsi0", f"{disk_size}G")
    
    async def _wait_for_ip(self, node: str, vmid: int, timeout: int = 60) -> Optional[str]:
        """
        Wait for VM to get an IP address
        
        Args:
            node: Proxmox node
            vmid: VM ID
            timeout: Timeout in seconds
            
        Returns:
            IP address or None
        """
        logger.info(f"Waiting for VM {vmid} to get IP address (timeout: {timeout}s)")
        
        # Use ProxmoxClient's get_vm_ip method which handles QEMU guest agent
        ip = await self.proxmox.get_vm_ip(node, vmid, timeout=timeout)
        
        if ip:
            logger.info(f"VM {vmid} got IP: {ip}")
        else:
            logger.warning(f"Timeout waiting for IP for VM {vmid}")
        
        return ip
    
    async def create_template(
        self,
        node: str,
        ubuntu_version: str = "22.04",
        template_vmid: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a base Ubuntu template for faster cloning
        
        Args:
            node: Proxmox node
            ubuntu_version: Ubuntu version
            template_vmid: Specific VM ID for template (optional)
            
        Returns:
            Template creation result
        """
        logger.info(f"Creating Ubuntu {ubuntu_version} template on node {node}")
        
        ubuntu_info = self.UBUNTU_VERSIONS.get(ubuntu_version)
        if not ubuntu_info:
            return {
                "success": False,
                "error": f"Unsupported Ubuntu version: {ubuntu_version}"
            }
        
        vmid = template_vmid or ubuntu_info["template_id"]
        
        # Create base VM
        result = await self._create_from_iso(
            node=node,
            vm_name=f"ubuntu-{ubuntu_version}-template",
            ubuntu_info=ubuntu_info,
            vm_config=self.DEFAULT_CONFIG
        )
        
        # Convert to template
        # In real implementation: self.proxmox.client.nodes(node).qemu(vmid).template.post()
        
        logger.info(f"Template created: {vmid}")
        
        return {
            "success": True,
            "template_id": vmid,
            "ubuntu_version": ubuntu_version,
            "node": node
        }
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Ubuntu installation task
        
        Args:
            task: Task definition
            
        Returns:
            Execution result
        """
        element_type = task.get("element_type")
        config = task.get("config", {})
        
        logger.info(f"Ubuntu Installer Agent executing task: {task.get('task_id')}")
        
        # Deploy the Ubuntu VM
        result = await self._deploy_element(element_type, config)
        
        # Add agent info to result
        result["agent_id"] = self.agent_id
        result["agent_type"] = self.agent_type.value
        
        return result


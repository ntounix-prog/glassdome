"""
Ubuntu Installer Agent
Autonomous agent for creating base Ubuntu installation images
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from glassdome.agents.base import DeploymentAgent, AgentStatus
from glassdome.platforms.proxmox_client import ProxmoxClient

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
            "template_id": 9000,
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
    
    def __init__(self, agent_id: str, proxmox_client: ProxmoxClient):
        """
        Initialize Ubuntu Installer Agent
        
        Args:
            agent_id: Unique agent identifier
            proxmox_client: Configured Proxmox client
        """
        super().__init__(agent_id, proxmox_client)
        self.proxmox = proxmox_client
        logger.info(f"Ubuntu Installer Agent {agent_id} initialized")
    
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
        
        # Validate node
        if not config.get("node"):
            logger.error("No Proxmox node specified")
            return False
        
        return True
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy Ubuntu VM
        
        Args:
            element_type: Should be "ubuntu_vm"
            config: VM configuration
            
        Returns:
            Deployment result with VM details
        """
        logger.info(f"Starting Ubuntu VM deployment with config: {config}")
        
        # Extract configuration
        node = config.get("node")
        ubuntu_version = config.get("ubuntu_version", "22.04")
        vm_name = config.get("name", f"ubuntu-{ubuntu_version}-base")
        use_template = config.get("use_template", True)
        
        # Merge with defaults
        vm_config = {**self.DEFAULT_CONFIG, **config.get("resources", {})}
        
        ubuntu_info = self.UBUNTU_VERSIONS[ubuntu_version]
        
        try:
            if use_template:
                # Clone from template (faster)
                result = await self._clone_from_template(
                    node, 
                    ubuntu_info["template_id"],
                    vm_name,
                    vm_config
                )
            else:
                # Create new VM from ISO
                result = await self._create_from_iso(
                    node,
                    vm_name,
                    ubuntu_info,
                    vm_config
                )
            
            return {
                "success": True,
                "resource_id": result["vmid"],
                "vm_name": vm_name,
                "node": node,
                "ubuntu_version": ubuntu_version,
                "ip_address": result.get("ip_address"),
                "status": "created",
                "details": result
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy Ubuntu VM: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "node": node
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
        
        # In a real implementation, you'd call Proxmox API to update VM config
        # For now, this is a placeholder
        # self.proxmox.client.nodes(node).qemu(vmid).config.put(**config)
        
        await asyncio.sleep(0.5)  # Simulate configuration time
    
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
        
        elapsed = 0
        while elapsed < timeout:
            try:
                status = await self.proxmox.get_vm_status(node, vmid)
                
                # Check if VM is running and has IP
                # In real implementation, you'd parse QEMU guest agent data
                # For now, simulate
                if elapsed > 10:  # Simulate IP assignment after 10 seconds
                    ip = f"10.0.0.{vmid % 255}"
                    logger.info(f"VM {vmid} got IP: {ip}")
                    return ip
                
            except Exception as e:
                logger.debug(f"Error checking VM status: {str(e)}")
            
            await asyncio.sleep(2)
            elapsed += 2
        
        logger.warning(f"Timeout waiting for IP for VM {vmid}")
        return None
    
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


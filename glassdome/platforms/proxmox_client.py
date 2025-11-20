"""
Proxmox API Integration
Implements the PlatformClient interface for Proxmox VE
"""
from proxmoxer import ProxmoxAPI
from typing import Dict, Any, List, Optional
import logging
import asyncio
import time

from glassdome.platforms.base import PlatformClient, VMStatus

logger = logging.getLogger(__name__)


class ProxmoxClient(PlatformClient):
    """
    Client for interacting with Proxmox VE API
    Handles VM creation, configuration, networking, and management
    """
    
    def __init__(self, host: str, user: str, password: Optional[str] = None,
                 token_name: Optional[str] = None, token_value: Optional[str] = None,
                 verify_ssl: bool = False, default_node: str = "pve01",
                 default_storage: str = "local-lvm"):
        """
        Initialize Proxmox client
        
        Args:
            host: Proxmox host address
            user: Username (format: user@pam or user@pve)
            password: Password (for password auth)
            token_name: API token name (for token auth)
            token_value: API token value (for token auth)
            verify_ssl: Verify SSL certificates
            default_node: Default node for VM operations
            default_storage: Default storage for VM disks
        """
        self.host = host
        self.user = user
        self.default_node = default_node
        self.default_storage = default_storage
        
        # Initialize ProxmoxAPI with either password or token auth
        if token_name and token_value:
            self.client = ProxmoxAPI(
                host,
                user=user,
                token_name=token_name,
                token_value=token_value,
                verify_ssl=verify_ssl
            )
        elif password:
            self.client = ProxmoxAPI(
                host,
                user=user,
                password=password,
                verify_ssl=verify_ssl
            )
        else:
            raise ValueError("Either password or token credentials must be provided")
        
        logger.info(f"Proxmox client initialized for {host}")
    
    # =========================================================================
    # PLATFORM CLIENT INTERFACE IMPLEMENTATION
    # =========================================================================
    
    async def create_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a VM (implements PlatformClient interface)
        
        This is the standardized interface method that OS agents will call.
        """
        node = config.get("node", self.default_node)
        vmid = config.get("vmid") or await self.get_next_vmid(node)
        name = config.get("name", f"vm-{vmid}")
        
        # Build Proxmox-specific config
        vm_config = {
            "vmid": vmid,
            "name": name,
            "cores": config.get("cores", 2),
            "memory": config.get("memory", 2048),
            "net0": f"virtio,bridge={config.get('network', 'vmbr0')}",
            "storage": config.get("storage", self.default_storage),
        }
        
        # Handle template cloning vs ISO installation
        if config.get("template_id"):
            # Clone from template
            result = await self.clone_vm_from_template(
                node=node,
                template_id=config["template_id"],
                new_vmid=vmid,
                config=config
            )
        else:
            # Create from scratch (ISO installation)
            result = await self.create_vm_raw(node, vmid, vm_config)
        
        # Start the VM
        await self.start_vm(str(vmid))
        
        # Wait for IP address
        ip_address = await self.get_vm_ip(str(vmid), timeout=config.get("ip_timeout", 120))
        
        # Return standardized format
        return {
            "vm_id": str(vmid),
            "ip_address": ip_address,
            "platform": "proxmox",
            "status": (await self.get_vm_status(str(vmid))).value,
            "ansible_connection": {
                "host": ip_address or "unknown",
                "user": config.get("ssh_user", "ubuntu"),
                "ssh_key_path": config.get("ssh_key_path", "/root/.ssh/id_rsa"),
                "port": 22
            },
            "platform_specific": {
                "node": node,
                "vmid": vmid,
                "name": name,
                "host": self.host
            }
        }
    
    async def start_vm(self, vm_id: str) -> bool:
        """Start a VM (implements PlatformClient interface)"""
        try:
            # Parse node from vm_id if formatted as "node:vmid"
            if ":" in vm_id:
                node, vmid = vm_id.split(":")
            else:
                node = self.default_node
                vmid = vm_id
            
            self.client.nodes(node).qemu(int(vmid)).status.start.post()
            logger.info(f"VM {vmid} started on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to start VM {vm_id}: {str(e)}")
            return False
    
    async def stop_vm(self, vm_id: str, force: bool = False) -> bool:
        """Stop a VM (implements PlatformClient interface)"""
        try:
            if ":" in vm_id:
                node, vmid = vm_id.split(":")
            else:
                node = self.default_node
                vmid = vm_id
            
            if force:
                self.client.nodes(node).qemu(int(vmid)).status.stop.post()
            else:
                self.client.nodes(node).qemu(int(vmid)).status.shutdown.post()
            
            logger.info(f"VM {vmid} {'stopped' if force else 'shutdown'} on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop VM {vm_id}: {str(e)}")
            return False
    
    async def delete_vm(self, vm_id: str) -> bool:
        """Delete a VM (implements PlatformClient interface)"""
        try:
            if ":" in vm_id:
                node, vmid = vm_id.split(":")
            else:
                node = self.default_node
                vmid = vm_id
            
            self.client.nodes(node).qemu(int(vmid)).delete()
            logger.info(f"VM {vmid} deleted from node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_id}: {str(e)}")
            return False
    
    async def get_vm_status(self, vm_id: str) -> VMStatus:
        """Get VM status (implements PlatformClient interface)"""
        try:
            if ":" in vm_id:
                node, vmid = vm_id.split(":")
            else:
                node = self.default_node
                vmid = vm_id
            
            status_info = self.client.nodes(node).qemu(int(vmid)).status.current.get()
            proxmox_status = status_info.get("status", "unknown")
            
            # Map Proxmox status to standardized VMStatus
            status_map = {
                "running": VMStatus.RUNNING,
                "stopped": VMStatus.STOPPED,
                "paused": VMStatus.PAUSED
            }
            return status_map.get(proxmox_status, VMStatus.UNKNOWN)
        except Exception as e:
            logger.error(f"Failed to get status for VM {vm_id}: {str(e)}")
            return VMStatus.ERROR
    
    async def get_vm_ip(self, vm_id: str, timeout: int = 120) -> Optional[str]:
        """Get VM IP address (implements PlatformClient interface)"""
        if ":" in vm_id:
            node, vmid = vm_id.split(":")
        else:
            node = self.default_node
            vmid = vm_id
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                # Try to get IP from QEMU guest agent
                agent_info = self.client.nodes(node).qemu(int(vmid)).agent('network-get-interfaces').get()
                
                for interface in agent_info.get('result', []):
                    if interface.get('name') not in ['lo']:
                        for ip_addr in interface.get('ip-addresses', []):
                            if ip_addr.get('ip-address-type') == 'ipv4':
                                ip = ip_addr.get('ip-address')
                                if ip and not ip.startswith('127.'):
                                    logger.info(f"VM {vmid} IP detected: {ip}")
                                    return ip
            except Exception as e:
                logger.debug(f"Waiting for VM {vmid} IP... ({int(time.time() - start_time)}s)")
            
            await asyncio.sleep(5)
        
        logger.warning(f"Timeout waiting for VM {vmid} IP address")
        return None
    
    async def get_platform_info(self) -> Dict[str, Any]:
        """Get platform info (implements PlatformClient interface)"""
        try:
            version = self.client.version.get()
            return {
                "platform": "proxmox",
                "version": version.get("version", "unknown"),
                "host": self.host,
                "default_node": self.default_node
            }
        except Exception as e:
            logger.error(f"Failed to get platform info: {str(e)}")
            return {"platform": "proxmox", "version": "unknown"}
    
    # =========================================================================
    # LEGACY/PROXMOX-SPECIFIC METHODS (kept for backward compatibility)
    # =========================================================================
    
    async def test_connection(self) -> bool:
        """Test connection to Proxmox"""
        try:
            version = self.client.version.get()
            logger.info(f"Connected to Proxmox version {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {str(e)}")
            return False
    
    async def list_nodes(self) -> List[Dict[str, Any]]:
        """List all nodes in the cluster"""
        try:
            nodes = self.client.nodes.get()
            return nodes
        except Exception as e:
            logger.error(f"Failed to list nodes: {str(e)}")
            return []
    
    async def list_vms(self, node: str) -> List[Dict[str, Any]]:
        """List all VMs on a node"""
        try:
            vms = self.client.nodes(node).qemu.get()
            return vms
        except Exception as e:
            logger.error(f"Failed to list VMs on node {node}: {str(e)}")
            return []
    
    async def create_vm_raw(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new VM (Proxmox-specific, low-level)
        
        Args:
            node: Node name
            vmid: VM ID
            config: Proxmox-specific VM configuration
            
        Returns:
            Task status
        """
        try:
            task = self.client.nodes(node).qemu.create(**config)
            logger.info(f"VM {vmid} created on node {node}")
            return {"success": True, "task": task, "vmid": vmid}
        except Exception as e:
            logger.error(f"Failed to create VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def clone_vm_from_template(self, node: str, template_id: int, new_vmid: int,
                                    config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clone a VM from a template (wrapper for interface compatibility)
        
        Args:
            node: Node name
            template_id: Template VM ID
            new_vmid: New VM ID
            config: VM configuration
            
        Returns:
            Standardized result dictionary
        """
        name = config.get("name", f"vm-{new_vmid}")
        
        # Clone the template
        result = await self.clone_vm_raw(
            node=node,
            vmid=template_id,
            newid=new_vmid,
            name=name,
            full=True
        )
        
        if not result.get("success"):
            raise Exception(f"Failed to clone template: {result.get('error')}")
        
        # Update VM configuration if needed
        await self.configure_vm(node, new_vmid, {
            "cores": config.get("cores", 2),
            "memory": config.get("memory", 2048),
        })
        
        return result
    
    async def clone_vm_raw(self, node: str, vmid: int, newid: int, name: str,
                          full: bool = True) -> Dict[str, Any]:
        """
        Clone an existing VM (Proxmox-specific, low-level)
        
        Args:
            node: Node name
            vmid: Source VM ID
            newid: New VM ID
            name: New VM name
            full: Full clone (vs linked clone)
            
        Returns:
            Task status
        """
        try:
            task = self.client.nodes(node).qemu(vmid).clone.post(
                newid=newid,
                name=name,
                full=1 if full else 0
            )
            logger.info(f"VM {vmid} cloned to {newid} on node {node}")
            return {"success": True, "task": task, "vmid": newid}
        except Exception as e:
            logger.error(f"Failed to clone VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def start_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start a VM"""
        try:
            task = self.client.nodes(node).qemu(vmid).status.start.post()
            logger.info(f"VM {vmid} started on node {node}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to start VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def stop_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Stop a VM"""
        try:
            task = self.client.nodes(node).qemu(vmid).status.stop.post()
            logger.info(f"VM {vmid} stopped on node {node}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to stop VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Delete a VM"""
        try:
            task = self.client.nodes(node).qemu(vmid).delete()
            logger.info(f"VM {vmid} deleted from node {node}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to delete VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_vm_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get VM status"""
        try:
            status = self.client.nodes(node).qemu(vmid).status.current.get()
            return {"success": True, "status": status}
        except Exception as e:
            logger.error(f"Failed to get VM {vmid} status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_next_vmid(self) -> int:
        """Get next available VM ID"""
        try:
            vmid = self.client.cluster.nextid.get()
            return int(vmid)
        except Exception as e:
            logger.error(f"Failed to get next VMID: {str(e)}")
            return 100  # Default fallback
    
    async def create_network(self, node: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a network configuration"""
        try:
            # Proxmox networking is configured at node level
            result = self.client.nodes(node).network.post(**config)
            logger.info(f"Network created on node {node}")
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Failed to create network: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def wait_for_task(self, node: str, upid: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for a Proxmox task to complete
        
        Args:
            node: Node name
            upid: Task UPID
            timeout: Timeout in seconds
            
        Returns:
            Task result
        """
        import time
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                status = self.client.nodes(node).tasks(upid).status.get()
                
                if status['status'] == 'stopped':
                    if status.get('exitstatus') == 'OK':
                        logger.info(f"Task {upid} completed successfully")
                        return {"success": True, "status": status}
                    else:
                        logger.error(f"Task {upid} failed: {status.get('exitstatus')}")
                        return {"success": False, "error": status.get('exitstatus')}
                
                time.sleep(2)
            
            logger.error(f"Task {upid} timed out after {timeout}s")
            return {"success": False, "error": f"Timeout after {timeout}s"}
            
        except Exception as e:
            logger.error(f"Failed to wait for task {upid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_vm_ip(self, node: str, vmid: int, timeout: int = 120) -> Optional[str]:
        """
        Get VM IP address (waits for QEMU guest agent)
        
        Args:
            node: Node name
            vmid: VM ID
            timeout: Timeout in seconds
            
        Returns:
            IP address or None
        """
        import time
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Try to get agent network interfaces
                    interfaces = self.client.nodes(node).qemu(vmid).agent.get('network-get-interfaces')
                    
                    for iface in interfaces.get('result', []):
                        if iface.get('name') in ['eth0', 'ens18', 'ens3']:
                            for addr in iface.get('ip-addresses', []):
                                if addr.get('ip-address-type') == 'ipv4':
                                    ip = addr.get('ip-address')
                                    if not ip.startswith('127.'):
                                        logger.info(f"VM {vmid} has IP: {ip}")
                                        return ip
                except:
                    # Agent not ready yet
                    pass
                
                time.sleep(5)
            
            logger.warning(f"Could not get IP for VM {vmid} after {timeout}s")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get IP for VM {vmid}: {str(e)}")
            return None
    
    async def configure_vm(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure VM settings
        
        Args:
            node: Node name
            vmid: VM ID
            config: Configuration parameters
            
        Returns:
            Success status
        """
        try:
            self.client.nodes(node).qemu(vmid).config.put(**config)
            logger.info(f"VM {vmid} configured")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to configure VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def resize_disk(self, node: str, vmid: int, disk: str, size: str) -> Dict[str, Any]:
        """
        Resize VM disk
        
        Args:
            node: Node name
            vmid: VM ID
            disk: Disk name (e.g., 'scsi0')
            size: New size (e.g., '+10G')
            
        Returns:
            Success status
        """
        try:
            self.client.nodes(node).qemu(vmid).resize.put(disk=disk, size=size)
            logger.info(f"VM {vmid} disk {disk} resized to {size}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to resize disk {disk} on VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}


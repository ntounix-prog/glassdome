"""
Proxmox API Integration
"""
from proxmoxer import ProxmoxAPI
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ProxmoxClient:
    """
    Client for interacting with Proxmox VE API
    Handles VM creation, configuration, networking, and management
    """
    
    def __init__(self, host: str, user: str, password: Optional[str] = None,
                 token_name: Optional[str] = None, token_value: Optional[str] = None,
                 verify_ssl: bool = False):
        """
        Initialize Proxmox client
        
        Args:
            host: Proxmox host address
            user: Username (format: user@pam or user@pve)
            password: Password (for password auth)
            token_name: API token name (for token auth)
            token_value: API token value (for token auth)
            verify_ssl: Verify SSL certificates
        """
        self.host = host
        self.user = user
        
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
    
    async def create_vm(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new VM
        
        Args:
            node: Node name
            vmid: VM ID
            config: VM configuration
            
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
    
    async def clone_vm(self, node: str, vmid: int, newid: int, name: str,
                      full: bool = True) -> Dict[str, Any]:
        """
        Clone an existing VM
        
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


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


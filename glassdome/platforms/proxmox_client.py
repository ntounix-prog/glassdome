"""
Proxmox API Integration
Implements the PlatformClient interface for Proxmox VE
"""
from proxmoxer import ProxmoxAPI
from typing import Dict, Any, List, Optional
import logging
import asyncio
import time
from pathlib import Path

from glassdome.platforms.base import PlatformClient, VMStatus
from glassdome.utils.windows_autounattend import generate_autounattend_xml, create_autounattend_iso

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
                verify_ssl=verify_ssl,
                timeout=30  # Increase timeout for slow operations
            )
        elif password:
            self.client = ProxmoxAPI(
                host,
                user=user,
                password=password,
                verify_ssl=verify_ssl,
                timeout=30  # Increase timeout for slow operations
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
        node = config.get("node") or self.default_node
        vmid = config.get("vmid") or await self.get_next_vmid()
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
        
        # Determine deployment method based on OS type
        os_type = config.get("os_type", "linux")
        
        if os_type == "windows":
            # Windows: Create from ISO with autounattend
            result = await self.create_windows_vm_from_iso(
                node=node,
                vmid=vmid,
                config=config
            )
            ip_address = result.get("ip_address")
        elif config.get("template_id"):
            # Linux: Clone from template
            result = await self.clone_vm_from_template(
                node=node,
                template_id=config["template_id"],
                new_vmid=vmid,
                config=config
            )
            # Start the VM
            await self.start_vm(str(vmid))
            # Wait for IP address
            ip_address = await self.get_vm_ip(str(vmid), timeout=config.get("ip_timeout", 120))
        else:
            # No template and not Windows
            raise Exception(f"Linux VMs require template_id. Use UBUNTU_2204_TEMPLATE_ID from .env")
        
        # Return standardized format
        return {
            "vm_id": str(vmid),
            "ip_address": ip_address,
            "platform": "proxmox",
            "status": (await self.get_vm_status(str(vmid))).value,
            "ansible_connection": {
                "host": ip_address or "unknown",
                "user": config.get("ssh_user", "ubuntu") if os_type == "linux" else config.get("admin_user", "Administrator"),
                "ssh_key_path": config.get("ssh_key_path", "/root/.ssh/id_rsa") if os_type == "linux" else None,
                "port": 22 if os_type == "linux" else 3389
            },
            "platform_specific": {
                "node": node,
                "vmid": vmid,
                "name": name,
                "host": self.host,
                "os_type": os_type
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
        logger.info(f"Cloning template {template_id} to {new_vmid} on node '{node}'")
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
            logger.info(f"API call: nodes('{node}').qemu({vmid}).clone.post(newid={newid}, name='{name}', full={1 if full else 0})")
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
    
    async def start_vm_raw(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start a VM (Proxmox-specific, low-level)"""
        try:
            task = self.client.nodes(node).qemu(vmid).status.start.post()
            logger.info(f"VM {vmid} started on node {node}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to start VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def stop_vm_raw(self, node: str, vmid: int) -> Dict[str, Any]:
        """Stop a VM (Proxmox-specific, low-level)"""
        try:
            task = self.client.nodes(node).qemu(vmid).status.stop.post()
            logger.info(f"VM {vmid} stopped on node {node}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to stop VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_vm_raw(self, node: str, vmid: int) -> Dict[str, Any]:
        """Delete a VM (Proxmox-specific, low-level)"""
        try:
            task = self.client.nodes(node).qemu(vmid).delete()
            logger.info(f"VM {vmid} deleted from node {node}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to delete VM {vmid}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_vm_status_raw(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get VM status (Proxmox-specific, low-level)"""
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
    
    async def get_vm_ip_raw(self, node: str, vmid: int, timeout: int = 120) -> Optional[str]:
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
    
    async def create_windows_vm_from_iso(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Windows VM from ISO with autounattend
        
        Args:
            node: Proxmox node
            vmid: VM ID
            config: VM configuration
        
        Returns:
            Dict with vm_id and ip_address
        """
        from glassdome.core.config import settings
        from glassdome.utils.ip_pool import get_ip_pool_manager
        
        name = config.get("name", f"windows-vm-{vmid}")
        windows_version = config.get("windows_version", "server2022")
        memory_mb = config.get("memory_mb", 4096)
        cores = config.get("cpu_cores", 2)
        disk_size_gb = config.get("disk_size_gb", 80)
        admin_password = config.get("admin_password", "Glassdome123!")
        network_cidr = config.get("network_cidr", "192.168.3.0/24")
        
        logger.info(f"Creating Windows VM {vmid} from ISO on node {node}")
        
        # Allocate static IP
        ip_manager = get_ip_pool_manager()
        ip_allocation = ip_manager.allocate_ip(network_cidr, str(vmid))
        
        if not ip_allocation:
            raise Exception(f"Failed to allocate IP from network {network_cidr}")
        
        static_ip = ip_allocation["ip"]
        gateway = ip_allocation["gateway"]
        netmask = ip_allocation["netmask"]
        dns_servers = ip_allocation["dns"]
        
        logger.info(f"Allocated IP {static_ip} to VM {vmid}")
        
        # Paths to ISOs
        glassdome_root = Path(settings.glassdome_root) if hasattr(settings, 'glassdome_root') else Path.cwd()
        windows_iso_path = glassdome_root / "isos" / "windows" / "windows-server-2022-eval.iso"
        virtio_iso_path = glassdome_root / "isos" / "drivers" / "virtio-win.iso"
        
        # Generate autounattend.xml with static IP
        autounattend_config = {
            "hostname": name,
            "admin_password": admin_password,
            "windows_version": windows_version,
            "enable_rdp": True,
            "virtio_drivers": True,
            "static_ip": static_ip,
            "gateway": gateway,
            "netmask": netmask,
            "dns": dns_servers
        }
        autounattend_xml = generate_autounattend_xml(autounattend_config)
        
        # Create autounattend ISO
        autounattend_iso_path = glassdome_root / "isos" / "custom" / f"autounattend-{vmid}.iso"
        autounattend_iso_path.parent.mkdir(parents=True, exist_ok=True)
        create_autounattend_iso(autounattend_xml, autounattend_iso_path)
        
        logger.info(f"Created autounattend ISO: {autounattend_iso_path}")
        
        # Create VM with Windows-optimized settings
        vm_config = {
            "vmid": vmid,
            "name": name,
            "memory": memory_mb,
            "cores": cores,
            "sockets": 1,
            "cpu": "host",
            "ostype": "win11",  # Windows 10/11/2022
            "machine": "pc-q35-7.2",  # Modern machine type for Windows
            "bios": "ovmf",  # UEFI BIOS
            "scsihw": "virtio-scsi-pci",
            "net0": f"virtio,bridge={config.get('network', 'vmbr0')}",
            "ide2": f"none,media=cdrom",  # CDROM for Windows ISO
            "efidisk0": f"{self.default_storage}:1,efitype=4m,pre-enrolled-keys=1",
        }
        
        # Create the VM
        try:
            self.client.nodes(node).qemu.create(**vm_config)
            logger.info(f"Created VM {vmid} shell")
        except Exception as e:
            logger.error(f"Failed to create VM shell: {e}")
            raise
        
        # Wait a moment for VM to be fully created
        await asyncio.sleep(2)
        
        # Add disk
        try:
            disk_config = {
                "scsi0": f"{self.default_storage}:{disk_size_gb},cache=writeback,discard=on"
            }
            self.client.nodes(node).qemu(vmid).config.put(**disk_config)
            logger.info(f"Added {disk_size_gb}GB disk to VM {vmid}")
        except Exception as e:
            logger.error(f"Failed to add disk: {e}")
            raise
        
        # Upload ISOs to Proxmox if not already there (simplified - assumes ISOs are accessible)
        # In production, you'd upload these to Proxmox storage
        
        # Attach ISOs
        try:
            # Windows ISO as IDE2 (primary CD-ROM)
            # VirtIO drivers as IDE0 (secondary CD-ROM)
            # Autounattend as IDE1 (third CD-ROM)
            iso_config = {
                "ide2": f"local:iso/{windows_iso_path.name},media=cdrom",
                "ide0": f"local:iso/{virtio_iso_path.name},media=cdrom",
                "ide1": f"local:iso/{autounattend_iso_path.name},media=cdrom"
            }
            self.client.nodes(node).qemu(vmid).config.put(**iso_config)
            logger.info(f"Attached ISOs to VM {vmid}")
        except Exception as e:
            logger.warning(f"Failed to attach ISOs (may need manual upload): {e}")
            # This is expected - ISOs need to be manually uploaded to Proxmox storage
            logger.info(f"Please upload ISOs to Proxmox:")
            logger.info(f"  1. {windows_iso_path}")
            logger.info(f"  2. {virtio_iso_path}")
            logger.info(f"  3. {autounattend_iso_path}")
        
        # Set boot order (CD-ROM first for installation)
        try:
            boot_config = {
                "boot": "order=ide2;scsi0",
                "bootdisk": "scsi0"
            }
            self.client.nodes(node).qemu(vmid).config.put(**boot_config)
            logger.info(f"Set boot order for VM {vmid}")
        except Exception as e:
            logger.warning(f"Failed to set boot order: {e}")
        
        # Start VM
        logger.info(f"Starting Windows VM {vmid} (Windows will auto-install, ~15-20 minutes)")
        await self.start_vm(str(vmid))
        
        # Return with assigned static IP
        logger.info(f"Windows VM {vmid} is installing. Check Proxmox console for progress.")
        logger.info(f"After installation: RDP to {static_ip} with Administrator / {admin_password}")
        
        return {
            "vm_id": str(vmid),
            "ip_address": static_ip,  # Static IP assigned via autounattend
            "status": "installing",
            "notes": f"Windows is installing automatically. This takes 15-20 minutes. RDP: {static_ip}:3389, User: Administrator, Password: {admin_password}"
        }
    
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


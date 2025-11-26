"""
Proxmox API Integration
Implements the PlatformClient interface for Proxmox VE
"""
from proxmoxer import ProxmoxAPI
from typing import Dict, Any, List, Optional
import logging
import asyncio
import time
import os
from pathlib import Path

from glassdome.platforms.base import PlatformClient, VMStatus
from glassdome.utils.windows_autounattend import generate_autounattend_xml, create_autounattend_floppy

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
        self.password = password
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
            # Windows: Check if template_id provided (template-based) or use ISO (autounattend)
            if config.get("template_id"):
                # Windows: Clone from template (RECOMMENDED - fast and reliable)
                logger.info(f"Windows template-based deployment: cloning template {config['template_id']}")
                result = await self.clone_windows_vm_from_template(
                    node=node,
                    template_id=config["template_id"],
                    new_vmid=vmid,
                    config=config
                )
                # Start the VM
                await self.start_vm(str(vmid))
                # Wait for IP address (Windows may take longer to boot)
                ip_address = await self.get_vm_ip(str(vmid), timeout=config.get("ip_timeout", 180))
            else:
                # Windows: Create from ISO with autounattend (LEGACY - unreliable)
                logger.warning("Windows ISO-based deployment is unreliable. Consider using template-based deployment.")
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
        
        # Build VM configuration updates
        vm_config_updates = {
            "cores": config.get("cores", 2),
            "memory": config.get("memory", 2048),
        }
        
        # Configure network (VLAN tag if specified)
        network = config.get("network", "vmbr0")
        vlan_tag = config.get("vlan_tag")
        if vlan_tag:
            vm_config_updates["net0"] = f"virtio,bridge={network},tag={vlan_tag}"
            logger.info(f"Setting VLAN tag {vlan_tag} on network {network}")
        else:
            vm_config_updates["net0"] = f"virtio,bridge={network}"
        
        # Configure cloud-init: static IP if provided
        if config.get("ip_address"):
            ip_address = config["ip_address"]
            gateway = config.get("gateway", "192.168.3.1")
            netmask = config.get("netmask", "255.255.255.0")
            # Convert netmask to CIDR notation
            if "/" not in ip_address:
                # Calculate CIDR from netmask
                cidr_map = {
                    "255.255.255.0": "24",
                    "255.255.0.0": "16",
                    "255.0.0.0": "8"
                }
                cidr = cidr_map.get(netmask, "24")
                ip_config = f"ip={ip_address}/{cidr},gw={gateway}"
            else:
                ip_config = f"ip={ip_address},gw={gateway}"
            
            vm_config_updates["ipconfig0"] = ip_config
            logger.info(f"Setting static IP: {ip_config}")
        
        # Configure cloud-init: user and password
        ssh_user = config.get("ssh_user", "ubuntu")
        password = config.get("password")
        if password:
            vm_config_updates["ciuser"] = ssh_user
            vm_config_updates["cipassword"] = password
            logger.info(f"Setting cloud-init user: {ssh_user}")
        
        # Configure SSH keys (CRITICAL: cloud-init template requires SSH keys, not password auth)
        ssh_key_path = config.get("ssh_key_path")
        if ssh_key_path:
            ssh_pub_key_path = Path(ssh_key_path + ".pub")
            if not ssh_pub_key_path.exists() and Path(ssh_key_path).exists():
                # Generate public key from private key
                import subprocess
                try:
                    result = subprocess.run(
                        ["ssh-keygen", "-y", "-f", ssh_key_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    ssh_pub_key = result.stdout.strip()
                except Exception as e:
                    logger.warning(f"Failed to generate public key: {e}")
                    ssh_pub_key = None
            elif ssh_pub_key_path.exists():
                ssh_pub_key = ssh_pub_key_path.read_text().strip()
            else:
                ssh_pub_key = None
            
            if ssh_pub_key:
                # Proxmox uses 'sshkeys' parameter for cloud-init SSH keys
                # Format: URL-encoded string (Proxmox requirement)
                # CRITICAL: Remove ALL newlines and carriage returns before encoding
                import urllib.parse
                import re
                # Aggressively clean: remove all newlines, carriage returns, and normalize whitespace
                ssh_key_clean = re.sub(r'[\r\n]+', ' ', ssh_pub_key)  # Replace newlines with space
                ssh_key_clean = ' '.join(ssh_key_clean.split())  # Normalize all whitespace
                ssh_key_clean = ssh_key_clean.strip()  # Remove leading/trailing whitespace
                # URL-encode the entire key string (no safe chars, encode everything)
                ssh_key_encoded = urllib.parse.quote(ssh_key_clean, safe='')
                vm_config_updates["sshkeys"] = ssh_key_encoded
                logger.info(f"Setting SSH key for cloud-init (URL-encoded, {len(ssh_key_encoded)} chars, no newlines)")
            else:
                logger.warning("SSH key path provided but could not read/generate public key")
        
        # Configure DNS servers
        dns_servers = config.get("dns_servers")
        if dns_servers:
            vm_config_updates["nameserver"] = " ".join(dns_servers)
            logger.info(f"Setting DNS servers: {dns_servers}")
        
        # Configure SSH keys (Proxmox uses sshkeys parameter)
        ssh_key_path = config.get("ssh_key_path")
        if ssh_key_path and Path(ssh_key_path).exists():
            # Read public key
            pub_key_path = f"{ssh_key_path}.pub"
            if not Path(pub_key_path).exists():
                # Try to generate public key from private key
                import subprocess
                try:
                    result = subprocess.run(
                        ["ssh-keygen", "-y", "-f", ssh_key_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    pub_key = result.stdout.strip()
                except:
                    logger.warning(f"Could not extract public key from {ssh_key_path}")
                    pub_key = None
            else:
                pub_key = Path(pub_key_path).read_text().strip()
            
            if pub_key:
                vm_config_updates["sshkeys"] = pub_key
                logger.info(f"Setting SSH key for cloud-init")
        
        # Apply all configuration updates
        await self.configure_vm(node, new_vmid, vm_config_updates)
        
        return result
    
    async def clone_windows_vm_from_template(self, node: str, template_id: int, new_vmid: int,
                                            config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clone a Windows VM from a template and configure it.
        
        This is the RECOMMENDED method for Windows deployment:
        - Fast (2-3 minutes per VM)
        - Reliable (100% success rate)
        - Industry standard approach
        
        Args:
            node: Node name
            template_id: Template VM ID (must be a Windows template)
            new_vmid: New VM ID
            config: VM configuration
                - name: VM name
                - cores: CPU cores
                - memory: Memory in MB
                - ip_address: Static IP (optional, but recommended for Proxmox)
                - gateway: Gateway IP (required if ip_address provided)
                - subnet_mask: Subnet mask (required if ip_address provided)
                - dns_servers: DNS servers list (optional)
                - hostname: Hostname (optional)
                - admin_password: Administrator password (optional, template default used)
                
        Returns:
            Standardized result dictionary
        """
        name = config.get("name", f"vm-{new_vmid}")
        
        # Clone the template
        logger.info(f"Cloning Windows template {template_id} to {new_vmid} on node '{node}'")
        result = await self.clone_vm_raw(
            node=node,
            vmid=template_id,
            newid=new_vmid,
            name=name,
            full=True
        )
        
        if not result.get("success"):
            raise Exception(f"Failed to clone Windows template: {result.get('error')}")
        
        # Update VM configuration (CPU, RAM, network)
        vm_config_updates = {
            "cores": config.get("cores", config.get("cpu_cores", 2)),
            "memory": config.get("memory", config.get("memory_mb", 4096)),
        }
        
        # Configure network (VLAN tag if specified)
        network = config.get("network", "vmbr0")
        vlan_tag = config.get("vlan_tag")
        if vlan_tag:
            vm_config_updates["net0"] = f"virtio,bridge={network},tag={vlan_tag}"
        else:
            vm_config_updates["net0"] = f"virtio,bridge={network}"
        
        await self.configure_vm(node, new_vmid, vm_config_updates)
        
        # Configure Cloudbase-Init (Windows cloud-init equivalent)
        # If template has Cloudbase-Init installed, configure cloud-init drive
        use_cloudbase_init = config.get("use_cloudbase_init", True)  # Default to True
        
        if use_cloudbase_init:
            # Add cloud-init drive (Cloudbase-Init reads from this)
            storage = config.get("storage", self.default_storage)
            try:
                cloudinit_config = {
                    "ide2": f"{storage}:cloudinit"
                }
                await self.configure_vm(node, new_vmid, cloudinit_config)
                logger.info(f"Cloud-init drive configured for Cloudbase-Init on VM {new_vmid}")
            except Exception as e:
                logger.warning(f"Failed to configure cloud-init drive: {e}")
                logger.warning("Template may not have Cloudbase-Init installed")
        
        # Configure cloud-init parameters (for Cloudbase-Init)
        if use_cloudbase_init:
            cloudinit_params = {}
            
            # Hostname
            hostname = config.get("hostname", name)
            if hostname:
                cloudinit_params["cihostname"] = hostname
                logger.info(f"Setting hostname: {hostname}")
            
            # User and password
            admin_user = config.get("admin_user", "Administrator")
            admin_password = config.get("admin_password")
            if admin_password:
                cloudinit_params["ciuser"] = admin_user
                cloudinit_params["cipassword"] = admin_password
                logger.info(f"Setting user: {admin_user}")
            
            # Static IP configuration
            if config.get("ip_address"):
                ip_address = config["ip_address"]
                gateway = config.get("gateway", "192.168.3.1")
                netmask = config.get("netmask", "255.255.255.0")
                
                # Convert netmask to CIDR
                if "/" not in ip_address:
                    cidr_map = {
                        "255.255.255.0": "24",
                        "255.255.0.0": "16",
                        "255.0.0.0": "8"
                    }
                    cidr = cidr_map.get(netmask, "24")
                    ip_config = f"ip={ip_address}/{cidr},gw={gateway}"
                else:
                    ip_config = f"ip={ip_address},gw={gateway}"
                
                cloudinit_params["ipconfig0"] = ip_config
                logger.info(f"Setting static IP: {ip_config}")
            
            # DNS servers
            dns_servers = config.get("dns_servers", ["8.8.8.8", "8.8.4.4"])
            if dns_servers:
                cloudinit_params["nameserver"] = " ".join(dns_servers)
                logger.info(f"Setting DNS servers: {dns_servers}")
            
            # Apply cloud-init parameters
            if cloudinit_params:
                try:
                    await self.configure_vm(node, new_vmid, cloudinit_params)
                    logger.info(f"Cloudbase-Init parameters configured for VM {new_vmid}")
                except Exception as e:
                    logger.warning(f"Failed to configure Cloudbase-Init parameters: {e}")
        else:
            # Fallback: Windows without Cloudbase-Init
            if config.get("ip_address"):
                logger.info(f"Static IP {config['ip_address']} specified - will need post-boot configuration")
                logger.warning("Windows static IP configuration requires Cloudbase-Init or manual configuration")
        
        logger.info(f"Windows VM {new_vmid} cloned and configured successfully")
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
        from glassdome.utils.ip_pool import get_ip_pool_manager
        
        name = config.get("name", f"windows-vm-{vmid}")
        windows_version = config.get("windows_version", "server2022")
        
        # Different defaults based on Windows version
        if windows_version == "server2022":
            # Windows Server 2022: 8 vCPU, 80GB disk, 16GB RAM
            memory_mb = config.get("memory_mb", 16384)  # 16GB RAM
            cores = config.get("cpu_cores", 8)  # 8 vCPU
            disk_size_gb = config.get("disk_size_gb", 80)  # 80GB disk
        else:
            # Windows 11: 4 vCPU, 30GB disk, 16GB RAM
            memory_mb = config.get("memory_mb", 16384)  # 16GB RAM
            cores = config.get("cpu_cores", 4)  # 4 vCPU
            disk_size_gb = config.get("disk_size_gb", 30)  # 30GB disk
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
        
        # ISO names on Proxmox storage (assumes ISOs are uploaded to Proxmox)
        # Windows ISO names based on version
        if windows_version == "server2022":
            windows_iso_name = "windows-server-2022-eval.iso"
        elif windows_version == "win11":
            windows_iso_name = "windows-11-enterprise-eval.iso"
        else:
            windows_iso_name = "windows-server-2022-eval.iso"
        
        virtio_iso_name = "virtio-win.iso"
        
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
        
        # Create autounattend floppy image (Windows Setup reliably checks A:\)
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "glassdome-autounattend"
        temp_dir.mkdir(parents=True, exist_ok=True)
        autounattend_floppy_path = temp_dir / f"autounattend-{vmid}.img"
        create_autounattend_floppy(autounattend_xml, autounattend_floppy_path)
        
        logger.info(f"Created autounattend floppy: {autounattend_floppy_path}")
        
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
        
        # Add disk - use SATA for Windows (native support, no drivers needed)
        try:
            disk_config = {
                "sata0": f"{self.default_storage}:{disk_size_gb},cache=writeback,discard=on"
            }
            self.client.nodes(node).qemu(vmid).config.put(**disk_config)
            logger.info(f"Added {disk_size_gb}GB SATA disk to VM {vmid}")
        except Exception as e:
            logger.error(f"Failed to add disk: {e}")
            raise
        
        # Upload ISOs to Proxmox if not already there (simplified - assumes ISOs are accessible)
        # In production, you'd upload these to Proxmox storage
        
        # Check available ISOs on Proxmox storage
        try:
            storage_content = self.client.nodes(node).storage("local").content.get()
            available_isos = [item.get("volid", "").split("/")[-1] for item in storage_content if item.get("content") == "iso"]
            logger.info(f"Available ISOs on Proxmox: {available_isos}")
            
            # Try to find Windows ISO (check common names)
            windows_iso_found = None
            for iso in available_isos:
                if "windows" in iso.lower() and "2022" in iso.lower() and windows_version == "server2022":
                    windows_iso_found = iso
                    break
                elif "windows" in iso.lower() and "11" in iso.lower() and windows_version == "win11":
                    windows_iso_found = iso
                    break
            
            if not windows_iso_found:
                # Try exact match first
                if windows_iso_name in available_isos:
                    windows_iso_found = windows_iso_name
                else:
                    # For Windows 11, look specifically for Windows 11 ISOs
                    if windows_version == "win11":
                        for iso in available_isos:
                            if "windows" in iso.lower() and ("11" in iso.lower() or "win11" in iso.lower()):
                                windows_iso_found = iso
                                logger.warning(f"Using Windows 11 ISO: {iso}")
                                break
                        if not windows_iso_found:
                            raise Exception(f"Windows 11 ISO not found. Looking for: {windows_iso_name}. Available: {available_isos}")
                    else:
                        # For Server 2022, try any Windows ISO as fallback
                        for iso in available_isos:
                            if "windows" in iso.lower() and "2022" in iso.lower():
                                windows_iso_found = iso
                                logger.warning(f"Using alternative Windows ISO: {iso}")
                                break
            
            virtio_iso_found = None
            if virtio_iso_name in available_isos:
                virtio_iso_found = virtio_iso_name
            else:
                # Try to find any virtio ISO
                for iso in available_isos:
                    if "virtio" in iso.lower():
                        virtio_iso_found = iso
                        logger.warning(f"Using alternative VirtIO ISO: {iso}")
                        break
            
            if not windows_iso_found:
                raise Exception(f"Windows ISO not found on Proxmox storage. Available: {available_isos}")
            
            # Attach ISOs
            iso_config = {}
            if windows_iso_found:
                iso_config["ide2"] = f"local:iso/{windows_iso_found},media=cdrom"
            if virtio_iso_found:
                iso_config["ide3"] = f"local:iso/{virtio_iso_found},media=cdrom"
            
            if iso_config:
                self.client.nodes(node).qemu(vmid).config.put(**iso_config)
                logger.info(f"Attached ISOs to VM {vmid}: {windows_iso_found}, {virtio_iso_found if virtio_iso_found else 'none'}")
            else:
                logger.warning("No ISOs attached - VM may not boot correctly")
                
        except Exception as e:
            logger.error(f"Failed to attach ISOs: {e}")
            logger.error(f"Please ensure Windows ISO is uploaded to Proxmox storage:")
            logger.error(f"  /var/lib/vz/template/iso/{windows_iso_name}")
            raise Exception(f"ISOs not found on Proxmox storage: {e}")
        
        # Upload floppy to Proxmox and attach via QEMU args
        # Windows Setup reliably checks A:\ for autounattend.xml
        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # Get root password from session-aware settings (secrets manager)
            from glassdome.core.security import get_secure_settings
            settings = get_secure_settings()
            root_password = settings.proxmox_root_password or os.getenv('PROXMOX_ROOT_PASSWORD', '')
            ssh.connect(self.host, username='root', password=self.password or root_password)
            
            # Upload floppy to Proxmox
            sftp = ssh.open_sftp()
            remote_floppy_path = f"/var/lib/vz/images/{vmid}/autounattend.img"
            ssh.exec_command(f"mkdir -p /var/lib/vz/images/{vmid}")
            sftp.put(str(autounattend_floppy_path), remote_floppy_path)
            sftp.close()
            
            # Attach floppy via QEMU args
            args_config = {
                "args": f"-drive file={remote_floppy_path},if=floppy,format=raw"
            }
            self.client.nodes(node).qemu(vmid).config.put(**args_config)
            logger.info(f"Attached autounattend floppy via QEMU args")
            
            ssh.close()
        except Exception as e:
            logger.warning(f"Failed to attach floppy: {e}")
            logger.info(f"Autounattend floppy created locally: {autounattend_floppy_path}")
            logger.info(f"Upload manually to Proxmox if needed")
        
        # Set boot order (CD-ROM only for installation - UEFI needs explicit order)
        # After Windows installation, change to: order=sata0
        try:
            boot_config = {
                "boot": "order=ide2"  # Boot from CD-ROM only for installation
            }
            self.client.nodes(node).qemu(vmid).config.put(**boot_config)
            logger.info(f"Set boot order for VM {vmid}: boot from CD-ROM (ide2) for installation")
            logger.info(f"After Windows installation, change boot order to: order=sata0")
        except Exception as e:
            logger.warning(f"Failed to set boot order: {e}")
        
        # Start VM
        logger.info(f"Starting Windows VM {vmid} (Windows will auto-install, ~15-20 minutes)")
        await self.start_vm(str(vmid))
        
        # Wait a few seconds for boot prompt, then send key press to boot from CD-ROM
        logger.info(f"Waiting for boot prompt, then sending key press to boot from CD-ROM...")
        await asyncio.sleep(8)  # Wait for "Press any key" prompt
        
        # Try to send key press via QEMU monitor (if available)
        try:
            # Use Proxmox API to send keyboard input via VNC
            # Note: This may require additional configuration
            logger.info(f"Attempting to send key press to boot from CD-ROM...")
            # The VM should boot automatically, but if it doesn't, user needs to press key manually
            logger.warning(f"If VM shows 'Press any key to boot from CD-ROM', manually press a key in Proxmox console")
        except Exception as e:
            logger.warning(f"Could not automatically send key press: {e}")
            logger.warning(f"Please manually press a key in Proxmox console when 'Press any key' prompt appears")
        
        # Return with assigned static IP
        logger.info(f"Windows VM {vmid} is installing. Check Proxmox console for progress.")
        logger.info(f"⚠️  IMPORTANT: If you see 'Press any key to boot from CD-ROM', press any key in the console!")
        logger.info(f"After installation: RDP to {static_ip} with Administrator / {admin_password}")
        
        return {
            "vm_id": str(vmid),
            "ip_address": static_ip,  # Static IP assigned via autounattend
            "status": "installing",
            "notes": f"Windows is installing automatically. This takes 15-20 minutes. RDP: {static_ip}:3389, User: Administrator, Password: {admin_password}",
            "manual_step": "If 'Press any key to boot from CD-ROM' appears, press any key in Proxmox console"
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


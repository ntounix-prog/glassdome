"""
ESXi API Integration (Direct ESXi Host Connection)
Implements the PlatformClient interface for standalone ESXi hosts (no vCenter required)

This client connects directly to an ESXi host using the VMware vSphere API (pyvmomi).
It provides VM creation, management, and networking capabilities on a single ESXi host.
"""
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import time
import asyncio
from typing import Dict, Any, List, Optional
import logging

from glassdome.platforms.base import PlatformClient, VMStatus

logger = logging.getLogger(__name__)


class ESXiClient(PlatformClient):
    """
    Client for interacting with standalone ESXi hosts
    
    NO VCENTER REQUIRED - Connects directly to ESXi host API.
    
    Uses pyvmomi (VMware vSphere Python SDK) to:
    - Create and manage VMs
    - Clone from templates
    - Manage virtual networks
    - Handle storage
    
    Note: Some advanced features (like DRS, HA, distributed switches) 
    require vCenter and are not available on standalone ESXi.
    """
    
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = False,
        datacenter_name: str = "ha-datacenter",  # Default for standalone ESXi
        datastore_name: Optional[str] = None,
        network_name: str = "VM Network"
    ):
        """
        Initialize ESXi client (direct host connection, no vCenter)
        
        Args:
            host: ESXi host IP or hostname
            user: Username (usually 'root')
            password: Password
            port: HTTPS port (default: 443)
            verify_ssl: Verify SSL certificates (usually False for self-signed certs)
            datacenter_name: Datacenter name (default 'ha-datacenter' for standalone)
            datastore_name: Datastore to use (if None, uses first available)
            network_name: Virtual network name (default: "VM Network")
        """
        self.host = host
        self.user = user
        self.port = port
        self.datacenter_name = datacenter_name
        self.default_datastore_name = datastore_name
        self.default_network_name = network_name
        
        # SSL context (disable verification for self-signed certs)
        if verify_ssl:
            self.ssl_context = ssl.create_default_context()
        else:
            self.ssl_context = ssl._create_unverified_context()
        
        # Connect to ESXi
        try:
            self.service_instance = SmartConnect(
                host=host,
                user=user,
                pwd=password,
                port=port,
                sslContext=self.ssl_context
            )
            
            # Register disconnect on exit
            atexit.register(Disconnect, self.service_instance)
            
            # Get content (main API entry point)
            self.content = self.service_instance.RetrieveContent()
            
            # Get datacenter
            self.datacenter = self._get_datacenter()
            
            # Get compute resource (host)
            self.compute_resource = self._get_compute_resource()
            
            # Get resource pool
            self.resource_pool = self.compute_resource.resourcePool
            
            # Get default datastore
            if not datastore_name:
                datastores = self.compute_resource.datastore
                if datastores:
                    self.default_datastore = datastores[0]
                    self.default_datastore_name = self.default_datastore.name
                else:
                    raise Exception("No datastores found on ESXi host")
            else:
                self.default_datastore = self._get_datastore(datastore_name)
            
            logger.info(f"ESXi client connected to {host}")
            logger.info(f"Using datastore: {self.default_datastore_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ESXi host {host}: {str(e)}")
            raise
    
    # =========================================================================
    # PLATFORM CLIENT INTERFACE IMPLEMENTATION
    # =========================================================================
    
    async def create_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a VM on ESXi (implements PlatformClient interface)
        
        Supports:
        - Cloning from template (if template_id provided)
        - Creating from scratch (if no template)
        - Custom hardware configuration
        - Network assignment
        """
        name = config.get("name", "glassdome-vm")
        
        logger.info(f"Creating VM on ESXi: {name}")
        
        # Check if cloning from template
        if config.get("template_id"):
            vm = await self._clone_from_template(config)
        else:
            vm = await self._create_from_scratch(config)
        
        # Power on the VM
        await self._power_on_vm(vm)
        
        # Wait for IP address
        ip_address = await self.get_vm_ip(vm.name, timeout=config.get("ip_timeout", 120))
        
        # Return standardized result
        return {
            "vm_id": vm.name,  # ESXi uses VM name as primary identifier
            "ip_address": ip_address,
            "platform": "esxi",
            "status": (await self.get_vm_status(vm.name)).value,
            "ansible_connection": {
                "host": ip_address or "unknown",
                "user": config.get("ssh_user", "root"),
                "ssh_key_path": config.get("ssh_key_path", "/root/.ssh/id_rsa"),
                "port": 22
            },
            "platform_specific": {
                "esxi_host": self.host,
                "datastore": self.default_datastore_name,
                "vm_name": vm.name,
                "vm_path": f"[{self.default_datastore_name}] {vm.name}"
            }
        }
    
    async def start_vm(self, vm_id: str) -> bool:
        """Start a VM (implements PlatformClient interface)"""
        try:
            vm = self._get_vm_by_name(vm_id)
            if not vm:
                logger.error(f"VM not found: {vm_id}")
                return False
            
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                logger.info(f"VM {vm_id} is already powered on")
                return True
            
            task = vm.PowerOn()
            self._wait_for_task(task)
            
            logger.info(f"VM {vm_id} powered on")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start VM {vm_id}: {str(e)}")
            return False
    
    async def stop_vm(self, vm_id: str, force: bool = False) -> bool:
        """Stop a VM (implements PlatformClient interface)"""
        try:
            vm = self._get_vm_by_name(vm_id)
            if not vm:
                logger.error(f"VM not found: {vm_id}")
                return False
            
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                logger.info(f"VM {vm_id} is already powered off")
                return True
            
            if force:
                task = vm.PowerOff()
            else:
                # Try graceful shutdown first (requires VMware Tools)
                try:
                    vm.ShutdownGuest()
                    logger.info(f"VM {vm_id} shutdown initiated (graceful)")
                    return True
                except:
                    # Fall back to hard power off
                    task = vm.PowerOff()
            
            self._wait_for_task(task)
            logger.info(f"VM {vm_id} powered off")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop VM {vm_id}: {str(e)}")
            return False
    
    async def delete_vm(self, vm_id: str) -> bool:
        """Delete a VM (implements PlatformClient interface)"""
        try:
            vm = self._get_vm_by_name(vm_id)
            if not vm:
                logger.error(f"VM not found: {vm_id}")
                return False
            
            # Power off if running
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                await self.stop_vm(vm_id, force=True)
            
            # Destroy VM
            task = vm.Destroy()
            self._wait_for_task(task)
            
            logger.info(f"VM {vm_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_id}: {str(e)}")
            return False
    
    async def get_vm_status(self, vm_id: str) -> VMStatus:
        """Get VM status (implements PlatformClient interface)"""
        try:
            vm = self._get_vm_by_name(vm_id)
            if not vm:
                return VMStatus.UNKNOWN
            
            power_state = vm.runtime.powerState
            
            if power_state == vim.VirtualMachinePowerState.poweredOn:
                return VMStatus.RUNNING
            elif power_state == vim.VirtualMachinePowerState.poweredOff:
                return VMStatus.STOPPED
            elif power_state == vim.VirtualMachinePowerState.suspended:
                return VMStatus.PAUSED
            else:
                return VMStatus.UNKNOWN
                
        except Exception as e:
            logger.error(f"Failed to get status for VM {vm_id}: {str(e)}")
            return VMStatus.ERROR
    
    async def get_vm_ip(self, vm_id: str, timeout: int = 120) -> Optional[str]:
        """Get VM IP address (implements PlatformClient interface)"""
        vm = self._get_vm_by_name(vm_id)
        if not vm:
            return None
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                # Get IP from VMware Tools
                if vm.guest and vm.guest.ipAddress:
                    ip = vm.guest.ipAddress
                    if ip and not ip.startswith('127.'):
                        logger.info(f"VM {vm_id} IP detected: {ip}")
                        return ip
                
                # Alternative: check network adapters
                if vm.guest and vm.guest.net:
                    for net in vm.guest.net:
                        if net.ipAddress:
                            for ip in net.ipAddress:
                                if not ip.startswith('127.') and not ip.startswith('fe80'):
                                    logger.info(f"VM {vm_id} IP detected: {ip}")
                                    return ip
                
            except Exception as e:
                logger.debug(f"Waiting for VM {vm_id} IP... ({int(time.time() - start_time)}s)")
            
            await asyncio.sleep(5)
        
        logger.warning(f"Timeout waiting for VM {vm_id} IP address")
        return None
    
    async def test_connection(self) -> bool:
        """Test connection to ESXi (implements PlatformClient interface)"""
        try:
            about = self.content.about
            logger.info(f"Connected to ESXi: {about.fullName}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def get_platform_info(self) -> Dict[str, Any]:
        """Get platform info (implements PlatformClient interface)"""
        try:
            about = self.content.about
            return {
                "platform": "esxi",
                "version": about.version,
                "build": about.build,
                "fullName": about.fullName,
                "host": self.host,
                "datacenter": self.datacenter_name,
                "datastore": self.default_datastore_name
            }
        except Exception as e:
            logger.error(f"Failed to get platform info: {str(e)}")
            return {"platform": "esxi", "version": "unknown"}
    
    # =========================================================================
    # ESXI-SPECIFIC HELPER METHODS
    # =========================================================================
    
    async def _clone_from_template(self, config: Dict[str, Any]) -> vim.VirtualMachine:
        """Clone a VM from a template"""
        template_name = config.get("template_id")
        vm_name = config.get("name")
        
        logger.info(f"Cloning VM from template: {template_name}")
        
        # Get template
        template = self._get_vm_by_name(template_name)
        if not template:
            raise Exception(f"Template not found: {template_name}")
        
        # Clone spec
        relocate_spec = vim.vm.RelocateSpec(
            datastore=self.default_datastore,
            pool=self.resource_pool
        )
        
        clone_spec = vim.vm.CloneSpec(
            location=relocate_spec,
            powerOn=False,
            template=False
        )
        
        # Clone
        task = template.Clone(
            folder=self.datacenter.vmFolder,
            name=vm_name,
            spec=clone_spec
        )
        
        self._wait_for_task(task)
        
        # Get cloned VM
        vm = self._get_vm_by_name(vm_name)
        logger.info(f"VM cloned successfully: {vm_name}")
        
        # Reconfigure if needed
        if config.get("cores") or config.get("memory"):
            await self._reconfigure_vm(vm, config)
        
        return vm
    
    async def _create_from_scratch(self, config: Dict[str, Any]) -> vim.VirtualMachine:
        """Create a new VM from scratch"""
        vm_name = config.get("name")
        
        logger.info(f"Creating VM from scratch: {vm_name}")
        
        # VM configuration spec
        vm_config = vim.vm.ConfigSpec(
            name=vm_name,
            memoryMB=config.get("memory", 2048),
            numCPUs=config.get("cores", 2),
            guestId=self._get_guest_id(config.get("os_type")),
            files=vim.vm.FileInfo(
                vmPathName=f"[{self.default_datastore_name}]"
            )
        )
        
        # Add network adapter
        network = self._get_network(config.get("network", self.default_network_name))
        if network:
            vm_config.deviceChange = [self._create_network_spec(network)]
        
        # Add disk
        vm_config.deviceChange.extend(self._create_disk_spec(config.get("disk_size", 20)))
        
        # Create VM
        task = self.datacenter.vmFolder.CreateVM_Task(
            config=vm_config,
            pool=self.resource_pool
        )
        
        self._wait_for_task(task)
        
        vm = self._get_vm_by_name(vm_name)
        logger.info(f"VM created successfully: {vm_name}")
        
        return vm
    
    async def _reconfigure_vm(self, vm: vim.VirtualMachine, config: Dict[str, Any]) -> None:
        """Reconfigure VM (CPU, memory, etc.)"""
        spec = vim.vm.ConfigSpec()
        
        if config.get("cores"):
            spec.numCPUs = config["cores"]
        
        if config.get("memory"):
            spec.memoryMB = config["memory"]
        
        task = vm.Reconfigure(spec)
        self._wait_for_task(task)
        
        logger.info(f"VM {vm.name} reconfigured")
    
    async def _power_on_vm(self, vm: vim.VirtualMachine) -> None:
        """Power on a VM"""
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            return
        
        task = vm.PowerOn()
        self._wait_for_task(task)
        logger.info(f"VM {vm.name} powered on")
    
    def _get_datacenter(self) -> vim.Datacenter:
        """Get datacenter object"""
        for child in self.content.rootFolder.childEntity:
            if hasattr(child, 'vmFolder'):
                return child
        raise Exception("Datacenter not found")
    
    def _get_compute_resource(self) -> vim.ComputeResource:
        """Get compute resource (ESXi host)"""
        for child in self.datacenter.hostFolder.childEntity:
            if isinstance(child, vim.ComputeResource):
                return child
        raise Exception("Compute resource not found")
    
    def _get_vm_by_name(self, name: str) -> Optional[vim.VirtualMachine]:
        """Get VM by name"""
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder,
            [vim.VirtualMachine],
            True
        )
        
        for vm in container.view:
            if vm.name == name:
                container.Destroy()
                return vm
        
        container.Destroy()
        return None
    
    def _get_datastore(self, name: str) -> vim.Datastore:
        """Get datastore by name"""
        for datastore in self.compute_resource.datastore:
            if datastore.name == name:
                return datastore
        raise Exception(f"Datastore not found: {name}")
    
    def _get_network(self, name: str) -> Optional[vim.Network]:
        """Get network by name"""
        for network in self.compute_resource.network:
            if network.name == name:
                return network
        return None
    
    def _get_guest_id(self, os_type: Optional[str]) -> str:
        """Map OS type to ESXi guest ID"""
        os_map = {
            "ubuntu": "ubuntu64Guest",
            "kali": "debian10_64Guest",
            "windows": "windows9Server64Guest",
            "centos": "centos7_64Guest",
            "debian": "debian10_64Guest"
        }
        return os_map.get(os_type, "otherLinux64Guest")
    
    def _create_network_spec(self, network: vim.Network) -> vim.vm.device.VirtualDeviceSpec:
        """Create network adapter spec"""
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        spec.device = vim.vm.device.VirtualVmxnet3()
        spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        spec.device.backing.network = network
        spec.device.backing.deviceName = network.name
        spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        spec.device.connectable.startConnected = True
        spec.device.connectable.allowGuestControl = True
        return spec
    
    def _create_disk_spec(self, disk_size_gb: int) -> List[vim.vm.device.VirtualDeviceSpec]:
        """Create virtual disk spec"""
        specs = []
        
        # SCSI controller
        controller_spec = vim.vm.device.VirtualDeviceSpec()
        controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        controller_spec.device = vim.vm.device.ParaVirtualSCSIController()
        controller_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
        controller_spec.device.busNumber = 0
        specs.append(controller_spec)
        
        # Disk
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.capacityInKB = disk_size_gb * 1024 * 1024
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.controllerKey = 1000
        disk_spec.device.unitNumber = 0
        specs.append(disk_spec)
        
        return specs
    
    def _wait_for_task(self, task: vim.Task) -> None:
        """Wait for a vSphere task to complete"""
        while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            time.sleep(0.5)
        
        if task.info.state == vim.TaskInfo.State.error:
            raise Exception(f"Task failed: {task.info.error.msg}")


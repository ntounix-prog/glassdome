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
from pathlib import Path

from glassdome.platforms.base import PlatformClient, VMStatus
from glassdome.utils.windows_autounattend import generate_autounattend_xml, create_autounattend_iso

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
        self.password = password  # Store for HTTP API access
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
        - Windows VMs from ISO (if os_type="windows")
        - Cloning from template (if template_id provided)
        - Creating from scratch (Linux)
        - Custom hardware configuration
        - Network assignment
        """
        name = config.get("name", "glassdome-vm")
        os_type = config.get("os_type", "linux")
        
        logger.info(f"Creating {os_type} VM on ESXi: {name}")
        
        # Windows deployment from ISO
        if os_type == "windows":
            result = await self.create_windows_vm_from_iso(config)
            return result
        # Clone from template
        elif config.get("template_id"):
            vm = await self._clone_from_template(config)
        # Create from scratch
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
            
            # SAFETY CHECK: Only delete VMs with glassdome prefix
            if not vm.name.startswith("glassdome-"):
                logger.error(f"SAFETY: Refusing to delete VM '{vm.name}' - not a glassdome VM!")
                raise Exception(f"Safety check failed: VM name must start with 'glassdome-'")
            
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
        
        logger.debug(f"Template found: {template.name}, power state: {template.runtime.powerState}")
        
        # ESXi standalone doesn't support cloning like vCenter does
        # We'll use a simpler approach: Create a linked clone by copying the VM
        try:
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
            logger.debug(f"Starting clone task...")
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
            
        except Exception as e:
            logger.error(f"Clone failed, error: {str(e)}")
            # If cloning is not supported, fall back to manual VMDK copy
            if "not supported" in str(e).lower():
                logger.warning(f"Cloning not supported on standalone ESXi, using VMDK copy method instead")
                return await self._clone_via_vmdk_copy(template, vm_name, config)
            else:
                raise
    
    async def _clone_via_vmdk_copy(self, template: vim.VirtualMachine, vm_name: str, config: Dict[str, Any]) -> vim.VirtualMachine:
        """
        Clone a VM by copying its VMDK files (workaround for standalone ESXi)
        This is slower than vCenter cloning but works on standalone hosts
        """
        logger.info(f"Cloning via VMDK copy: {vm_name}")
        
        # Get template's disk
        template_disk = None
        for device in template.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualDisk):
                template_disk = device
                break
        
        if not template_disk:
            raise Exception(f"Template {template.name} has no disk!")
        
        template_vmdk_path = template_disk.backing.fileName
        logger.debug(f"Template VMDK: {template_vmdk_path}")
        
        # Create new VMDK path for cloned VM
        new_vmdk_path = f"[{self.default_datastore_name}] {vm_name}/{vm_name}.vmdk"
        
        # Copy VMDK with format conversion using VirtualDiskManager
        logger.info(f"Copying and converting VMDK from {template_vmdk_path} to {new_vmdk_path}...")
        
        try:
            disk_manager = self.content.virtualDiskManager
            
            # Create destSpec to convert to thin-provisioned eagerzeroedthick format
            dest_spec = vim.VirtualDiskManager.VirtualDiskSpec()
            dest_spec.diskType = vim.VirtualDiskManager.VirtualDiskType.thin  # Thin provisioned
            dest_spec.adapterType = vim.VirtualDiskManager.VirtualDiskAdapterType.lsiLogic
            
            logger.debug(f"Converting disk to thin format...")
            
            # Use CopyVirtualDisk_Task with format conversion
            task = disk_manager.CopyVirtualDisk_Task(
                sourceName=template_vmdk_path,
                sourceDatacenter=self.datacenter,
                destName=new_vmdk_path,
                destDatacenter=self.datacenter,
                destSpec=dest_spec,
                force=True
            )
            
            self._wait_for_task(task)
            logger.info(f"VMDK copied and converted successfully")
            
        except Exception as e:
            logger.error(f"Failed to copy VMDK: {str(e)}")
            # If copy fails completely, fall back to creating empty VM
            logger.warning(f"Falling back to creating empty VM (no OS installed)")
            return await self._create_from_scratch(config)
        
        # Create VM using the copied VMDK
        logger.info(f"Creating VM with copied VMDK...")
        
        vm_config_spec = vim.vm.ConfigSpec(
            name=vm_name,
            memoryMB=config.get("memory", template.config.hardware.memoryMB),
            numCPUs=config.get("cores", template.config.hardware.numCPU),
            guestId=template.config.guestId,
            files=vim.vm.FileInfo(
                vmPathName=f"[{self.default_datastore_name}] {vm_name}"
            )
        )
        
        # Add SCSI controller (same as template)
        scsi_controller = vim.vm.device.VirtualDeviceSpec()
        scsi_controller.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        scsi_controller.device = vim.vm.device.ParaVirtualSCSIController()
        scsi_controller.device.key = 1000
        scsi_controller.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
        scsi_controller.device.busNumber = 0
        
        # Attach the copied VMDK
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.fileName = new_vmdk_path
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.controllerKey = 1000
        disk_spec.device.unitNumber = 0
        
        # Add network adapter
        network = None
        for net in self.compute_resource.network:
            if net.name == config.get("network", self.default_network_name):
                network = net
                break
        
        device_changes = [scsi_controller, disk_spec]
        
        if network:
            network_spec = vim.vm.device.VirtualDeviceSpec()
            network_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            network_spec.device = vim.vm.device.VirtualVmxnet3()
            network_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            network_spec.device.backing.network = network
            network_spec.device.backing.deviceName = network.name
            network_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            network_spec.device.connectable.startConnected = True
            network_spec.device.connectable.allowGuestControl = True
            device_changes.append(network_spec)
        
        vm_config_spec.deviceChange = device_changes
        
        # Create the VM
        task = self.datacenter.vmFolder.CreateVM_Task(
            config=vm_config_spec,
            pool=self.resource_pool
        )
        
        self._wait_for_task(task)
        
        # Get the created VM
        vm = self._get_vm_by_name(vm_name)
        logger.info(f"VM created successfully from copied VMDK: {vm_name}")
        
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
        controller_spec.device.key = 1000  # Controller key
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
    
    async def create_windows_vm_from_iso(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Windows VM from ISO with autounattend
        
        Args:
            config: VM configuration
        
        Returns:
            Dict with vm_id and ip_address
        """
        from glassdome.core.config import settings
        from glassdome.utils.ip_pool import get_ip_pool_manager
        
        name = config.get("name", f"windows-vm-{int(time.time())}")
        windows_version = config.get("windows_version", "server2022")
        memory_mb = config.get("memory_mb", 4096)
        cores = config.get("cpu_cores", 2)
        disk_size_gb = config.get("disk_size_gb", 80)
        admin_password = config.get("admin_password", "Glassdome123!")
        network_cidr = config.get("network_cidr", "192.168.2.0/24")  # ESXi management network
        
        logger.info(f"Creating Windows VM {name} from ISO on ESXi")
        
        # Allocate static IP
        ip_manager = get_ip_pool_manager()
        ip_allocation = ip_manager.allocate_ip(network_cidr, name)
        
        if not ip_allocation:
            raise Exception(f"Failed to allocate IP from network {network_cidr}")
        
        static_ip = ip_allocation["ip"]
        gateway = ip_allocation["gateway"]
        netmask = ip_allocation["netmask"]
        dns_servers = ip_allocation["dns"]
        
        logger.info(f"Allocated IP {static_ip} to VM {name}")
        
        # Paths to ISOs (on ESXi datastore)
        windows_iso = f"[{self.default_datastore_name}] ISO/windows-server-2022-eval.iso"
        autounattend_iso = f"[{self.default_datastore_name}] ISO/autounattend-{name}.iso"
        
        # Generate autounattend.xml (no VirtIO for ESXi)
        autounattend_config = {
            "hostname": name,
            "admin_password": admin_password,
            "windows_version": windows_version,
            "enable_rdp": True,
            "virtio_drivers": False,  # ESXi uses VMware drivers, not VirtIO
            "static_ip": static_ip,
            "gateway": gateway,
            "netmask": netmask,
            "dns": dns_servers
        }
        autounattend_xml = generate_autounattend_xml(autounattend_config)
        
        # Create autounattend ISO locally
        glassdome_root = Path(settings.glassdome_root) if hasattr(settings, 'glassdome_root') else Path.cwd()
        autounattend_iso_path = glassdome_root / "isos" / "custom" / f"autounattend-{name}.iso"
        autounattend_iso_path.parent.mkdir(parents=True, exist_ok=True)
        create_autounattend_iso(autounattend_xml, autounattend_iso_path)
        
        logger.info(f"Created autounattend ISO: {autounattend_iso_path}")
        logger.info(f"NOTE: Upload to ESXi manually or via upload script")
        
        # Create VM config spec
        config_spec = vim.vm.ConfigSpec()
        config_spec.name = name
        config_spec.memoryMB = memory_mb
        config_spec.numCPUs = cores
        config_spec.guestId = "windows9Server64Guest"  # Windows Server 2016+
        config_spec.version = "vmx-14"  # ESXi 6.7+
        
        # Set firmware to EFI
        config_spec.firmware = "efi"
        
        # Files (VM location)
        config_spec.files = vim.vm.FileInfo()
        config_spec.files.vmPathName = f"[{self.default_datastore_name}] {name}/{name}.vmx"
        
        # Create device specs
        device_changes = []
        
        # SCSI controller
        scsi_spec = vim.vm.device.VirtualDeviceSpec()
        scsi_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        scsi_spec.device = vim.vm.device.ParaVirtualSCSIController()
        scsi_spec.device.key = 1000
        scsi_spec.device.busNumber = 0
        scsi_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
        device_changes.append(scsi_spec)
        
        # Disk
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.key = 2000
        disk_spec.device.controllerKey = 1000
        disk_spec.device.unitNumber = 0
        disk_spec.device.capacityInKB = disk_size_gb * 1024 * 1024
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.backing.fileName = f"[{self.default_datastore_name}] {name}/{name}.vmdk"
        disk_spec.device.backing.thinProvisioned = True
        device_changes.append(disk_spec)
        
        # Network
        network = self._get_network(self.default_network_name)
        if network:
            nic_spec = vim.vm.device.VirtualDeviceSpec()
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            nic_spec.device = vim.vm.device.VirtualVmxnet3()
            nic_spec.device.key = 4000
            nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            nic_spec.device.backing.network = network
            nic_spec.device.backing.deviceName = network.name
            nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nic_spec.device.connectable.startConnected = True
            nic_spec.device.connectable.allowGuestControl = True
            device_changes.append(nic_spec)
        
        # CD-ROM with Windows ISO
        cdrom_spec = vim.vm.device.VirtualDeviceSpec()
        cdrom_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        cdrom_spec.device = vim.vm.device.VirtualCdrom()
        cdrom_spec.device.key = 3000
        cdrom_spec.device.controllerKey = 200  # IDE controller
        cdrom_spec.device.unitNumber = 0
        cdrom_spec.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
        cdrom_spec.device.backing.fileName = windows_iso
        cdrom_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        cdrom_spec.device.connectable.startConnected = True
        cdrom_spec.device.connectable.allowGuestControl = True
        device_changes.append(cdrom_spec)
        
        # Second CD-ROM with autounattend ISO
        cdrom2_spec = vim.vm.device.VirtualDeviceSpec()
        cdrom2_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        cdrom2_spec.device = vim.vm.device.VirtualCdrom()
        cdrom2_spec.device.key = 3001
        cdrom2_spec.device.controllerKey = 200  # IDE controller
        cdrom2_spec.device.unitNumber = 1
        cdrom2_spec.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
        cdrom2_spec.device.backing.fileName = autounattend_iso
        cdrom2_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        cdrom2_spec.device.connectable.startConnected = True
        cdrom2_spec.device.connectable.allowGuestControl = True
        device_changes.append(cdrom2_spec)
        
        config_spec.deviceChange = device_changes
        
        # Create the VM
        logger.info(f"Creating VM {name} on ESXi...")
        task = self.datacenter.vmFolder.CreateVM_Task(
            config=config_spec,
            pool=self.resource_pool
        )
        
        self._wait_for_task(task)
        logger.info(f"VM {name} created")
        
        # Get the VM object
        vm = self._get_vm_by_name(name)
        
        # Power on
        logger.info(f"Starting Windows VM {name} (Windows will auto-install, ~15-20 minutes)")
        await self._power_on_vm(vm)
        
        logger.info(f"Windows VM {name} is installing. Check ESXi console for progress.")
        logger.info(f"After installation: RDP to {static_ip} with Administrator / {admin_password}")
        
        return {
            "vm_id": name,
            "ip_address": static_ip,
            "platform": "esxi",
            "status": "installing",
            "ansible_connection": {
                "host": static_ip,
                "user": "Administrator",
                "port": 3389
            },
            "platform_specific": {
                "esxi_host": self.host,
                "datastore": self.default_datastore_name,
                "vm_name": name,
                "vm_path": f"[{self.default_datastore_name}] {name}"
            },
            "notes": f"Windows is installing automatically. This takes 15-20 minutes. RDP: {static_ip}:3389, User: Administrator, Password: {admin_password}"
        }


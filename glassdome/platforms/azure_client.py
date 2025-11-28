"""
Platform client for Azure

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import ResourceNotFoundError
import asyncio
import time
from typing import Dict, Any, List, Optional
import logging

from glassdome.platforms.base import PlatformClient, VMStatus

logger = logging.getLogger(__name__)


class AzureClient(PlatformClient):
    """
    Azure Platform Client
    
    Implements the PlatformClient interface for Azure deployments.
    Supports dynamic region selection, auto image lookup, and cloud-init.
    """
    
    def __init__(self, subscription_id: str, tenant_id: str,
                 client_id: str, client_secret: str,
                 region: str = "eastus",
                 resource_group: Optional[str] = None):
        """
        Initialize Azure client
        
        Args:
            subscription_id: Azure subscription ID
            tenant_id: Azure AD tenant ID
            client_id: Service principal client ID
            client_secret: Service principal client secret
            region: Azure region (can deploy to 101 regions globally)
            resource_group: Resource group name (creates if doesn't exist)
        """
        self.subscription_id = subscription_id
        self.region = region
        self.resource_group_name = resource_group or "glassdome-rg"
        
        # Create credential
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Initialize management clients
        self.compute_client = ComputeManagementClient(
            self.credential,
            subscription_id
        )
        self.network_client = NetworkManagementClient(
            self.credential,
            subscription_id
        )
        self.resource_client = ResourceManagementClient(
            self.credential,
            subscription_id
        )
        
        # Auto-register required providers (one-time per subscription)
        self._ensure_providers_registered()
        
        logger.info(f"Azure client initialized for region {region}")
    
    # =========================================================================
    # CORE VM OPERATIONS (PlatformClient Interface)
    # =========================================================================
    
    async def create_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create and start an Azure VM (Linux or Windows)
        
        Args:
            config: VM configuration with keys:
                - name: VM name (required)
                - os_type: "linux" or "windows" (default: "linux")
                - os_version: Ubuntu version (default: "22.04") or windows_version
                - windows_version: "server2022" or "win11" (for Windows VMs)
                - cores: CPU cores (maps to VM size)
                - memory: RAM in MB (maps to VM size)
                - ssh_user: SSH username (default: "ubuntu")
                - vm_size: Override VM size (optional)
                - packages: List of packages to install
                - users: List of user accounts to create
        
        Returns:
            Dict with vm_id, ip_address, platform, status, ansible_connection
        """
        name = config.get("name", f"glassdome-vm-{int(time.time())}")
        os_type = config.get("os_type", "linux")
        os_version = config.get("os_version", "22.04")
        vm_size = config.get("vm_size") or self._map_vm_size(config, os_type)
        
        logger.info(f"Creating Azure VM: {name} ({os_type}, {vm_size}) in {self.region}")
        
        # 1. Ensure resource group exists
        await self._ensure_resource_group()
        
        # 2. Create/get network resources
        vnet_name, subnet_name, nsg_name = await self._ensure_network(name, os_type)
        
        # 3. Create public IP
        public_ip_name = f"{name}-ip"
        public_ip = await self._create_public_ip(public_ip_name)
        
        # 4. Create NIC
        nic_name = f"{name}-nic"
        nic = await self._create_nic(nic_name, subnet_name, vnet_name, public_ip_name, nsg_name)
        
        # 5. Get image reference
        if os_type == "windows":
            windows_version = config.get("windows_version", "server2022")
            image_ref = self._get_windows_image(windows_version)
        else:
            image_ref = self._get_ubuntu_image(os_version)
        
        # 6. Build user data
        if os_type == "windows":
            custom_data = self._build_windows_customdata(config)
        else:
            custom_data = self._build_cloud_init(config)
        
        # 7. Create VM
        try:
            logger.info(f"Creating VM {name}...")
            
            # Build OS profile based on OS type
            if os_type == "windows":
                os_profile = {
                    'computer_name': name[:15],  # Windows has 15 char limit
                    'admin_username': config.get('admin_user', 'glassdomeadmin'),  # Azure reserves 'Administrator'
                    'admin_password': config.get('admin_password', 'Glassdome123!'),
                    'custom_data': custom_data,
                    'windows_configuration': {
                        'enable_automatic_updates': False,
                        'provision_vm_agent': True
                    }
                }
            else:
                os_profile = {
                    'computer_name': name,
                    'admin_username': config.get('ssh_user', 'ubuntu'),
                    'admin_password': config.get('password', 'Glassdome123!'),  # Required by Azure
                    'custom_data': custom_data,
                    'linux_configuration': {
                        'disable_password_authentication': False,  # Allow password for simplicity
                    }
                }
            
            vm_params = {
                'location': self.region,
                'os_profile': os_profile,
                'hardware_profile': {
                    'vm_size': vm_size
                },
                'storage_profile': {
                    'image_reference': image_ref,
                    'os_disk': {
                        'create_option': 'FromImage',
                        'managed_disk': {
                            'storage_account_type': 'Standard_LRS'  # Cheapest
                        }
                    }
                },
                'network_profile': {
                    'network_interfaces': [{
                        'id': nic.id
                    }]
                },
                'tags': {
                    'Project': 'glassdome',
                    'ManagedBy': 'glassdome-platform'
                }
            }
            
            # Start VM creation (async operation)
            vm_operation = self.compute_client.virtual_machines.begin_create_or_update(
                self.resource_group_name,
                name,
                vm_params
            )
            
            # Wait for completion
            logger.info(f"Waiting for VM {name} to be created...")
            vm = vm_operation.result()
            
            logger.info(f"VM {name} created, waiting for IP...")
            
            # Get public IP
            ip_address = await self.get_vm_ip(name, timeout=120)
            
            logger.info(f"✅ Azure VM {name} created @ {ip_address}")
            
            return {
                "vm_id": name,  # Azure uses names as IDs
                "ip_address": ip_address,
                "platform": "azure",
                "status": VMStatus.RUNNING.value,
                "ansible_connection": {
                    "host": ip_address,
                    "user": config.get("ssh_user", "ubuntu"),
                    "ssh_key_path": config.get("ssh_key_path"),
                    "port": 22
                },
                "platform_specific": {
                    "region": self.region,
                    "resource_group": self.resource_group_name,
                    "vm_size": vm_size,
                    "image": f"Ubuntu {os_version}",
                    "nic_id": nic.id,
                    "public_ip_id": public_ip.id
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create VM: {e}")
            raise
    
    async def start_vm(self, vm_id: str) -> bool:
        """Start a stopped Azure VM"""
        try:
            operation = self.compute_client.virtual_machines.begin_start(
                self.resource_group_name,
                vm_id
            )
            operation.result()
            logger.info(f"Started VM {vm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start VM {vm_id}: {e}")
            return False
    
    async def stop_vm(self, vm_id: str, force: bool = False) -> bool:
        """Stop a running Azure VM"""
        try:
            if force:
                operation = self.compute_client.virtual_machines.begin_power_off(
                    self.resource_group_name,
                    vm_id
                )
            else:
                operation = self.compute_client.virtual_machines.begin_deallocate(
                    self.resource_group_name,
                    vm_id
                )
            operation.result()
            logger.info(f"Stopped VM {vm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop VM {vm_id}: {e}")
            return False
    
    async def delete_vm(self, vm_id: str) -> bool:
        """Delete an Azure VM"""
        try:
            operation = self.compute_client.virtual_machines.begin_delete(
                self.resource_group_name,
                vm_id
            )
            operation.result()
            logger.info(f"Deleted VM {vm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_id}: {e}")
            return False
    
    async def get_vm_status(self, vm_id: str) -> VMStatus:
        """Get Azure VM status"""
        try:
            instance_view = self.compute_client.virtual_machines.instance_view(
                self.resource_group_name,
                vm_id
            )
            
            if instance_view.statuses:
                for status in instance_view.statuses:
                    if status.code.startswith('PowerState/'):
                        state = status.code.split('/')[-1]
                        return self._standardize_vm_status(state)
            
            return VMStatus.UNKNOWN
        except Exception as e:
            logger.error(f"Failed to get VM status {vm_id}: {e}")
            return VMStatus.UNKNOWN
    
    async def get_vm_ip(self, vm_id: str, timeout: int = 120) -> Optional[str]:
        """
        Get Azure VM public IP address
        
        Waits up to timeout seconds for IP to be assigned
        """
        start_time = time.time()
        public_ip_name = f"{vm_id}-ip"
        
        while (time.time() - start_time) < timeout:
            try:
                public_ip = self.network_client.public_ip_addresses.get(
                    self.resource_group_name,
                    public_ip_name
                )
                
                if public_ip.ip_address:
                    return public_ip.ip_address
                
                # Wait and retry
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error getting IP for {vm_id}: {e}")
                await asyncio.sleep(2)
        
        logger.warning(f"Timeout waiting for IP address for {vm_id}")
        return None
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _ensure_providers_registered(self):
        """
        Ensure required Azure resource providers are registered
        This is a one-time operation per subscription
        """
        required_providers = ['Microsoft.Network', 'Microsoft.Compute']
        
        try:
            for provider_namespace in required_providers:
                try:
                    provider = self.resource_client.providers.get(provider_namespace)
                    
                    if provider.registration_state != 'Registered':
                        logger.info(f"Registering provider: {provider_namespace}")
                        self.resource_client.providers.register(provider_namespace)
                        logger.info(f"Provider {provider_namespace} registration initiated (may take 1-2 minutes)")
                    else:
                        logger.debug(f"Provider {provider_namespace} already registered")
                        
                except Exception as e:
                    logger.warning(f"Could not check/register provider {provider_namespace}: {e}")
        except Exception as e:
            logger.warning(f"Provider registration check failed (may need manual registration): {e}")
    
    def _map_vm_size(self, config: Dict[str, Any], os_type: str = "linux") -> str:
        """
        Map cores/memory to Azure VM size
        
        For Linux: B-series (burstable) - cheapest!
        For Windows: D-series (more resources needed)
        """
        cores = config.get("cores", 1)
        memory_mb = config.get("memory", 4096 if os_type == "windows" else 1024)
        
        if os_type == "windows":
            # Windows needs more resources
            # Minimum for Windows: 2 cores, 8GB RAM
            if cores <= 2 and memory_mb <= 8192:
                return "Standard_D2s_v3"  # 2 vCPU, 8 GB RAM
            elif cores <= 4:
                return "Standard_D4s_v3"  # 4 vCPU, 16 GB RAM
            else:
                return "Standard_D8s_v3"  # 8 vCPU, 32 GB RAM
        else:
            # Linux - B-series (burstable, cheapest)
            if cores == 1 and memory_mb <= 512:
                return "Standard_B1ls"  # $0.0052/hour - cheapest!
            elif cores == 1 and memory_mb <= 2048:
                return "Standard_B1s"  # $0.0104/hour
            elif cores == 1 and memory_mb <= 4096:
                return "Standard_B1ms"  # $0.0208/hour
            elif cores == 2:
                return "Standard_B2s"  # $0.0416/hour
            elif cores == 4:
                return "Standard_B4ms"  # $0.166/hour
        
        # Default
        return "Standard_B1s" if os_type == "linux" else "Standard_D2s_v3"
    
    def _get_ubuntu_image(self, version: str) -> Dict[str, str]:
        """
        Get Ubuntu image reference for Azure
        
        Args:
            version: Ubuntu version (e.g., "22.04")
        
        Returns:
            Image reference dict
        """
        # Canonical publisher
        publisher = "Canonical"
        
        if version == "22.04":
            offer = "0001-com-ubuntu-server-jammy"
            sku = "22_04-lts-gen2"
        elif version == "20.04":
            offer = "0001-com-ubuntu-server-focal"
            sku = "20_04-lts-gen2"
        else:
            # Default to 22.04
            offer = "0001-com-ubuntu-server-jammy"
            sku = "22_04-lts-gen2"
        
        return {
            'publisher': publisher,
            'offer': offer,
            'sku': sku,
            'version': 'latest'
        }
    
    def _get_windows_image(self, version: str) -> Dict[str, str]:
        """
        Get Windows image reference for Azure
        
        Args:
            version: Windows version ("server2022" or "win11")
        
        Returns:
            Image reference dict
        """
        # Microsoft Windows publisher
        publisher = "MicrosoftWindowsServer"
        
        if version == "server2022":
            offer = "WindowsServer"
            sku = "2022-datacenter-azure-edition"
        elif version == "win11":
            # Windows 11 Enterprise
            publisher = "MicrosoftWindowsDesktop"
            offer = "Windows-11"
            sku = "win11-22h2-ent"
        else:
            # Default to Server 2022
            offer = "WindowsServer"
            sku = "2022-datacenter-azure-edition"
        
        return {
            'publisher': publisher,
            'offer': offer,
            'sku': sku,
            'version': 'latest'
        }
    
    def _build_windows_customdata(self, config: Dict[str, Any]) -> str:
        """
        Build Windows custom data script (PowerShell)
        
        Args:
            config: VM configuration
        
        Returns:
            Base64-encoded PowerShell script
        """
        import base64
        
        name = config.get("name", "glassdome-vm")
        admin_password = config.get("admin_password", "Glassdome123!")
        
        # PowerShell script for Windows initialization
        script = f"""#ps1_sysnative
# Glassdome Windows Initialization

# Set hostname (already set by Azure, but log it)
$hostname = hostname
Write-Host "Hostname: $hostname"

# Enable RDP
Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# Disable Windows Firewall for cyber range (allow all traffic)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Create initialization log
$logMessage = "Glassdome Windows initialization completed at $(Get-Date)"
Add-Content -Path "C:\\glassdome-init.log" -Value $logMessage

Write-Host "Glassdome initialization complete"
"""
        
        # Azure expects base64-encoded custom data
        encoded = base64.b64encode(script.encode('utf-8')).decode('utf-8')
        return encoded
    
    async def _ensure_resource_group(self):
        """Ensure resource group exists"""
        try:
            self.resource_client.resource_groups.get(self.resource_group_name)
            logger.info(f"Using existing resource group: {self.resource_group_name}")
        except ResourceNotFoundError:
            logger.info(f"Creating resource group: {self.resource_group_name}")
            self.resource_client.resource_groups.create_or_update(
                self.resource_group_name,
                {
                    'location': self.region,
                    'tags': {
                        'Project': 'glassdome',
                        'ManagedBy': 'glassdome-platform'
                    }
                }
            )
    
    async def _ensure_network(self, vm_name: str, os_type: str = "linux") -> tuple:
        """
        Ensure virtual network, subnet, and NSG exist
        
        Args:
            vm_name: VM name
            os_type: "linux" or "windows" (adds RDP for Windows)
        
        Returns:
            (vnet_name, subnet_name, nsg_name)
        """
        vnet_name = f"glassdome-vnet-{self.region}"
        subnet_name = "default"
        nsg_name = f"glassdome-nsg-{self.region}"
        
        # Build security rules
        security_rules = [
            {
                'name': 'AllowSSH',
                'protocol': 'Tcp',
                'source_port_range': '*',
                'destination_port_range': '22',
                'source_address_prefix': '*',
                'destination_address_prefix': '*',
                'access': 'Allow',
                'priority': 300,
                'direction': 'Inbound'
            }
        ]
        
        # Add RDP rule for Windows
        if os_type == "windows":
            security_rules.append({
                'name': 'AllowRDP',
                'protocol': 'Tcp',
                'source_port_range': '*',
                'destination_port_range': '3389',
                'source_address_prefix': '*',
                'destination_address_prefix': '*',
                'access': 'Allow',
                'priority': 310,
                'direction': 'Inbound'
            })
        
        # Create/get NSG
        try:
            nsg = self.network_client.network_security_groups.get(
                self.resource_group_name,
                nsg_name
            )
            logger.info(f"Using existing NSG: {nsg_name}")
            
            # Ensure RDP rule exists if os_type is windows
            if os_type == "windows":
                await self._ensure_rdp_rule(nsg_name)
            
        except ResourceNotFoundError:
            logger.info(f"Creating NSG: {nsg_name}")
            nsg_params = {
                'location': self.region,
                'security_rules': security_rules
            }
            operation = self.network_client.network_security_groups.begin_create_or_update(
                self.resource_group_name,
                nsg_name,
                nsg_params
            )
            operation.result()
        
        # Create/get VNet
        try:
            self.network_client.virtual_networks.get(
                self.resource_group_name,
                vnet_name
            )
            logger.info(f"Using existing VNet: {vnet_name}")
        except ResourceNotFoundError:
            logger.info(f"Creating VNet: {vnet_name}")
            vnet_params = {
                'location': self.region,
                'address_space': {
                    'address_prefixes': ['10.0.0.0/16']
                },
                'subnets': [{
                    'name': subnet_name,
                    'address_prefix': '10.0.0.0/24'
                }]
            }
            operation = self.network_client.virtual_networks.begin_create_or_update(
                self.resource_group_name,
                vnet_name,
                vnet_params
            )
            operation.result()
        
        return (vnet_name, subnet_name, nsg_name)
    
    async def _ensure_rdp_rule(self, nsg_name: str):
        """Ensure RDP port 3389 is open in NSG"""
        try:
            # Get current NSG
            nsg = self.network_client.network_security_groups.get(
                self.resource_group_name,
                nsg_name
            )
            
            # Check if RDP rule already exists
            for rule in nsg.security_rules:
                if rule.destination_port_range == '3389':
                    logger.info(f"RDP rule already exists in NSG {nsg_name}")
                    return
            
            # Add RDP rule
            logger.info(f"Adding RDP rule to NSG {nsg_name}")
            rdp_rule = {
                'name': 'AllowRDP',
                'protocol': 'Tcp',
                'source_port_range': '*',
                'destination_port_range': '3389',
                'source_address_prefix': '*',
                'destination_address_prefix': '*',
                'access': 'Allow',
                'priority': 310,
                'direction': 'Inbound'
            }
            
            operation = self.network_client.security_rules.begin_create_or_update(
                self.resource_group_name,
                nsg_name,
                'AllowRDP',
                rdp_rule
            )
            operation.result()
            logger.info(f"RDP rule added to NSG {nsg_name}")
            
        except Exception as e:
            logger.warning(f"Failed to ensure RDP rule: {e}")
    
    async def _create_public_ip(self, ip_name: str):
        """Create public IP address"""
        logger.info(f"Creating public IP: {ip_name}")
        ip_params = {
            'location': self.region,
            'public_ip_allocation_method': 'Static',
            'sku': {'name': 'Standard'}
        }
        operation = self.network_client.public_ip_addresses.begin_create_or_update(
            self.resource_group_name,
            ip_name,
            ip_params
        )
        return operation.result()
    
    async def _create_nic(self, nic_name: str, subnet_name: str, vnet_name: str,
                         public_ip_name: str, nsg_name: str):
        """Create network interface"""
        logger.info(f"Creating NIC: {nic_name}")
        
        # Get subnet
        subnet = self.network_client.subnets.get(
            self.resource_group_name,
            vnet_name,
            subnet_name
        )
        
        # Get public IP
        public_ip = self.network_client.public_ip_addresses.get(
            self.resource_group_name,
            public_ip_name
        )
        
        # Get NSG
        nsg = self.network_client.network_security_groups.get(
            self.resource_group_name,
            nsg_name
        )
        
        nic_params = {
            'location': self.region,
            'ip_configurations': [{
                'name': 'ipconfig1',
                'subnet': {'id': subnet.id},
                'public_ip_address': {'id': public_ip.id}
            }],
            'network_security_group': {'id': nsg.id}
        }
        
        operation = self.network_client.network_interfaces.begin_create_or_update(
            self.resource_group_name,
            nic_name,
            nic_params
        )
        return operation.result()
    
    def _build_cloud_init(self, config: Dict[str, Any]) -> str:
        """
        Build cloud-init custom data (base64 encoded by Azure SDK)
        
        Args:
            config: VM configuration
        
        Returns:
            Cloud-init script
        """
        import base64
        
        name = config.get("name", "glassdome-vm")
        ssh_user = config.get("ssh_user", "ubuntu")
        password = config.get("password", "Glassdome123!")
        
        cloud_init = f"""#cloud-config
hostname: {name}
fqdn: {name}.local
manage_etc_hosts: true

users:
  - name: {ssh_user}
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    shell: /bin/bash

chpasswd:
  list: |
    {ssh_user}:{password}
  expire: false

ssh_pwauth: true
"""
        
        # Add packages if specified
        if config.get('packages'):
            cloud_init += "\npackages:\n"
            for pkg in config['packages']:
                cloud_init += f"  - {pkg}\n"
        
        cloud_init += """
runcmd:
  - echo "Cloud-init completed at $(date)" > /var/log/glassdome-init.log
"""
        
        # Base64 encode for Azure
        return base64.b64encode(cloud_init.encode()).decode()
    
    def _standardize_vm_status(self, azure_state: str) -> VMStatus:
        """
        Map Azure power state to VMStatus
        
        Azure states: running, stopped, deallocated, starting, stopping
        """
        state_map = {
            "running": VMStatus.RUNNING,
            "stopped": VMStatus.STOPPED,
            "deallocated": VMStatus.STOPPED,
            "starting": VMStatus.CREATING,
            "stopping": VMStatus.CREATING
        }
        return state_map.get(azure_state.lower(), VMStatus.UNKNOWN)
    
    # =========================================================================
    # PLATFORM INFO
    # =========================================================================
    
    async def test_connection(self) -> bool:
        """Test connection to Azure"""
        try:
            list(self.resource_client.resource_groups.list())
            logger.info("Successfully connected to Azure")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Azure: {str(e)}")
            return False
    
    async def get_platform_info(self) -> Dict[str, Any]:
        """Get Azure platform information"""
        return {
            "platform": "azure",
            "region": self.region,
            "resource_group": self.resource_group_name
        }
    
    def get_platform_name(self) -> str:
        """Get platform name"""
        return "azure"
    
    async def list_vms(self, resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all VMs in the subscription or a specific resource group
        
        Args:
            resource_group: Optional resource group name (defaults to glassdome-rg)
        
        Returns:
            List of VM dictionaries with name, power_state, location, size, etc.
        """
        vms = []
        rg = resource_group or self.resource_group_name
        
        try:
            # Get VMs from the resource group
            vm_list = self.compute_client.virtual_machines.list(rg)
            
            for vm in vm_list:
                try:
                    # Get power state from instance view
                    power_state = "unknown"
                    try:
                        instance_view = self.compute_client.virtual_machines.instance_view(rg, vm.name)
                        if instance_view.statuses:
                            for status in instance_view.statuses:
                                if status.code.startswith('PowerState/'):
                                    power_state = status.code.split('/')[-1]
                                    break
                    except Exception:
                        pass
                    
                    # Get public IP if available
                    ip_address = None
                    try:
                        public_ip_name = f"{vm.name}-ip"
                        public_ip = self.network_client.public_ip_addresses.get(rg, public_ip_name)
                        ip_address = public_ip.ip_address
                    except Exception:
                        pass
                    
                    vm_info = {
                        "id": vm.id,
                        "name": vm.name,
                        "power_state": power_state,
                        "location": vm.location,
                        "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else "Unknown",
                        "os_type": vm.storage_profile.os_disk.os_type if vm.storage_profile and vm.storage_profile.os_disk else "Unknown",
                        "ip_address": ip_address,
                        "resource_group": rg,
                        "tags": dict(vm.tags) if vm.tags else {}
                    }
                    vms.append(vm_info)
                    
                except Exception as e:
                    logger.warning(f"Error getting VM info for {vm.name}: {e}")
                    continue
            
            logger.info(f"Listed {len(vms)} VMs in Azure resource group {rg}")
            
        except Exception as e:
            logger.error(f"Failed to list Azure VMs: {e}")
        
        return vms
    
    async def list_all_vms(self) -> List[Dict[str, Any]]:
        """
        List all VMs across all resource groups in the subscription
        
        Returns:
            List of VM dictionaries
        """
        vms = []
        
        try:
            # Get all VMs in the subscription
            vm_list = self.compute_client.virtual_machines.list_all()
            
            for vm in vm_list:
                try:
                    # Extract resource group from VM ID
                    # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/...
                    parts = vm.id.split('/')
                    rg_index = parts.index('resourceGroups') + 1 if 'resourceGroups' in parts else -1
                    rg = parts[rg_index] if rg_index > 0 else "unknown"
                    
                    # Get power state
                    power_state = "unknown"
                    try:
                        instance_view = self.compute_client.virtual_machines.instance_view(rg, vm.name)
                        if instance_view.statuses:
                            for status in instance_view.statuses:
                                if status.code.startswith('PowerState/'):
                                    power_state = status.code.split('/')[-1]
                                    break
                    except Exception:
                        pass
                    
                    # Get public IP if available
                    ip_address = None
                    try:
                        public_ip_name = f"{vm.name}-ip"
                        public_ip = self.network_client.public_ip_addresses.get(rg, public_ip_name)
                        ip_address = public_ip.ip_address
                    except Exception:
                        pass
                    
                    vm_info = {
                        "id": vm.id,
                        "name": vm.name,
                        "power_state": power_state,
                        "location": vm.location,
                        "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else "Unknown",
                        "os_type": vm.storage_profile.os_disk.os_type if vm.storage_profile and vm.storage_profile.os_disk else "Unknown",
                        "ip_address": ip_address,
                        "resource_group": rg,
                        "tags": dict(vm.tags) if vm.tags else {}
                    }
                    vms.append(vm_info)
                    
                except Exception as e:
                    logger.warning(f"Error getting VM info: {e}")
                    continue
            
            logger.info(f"Listed {len(vms)} VMs across all Azure resource groups")
            
        except Exception as e:
            logger.error(f"Failed to list all Azure VMs: {e}")
        
        return vms
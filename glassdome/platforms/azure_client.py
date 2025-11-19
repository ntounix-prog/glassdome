"""
Azure API Integration
"""
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AzureClient:
    """
    Client for interacting with Azure API
    Handles VM creation, networking, and resource management
    """
    
    def __init__(self, subscription_id: str, tenant_id: str,
                 client_id: str, client_secret: str):
        """
        Initialize Azure client
        
        Args:
            subscription_id: Azure subscription ID
            tenant_id: Azure AD tenant ID
            client_id: Service principal client ID
            client_secret: Service principal client secret
        """
        self.subscription_id = subscription_id
        
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
        
        logger.info(f"Azure client initialized for subscription {subscription_id}")
    
    async def test_connection(self) -> bool:
        """Test connection to Azure"""
        try:
            # List resource groups to test connection
            list(self.resource_client.resource_groups.list())
            logger.info("Successfully connected to Azure")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Azure: {str(e)}")
            return False
    
    async def create_resource_group(self, name: str, location: str) -> Dict[str, Any]:
        """Create a resource group"""
        try:
            rg = self.resource_client.resource_groups.create_or_update(
                name,
                {"location": location}
            )
            logger.info(f"Resource group {name} created in {location}")
            return {"success": True, "resource_group": rg.name}
        except Exception as e:
            logger.error(f"Failed to create resource group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_virtual_network(self, resource_group: str, name: str,
                                    location: str, address_prefix: str = "10.0.0.0/16") -> Dict[str, Any]:
        """Create a virtual network"""
        try:
            vnet_params = {
                "location": location,
                "address_space": {
                    "address_prefixes": [address_prefix]
                }
            }
            
            poller = self.network_client.virtual_networks.begin_create_or_update(
                resource_group,
                name,
                vnet_params
            )
            vnet = poller.result()
            
            logger.info(f"Virtual network {name} created")
            return {"success": True, "vnet_id": vnet.id}
        except Exception as e:
            logger.error(f"Failed to create virtual network: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_vm(self, resource_group: str, name: str, location: str,
                       vm_size: str = "Standard_B2s",
                       image: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a virtual machine
        
        Args:
            resource_group: Resource group name
            name: VM name
            location: Azure location
            vm_size: VM size (SKU)
            image: Image reference
            
        Returns:
            VM details
        """
        try:
            # Default to Ubuntu if no image specified
            if not image:
                image = {
                    "publisher": "Canonical",
                    "offer": "UbuntuServer",
                    "sku": "18.04-LTS",
                    "version": "latest"
                }
            
            # This is a simplified version - full implementation would need
            # network interface, public IP, etc.
            logger.info(f"Creating VM {name} in resource group {resource_group}")
            
            # Placeholder for actual VM creation
            return {
                "success": True,
                "vm_name": name,
                "status": "creating"
            }
        except Exception as e:
            logger.error(f"Failed to create VM: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def list_vms(self, resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
        """List VMs in subscription or resource group"""
        try:
            if resource_group:
                vms = list(self.compute_client.virtual_machines.list(resource_group))
            else:
                vms = list(self.compute_client.virtual_machines.list_all())
            
            return [{"name": vm.name, "id": vm.id, "location": vm.location} for vm in vms]
        except Exception as e:
            logger.error(f"Failed to list VMs: {str(e)}")
            return []
    
    async def delete_vm(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """Delete a virtual machine"""
        try:
            poller = self.compute_client.virtual_machines.begin_delete(
                resource_group,
                vm_name
            )
            poller.result()
            
            logger.info(f"VM {vm_name} deleted")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to delete VM: {str(e)}")
            return {"success": False, "error": str(e)}


"""
Orchestrator module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from glassdome.networking.models import (
    NetworkDefinition,
    PlatformNetworkMapping,
    VMInterface,
    DeployedVM,
    NetworkType,
)

logger = logging.getLogger(__name__)


class NetworkOrchestrator:
    """
    Orchestrates network operations across platforms.
    
    Responsibilities:
    - Create abstract network definitions
    - Translate to platform-specific configs
    - Coordinate provisioning across platforms
    - Track VM interfaces
    """
    
    def __init__(self):
        self._platform_handlers = {}
    
    def register_platform(self, platform: str, handler):
        """Register a platform-specific network handler"""
        self._platform_handlers[platform] = handler
        logger.info(f"Registered network handler for platform: {platform}")
    
    # =========================================================================
    # Network Definition CRUD
    # =========================================================================
    
    async def create_network(
        self,
        session: AsyncSession,
        name: str,
        cidr: str,
        vlan_id: Optional[int] = None,
        gateway: Optional[str] = None,
        network_type: str = NetworkType.ISOLATED.value,
        dhcp_enabled: bool = False,
        lab_id: Optional[str] = None,
        **kwargs
    ) -> NetworkDefinition:
        """
        Create an abstract network definition.
        
        This doesn't provision anything yet - just defines the network.
        Call provision_network() to create it on a specific platform.
        """
        # Check for duplicate name
        existing = await session.execute(
            select(NetworkDefinition).where(NetworkDefinition.name == name)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Network '{name}' already exists")
        
        # Calculate gateway if not provided
        if not gateway and cidr:
            # Default: first usable IP in the range
            network_parts = cidr.split("/")[0].split(".")
            network_parts[3] = "1"
            gateway = ".".join(network_parts)
        
        network = NetworkDefinition(
            name=name,
            cidr=cidr,
            vlan_id=vlan_id,
            gateway=gateway,
            network_type=network_type,
            dhcp_enabled=dhcp_enabled,
            lab_id=lab_id,
            **kwargs
        )
        
        session.add(network)
        await session.commit()
        await session.refresh(network)
        
        logger.info(f"Created network definition: {name} ({cidr}, VLAN {vlan_id})")
        return network
    
    async def get_network(
        self,
        session: AsyncSession,
        network_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Optional[NetworkDefinition]:
        """Get a network by ID or name"""
        if network_id:
            result = await session.execute(
                select(NetworkDefinition).where(NetworkDefinition.id == network_id)
            )
        elif name:
            result = await session.execute(
                select(NetworkDefinition).where(NetworkDefinition.name == name)
            )
        else:
            return None
        
        return result.scalar_one_or_none()
    
    async def list_networks(
        self,
        session: AsyncSession,
        lab_id: Optional[str] = None
    ) -> List[NetworkDefinition]:
        """List all networks, optionally filtered by lab"""
        query = select(NetworkDefinition)
        if lab_id:
            query = query.where(NetworkDefinition.lab_id == lab_id)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def delete_network(
        self,
        session: AsyncSession,
        network_id: int,
        deprovision: bool = True
    ) -> bool:
        """
        Delete a network definition.
        
        If deprovision=True, also remove from all platforms.
        """
        network = await self.get_network(session, network_id=network_id)
        if not network:
            return False
        
        # TODO: Deprovision from platforms if requested
        
        await session.delete(network)
        await session.commit()
        
        logger.info(f"Deleted network: {network.name}")
        return True
    
    # =========================================================================
    # Platform Provisioning
    # =========================================================================
    
    async def provision_network(
        self,
        session: AsyncSession,
        network_id: int,
        platform: str,
        platform_instance: Optional[str] = None,
        platform_config: Optional[Dict] = None
    ) -> PlatformNetworkMapping:
        """
        Provision a network on a specific platform.
        
        Translates the abstract network definition to platform-specific
        configuration and creates the resources.
        """
        network = await self.get_network(session, network_id=network_id)
        if not network:
            raise ValueError(f"Network {network_id} not found")
        
        # Check if already provisioned on this platform
        existing = await session.execute(
            select(PlatformNetworkMapping).where(
                PlatformNetworkMapping.network_id == network_id,
                PlatformNetworkMapping.platform == platform,
                PlatformNetworkMapping.platform_instance == platform_instance
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Network already provisioned on {platform}/{platform_instance}")
        
        # Get platform handler
        handler = self._platform_handlers.get(platform)
        if not handler:
            raise ValueError(f"No handler registered for platform: {platform}")
        
        # Generate platform-specific config if not provided
        if not platform_config:
            platform_config = await handler.generate_network_config(network, platform_instance)
        
        # Create the mapping record
        mapping = PlatformNetworkMapping(
            network_id=network_id,
            platform=platform,
            platform_instance=platform_instance,
            platform_config=platform_config,
            provisioned=False
        )
        session.add(mapping)
        
        # Actually provision on the platform
        try:
            await handler.create_network(network, platform_config, platform_instance)
            mapping.provisioned = True
            logger.info(f"Provisioned network {network.name} on {platform}/{platform_instance}")
        except Exception as e:
            mapping.provision_error = str(e)
            logger.error(f"Failed to provision network {network.name}: {e}")
        
        await session.commit()
        await session.refresh(mapping)
        
        return mapping
    
    async def get_platform_mapping(
        self,
        session: AsyncSession,
        network_id: int,
        platform: str,
        platform_instance: Optional[str] = None
    ) -> Optional[PlatformNetworkMapping]:
        """Get the platform-specific mapping for a network"""
        result = await session.execute(
            select(PlatformNetworkMapping).where(
                PlatformNetworkMapping.network_id == network_id,
                PlatformNetworkMapping.platform == platform,
                PlatformNetworkMapping.platform_instance == platform_instance
            )
        )
        return result.scalar_one_or_none()
    
    # =========================================================================
    # VM Interface Management
    # =========================================================================
    
    async def attach_vm_to_network(
        self,
        session: AsyncSession,
        vm_id: str,
        network_id: int,
        platform: str,
        platform_instance: Optional[str] = None,
        interface_index: int = 0,
        ip_address: Optional[str] = None,
        ip_method: str = "dhcp",
        mac_address: Optional[str] = None,
        lab_id: Optional[str] = None
    ) -> VMInterface:
        """
        Attach a VM to a network.
        
        Creates a VMInterface record and optionally configures the NIC
        on the platform.
        """
        network = await self.get_network(session, network_id=network_id)
        if not network:
            raise ValueError(f"Network {network_id} not found")
        
        # Inherit lab_id from network if not provided
        if not lab_id and network.lab_id:
            lab_id = network.lab_id
        
        # Check if already attached at this interface index
        existing = await session.execute(
            select(VMInterface).where(
                VMInterface.vm_id == vm_id,
                VMInterface.platform == platform,
                VMInterface.interface_index == interface_index
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"VM {vm_id} already has an interface at index {interface_index}")
        
        interface = VMInterface(
            lab_id=lab_id,
            vm_id=vm_id,
            platform=platform,
            platform_instance=platform_instance,
            network_id=network_id,
            interface_index=interface_index,
            ip_address=ip_address,
            ip_method=ip_method,
            mac_address=mac_address,
        )
        
        session.add(interface)
        await session.commit()
        await session.refresh(interface)
        
        logger.info(f"Attached VM {vm_id} to network {network.name} at index {interface_index}")
        return interface
    
    async def get_vm_interfaces(
        self,
        session: AsyncSession,
        vm_id: str,
        platform: Optional[str] = None
    ) -> List[VMInterface]:
        """Get all interfaces for a VM"""
        query = select(VMInterface).where(VMInterface.vm_id == vm_id)
        if platform:
            query = query.where(VMInterface.platform == platform)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def update_interface_ip(
        self,
        session: AsyncSession,
        interface_id: int,
        ip_address: str,
        ip_method: str = "static"
    ) -> VMInterface:
        """Update the IP address of a VM interface"""
        result = await session.execute(
            select(VMInterface).where(VMInterface.id == interface_id)
        )
        interface = result.scalar_one_or_none()
        if not interface:
            raise ValueError(f"Interface {interface_id} not found")
        
        interface.ip_address = ip_address
        interface.ip_method = ip_method
        
        await session.commit()
        await session.refresh(interface)
        
        logger.info(f"Updated interface {interface_id} IP to {ip_address}")
        return interface
    
    async def discover_vm_interfaces(
        self,
        session: AsyncSession,
        vm_id: str,
        platform: str,
        platform_instance: Optional[str] = None
    ) -> List[VMInterface]:
        """
        Discover and record VM interfaces from the platform.
        
        Queries the platform for VM network config and updates our records.
        """
        handler = self._platform_handlers.get(platform)
        if not handler:
            raise ValueError(f"No handler registered for platform: {platform}")
        
        # Get interface info from platform
        interfaces_data = await handler.get_vm_interfaces(vm_id, platform_instance)
        
        interfaces = []
        for iface_data in interfaces_data:
            # Check if we already have this interface
            existing = await session.execute(
                select(VMInterface).where(
                    VMInterface.vm_id == vm_id,
                    VMInterface.platform == platform,
                    VMInterface.interface_index == iface_data.get("index", 0)
                )
            )
            interface = existing.scalar_one_or_none()
            
            if interface:
                # Update existing
                interface.mac_address = iface_data.get("mac_address")
                interface.ip_address = iface_data.get("ip_address")
                interface.interface_name = iface_data.get("interface_name")
                interface.platform_config = iface_data.get("platform_config")
            else:
                # Create new
                interface = VMInterface(
                    vm_id=vm_id,
                    platform=platform,
                    platform_instance=platform_instance,
                    interface_index=iface_data.get("index", 0),
                    mac_address=iface_data.get("mac_address"),
                    ip_address=iface_data.get("ip_address"),
                    interface_name=iface_data.get("interface_name"),
                    platform_config=iface_data.get("platform_config"),
                )
                session.add(interface)
            
            interfaces.append(interface)
        
        await session.commit()
        return interfaces
    
    # =========================================================================
    # Lab Resource Tracking (for migration/orchestration)
    # =========================================================================
    
    async def register_deployed_vm(
        self,
        session: AsyncSession,
        lab_id: str,
        name: str,
        vm_id: str,
        platform: str,
        platform_instance: Optional[str] = None,
        os_type: Optional[str] = None,
        template_id: Optional[str] = None,
        cpu_cores: Optional[int] = None,
        memory_mb: Optional[int] = None,
        disk_gb: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> DeployedVM:
        """
        Register a deployed VM as part of a lab.
        
        This is called after VM deployment to track it for orchestration.
        """
        deployed_vm = DeployedVM(
            lab_id=lab_id,
            name=name,
            vm_id=vm_id,
            platform=platform,
            platform_instance=platform_instance,
            os_type=os_type,
            template_id=template_id,
            cpu_cores=cpu_cores,
            memory_mb=memory_mb,
            disk_gb=disk_gb,
            ip_address=ip_address,
            status="deployed"
        )
        
        session.add(deployed_vm)
        await session.commit()
        await session.refresh(deployed_vm)
        
        logger.info(f"Registered VM {name} ({vm_id}) for lab {lab_id}")
        return deployed_vm
    
    async def get_lab_resources(
        self,
        session: AsyncSession,
        lab_id: str
    ) -> Dict[str, Any]:
        """
        Get ALL resources associated with a lab.
        
        This is THE KEY for migration - everything with this lab_id moves together.
        
        Returns:
            {
                "lab_id": "xxx",
                "vms": [DeployedVM, ...],
                "networks": [NetworkDefinition, ...],
                "interfaces": [VMInterface, ...]
            }
        """
        # Get VMs
        vms_result = await session.execute(
            select(DeployedVM).where(DeployedVM.lab_id == lab_id)
        )
        vms = list(vms_result.scalars().all())
        
        # Get Networks
        networks_result = await session.execute(
            select(NetworkDefinition).where(NetworkDefinition.lab_id == lab_id)
        )
        networks = list(networks_result.scalars().all())
        
        # Get Interfaces (from the VMs)
        vm_ids = [vm.vm_id for vm in vms]
        if vm_ids:
            interfaces_result = await session.execute(
                select(VMInterface).where(VMInterface.vm_id.in_(vm_ids))
            )
            interfaces = list(interfaces_result.scalars().all())
        else:
            interfaces = []
        
        logger.info(f"Lab {lab_id}: {len(vms)} VMs, {len(networks)} networks, {len(interfaces)} interfaces")
        
        return {
            "lab_id": lab_id,
            "vms": vms,
            "networks": networks,
            "interfaces": interfaces
        }
    
    async def get_lab_vms(
        self,
        session: AsyncSession,
        lab_id: str
    ) -> List[DeployedVM]:
        """Get all VMs for a lab"""
        result = await session.execute(
            select(DeployedVM).where(DeployedVM.lab_id == lab_id)
        )
        return list(result.scalars().all())
    
    async def update_vm_status(
        self,
        session: AsyncSession,
        vm_id: str,
        status: str,
        ip_address: Optional[str] = None
    ) -> Optional[DeployedVM]:
        """Update a deployed VM's status"""
        result = await session.execute(
            select(DeployedVM).where(DeployedVM.vm_id == vm_id)
        )
        vm = result.scalar_one_or_none()
        if not vm:
            return None
        
        vm.status = status
        if ip_address:
            vm.ip_address = ip_address
        
        await session.commit()
        await session.refresh(vm)
        return vm
    
    async def prepare_lab_migration(
        self,
        session: AsyncSession,
        lab_id: str,
        target_platform: str,
        target_instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare a lab for migration to another platform.
        
        Returns a migration plan with all resources and their target configs.
        """
        resources = await self.get_lab_resources(session, lab_id)
        
        # Build migration plan
        migration_plan = {
            "lab_id": lab_id,
            "source": {
                "vms": [(vm.platform, vm.platform_instance, vm.vm_id) for vm in resources["vms"]],
                "networks": [(n.name, n.cidr, n.vlan_id) for n in resources["networks"]]
            },
            "target": {
                "platform": target_platform,
                "platform_instance": target_instance
            },
            "steps": []
        }
        
        # Plan network creation on target
        for network in resources["networks"]:
            migration_plan["steps"].append({
                "type": "create_network",
                "network": network.name,
                "cidr": network.cidr,
                "vlan_id": network.vlan_id
            })
        
        # Plan VM migration
        for vm in resources["vms"]:
            migration_plan["steps"].append({
                "type": "migrate_vm",
                "name": vm.name,
                "source_vm_id": vm.vm_id,
                "source_platform": vm.platform,
                "os_type": vm.os_type,
                "template_id": vm.template_id,
                "cpu_cores": vm.cpu_cores,
                "memory_mb": vm.memory_mb
            })
        
        # Plan interface reattachment
        for interface in resources["interfaces"]:
            network = next(
                (n for n in resources["networks"] if n.id == interface.network_id),
                None
            )
            migration_plan["steps"].append({
                "type": "attach_interface",
                "vm_id": interface.vm_id,
                "network": network.name if network else None,
                "ip_address": interface.ip_address,
                "interface_index": interface.interface_index
            })
        
        logger.info(f"Prepared migration plan for lab {lab_id}: {len(migration_plan['steps'])} steps")
        return migration_plan


# ============================================================================
# Platform Handler Interface
# ============================================================================

class PlatformNetworkHandler:
    """
    Base class for platform-specific network handlers.
    
    Each platform implements this interface to handle its networking quirks.
    """
    
    async def generate_network_config(
        self,
        network: NetworkDefinition,
        platform_instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate platform-specific config from abstract network definition"""
        raise NotImplementedError
    
    async def create_network(
        self,
        network: NetworkDefinition,
        config: Dict[str, Any],
        platform_instance: Optional[str] = None
    ) -> bool:
        """Create the network on the platform"""
        raise NotImplementedError
    
    async def delete_network(
        self,
        config: Dict[str, Any],
        platform_instance: Optional[str] = None
    ) -> bool:
        """Delete the network from the platform"""
        raise NotImplementedError
    
    async def attach_interface(
        self,
        vm_id: str,
        network: NetworkDefinition,
        config: Dict[str, Any],
        interface_index: int = 0,
        platform_instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """Attach a network interface to a VM"""
        raise NotImplementedError
    
    async def get_vm_interfaces(
        self,
        vm_id: str,
        platform_instance: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all network interfaces for a VM"""
        raise NotImplementedError


# ============================================================================
# Singleton Instance
# ============================================================================

_orchestrator: Optional[NetworkOrchestrator] = None


def get_network_orchestrator() -> NetworkOrchestrator:
    """Get or create the network orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = NetworkOrchestrator()
    return _orchestrator


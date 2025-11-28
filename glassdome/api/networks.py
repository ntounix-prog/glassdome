"""
API endpoints for networks

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.core.database import get_db
from glassdome.networking.models import NetworkType
from glassdome.networking.orchestrator import get_network_orchestrator
from glassdome.networking.proxmox_handler import get_proxmox_network_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/networks", tags=["networks"])


# ============================================================================
# Pydantic Models
# ============================================================================

class NetworkCreate(BaseModel):
    name: str
    cidr: str
    vlan_id: Optional[int] = None
    gateway: Optional[str] = None
    network_type: str = NetworkType.ISOLATED.value
    dhcp_enabled: bool = False
    dhcp_range_start: Optional[str] = None
    dhcp_range_end: Optional[str] = None
    dns_servers: Optional[List[str]] = None
    lab_id: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None


class NetworkProvision(BaseModel):
    platform: str
    platform_instance: Optional[str] = None
    platform_config: Optional[dict] = None


class VMAttach(BaseModel):
    vm_id: str
    network_id: int
    platform: str
    platform_instance: Optional[str] = None
    interface_index: int = 0
    ip_address: Optional[str] = None
    ip_method: str = "dhcp"


class IPConfig(BaseModel):
    ip_address: str
    gateway: Optional[str] = None
    dns_servers: Optional[List[str]] = None


# ============================================================================
# Initialize Orchestrator
# ============================================================================

def _init_orchestrator():
    """Initialize the network orchestrator with platform handlers"""
    orchestrator = get_network_orchestrator()
    
    # Register Proxmox handler
    proxmox_handler = get_proxmox_network_handler()
    orchestrator.register_platform("proxmox", proxmox_handler)
    
    # TODO: Register other platform handlers
    # orchestrator.register_platform("esxi", get_esxi_network_handler())
    # orchestrator.register_platform("aws", get_aws_network_handler())
    
    return orchestrator


# ============================================================================
# Network CRUD Endpoints
# ============================================================================

@router.get("")
async def list_networks(
    lab_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """List all network definitions"""
    orchestrator = _init_orchestrator()
    networks = await orchestrator.list_networks(session, lab_id=lab_id)
    
    return {
        "networks": [n.to_dict() for n in networks],
        "total": len(networks)
    }


@router.post("")
async def create_network(
    network: NetworkCreate,
    session: AsyncSession = Depends(get_db)
):
    """Create a new network definition"""
    orchestrator = _init_orchestrator()
    
    try:
        result = await orchestrator.create_network(
            session,
            name=network.name,
            cidr=network.cidr,
            vlan_id=network.vlan_id,
            gateway=network.gateway,
            network_type=network.network_type,
            dhcp_enabled=network.dhcp_enabled,
            lab_id=network.lab_id,
            display_name=network.display_name,
            description=network.description,
            dhcp_range_start=network.dhcp_range_start,
            dhcp_range_end=network.dhcp_range_end,
            dns_servers=network.dns_servers,
        )
        
        return {
            "success": True,
            "network": result.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{network_id}")
async def get_network(
    network_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get a network by ID"""
    orchestrator = _init_orchestrator()
    network = await orchestrator.get_network(session, network_id=network_id)
    
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    return network.to_dict()


@router.delete("/{network_id}")
async def delete_network(
    network_id: int,
    deprovision: bool = True,
    session: AsyncSession = Depends(get_db)
):
    """Delete a network definition"""
    orchestrator = _init_orchestrator()
    
    success = await orchestrator.delete_network(session, network_id, deprovision=deprovision)
    
    if not success:
        raise HTTPException(status_code=404, detail="Network not found")
    
    return {"success": True, "message": f"Network {network_id} deleted"}


# ============================================================================
# Platform Provisioning Endpoints
# ============================================================================

@router.post("/{network_id}/provision")
async def provision_network(
    network_id: int,
    provision: NetworkProvision,
    session: AsyncSession = Depends(get_db)
):
    """Provision a network on a specific platform"""
    orchestrator = _init_orchestrator()
    
    try:
        mapping = await orchestrator.provision_network(
            session,
            network_id=network_id,
            platform=provision.platform,
            platform_instance=provision.platform_instance,
            platform_config=provision.platform_config
        )
        
        return {
            "success": mapping.provisioned,
            "mapping": mapping.to_dict(),
            "error": mapping.provision_error
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{network_id}/mappings")
async def get_network_mappings(
    network_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get all platform mappings for a network"""
    from sqlalchemy import select
    from glassdome.networking.models import PlatformNetworkMapping
    
    result = await session.execute(
        select(PlatformNetworkMapping).where(
            PlatformNetworkMapping.network_id == network_id
        )
    )
    mappings = result.scalars().all()
    
    return {
        "network_id": network_id,
        "mappings": [m.to_dict() for m in mappings]
    }


# ============================================================================
# VM Interface Endpoints
# ============================================================================

@router.post("/attach")
async def attach_vm_to_network(
    attach: VMAttach,
    session: AsyncSession = Depends(get_db)
):
    """Attach a VM to a network"""
    orchestrator = _init_orchestrator()
    
    try:
        interface = await orchestrator.attach_vm_to_network(
            session,
            vm_id=attach.vm_id,
            network_id=attach.network_id,
            platform=attach.platform,
            platform_instance=attach.platform_instance,
            interface_index=attach.interface_index,
            ip_address=attach.ip_address,
            ip_method=attach.ip_method
        )
        
        return {
            "success": True,
            "interface": interface.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vm/{vm_id}/interfaces")
async def get_vm_interfaces(
    vm_id: str,
    platform: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Get all interfaces for a VM"""
    orchestrator = _init_orchestrator()
    interfaces = await orchestrator.get_vm_interfaces(session, vm_id=vm_id, platform=platform)
    
    return {
        "vm_id": vm_id,
        "interfaces": [i.to_dict() for i in interfaces]
    }


@router.post("/vm/{vm_id}/discover")
async def discover_vm_interfaces(
    vm_id: str,
    platform: str,
    platform_instance: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Discover and record VM interfaces from the platform"""
    orchestrator = _init_orchestrator()
    
    try:
        interfaces = await orchestrator.discover_vm_interfaces(
            session,
            vm_id=vm_id,
            platform=platform,
            platform_instance=platform_instance
        )
        
        return {
            "vm_id": vm_id,
            "discovered": len(interfaces),
            "interfaces": [i.to_dict() for i in interfaces]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/interface/{interface_id}/ip")
async def update_interface_ip(
    interface_id: int,
    config: IPConfig,
    session: AsyncSession = Depends(get_db)
):
    """Update the IP address of a VM interface"""
    orchestrator = _init_orchestrator()
    
    try:
        interface = await orchestrator.update_interface_ip(
            session,
            interface_id=interface_id,
            ip_address=config.ip_address,
            ip_method="static"
        )
        
        return {
            "success": True,
            "interface": interface.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Proxmox-Specific Endpoints
# ============================================================================

@router.post("/proxmox/{vm_id}/configure-ip")
async def configure_proxmox_vm_ip(
    vm_id: str,
    interface_index: int,
    config: IPConfig,
    platform_instance: str = "02"
):
    """Configure IP address on a Proxmox VM via cloud-init"""
    handler = get_proxmox_network_handler()
    
    success = await handler.configure_vm_ip(
        vm_id=vm_id,
        interface_index=interface_index,
        ip_address=config.ip_address,
        gateway=config.gateway,
        dns_servers=config.dns_servers,
        platform_instance=platform_instance
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to configure IP")
    
    return {
        "success": True,
        "vm_id": vm_id,
        "interface_index": interface_index,
        "ip_address": config.ip_address
    }


@router.get("/proxmox/{vm_id}/interfaces")
async def get_proxmox_vm_interfaces(
    vm_id: str,
    platform_instance: str = "02"
):
    """Get network interfaces for a Proxmox VM"""
    handler = get_proxmox_network_handler()
    
    interfaces = await handler.get_vm_interfaces(
        vm_id=vm_id,
        platform_instance=platform_instance
    )
    
    return {
        "vm_id": vm_id,
        "platform": "proxmox",
        "platform_instance": platform_instance,
        "interfaces": interfaces
    }


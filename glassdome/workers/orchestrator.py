"""
Celery worker for orchestrator

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from celery import group, chord
from .celery_app import celery_app

logger = logging.getLogger(__name__)


# ============================================================================
# Synchronous Helper Functions (avoid Celery .get() issues)
# ============================================================================

def _allocate_network_sync(lab_id: str) -> Dict[str, Any]:
    """Synchronously allocate a network for a lab"""
    return asyncio.run(_allocate_network_async(lab_id))


def _deploy_vm_sync(
    lab_id: str,
    vm_node: Dict[str, Any],
    vm_index: int,
    network_config: Optional[Dict[str, Any]],
    platform_id: str
) -> Dict[str, Any]:
    """Synchronously deploy a VM"""
    return asyncio.run(_deploy_vm_async(
        lab_id=lab_id,
        vm_node=vm_node,
        vm_index=vm_index,
        network_config=network_config,
        platform_id=platform_id
    ))


async def _allocate_network_async(lab_id: str) -> Dict[str, Any]:
    """Async network allocation logic"""
    from glassdome.core.database import AsyncSessionLocal
    from glassdome.networking.models import NetworkDefinition
    from sqlalchemy import select, func
    
    async with AsyncSessionLocal() as session:
        # Find next available VLAN in range 100-170
        result = await session.execute(
            select(func.max(NetworkDefinition.vlan_id)).where(
                NetworkDefinition.vlan_id >= 100,
                NetworkDefinition.vlan_id <= 170
            )
        )
        max_vlan = result.scalar() or 99
        vlan_id = min(max_vlan + 1, 170)
        
        if vlan_id > 170:
            return {"success": False, "error": "No VLANs available"}
        
        # Create network record
        network = NetworkDefinition(
            name=f"lab-{lab_id[:8]}-net",
            cidr=f"192.168.{vlan_id}.0/24",
            vlan_id=vlan_id,
            gateway=f"192.168.{vlan_id}.1",
            network_type="isolated",
            lab_id=lab_id
        )
        session.add(network)
        await session.commit()
        
        return {
            "success": True,
            "vlan_id": vlan_id,
            "cidr": f"192.168.{vlan_id}.0/24",
            "gateway": f"192.168.{vlan_id}.1",
            "bridge": f"vmbr{vlan_id}",
            "network_id": network.id
        }


# ============================================================================
# Lab Deployment Tasks
# ============================================================================

@celery_app.task(bind=True, name="orchestrator.deploy_lab")
def deploy_lab(self, lab_id: str, lab_data: Dict[str, Any], platform_id: str = "1") -> Dict[str, Any]:
    """
    Deploy a complete lab - dispatches parallel VM deployments.
    
    This is the main entry point called by the API.
    It fans out to deploy_vm tasks that run in parallel.
    """
    logger.info(f"[{self.request.id}] Deploying lab {lab_id}")
    
    nodes = lab_data.get("nodes", [])
    vm_nodes = [n for n in nodes if n.get("type") == "vm" or n.get("data", {}).get("nodeType") == "vm"]
    network_nodes = [n for n in nodes if n.get("type") == "network" or n.get("data", {}).get("nodeType") == "network"]
    
    if not vm_nodes:
        return {"success": False, "error": "No VMs to deploy", "lab_id": lab_id}
    
    logger.info(f"Lab {lab_id}: {len(vm_nodes)} VMs, {len(network_nodes)} networks")
    
    # Step 1: Allocate VLAN (call directly, not as subtask)
    network_config = None
    if network_nodes:
        network_config = _allocate_network_sync(lab_id)
        if not network_config.get("success"):
            return {"success": False, "error": "Failed to allocate network", "lab_id": lab_id}
        logger.info(f"Allocated VLAN {network_config.get('vlan_id')} for lab {lab_id}")
    
    # Step 2: Deploy all VMs SEQUENTIALLY for now (parallel has .get() issues in Celery)
    # TODO: Refactor to use callbacks instead of .get()
    deployed_vms = []
    errors = []
    
    for idx, vm_node in enumerate(vm_nodes):
        try:
            result = _deploy_vm_sync(
                lab_id=lab_id,
                vm_node=vm_node.get("data", vm_node),
                vm_index=idx,
                network_config=network_config,
                platform_id=platform_id
            )
            if result.get("success"):
                deployed_vms.append(result)
            else:
                errors.append(result.get("error", "Unknown error"))
        except Exception as e:
            logger.error(f"VM deploy error: {e}")
            errors.append(str(e))
    
    # Step 3: Start WhitePawn monitoring (async, don't wait)
    if deployed_vms:
        start_whitepawn_monitoring.delay(lab_id, [vm.get("vm_id") for vm in deployed_vms])
    
    return {
        "success": len(errors) == 0,
        "lab_id": lab_id,
        "deployment_id": f"deploy-{lab_id[:12]}-{datetime.utcnow().strftime('%H%M%S')}",
        "vms_deployed": len(deployed_vms),
        "vms_failed": len(errors),
        "deployed_vms": deployed_vms,
        "errors": errors,
        "network": network_config
    }


@celery_app.task(bind=True, name="orchestrator.deploy_vm")
def deploy_vm(
    self,
    lab_id: str,
    vm_node: Dict[str, Any],
    vm_index: int,
    network_config: Optional[Dict[str, Any]],
    platform_id: str
) -> Dict[str, Any]:
    """
    Deploy a single VM. Runs in parallel with other VM deployments.
    
    Each worker can deploy one VM at a time, but multiple workers
    can deploy multiple VMs simultaneously.
    """
    worker_id = os.getenv("WORKER_ID", "worker")
    element_id = vm_node.get("elementId", "ubuntu")
    node_id = vm_node.get("id", f"node_{vm_index}")
    
    logger.info(f"[{worker_id}] Deploying VM {element_id} for lab {lab_id}")
    
    try:
        # Run the async deployment in a new event loop
        result = asyncio.run(_deploy_vm_async(
            lab_id=lab_id,
            vm_node=vm_node,
            vm_index=vm_index,
            network_config=network_config,
            platform_id=platform_id
        ))
        
        logger.info(f"[{worker_id}] VM deployed: {result.get('vm_id')}")
        return result
        
    except Exception as e:
        logger.error(f"[{worker_id}] VM deployment failed: {e}")
        return {
            "success": False,
            "node_id": node_id,
            "error": str(e)
        }


async def _deploy_vm_async(
    lab_id: str,
    vm_node: Dict[str, Any],
    vm_index: int,
    network_config: Optional[Dict[str, Any]],
    platform_id: str
) -> Dict[str, Any]:
    """Async implementation of VM deployment"""
    from glassdome.core.config import Settings
    from glassdome.platforms.proxmox_client import ProxmoxClient
    from glassdome.reaper.hot_spare import get_hot_spare_pool
    from glassdome.core.database import AsyncSessionLocal
    
    settings = Settings()
    element_id = vm_node.get("elementId", "ubuntu")
    node_id = vm_node.get("id", f"node_{vm_index}")
    
    # Template and spec mappings
    TEMPLATE_MAPPING = {
        "ubuntu": 9000, "kali": 9001, "dvwa": 9000,
        "metasploitable": 9002, "windows": 9010, "pfsense": 9020
    }
    OS_TYPE_MAPPING = {
        "ubuntu": "ubuntu", "kali": "kali", "dvwa": "ubuntu",
        "metasploitable": "ubuntu", "windows": "windows", "pfsense": "pfsense"
    }
    
    os_type = OS_TYPE_MAPPING.get(element_id, "ubuntu")
    vm_name = f"lab-{lab_id[:8]}-{element_id}-{node_id[-4:]}"
    
    async with AsyncSessionLocal() as session:
        # Try hot spare pool first
        pool = get_hot_spare_pool()
        acquired_spare = await pool.acquire_spare(session, os_type=os_type, mission_id=lab_id)
        
        if acquired_spare:
            vm_id = str(acquired_spare.vmid)
            ip_address = acquired_spare.ip_address
            node_name = acquired_spare.node
            
            # Get Proxmox client
            pve_config = settings.get_proxmox_config(acquired_spare.platform_instance)
            client = ProxmoxClient(
                host=pve_config["host"],
                user=pve_config["user"],
                password=pve_config.get("password"),
                token_name=pve_config.get("token_name"),
                token_value=pve_config.get("token_value"),
                verify_ssl=pve_config.get("verify_ssl", False),
                default_node=node_name
            )
            
            # Rename VM
            await client.configure_vm(node_name, int(vm_id), {"name": vm_name})
            
            # Configure network if provided
            lab_ip = None
            if network_config:
                bridge = network_config.get("bridge")
                gateway = network_config.get("gateway")
                vlan_id = network_config.get("vlan_id")
                
                if bridge and vlan_id:
                    # Calculate IP: .1 for pfSense, .10+ for others
                    if element_id == "pfsense":
                        lab_ip = gateway
                        ipconfig0 = f"ip={lab_ip}/24"
                    else:
                        lab_ip = f"192.168.{vlan_id}.{10 + vm_index}"
                        ipconfig0 = f"ip={lab_ip}/24,gw={gateway}"
                    
                    # Configure net0 for isolated network
                    await client.configure_vm(node_name, int(vm_id), {
                        "net0": f"virtio,bridge={bridge}",
                        "ipconfig0": ipconfig0
                    })
            
            return {
                "success": True,
                "node_id": node_id,
                "name": vm_name,
                "vm_id": vm_id,
                "ip_address": ip_address,
                "lab_ip": lab_ip,
                "status": "running"
            }
        else:
            # No hot spare - would need to clone from template
            return {
                "success": False,
                "node_id": node_id,
                "error": "No hot spare available"
            }


@celery_app.task(bind=True, name="orchestrator.allocate_lab_network")
def allocate_lab_network(self, lab_id: str) -> Dict[str, Any]:
    """Allocate a VLAN from the pool for a new lab"""
    return asyncio.run(_allocate_network_async(lab_id))


async def _allocate_network_async(lab_id: str) -> Dict[str, Any]:
    """Async VLAN allocation"""
    from glassdome.core.database import AsyncSessionLocal
    from glassdome.networking.models import NetworkDefinition
    from sqlalchemy import select
    
    VLAN_POOL_START = 100
    VLAN_POOL_END = 170
    
    async with AsyncSessionLocal() as session:
        # Get used VLANs
        result = await session.execute(
            select(NetworkDefinition.vlan_id).where(NetworkDefinition.vlan_id.isnot(None))
        )
        used_vlans = {row[0] for row in result.fetchall() if row[0] is not None}
        
        # Find next available
        vlan_id = None
        for v in range(VLAN_POOL_START, VLAN_POOL_END + 1):
            if v not in used_vlans:
                vlan_id = v
                break
        
        if vlan_id is None:
            return {"success": False, "error": "No VLANs available"}
        
        # Create network definition
        net_def = NetworkDefinition(
            name=f"lab-{lab_id[:8]}-net",
            display_name="Lab Network",
            cidr=f"192.168.{vlan_id}.0/24",
            vlan_id=vlan_id,
            gateway=f"192.168.{vlan_id}.1",
            network_type="isolated",
            lab_id=lab_id
        )
        session.add(net_def)
        await session.commit()
        
        return {
            "success": True,
            "vlan_id": vlan_id,
            "cidr": f"192.168.{vlan_id}.0/24",
            "gateway": f"192.168.{vlan_id}.1",
            "bridge": f"vmbr{vlan_id}"
        }


@celery_app.task(bind=True, name="orchestrator.start_whitepawn_monitoring")
def start_whitepawn_monitoring(self, lab_id: str, vm_ids: List[str]) -> Dict[str, Any]:
    """Start WhitePawn monitoring for a deployed lab"""
    logger.info(f"Starting WhitePawn monitoring for lab {lab_id} with {len(vm_ids)} VMs")
    # This will be picked up by a WhitePawn worker
    return {"success": True, "lab_id": lab_id, "vm_count": len(vm_ids)}


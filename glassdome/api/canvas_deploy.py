"""
Canvas Lab Deployment API

Handles deployment of labs designed on the visual canvas.
- Auto-assigns VLAN from pool (100-170)
- Creates isolated bridge vmbr{vlan} on Proxmox
- Configures VMs with net0 on the lab network
- Uses hot spare pool (fast) or falls back to build agents (slower)
"""

import asyncio
import logging
import ipaddress
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.core.database import get_db
from glassdome.core.config import settings
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.networking.models import NetworkDefinition, DeployedVM, VMInterface
from glassdome.networking.orchestrator import get_network_orchestrator
from glassdome.whitepawn.orchestrator import get_whitepawn_orchestrator, auto_deploy_whitepawn
from glassdome.reaper.hot_spare import get_hot_spare_pool
from glassdome.api.reaper import deploy_mission_vm  # Reuse existing VM deployment logic
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])


# ============================================================================
# VLAN Allocation (100-170)
# ============================================================================

# Track allocated VLANs in memory (will be persisted via NetworkDefinition)
VLAN_POOL_START = 100
VLAN_POOL_END = 170
_allocated_vlans: Set[int] = set()


async def get_allocated_vlans(session: AsyncSession) -> Set[int]:
    """Get all VLANs currently in use from database"""
    result = await session.execute(
        select(NetworkDefinition.vlan_id).where(NetworkDefinition.vlan_id.isnot(None))
    )
    return {row[0] for row in result.fetchall() if row[0] is not None}


async def allocate_vlan(session: AsyncSession) -> int:
    """Allocate the next available VLAN from the pool (100-170)"""
    used_vlans = await get_allocated_vlans(session)
    
    for vlan in range(VLAN_POOL_START, VLAN_POOL_END + 1):
        if vlan not in used_vlans:
            logger.info(f"Allocated VLAN {vlan}")
            return vlan
    
    raise ValueError(f"No VLANs available in pool {VLAN_POOL_START}-{VLAN_POOL_END}")


def derive_network_config(vlan_id: int) -> Dict[str, Any]:
    """Derive all network config from VLAN ID using convention:
    VLAN X -> CIDR 192.168.X.0/24, Gateway 192.168.X.1, Bridge vmbrX
    """
    return {
        "vlan_id": vlan_id,
        "cidr": f"192.168.{vlan_id}.0/24",
        "gateway": f"192.168.{vlan_id}.1",
        "bridge": f"vmbr{vlan_id}",
        "network": ipaddress.ip_network(f"192.168.{vlan_id}.0/24")
    }


async def create_lab_bridge(client: ProxmoxClient, node: str, vlan_id: int) -> bool:
    """Create an isolated bridge for the lab on Proxmox"""
    bridge_name = f"vmbr{vlan_id}"
    
    try:
        # Check if bridge already exists
        result = await client.create_network(node, {
            "iface": bridge_name,
            "type": "bridge",
            "bridge_ports": "none",  # Isolated - no physical port
            "bridge_stp": "off",
            "bridge_fd": "0",
            "autostart": 1,
            "comments": f"Glassdome Lab Network VLAN {vlan_id}"
        })
        logger.info(f"Created bridge {bridge_name} on {node}")
        return True
    except Exception as e:
        # Bridge might already exist
        if "already exists" in str(e).lower():
            logger.info(f"Bridge {bridge_name} already exists on {node}")
            return True
        logger.error(f"Failed to create bridge {bridge_name}: {e}")
        return False


# ============================================================================
# Pydantic Models
# ============================================================================

class CanvasNode(BaseModel):
    id: str
    type: str  # 'vm' or 'network'
    elementId: str  # 'ubuntu', 'kali', 'isolated', etc.
    elementType: Optional[str] = None
    os: Optional[str] = None
    networkConfig: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, float]] = None


class CanvasEdge(BaseModel):
    source: str
    target: str


class CanvasLabData(BaseModel):
    nodes: List[CanvasNode]
    edges: List[CanvasEdge]


class CanvasDeployRequest(BaseModel):
    lab_id: str
    platform_id: str  # "1" = Proxmox, "2" = AWS
    lab_data: CanvasLabData


class DeployedVMInfo(BaseModel):
    node_id: str
    name: str
    vm_id: str
    ip_address: Optional[str] = None
    status: str


class CanvasDeployResponse(BaseModel):
    success: bool
    deployment_id: str
    lab_id: str
    status: str
    message: str
    vms: List[DeployedVMInfo]
    errors: List[str]


# ============================================================================
# Template Mapping
# ============================================================================

# Map canvas element IDs to Proxmox template IDs
TEMPLATE_MAPPING = {
    "ubuntu": 9000,      # Ubuntu 22.04
    "kali": 9001,        # Kali Linux (if exists)
    "dvwa": 9000,        # DVWA runs on Ubuntu
    "metasploitable": 9002,  # Metasploitable
    "windows": 9010,     # Windows Server
    "pfsense": 9020,     # pfSense Firewall (needs template created)
}

# Default VM specs per element type
VM_SPECS = {
    "ubuntu": {"cores": 2, "memory": 2048, "disk": 20},
    "kali": {"cores": 2, "memory": 4096, "disk": 40},
    "dvwa": {"cores": 1, "memory": 1024, "disk": 10},
    "metasploitable": {"cores": 1, "memory": 1024, "disk": 20},
    "windows": {"cores": 2, "memory": 4096, "disk": 40},
    "pfsense": {"cores": 1, "memory": 1024, "disk": 8},  # pfSense is lightweight
}

# Map canvas element IDs to OS types for hot spare pool
OS_TYPE_MAPPING = {
    "ubuntu": "ubuntu",
    "kali": "kali",
    "dvwa": "ubuntu",  # DVWA runs on Ubuntu
    "metasploitable": "ubuntu",
    "windows": "windows",
    "pfsense": "pfsense",  # Separate pool for pfSense (no hot spares yet)
}


# ============================================================================
# Deployment Logic
# ============================================================================

async def deploy_vm_from_canvas(
    node: CanvasNode,
    lab_id: str,
    network_config: Optional[Dict] = None,
    session: AsyncSession = None,
    vm_index: int = 0
) -> Dict[str, Any]:
    """
    Deploy a single VM from canvas node definition.
    
    Strategy:
    1. Try hot spare pool first (instant deployment)
    2. Fall back to build agent / clone (slower but reliable)
    3. Add secondary NIC for isolated lab network with VLAN tag
    4. Configure static IP on the lab network interface
    """
    
    element_id = node.elementId
    template_id = TEMPLATE_MAPPING.get(element_id, 9000)  # Default to Ubuntu
    specs = VM_SPECS.get(element_id, {"cores": 2, "memory": 2048, "disk": 20})
    os_type = OS_TYPE_MAPPING.get(element_id, "ubuntu")
    
    # Generate VM name
    vm_name = f"lab-{lab_id[:8]}-{element_id}-{node.id[-4:]}"
    
    logger.info(f"Deploying VM: {vm_name} (element: {element_id}, os: {os_type})")
    if network_config:
        logger.info(f"  Network config: VLAN {network_config.get('vlan_id')}, CIDR {network_config.get('cidr')}")
    
    vm_id = None
    ip_address = None  # Management IP
    lab_ip = None      # Lab network IP
    client = None
    node_name = "pve02"
    
    try:
        # Strategy 1: Try hot spare pool (instant!)
        pool = get_hot_spare_pool()
        acquired_spare = await pool.acquire_spare(session, os_type=os_type, mission_id=lab_id)
        
        if acquired_spare:
            logger.info(f"⚡ Hot spare acquired: {acquired_spare.name} (VMID {acquired_spare.vmid})")
            vm_id = str(acquired_spare.vmid)
            ip_address = acquired_spare.ip_address
            node_name = acquired_spare.node
            
            # Get Proxmox client for configuration
            pve_config = settings.get_proxmox_config(acquired_spare.platform_instance)
            client = ProxmoxClient(
                host=pve_config["host"],
                user=pve_config["user"],
                password=pve_config.get("password"),
                token_name=pve_config.get("token_name"),
                token_value=pve_config.get("token_value"),
                verify_ssl=pve_config.get("verify_ssl", False),
                default_node=acquired_spare.node
            )
            
            # Rename the spare to match the lab
            try:
                logger.info(f"Renaming VM {acquired_spare.vmid} from '{acquired_spare.name}' to '{vm_name}'")
                result = await client.configure_vm(
                    acquired_spare.node,
                    acquired_spare.vmid,
                    {"name": vm_name}
                )
                if result.get("success"):
                    logger.info(f"✓ Renamed VM {acquired_spare.vmid} to '{vm_name}'")
                    # Update the spare record with the new name
                    acquired_spare.name = vm_name
                    await session.commit()
                else:
                    logger.error(f"✗ Rename failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"✗ Exception renaming VM: {e}")
        
        else:
            # Strategy 2: Fall back to build agent / clone
            logger.info(f"No hot spares available, using build agent for {vm_name}")
            
            vm_config = {
                "name": vm_name,
                "template_id": template_id,
                "cores": specs["cores"],
                "memory": specs["memory"],
                "os_type": "linux" if os_type != "windows" else "windows",
                "proxmox_instance": "02",  # Use pve02 which has working template
            }
            
            # Use the same deployment logic as Reaper
            result = await deploy_mission_vm("proxmox", vm_config)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "node_id": node.id,
                    "error": result.get("error", "Failed to deploy VM")
                }
            
            vm_id = result.get("vm_id")
            ip_address = result.get("ip_address")
            
            # Get client for network configuration
            pve_config = settings.get_proxmox_config("02")
            client = ProxmoxClient(
                host=pve_config["host"],
                user=pve_config["user"],
                password=pve_config.get("password"),
                token_name=pve_config.get("token_name"),
                token_value=pve_config.get("token_value"),
                verify_ssl=pve_config.get("verify_ssl", False),
                default_node=node_name
            )
        
        # ====================================================================
        # Configure primary NIC (net0) for isolated lab network
        # VMs get ONLY the lab network - no management interface
        # pfSense gets .1 (gateway), other VMs get .10, .11, .12...
        # ====================================================================
        if network_config and client and vm_id:
            bridge = network_config.get("bridge")  # vmbr{vlan}
            network_obj = network_config.get("network")  # ipaddress network object
            gateway = network_config.get("gateway")
            
            if bridge and network_obj:
                prefix_len = network_obj.prefixlen
                
                # pfSense gets the gateway IP (.1), other VMs get .10+
                if element_id == "pfsense":
                    lab_ip = gateway  # pfSense IS the gateway
                    # pfSense doesn't need a gateway - it IS the gateway
                    ipconfig0 = f"ip={lab_ip}/{prefix_len}"
                    logger.info(f"🛡️ pfSense configured as gateway: {lab_ip}")
                else:
                    # Regular VMs start at .10
                    lab_ip = str(list(network_obj.hosts())[9 + vm_index])
                    ipconfig0 = f"ip={lab_ip}/{prefix_len},gw={gateway}"
                
                logger.info(f"Configuring net0 on {bridge}: IP {lab_ip}/{prefix_len}")
                
                try:
                    # Configure net0 to use the lab bridge (isolated network)
                    net0_config = f"virtio,bridge={bridge}"
                    
                    await client.configure_vm(
                        node_name,
                        int(vm_id),
                        {"net0": net0_config}
                    )
                    logger.info(f"Set net0 to bridge {bridge}")
                    
                    await client.configure_vm(
                        node_name,
                        int(vm_id),
                        {"ipconfig0": ipconfig0}
                    )
                    logger.info(f"Configured ipconfig0: {ipconfig0}")
                    
                except Exception as e:
                    logger.error(f"Failed to configure lab network: {e}")
                    # Don't fail the whole deployment, just log the error
        
        logger.info(f"VM deployed: {vm_name} (VMID {vm_id}, Mgmt IP {ip_address}, Lab IP {lab_ip})")
        
        # Register in DeployedVM table
        if session and vm_id:
            orchestrator = get_network_orchestrator()
            await orchestrator.register_deployed_vm(
                session=session,
                lab_id=lab_id,
                name=vm_name,
                vm_id=vm_id,
                platform="proxmox",
                platform_instance="02",
                os_type=os_type,
                template_id=str(template_id),
                cpu_cores=specs["cores"],
                memory_mb=specs["memory"],
                disk_gb=specs["disk"],
                ip_address=ip_address  # Management IP for SSH access
            )
            
            # Also register the lab network interface
            if lab_ip and network_config:
                try:
                    from glassdome.networking.models import VMInterface
                    vm_interface = VMInterface(
                        vm_id=vm_id,
                        network_id=None,  # Could link to NetworkDefinition if we had the ID
                        lab_id=lab_id,
                        interface_name="net1",
                        mac_address=None,  # Will be auto-assigned by Proxmox
                        ip_address=lab_ip,
                        ip_source="static"
                    )
                    session.add(vm_interface)
                    await session.commit()
                    logger.info(f"Registered lab interface: {lab_ip}")
                except Exception as e:
                    logger.warning(f"Could not register lab interface: {e}")
        
        return {
            "success": True,
            "node_id": node.id,
            "name": vm_name,
            "vm_id": vm_id,
            "ip_address": ip_address,
            "lab_ip": lab_ip,
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Failed to deploy VM {vm_name}: {e}")
        return {
            "success": False,
            "node_id": node.id,
            "error": str(e)
        }


async def deploy_canvas_lab(
    request: CanvasDeployRequest,
    session: AsyncSession
) -> CanvasDeployResponse:
    """
    Deploy a complete lab from canvas definition.
    
    Auto-assigns VLAN from pool (100-170), creates isolated bridge,
    configures all VMs on that network with static IPs.
    """
    
    lab_id = request.lab_id
    platform_id = request.platform_id
    nodes = request.lab_data.nodes
    edges = request.lab_data.edges
    
    # Only Proxmox supported for now
    if platform_id != "1":
        return CanvasDeployResponse(
            success=False,
            deployment_id="",
            lab_id=lab_id,
            status="failed",
            message="Only Proxmox deployment is currently supported",
            vms=[],
            errors=["Platform not supported"]
        )
    
    deployment_id = f"deploy-{lab_id[:12]}-{datetime.utcnow().strftime('%H%M%S')}"
    
    # Separate VMs and networks
    vm_nodes = [n for n in nodes if n.type == "vm"]
    network_nodes = [n for n in nodes if n.type == "network"]
    
    if not vm_nodes:
        return CanvasDeployResponse(
            success=False,
            deployment_id=deployment_id,
            lab_id=lab_id,
            status="failed",
            message="No VMs to deploy",
            vms=[],
            errors=["No VM nodes found in canvas"]
        )
    
    logger.info(f"Deploying lab {lab_id}: {len(vm_nodes)} VMs, {len(network_nodes)} networks")
    
    # ========================================================================
    # Auto-assign VLAN and create isolated network
    # ========================================================================
    network_config = None
    
    if network_nodes:
        # Lab has a network - allocate VLAN and create bridge
        try:
            vlan_id = await allocate_vlan(session)
            network_config = derive_network_config(vlan_id)
            
            logger.info(f"Lab {lab_id} assigned VLAN {vlan_id}: {network_config['cidr']}, bridge {network_config['bridge']}")
            
            # Get Proxmox client to create bridge
            pve_config = settings.get_proxmox_config("02")
            client = ProxmoxClient(
                host=pve_config["host"],
                user=pve_config["user"],
                password=pve_config.get("password"),
                token_name=pve_config.get("token_name"),
                token_value=pve_config.get("token_value"),
                verify_ssl=pve_config.get("verify_ssl", False),
                default_node="pve02"
            )
            
            # Create the isolated bridge
            await create_lab_bridge(client, "pve02", vlan_id)
            
            # Save network definition to database
            net_def = NetworkDefinition(
                name=f"lab-{lab_id[:8]}-net",
                display_name=f"Lab Network",
                cidr=network_config["cidr"],
                vlan_id=vlan_id,
                gateway=network_config["gateway"],
                network_type="isolated",
                lab_id=lab_id
            )
            session.add(net_def)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to setup lab network: {e}")
            return CanvasDeployResponse(
                success=False,
                deployment_id=deployment_id,
                lab_id=lab_id,
                status="failed",
                message=f"Failed to setup network: {e}",
                vms=[],
                errors=[str(e)]
            )
    
    # Deploy each VM (uses hot spares first, falls back to build agent)
    # pfSense gets deployed FIRST as it's the gateway
    deployed_vms: List[DeployedVMInfo] = []
    errors: List[str] = []
    
    # Sort VMs: pfSense first (it's the gateway), then others
    pfsense_nodes = [n for n in vm_nodes if n.elementId == "pfsense"]
    other_nodes = [n for n in vm_nodes if n.elementId != "pfsense"]
    sorted_vm_nodes = pfsense_nodes + other_nodes
    
    for vm_index, vm_node in enumerate(sorted_vm_nodes):
        result = await deploy_vm_from_canvas(
            node=vm_node,
            lab_id=lab_id,
            network_config=network_config,  # Same network for all VMs in lab
            session=session,
            vm_index=vm_index
        )
        
        if result["success"]:
            deployed_vms.append(DeployedVMInfo(
                node_id=result["node_id"],
                name=result["name"],
                vm_id=result["vm_id"],
                ip_address=result.get("ip_address"),
                status=result.get("status", "running")
            ))
        else:
            errors.append(f"{vm_node.elementId}: {result.get('error', 'Unknown error')}")
    
    # Auto-deploy WhitePawn for monitoring
    if deployed_vms:
        try:
            await auto_deploy_whitepawn(lab_id, f"Canvas Lab {lab_id[:8]}")
            logger.info(f"WhitePawn monitoring deployed for lab {lab_id}")
        except Exception as e:
            logger.warning(f"Failed to deploy WhitePawn: {e}")
    
    success = len(deployed_vms) > 0
    status = "completed" if success and not errors else "partial" if deployed_vms else "failed"
    
    return CanvasDeployResponse(
        success=success,
        deployment_id=deployment_id,
        lab_id=lab_id,
        status=status,
        message=f"Deployed {len(deployed_vms)}/{len(vm_nodes)} VMs" + (f" with {len(errors)} errors" if errors else ""),
        vms=deployed_vms,
        errors=errors
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=CanvasDeployResponse)
async def deploy_from_canvas(
    request: CanvasDeployRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """
    Deploy a lab designed on the canvas.
    
    Creates VMs on Proxmox, configures networking, and starts WhitePawn monitoring.
    """
    logger.info(f"Canvas deployment request: lab={request.lab_id}, platform={request.platform_id}")
    
    # For now, deploy synchronously (could be background task for large labs)
    result = await deploy_canvas_lab(request, session)
    
    return result


@router.get("")
async def list_deployments(session: AsyncSession = Depends(get_db)):
    """List all canvas lab deployments"""
    result = await session.execute(
        select(DeployedVM).order_by(DeployedVM.created_at.desc())
    )
    vms = result.scalars().all()
    
    # Group by lab_id
    labs: Dict[str, List[Dict]] = {}
    for vm in vms:
        if vm.lab_id not in labs:
            labs[vm.lab_id] = []
        labs[vm.lab_id].append(vm.to_dict())
    
    return {
        "deployments": [
            {
                "lab_id": lab_id,
                "vms": vm_list,
                "vm_count": len(vm_list)
            }
            for lab_id, vm_list in labs.items()
        ],
        "total": len(labs)
    }


@router.get("/{lab_id}")
async def get_deployment(lab_id: str, session: AsyncSession = Depends(get_db)):
    """Get deployment details for a specific lab"""
    result = await session.execute(
        select(DeployedVM).where(DeployedVM.lab_id == lab_id)
    )
    vms = result.scalars().all()
    
    if not vms:
        raise HTTPException(status_code=404, detail=f"No deployment found for lab {lab_id}")
    
    return {
        "lab_id": lab_id,
        "vms": [vm.to_dict() for vm in vms],
        "vm_count": len(vms)
    }


@router.delete("/{lab_id}")
async def destroy_deployment(lab_id: str, session: AsyncSession = Depends(get_db)):
    """Destroy all VMs in a lab deployment"""
    result = await session.execute(
        select(DeployedVM).where(DeployedVM.lab_id == lab_id)
    )
    vms = result.scalars().all()
    
    if not vms:
        raise HTTPException(status_code=404, detail=f"No deployment found for lab {lab_id}")
    
    # Get Proxmox client
    client = await get_proxmox_client("02")
    
    destroyed = []
    errors = []
    
    for vm in vms:
        try:
            # Stop and delete VM
            await client.stop_vm(int(vm.vm_id), force=True)
            await asyncio.sleep(2)
            await client.delete_vm(int(vm.vm_id))
            
            vm.status = "deleted"
            destroyed.append(vm.vm_id)
            
        except Exception as e:
            errors.append(f"{vm.name}: {e}")
    
    await session.commit()
    
    # Stop WhitePawn monitoring
    try:
        orchestrator = get_whitepawn_orchestrator()
        await orchestrator.stop_for_lab(lab_id)
    except:
        pass
    
    return {
        "success": len(errors) == 0,
        "destroyed": destroyed,
        "errors": errors
    }


"""
API endpoints for canvas_deploy

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
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
from glassdome.registry.core import get_registry
from glassdome.registry.models import Resource, ResourceType, ResourceState
from glassdome.api.reaper import deploy_mission_vm
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])

# Semaphore to limit concurrent Proxmox API calls (prevent overwhelming the API)
_proxmox_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent VM operations


# ============================================================================
# VLAN Allocation (100-170)
# ============================================================================

VLAN_POOL_START = 100
VLAN_POOL_END = 170


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
    """
    Derive all network config from VLAN ID:
    VLAN X -> CIDR 10.X.0.0/24, Gateway 10.X.0.1, DHCP range 10.X.0.10-254
    
    Using 10.X.0.0/24 to avoid conflicts with management 192.168.x.x networks
    """
    return {
        "vlan_id": vlan_id,
        "cidr": f"10.{vlan_id}.0.0/24",
        "gateway": f"10.{vlan_id}.0.1",
        "dhcp_start": f"10.{vlan_id}.0.10",
        "dhcp_end": f"10.{vlan_id}.0.254",
        "bridge": "vmbr1",  # VLAN-aware bridge
        "network": ipaddress.ip_network(f"10.{vlan_id}.0.0/24")
    }


# ============================================================================
# Pydantic Models
# ============================================================================

class CanvasNode(BaseModel):
    id: str
    type: str  # 'vm' or 'network'
    elementId: str  # 'ubuntu', 'kali', 'pfsense', etc.
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
    platform_id: str  # "1" = Proxmox
    lab_data: CanvasLabData


class DeployedVMInfo(BaseModel):
    node_id: str
    name: str
    vm_id: str
    ip_address: Optional[str] = None
    lab_ip: Optional[str] = None
    role: Optional[str] = None  # 'gateway' or 'client'
    status: str


class CanvasDeployResponse(BaseModel):
    success: bool
    deployment_id: str
    lab_id: str
    status: str
    message: str
    network: Optional[Dict[str, Any]] = None
    vms: List[DeployedVMInfo]
    errors: List[str]


# ============================================================================
# Template Mapping
# ============================================================================

TEMPLATE_MAPPING = {
    "ubuntu": 9001,      # Ubuntu 22.04 with guest agent
    "kali": 9001,        # Use Ubuntu for now (Kali template TBD)
    "dvwa": 9001,        # DVWA on Ubuntu
    "metasploitable": 9002,
    "windows": 9010,
    "pfsense": 9020,     # pfSense gateway template
}

VM_SPECS = {
    "ubuntu": {"cores": 2, "memory": 2048, "disk": 20},
    "kali": {"cores": 2, "memory": 4096, "disk": 40},
    "dvwa": {"cores": 1, "memory": 1024, "disk": 10},
    "metasploitable": {"cores": 1, "memory": 1024, "disk": 20},
    "windows": {"cores": 2, "memory": 4096, "disk": 40},
    "pfsense": {"cores": 1, "memory": 1024, "disk": 8},
}


# ============================================================================
# pfSense Configuration via SSH
# ============================================================================

async def configure_pfsense_lan(
    wan_ip: str,
    lan_ip: str,
    lan_netmask: str = "24",
    dhcp_start: str = None,
    dhcp_end: str = None
) -> Dict[str, Any]:
    """
    Configure pfSense LAN interface and DHCP server via SSH.
    
    pfSense template has SSH enabled on WAN with firewall rules allowing access.
    
    Args:
        wan_ip: pfSense WAN IP (for SSH connection)
        lan_ip: IP to assign to LAN interface (e.g., 10.100.0.1)
        lan_netmask: Subnet mask bits (default 24)
        dhcp_start: DHCP range start (e.g., 10.100.0.10)
        dhcp_end: DHCP range end (e.g., 10.100.0.254)
    """
    import pexpect
    
    result = {"success": False, "wan_ip": wan_ip, "lan_ip": lan_ip}
    
    try:
        logger.info(f"[pfSense] Configuring LAN via SSH to {wan_ip}")
        
        # SSH to pfSense
        child = pexpect.spawn(
            f'sshpass -p pfsense ssh -o StrictHostKeyChecking=accept-new admin@{wan_ip}',
            timeout=60
        )
        
        # Wait for pfSense menu
        child.expect('Enter an option:', timeout=30)
        
        # Option 2: Set interface(s) IP address
        child.sendline('2')
        child.expect('Enter the number of the interface', timeout=10)
        
        # Select LAN (usually option 2)
        child.sendline('2')
        child.expect('Enter the new LAN IPv4 address', timeout=10)
        
        # Set LAN IP
        child.sendline(lan_ip)
        child.expect('Enter the new LAN IPv4 subnet bit count', timeout=10)
        
        # Set subnet mask
        child.sendline(lan_netmask)
        child.expect('upstream gateway', timeout=10)
        
        # No upstream gateway for LAN
        child.sendline('')
        child.expect('IPv6', timeout=10)
        
        # Skip IPv6
        child.sendline('n')
        child.expect('DHCP server', timeout=10)
        
        # Enable DHCP server
        child.sendline('y')
        child.expect('start address', timeout=10)
        
        # DHCP range start
        child.sendline(dhcp_start or lan_ip.rsplit('.', 1)[0] + '.10')
        child.expect('end address', timeout=10)
        
        # DHCP range end
        child.sendline(dhcp_end or lan_ip.rsplit('.', 1)[0] + '.254')
        child.expect('revert to HTTP', timeout=10)
        
        # Keep HTTPS
        child.sendline('n')
        
        # Wait for configuration to complete
        child.expect('Press.*Enter.*continue', timeout=30)
        child.sendline('')
        
        # Exit cleanly
        child.expect('Enter an option:', timeout=10)
        child.sendline('0')  # Logout
        child.close()
        
        result["success"] = True
        result["dhcp_enabled"] = True
        result["dhcp_range"] = f"{dhcp_start} - {dhcp_end}"
        
        logger.info(f"[pfSense] ✓ LAN configured: {lan_ip}/{lan_netmask}, DHCP: {dhcp_start}-{dhcp_end}")
        
    except pexpect.TIMEOUT as e:
        logger.error(f"[pfSense] ✗ SSH timeout: {e}")
        result["error"] = "SSH timeout"
    except pexpect.EOF as e:
        logger.error(f"[pfSense] ✗ SSH connection closed: {e}")
        result["error"] = "Connection closed"
    except Exception as e:
        logger.error(f"[pfSense] ✗ Configuration failed: {e}")
        result["error"] = str(e)
    
    return result


async def wait_for_pfsense_wan_ip(
    client: ProxmoxClient,
    node: str,
    vmid: int,
    mac_address: str,
    timeout: int = 90
) -> Optional[str]:
    """
    Wait for pfSense to get a WAN IP via DHCP.
    
    Uses Ubiquiti Dream Router API to look up IP by MAC address.
    Falls back to ARP scanning if API fails.
    """
    import subprocess
    import httpx
    import os
    
    logger.info(f"[pfSense VM {vmid}] Waiting for WAN IP (MAC: {mac_address}, timeout: {timeout}s)")
    mac_lower = mac_address.lower() if mac_address else ""
    
    # Get Unifi API credentials
    unifi_host = os.getenv("UBIQUITI_GATEWAY_HOST", "192.168.2.1")
    unifi_api_key = os.getenv("UBIQUITI_API_KEY", "")
    
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Method 1: Unifi API (preferred)
        if unifi_api_key:
            try:
                async with httpx.AsyncClient(verify=False, timeout=10) as http:
                    resp = await http.get(
                        f"https://{unifi_host}/proxy/network/api/s/default/stat/sta",
                        headers={"X-API-KEY": unifi_api_key}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for client_info in data.get("data", []):
                            if client_info.get("mac", "").lower() == mac_lower:
                                ip = client_info.get("ip")
                                if ip:
                                    logger.info(f"[pfSense VM {vmid}] ✓ Found WAN IP via Unifi API: {ip}")
                                    return ip
            except Exception as e:
                logger.debug(f"[pfSense VM {vmid}] Unifi API error: {e}")
        
        # Method 2: ARP fallback
        try:
            result = subprocess.run(['arp', '-an'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if mac_lower in line.lower():
                    parts = line.split()
                    for part in parts:
                        if part.startswith('(') and part.endswith(')'):
                            ip = part[1:-1]
                            if ip.startswith('192.168.'):
                                logger.info(f"[pfSense VM {vmid}] ✓ Found WAN IP via ARP: {ip}")
                                return ip
        except Exception as e:
            logger.debug(f"[pfSense VM {vmid}] ARP error: {e}")
        
        await asyncio.sleep(5)
    
    logger.warning(f"[pfSense VM {vmid}] ✗ Timeout waiting for WAN IP")
    return None


# ============================================================================
# VM Deployment
# ============================================================================

async def deploy_pfsense_gateway(
    node: CanvasNode,
    lab_id: str,
    lab_short: str,
    network_config: Dict[str, Any],
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Deploy pfSense as the lab gateway.
    
    1. Clone from template
    2. Configure dual-NIC: WAN (mgmt DHCP), LAN (lab VLAN)
    3. Boot and wait for WAN IP
    4. Configure LAN IP and DHCP server via SSH
    """
    vm_name = f"{lab_short}-gateway"
    template_id = TEMPLATE_MAPPING["pfsense"]
    node_name = "pve02"
    
    logger.info(f"")
    logger.info(f"[Gateway] ========================================")
    logger.info(f"[Gateway] Deploying pfSense gateway")
    logger.info(f"[Gateway]   lab_id: {lab_id}")
    logger.info(f"[Gateway]   lab_short: {lab_short}")
    logger.info(f"[Gateway]   vm_name: {vm_name}")
    logger.info(f"[Gateway]   template_id: {template_id}")
    logger.info(f"[Gateway]   node: {node_name}")
    logger.info(f"[Gateway] ========================================")
    
    try:
        # Get Proxmox client
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
        
        # Clone from template - get next available VMID
        next_vmid = client.client.cluster.nextid.get()
        
        # Clone using raw API
        try:
            client.client.nodes(node_name).qemu(template_id).clone.create(
                newid=next_vmid,
                name=vm_name,
                full=1
            )
            # Wait for clone task to complete
            await asyncio.sleep(10)
            vmid = next_vmid
            logger.info(f"[Gateway] Cloned template {template_id} -> VM {vmid}")
        except Exception as e:
            return {"success": False, "error": f"Clone failed: {e}"}
        logger.info(f"[Gateway] Cloned VM {vmid}")
        
        # Configure network interfaces
        vlan_id = network_config["vlan_id"]
        bridge = network_config["bridge"]
        
        # net0 = WAN (management network VLAN 2, DHCP)
        # net1 = LAN (lab network, will be gateway for DHCP)
        await client.configure_vm(node_name, vmid, {
            "net0": "virtio,bridge=vmbr2,tag=2",  # WAN: management DHCP
            "net1": f"virtio,bridge={bridge},tag={vlan_id}",  # LAN: lab network
            "delete": "ipconfig0,ipconfig1"  # Clear any cloud-init configs
        })
        
        logger.info(f"[Gateway] Configured NICs: WAN=vmbr2/tag2, LAN={bridge}/tag{vlan_id}")
        
        # Start the VM
        await client.start_vm(vmid)
        logger.info(f"[Gateway] Started VM {vmid}")
        
        # Get MAC address for ARP-based discovery
        vm_config = client.client.nodes(node_name).qemu(vmid).config.get()
        net0_config = vm_config.get('net0', '')
        mac_match = net0_config.split('=')[1].split(',')[0] if '=' in net0_config else None
        logger.info(f"[Gateway] WAN MAC: {mac_match}")
        
        # Wait for pfSense to boot and get WAN IP via DHCP
        await asyncio.sleep(45)  # Initial boot delay for pfSense
        wan_ip = await wait_for_pfsense_wan_ip(client, node_name, vmid, mac_match, timeout=60)
        
        if not wan_ip:
            # Try ARP scan as fallback
            logger.warning("[Gateway] Guest agent didn't return WAN IP, trying ARP...")
            wan_ip = None  # Could implement ARP scan here
        
        # Configure LAN interface and DHCP via SSH
        lan_config_result = {"success": False}
        if wan_ip:
            await asyncio.sleep(10)  # Let pfSense fully initialize
            lan_config_result = await configure_pfsense_lan(
                wan_ip=wan_ip,
                lan_ip=network_config["gateway"],
                lan_netmask="24",
                dhcp_start=network_config["dhcp_start"],
                dhcp_end=network_config["dhcp_end"]
            )
        
        # Register in database
        orchestrator = get_network_orchestrator()
        await orchestrator.register_deployed_vm(
            session=session,
            lab_id=lab_id,
            name=vm_name,
            vm_id=str(vmid),
            platform="proxmox",
            platform_instance="02",
            os_type="pfsense",
            template_id=str(template_id),
            cpu_cores=VM_SPECS["pfsense"]["cores"],
            memory_mb=VM_SPECS["pfsense"]["memory"],
            disk_gb=VM_SPECS["pfsense"]["disk"],
            ip_address=wan_ip
        )
        
        return {
            "success": True,
            "node_id": node.id,
            "name": vm_name,
            "vm_id": str(vmid),
            "ip_address": wan_ip,
            "lab_ip": network_config["gateway"],
            "role": "gateway",
            "dhcp_configured": lan_config_result.get("success", False),
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"[Gateway] Failed to deploy pfSense: {e}")
        return {"success": False, "node_id": node.id, "error": str(e)}


async def deploy_lab_vm(
    node: CanvasNode,
    lab_id: str,
    lab_short: str,
    network_config: Dict[str, Any],
    vm_index: int = 0
) -> Dict[str, Any]:
    """
    Deploy a lab VM (non-gateway).
    
    Single NIC on lab network - gets IP from pfSense DHCP.
    No management access - connect via pfSense or Proxmox console.
    
    Note: DB registration is deferred to avoid session conflicts in parallel tasks.
    """
    element_id = node.elementId
    template_id = TEMPLATE_MAPPING.get(element_id, 9001)
    specs = VM_SPECS.get(element_id, {"cores": 2, "memory": 2048, "disk": 20})
    # Use lab_short for naming, add index for uniqueness
    vm_name = f"{lab_short}-{element_id}-{vm_index:02d}"
    node_name = "pve02"
    
    logger.info(f"[Lab VM {vm_index}] Starting: {vm_name} (element: {element_id}, template: {template_id})")
    
    # Use semaphore to limit concurrent API calls
    async with _proxmox_semaphore:
        logger.info(f"[Lab VM {vm_index}] Acquired semaphore, proceeding with deployment")
        return await _deploy_lab_vm_internal(
            node, lab_id, lab_short, vm_name, element_id, template_id, specs, 
            network_config, vm_index
        )


async def _deploy_lab_vm_internal(
    node: CanvasNode,
    lab_id: str,
    lab_short: str,
    vm_name: str,
    element_id: str,
    template_id: int,
    specs: Dict[str, Any],
    network_config: Dict[str, Any],
    vm_index: int
) -> Dict[str, Any]:
    """Internal implementation of lab VM deployment (called within semaphore).
    
    Note: Hot spares are skipped for parallel deployment to avoid session conflicts.
    VMs are cloned directly from templates instead.
    """
    node_name = "pve02"
    
    try:
        # NOTE: Hot spares disabled for parallel deployment (session conflicts)
        # Direct clone from template instead
        if True:  # Skip hot spare check
            # Fall back to clone
            logger.info(f"[Lab VM] No hot spares, cloning from template {template_id}")
            
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
            
            # Get next available VMID
            next_vmid = client.client.cluster.nextid.get()
            
            # Clone using raw API
            try:
                client.client.nodes(node_name).qemu(template_id).clone.create(
                    newid=next_vmid,
                    name=vm_name,
                    full=1
                )
                await asyncio.sleep(5)
                vmid = next_vmid
                logger.info(f"[Lab VM] Cloned template {template_id} -> VM {vmid}")
            except Exception as e:
                return {"success": False, "node_id": node.id, "error": f"Clone failed: {e}"}
        
        # Configure single NIC on lab network (DHCP from pfSense)
        vlan_id = network_config["vlan_id"]
        bridge = network_config["bridge"]
        
        await client.configure_vm(node_name, vmid, {
            "net0": f"virtio,bridge={bridge},tag={vlan_id}",
            "delete": "net1,ipconfig0,ipconfig1"  # Remove any extra NICs/configs
        })
        
        logger.info(f"[Lab VM {vmid}] Configured: {bridge}/tag{vlan_id} (DHCP from pfSense)")
        
        # Start the VM
        await client.start_vm(vmid)
        logger.info(f"[Lab VM {vmid}] Started")
        
        # VM will get IP from pfSense DHCP
        # We can query it later via guest agent or ARP
        
        # NOTE: DB registration is deferred to after parallel deployment completes
        # This avoids SQLAlchemy session conflicts in parallel tasks
        
        return {
            "success": True,
            "node_id": node.id,
            "name": vm_name,
            "vm_id": str(vmid),
            "ip_address": None,  # DHCP from pfSense
            "lab_ip": "DHCP",
            "role": "client",
            "status": "running",
            # Include data needed for deferred DB registration
            "_db_data": {
                "lab_id": lab_id,
                "name": vm_name,
                "vm_id": str(vmid),
                "element_id": element_id,
                "template_id": str(template_id),
                "specs": specs
            }
        }
        
    except Exception as e:
        logger.error(f"[Lab VM] Failed to deploy {vm_name}: {e}")
        return {"success": False, "node_id": node.id, "error": str(e)}


# ============================================================================
# Main Deployment Orchestration
# ============================================================================

async def deploy_canvas_lab(
    request: CanvasDeployRequest,
    session: AsyncSession
) -> CanvasDeployResponse:
    """
    Deploy a complete lab from canvas definition.
    
    Architecture:
    1. Allocate VLAN from pool (100-170)
    2. Deploy pfSense as gateway (if in canvas, or auto-add)
    3. Configure pfSense LAN + DHCP
    4. Deploy all other VMs on lab network
    5. VMs get IPs from pfSense DHCP automatically
    """
    
    raw_lab_id = request.lab_id
    platform_id = request.platform_id
    nodes = request.lab_data.nodes
    
    # ========================================================================
    # LOGGING: Trace the request data
    # ========================================================================
    logger.info(f"")
    logger.info(f"{'='*70}")
    logger.info(f"CANVAS DEPLOYMENT REQUEST RECEIVED")
    logger.info(f"{'='*70}")
    logger.info(f"  raw_lab_id: {raw_lab_id}")
    logger.info(f"  platform_id: {platform_id}")
    logger.info(f"  node_count: {len(nodes)}")
    for i, node in enumerate(nodes):
        logger.info(f"  node[{i}]: id={node.id}, type={node.type}, elementId={node.elementId}")
    logger.info(f"{'='*70}")
    
    # Clean up lab_id - extract just the unique identifier
    # Handles cases like "lab-1764xxx" or "1764xxx" or any prefix
    lab_id = raw_lab_id
    if lab_id.startswith("lab-"):
        lab_id = lab_id[4:]  # Remove "lab-" prefix
    
    # Create DNS-safe lab_short for VM naming
    # Proxmox requires valid DNS names: alphanumeric + hyphens, max ~63 chars
    # Keep it short (8 chars) for readability: e.g., "lab-abc12345-gateway"
    import re
    # Extract just alphanumeric parts
    clean_id = re.sub(r'[^a-zA-Z0-9]', '', lab_id)
    # Take first 8 chars, ensure it starts with a letter
    if clean_id and clean_id[0].isdigit():
        lab_short = f"lab{clean_id[:6]}"  # e.g., "lab176421"
    else:
        lab_short = clean_id[:8] if clean_id else "lab"
    
    logger.info(f"  Cleaned lab_id: {lab_id}")
    logger.info(f"  lab_short (for naming): {lab_short}")
    
    if platform_id != "1":
        return CanvasDeployResponse(
            success=False, deployment_id="", lab_id=lab_id, status="failed",
            message="Only Proxmox deployment is currently supported",
            vms=[], errors=["Platform not supported"]
        )
    
    deployment_id = f"deploy-{lab_short}-{datetime.utcnow().strftime('%H%M%S')}"
    
    # Separate VMs and networks
    vm_nodes = [n for n in nodes if n.type == "vm"]
    network_nodes = [n for n in nodes if n.type == "network"]
    
    if not vm_nodes:
        return CanvasDeployResponse(
            success=False, deployment_id=deployment_id, lab_id=lab_id, status="failed",
            message="No VMs to deploy", vms=[], errors=["No VM nodes found"]
        )
    
    logger.info(f"╔══════════════════════════════════════════════════════════════╗")
    logger.info(f"║ Deploying Lab: {lab_id[:40]:<40} ║")
    logger.info(f"║ VMs: {len(vm_nodes):<3} Networks: {len(network_nodes):<3}                              ║")
    logger.info(f"╚══════════════════════════════════════════════════════════════╝")
    
    # ========================================================================
    # Step 1: Allocate VLAN and setup network config
    # ========================================================================
    try:
        vlan_id = await allocate_vlan(session)
        network_config = derive_network_config(vlan_id)
        
        logger.info(f"[Network] VLAN {vlan_id}: {network_config['cidr']}")
        logger.info(f"[Network] Gateway: {network_config['gateway']}")
        logger.info(f"[Network] DHCP: {network_config['dhcp_start']} - {network_config['dhcp_end']}")
        
        # Save network definition
        net_name = f"{lab_short}-net"
        net_def = NetworkDefinition(
            name=net_name,
            display_name=f"Lab Network",
            cidr=network_config["cidr"],
            vlan_id=vlan_id,
            gateway=network_config["gateway"],
            network_type="isolated",
            lab_id=lab_id
        )
        session.add(net_def)
        await session.commit()
        logger.info(f"[Network] Created network definition: {net_name}")
        
    except Exception as e:
        logger.error(f"[Network] Failed to setup: {e}")
        return CanvasDeployResponse(
            success=False, deployment_id=deployment_id, lab_id=lab_id, status="failed",
            message=f"Network setup failed: {e}", vms=[], errors=[str(e)]
        )
    
    deployed_vms: List[DeployedVMInfo] = []
    errors: List[str] = []
    
    # ========================================================================
    # Step 2: Deploy pfSense Gateway FIRST
    # ========================================================================
    pfsense_nodes = [n for n in vm_nodes if n.elementId == "pfsense"]
    other_nodes = [n for n in vm_nodes if n.elementId != "pfsense"]
    
    # Auto-add pfSense if not in canvas but network exists
    if not pfsense_nodes and network_nodes:
        logger.info("[Gateway] Auto-adding pfSense gateway (not in canvas but network requested)")
        pfsense_nodes = [CanvasNode(
            id="auto-pfsense",
            type="vm",
            elementId="pfsense"
        )]
    
    # Deploy gateway first
    for pf_node in pfsense_nodes:
        result = await deploy_pfsense_gateway(pf_node, lab_id, lab_short, network_config, session)
        
        if result["success"]:
            deployed_vms.append(DeployedVMInfo(
                node_id=result["node_id"],
                name=result["name"],
                vm_id=result["vm_id"],
                ip_address=result.get("ip_address"),
                lab_ip=result.get("lab_ip"),
                role="gateway",
                status=result.get("status", "running")
            ))
            logger.info(f"[Gateway] ✓ pfSense deployed: WAN={result.get('ip_address')}, LAN={result.get('lab_ip')}")
        else:
            errors.append(f"pfSense gateway: {result.get('error')}")
            logger.error(f"[Gateway] ✗ Failed: {result.get('error')}")
    
    # Wait for pfSense DHCP to be ready
    if deployed_vms:
        logger.info("[Gateway] Waiting 15s for DHCP server to initialize...")
        await asyncio.sleep(15)
    
    # ========================================================================
    # Step 3: Deploy Lab VMs IN PARALLEL (they get DHCP from pfSense)
    # ========================================================================
    if other_nodes:
        logger.info(f"[Lab VMs] Deploying {len(other_nodes)} VMs in PARALLEL...")
        
        # Create deployment tasks for all lab VMs
        # Note: session not passed - DB registration is deferred to avoid conflicts
        deployment_tasks = [
            deploy_lab_vm(vm_node, lab_id, lab_short, network_config, idx)
            for idx, vm_node in enumerate(other_nodes)
        ]
        
        # Execute all deployments in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*deployment_tasks, return_exceptions=True),
                timeout=180  # 3 minute timeout for all VMs
            )
        except asyncio.TimeoutError:
            logger.error(f"[Lab VMs] Parallel deployment timed out after 180s")
            results = []
            errors.append("Deployment timed out after 3 minutes")
        
        # Process results and collect DB data for deferred registration
        db_registrations = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"{other_nodes[i].elementId}: {str(result)}")
                logger.error(f"[Lab VM] ✗ {other_nodes[i].elementId} exception: {result}")
            elif isinstance(result, dict):
                if result.get("success"):
                    deployed_vms.append(DeployedVMInfo(
                        node_id=result["node_id"],
                        name=result["name"],
                        vm_id=result["vm_id"],
                        ip_address=result.get("ip_address"),
                        lab_ip=result.get("lab_ip"),
                        role="client",
                        status=result.get("status", "running")
                    ))
                    logger.info(f"[Lab VM] ✓ {result['name']} deployed (VMID {result['vm_id']})")
                    # Collect DB data for deferred registration
                    if "_db_data" in result:
                        db_registrations.append(result["_db_data"])
                else:
                    errors.append(f"{other_nodes[i].elementId}: {result.get('error')}")
                    logger.error(f"[Lab VM] ✗ {other_nodes[i].elementId} failed: {result.get('error')}")
        
        # Deferred DB registration (sequential to avoid session conflicts)
        if db_registrations:
            logger.info(f"[DB] Registering {len(db_registrations)} VMs in database...")
            orchestrator = get_network_orchestrator()
            for db_data in db_registrations:
                try:
                    await orchestrator.register_deployed_vm(
                        session=session,
                        lab_id=db_data["lab_id"],
                        name=db_data["name"],
                        vm_id=db_data["vm_id"],
                        platform="proxmox",
                        platform_instance="02",
                        os_type=db_data["element_id"],
                        template_id=db_data["template_id"],
                        cpu_cores=db_data["specs"]["cores"],
                        memory_mb=db_data["specs"]["memory"],
                        disk_gb=db_data["specs"]["disk"],
                        ip_address=None
                    )
                except Exception as e:
                    logger.error(f"[DB] Failed to register {db_data['name']}: {e}")
    
    # ========================================================================
    # Step 4: Register VMs with Lab Registry (source of truth)
    # ========================================================================
    if deployed_vms:
        try:
            registry = get_registry()
            for vm_info in deployed_vms:
                # The vm_info.name is already the correct name (e.g., "brettlab-gateway")
                expected_name = vm_info.name
                
                resource = Resource(
                    id=Resource.make_id("proxmox", "lab_vm", vm_info.vm_id, "02"),
                    resource_type=ResourceType.LAB_VM,
                    name=vm_info.name,
                    platform="proxmox",
                    platform_instance="02",
                    platform_id=vm_info.vm_id,
                    state=ResourceState.RUNNING,  # VMs should be running after deploy
                    lab_id=lab_id,
                    config={
                        "node": "pve02",
                        "vmid": int(vm_info.vm_id),
                        "vlan_id": vlan_id,
                        "role": "gateway" if vm_info.name.lower() == "pfsense" else "lab_vm",
                    },
                    # Set desired state for reconciliation
                    desired_state=ResourceState.RUNNING,
                    desired_config={"name": expected_name},
                    tier=1,  # Lab VMs are Tier 1 (1s updates)
                )
                await registry.register(resource)
            logger.info(f"[Registry] Registered {len(deployed_vms)} VMs in Lab Registry")
        except Exception as e:
            logger.warning(f"[Registry] Failed to register VMs: {e}")
    
    # ========================================================================
    # Step 5: Start WhitePawn monitoring
    # ========================================================================
    if deployed_vms:
        try:
            await auto_deploy_whitepawn(lab_id, f"Canvas Lab {lab_id[:8]}")
            logger.info(f"[Monitor] WhitePawn deployed for lab")
        except Exception as e:
            logger.warning(f"[Monitor] WhitePawn failed: {e}")
    
    # Summary
    success = len(deployed_vms) > 0
    status = "completed" if success and not errors else "partial" if deployed_vms else "failed"
    
    logger.info(f"╔══════════════════════════════════════════════════════════════╗")
    logger.info(f"║ Deployment Complete: {status.upper():<40} ║")
    logger.info(f"║ VMs: {len(deployed_vms)}/{len(vm_nodes) + len(pfsense_nodes)} deployed                                     ║")
    logger.info(f"╚══════════════════════════════════════════════════════════════╝")
    
    return CanvasDeployResponse(
        success=success,
        deployment_id=deployment_id,
        lab_id=lab_id,
        status=status,
        message=f"Deployed {len(deployed_vms)} VMs on VLAN {vlan_id}" + (f" ({len(errors)} errors)" if errors else ""),
        network={
            "vlan_id": vlan_id,
            "cidr": network_config["cidr"],
            "gateway": network_config["gateway"],
            "dhcp_range": f"{network_config['dhcp_start']} - {network_config['dhcp_end']}"
        },
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
    """Deploy a lab designed on the canvas."""
    logger.info(f"Canvas deployment request: lab={request.lab_id}, platform={request.platform_id}")
    return await deploy_canvas_lab(request, session)


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
            {"lab_id": lab_id, "vms": vm_list, "vm_count": len(vm_list)}
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
    
    # Get network config
    net_result = await session.execute(
        select(NetworkDefinition).where(NetworkDefinition.lab_id == lab_id)
    )
    network = net_result.scalar_one_or_none()
    
    return {
        "lab_id": lab_id,
        "network": {
            "vlan_id": network.vlan_id if network else None,
            "cidr": network.cidr if network else None,
            "gateway": network.gateway if network else None
        } if network else None,
        "vms": [vm.to_dict() for vm in vms],
        "vm_count": len(vms)
    }


@router.delete("/{lab_id}")
async def destroy_deployment(lab_id: str, session: AsyncSession = Depends(get_db)):
    """Destroy all VMs in a lab deployment and release VLAN"""
    result = await session.execute(
        select(DeployedVM).where(DeployedVM.lab_id == lab_id)
    )
    vms = result.scalars().all()
    
    if not vms:
        raise HTTPException(status_code=404, detail=f"No deployment found for lab {lab_id}")
    
    # Get Proxmox client
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
    
    destroyed = []
    errors = []
    
    for vm in vms:
        try:
            logger.info(f"Destroying VM {vm.name} (VMID {vm.vm_id})")
            await client.stop_vm(int(vm.vm_id), force=True)
            await asyncio.sleep(2)
            await client.delete_vm(int(vm.vm_id))
            vm.status = "deleted"
            destroyed.append(vm.vm_id)
        except Exception as e:
            errors.append(f"{vm.name}: {e}")
    
    # Delete network definition (releases VLAN)
    await session.execute(
        select(NetworkDefinition).where(NetworkDefinition.lab_id == lab_id)
    )
    net_result = await session.execute(
        select(NetworkDefinition).where(NetworkDefinition.lab_id == lab_id)
    )
    network = net_result.scalar_one_or_none()
    if network:
        await session.delete(network)
        logger.info(f"Released VLAN {network.vlan_id}")
    
    await session.commit()
    
    # Stop WhitePawn monitoring
    try:
        orchestrator = get_whitepawn_orchestrator()
        await orchestrator.stop_for_lab(lab_id)
    except:
        pass
    
    # Clean up registry entries
    try:
        registry = get_registry()
        lab_resources = await registry.list_by_lab(lab_id)
        for resource in lab_resources:
            await registry.delete(resource.id)
        logger.info(f"[Registry] Cleaned up {len(lab_resources)} resources for lab {lab_id}")
    except Exception as e:
        logger.warning(f"[Registry] Cleanup failed: {e}")
    
    return {
        "success": len(errors) == 0,
        "destroyed": destroyed,
        "vlan_released": network.vlan_id if network else None,
        "errors": errors
    }

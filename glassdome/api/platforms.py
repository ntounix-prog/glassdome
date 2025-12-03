"""
API endpoints for platforms

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from glassdome.core.config import settings
from glassdome.core.session import get_session
from glassdome.platforms.proxmox_factory import get_proxmox_client, list_available_proxmox_instances

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/platforms", tags=["platforms"])


def _get_session_secrets():
    """Get secrets from the session if available"""
    try:
        session = get_session()
        if session.authenticated:
            return session.secrets
    except Exception:
        pass
    return {}


class VMInfo(BaseModel):
    """VM information response"""
    vmid: int
    name: str
    status: str
    cpu: Optional[float] = None
    memory: Optional[int] = None
    memory_used: Optional[int] = None
    disk: Optional[int] = None
    uptime: Optional[int] = None
    node: Optional[str] = None
    template: bool = False


class PlatformStatusResponse(BaseModel):
    """Platform status response"""
    platform: str
    connected: bool
    message: str
    nodes: Optional[List[Dict[str, Any]]] = None
    vms: Optional[List[VMInfo]] = None
    summary: Optional[Dict[str, Any]] = None


class PlatformListResponse(BaseModel):
    """List of available platforms"""
    platforms: List[Dict[str, Any]]


# ============================================================================
# Platform List
# ============================================================================

@router.get("", response_model=PlatformListResponse)
async def list_platforms():
    """List all configured platforms and their connection status"""
    platforms = []
    
    # Check Proxmox instances
    try:
        proxmox_instances = list_available_proxmox_instances()
        for instance_id in proxmox_instances:
            config = settings.get_proxmox_config(instance_id)
            platforms.append({
                "id": f"proxmox-{instance_id}",
                "type": "proxmox",
                "name": f"Proxmox {instance_id}" if instance_id != "01" else "Proxmox",
                "host": config.get("host"),
                "configured": bool(config.get("host")),
                "instance_id": instance_id
            })
    except Exception as e:
        logger.error(f"Failed to list Proxmox instances: {e}")
    
    # Check ESXi
    if settings.esxi_host:
        platforms.append({
            "id": "esxi-01",
            "type": "esxi",
            "name": "ESXi",
            "host": settings.esxi_host,
            "configured": True
        })
    else:
        platforms.append({
            "id": "esxi-01",
            "type": "esxi",
            "name": "ESXi",
            "host": None,
            "configured": False
        })
    
    # Check AWS
    platforms.append({
        "id": "aws-01",
        "type": "aws",
        "name": "AWS",
        "region": settings.aws_region,
        "configured": bool(settings.aws_access_key_id)
    })
    
    # Check Azure
    platforms.append({
        "id": "azure-01",
        "type": "azure",
        "name": "Azure",
        "region": settings.azure_region,
        "configured": bool(settings.azure_subscription_id)
    })
    
    return PlatformListResponse(platforms=platforms)


# ============================================================================
# Proxmox Status
# ============================================================================

@router.get("/proxmox", response_model=PlatformStatusResponse)
async def get_proxmox_status(instance_id: str = "01"):
    """Get Proxmox platform status and list all VMs"""
    try:
        client = get_proxmox_client(instance_id)
        
        # Test connection
        connected = await client.test_connection()
        if not connected:
            return PlatformStatusResponse(
                platform="proxmox",
                connected=False,
                message="Failed to connect to Proxmox"
            )
        
        # Get nodes
        nodes = await client.list_nodes()
        
        # Get all VMs across all nodes
        all_vms = []
        summary = {"total": 0, "running": 0, "stopped": 0, "templates": 0}
        
        for node_info in nodes:
            node_name = node_info.get("node", settings.proxmox_node)
            vms = await client.list_vms(node_name)
            
            for vm in vms:
                vm_info = VMInfo(
                    vmid=vm.get("vmid", 0),
                    name=vm.get("name", f"VM-{vm.get('vmid')}"),
                    status=vm.get("status", "unknown"),
                    cpu=vm.get("cpu", 0),
                    memory=vm.get("maxmem", 0),
                    memory_used=vm.get("mem", 0),
                    disk=vm.get("maxdisk", 0),
                    uptime=vm.get("uptime", 0),
                    node=node_name,
                    template=vm.get("template", False)
                )
                all_vms.append(vm_info)
                
                summary["total"] += 1
                if vm_info.template:
                    summary["templates"] += 1
                elif vm_info.status == "running":
                    summary["running"] += 1
                else:
                    summary["stopped"] += 1
        
        return PlatformStatusResponse(
            platform="proxmox",
            connected=True,
            message=f"Connected to Proxmox ({len(nodes)} node(s), {summary['total']} VMs)",
            nodes=nodes,
            vms=all_vms,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Failed to get Proxmox status: {e}")
        return PlatformStatusResponse(
            platform="proxmox",
            connected=False,
            message=f"Error: {str(e)}"
        )


@router.get("/proxmox/{instance_id}/vms")
async def get_proxmox_vms(instance_id: str):
    """Get all VMs for a specific Proxmox instance"""
    return await get_proxmox_status(instance_id)


@router.get("/proxmox/all-instances")
async def get_all_proxmox_status():
    """Get status from all configured Proxmox instances (pve01, pve02, etc.)"""
    try:
        instances = list_available_proxmox_instances()
        logger.info(f"Checking Proxmox instances: {instances}")
        
        all_vms = []
        all_nodes = []
        summary = {"total": 0, "running": 0, "stopped": 0, "templates": 0}
        connected_count = 0
        instance_details = []
        
        for instance_id in instances:
            try:
                config = settings.get_proxmox_config(instance_id)
                if not config.get("host"):
                    logger.warning(f"Proxmox instance {instance_id} has no host configured, skipping")
                    continue
                    
                client = get_proxmox_client(instance_id)
                connected = await client.test_connection()
                
                if not connected:
                    logger.warning(f"Proxmox instance {instance_id} not reachable")
                    instance_details.append({
                        "instance_id": instance_id,
                        "host": config.get("host"),
                        "connected": False,
                        "node": config.get("node", "pve"),
                        "vms": 0
                    })
                    continue
                
                connected_count += 1
                nodes = await client.list_nodes()
                
                for node_info in nodes:
                    node_name = node_info.get("node", config.get("node", "pve"))
                    # Add instance info to node
                    node_info["instance_id"] = instance_id
                    node_info["host"] = config.get("host")
                    all_nodes.append(node_info)
                    
                    vms = await client.list_vms(node_name)
                    
                    for vm in vms:
                        vm_info = VMInfo(
                            vmid=vm.get("vmid", 0),
                            name=vm.get("name", f"VM-{vm.get('vmid')}"),
                            status=vm.get("status", "unknown"),
                            cpu=vm.get("cpu", 0),
                            memory=vm.get("maxmem", 0),
                            memory_used=vm.get("mem", 0),
                            disk=vm.get("maxdisk", 0),
                            uptime=vm.get("uptime", 0),
                            node=f"{node_name} ({instance_id})",  # Show which cluster
                            template=vm.get("template", False)
                        )
                        all_vms.append(vm_info)
                        
                        summary["total"] += 1
                        if vm_info.template:
                            summary["templates"] += 1
                        elif vm_info.status == "running":
                            summary["running"] += 1
                        else:
                            summary["stopped"] += 1
                
                instance_details.append({
                    "instance_id": instance_id,
                    "host": config.get("host"),
                    "connected": True,
                    "node": config.get("node", "pve"),
                    "vms": len([v for v in all_vms if f"({instance_id})" in v.node])
                })
                    
            except Exception as e:
                logger.error(f"Failed to get status from Proxmox instance {instance_id}: {e}")
                instance_details.append({
                    "instance_id": instance_id,
                    "host": config.get("host") if 'config' in dir() else "unknown",
                    "connected": False,
                    "error": str(e)
                })
        
        return PlatformStatusResponse(
            platform="proxmox",
            connected=connected_count > 0,
            message=f"Connected to {connected_count}/{len(instances)} Proxmox instances ({summary['total']} VMs)",
            nodes=all_nodes,
            vms=all_vms,
            summary={
                **summary,
                "instances": instance_details
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get all Proxmox status: {e}")
        return PlatformStatusResponse(
            platform="proxmox",
            connected=False,
            message=f"Error: {str(e)}"
        )


@router.post("/proxmox/{instance_id}/vms/{vmid}/start")
async def start_proxmox_vm(instance_id: str, vmid: int):
    """Start a VM on Proxmox"""
    try:
        client = get_proxmox_client(instance_id)
        config = settings.get_proxmox_config(instance_id)
        node = config.get("node", "pve")
        
        result = await client.start_vm(node, vmid)
        return {"success": True, "vmid": vmid, "result": result}
    except Exception as e:
        logger.error(f"Failed to start VM {vmid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proxmox/{instance_id}/vms/{vmid}/stop")
async def stop_proxmox_vm(instance_id: str, vmid: int):
    """Stop a VM on Proxmox"""
    try:
        client = get_proxmox_client(instance_id)
        config = settings.get_proxmox_config(instance_id)
        node = config.get("node", "pve")
        
        result = await client.stop_vm(node, vmid)
        return {"success": True, "vmid": vmid, "result": result}
    except Exception as e:
        logger.error(f"Failed to stop VM {vmid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ESXi Status
# ============================================================================

@router.get("/esxi", response_model=PlatformStatusResponse)
async def get_esxi_status():
    """Get ESXi platform status and list all VMs"""
    if not settings.esxi_host:
        return PlatformStatusResponse(
            platform="esxi",
            connected=False,
            message="ESXi not configured"
        )
    
    try:
        from glassdome.platforms.esxi_client import ESXiClient
        
        from glassdome.core.secrets_backend import get_secret
        client = ESXiClient(
            host=settings.esxi_host,
            user=settings.esxi_user,
            password=get_secret('esxi_password'),
            verify_ssl=settings.esxi_verify_ssl
        )
        
        # Test connection and get VMs
        connected = await client.test_connection()
        if not connected:
            return PlatformStatusResponse(
                platform="esxi",
                connected=False,
                message="Failed to connect to ESXi"
            )
        
        vms_raw = await client.list_vms()
        vms = []
        summary = {"total": 0, "running": 0, "stopped": 0, "templates": 0}
        
        for vm in vms_raw:
            vm_info = VMInfo(
                vmid=vm.get("moid", 0),
                name=vm.get("name", "Unknown"),
                status=vm.get("power_state", "unknown"),
                cpu=vm.get("cpu_usage", 0),
                memory=vm.get("memory_max_mb", 0) * 1024 * 1024 if vm.get("memory_max_mb") else 0,
                template=vm.get("template", False)
            )
            vms.append(vm_info)
            
            summary["total"] += 1
            if vm_info.template:
                summary["templates"] += 1
            elif vm_info.status == "running":
                summary["running"] += 1
            else:
                summary["stopped"] += 1
        
        return PlatformStatusResponse(
            platform="esxi",
            connected=True,
            message=f"Connected to ESXi ({summary['total']} VMs)",
            vms=vms,
            summary=summary
        )
        
    except ImportError:
        return PlatformStatusResponse(
            platform="esxi",
            connected=False,
            message="ESXi client not available"
        )
    except Exception as e:
        logger.error(f"Failed to get ESXi status: {e}")
        return PlatformStatusResponse(
            platform="esxi",
            connected=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# AWS Status
# ============================================================================

@router.get("/aws", response_model=PlatformStatusResponse)
async def get_aws_status(region: str = None):
    """Get AWS platform status and list EC2 instances"""
    # Get credentials from Vault
    from glassdome.core.secrets_backend import get_secret
    aws_access_key = get_secret('aws_access_key_id')
    aws_secret_key = get_secret('aws_secret_access_key')
    
    if not aws_access_key:
        return PlatformStatusResponse(
            platform="aws",
            connected=False,
            message="AWS not configured"
        )
    
    try:
        import boto3
        
        # Use provided region or default
        target_region = region or settings.aws_region
        
        ec2 = boto3.client(
            'ec2',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=target_region
        )
        
        # Get all instances
        response = ec2.describe_instances()
        
        vms = []
        summary = {"total": 0, "running": 0, "stopped": 0, "templates": 0}
        
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                name = "Unnamed"
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                state = instance.get('State', {}).get('Name', 'unknown')
                
                vm_info = VMInfo(
                    vmid=hash(instance['InstanceId']) % 10000,  # Convert to int
                    name=name,
                    status=state,
                    cpu=0,
                    memory=0,
                    template=False
                )
                vms.append(vm_info)
                
                summary["total"] += 1
                if state == "running":
                    summary["running"] += 1
                else:
                    summary["stopped"] += 1
        
        return PlatformStatusResponse(
            platform="aws",
            connected=True,
            message=f"Connected to AWS {target_region} ({summary['total']} instances)",
            vms=vms,
            summary=summary
        )
        
    except ImportError:
        return PlatformStatusResponse(
            platform="aws",
            connected=False,
            message="boto3 not installed"
        )
    except Exception as e:
        logger.error(f"Failed to get AWS status: {e}")
        return PlatformStatusResponse(
            platform="aws",
            connected=False,
            message=f"Error: {str(e)}"
        )


@router.get("/aws/all-regions", response_model=PlatformStatusResponse)
async def get_aws_all_regions_status():
    """Get AWS status across multiple regions (us-east-1, us-west-2)"""
    # Get credentials from Vault
    from glassdome.core.secrets_backend import get_secret
    aws_access_key = get_secret('aws_access_key_id')
    aws_secret_key = get_secret('aws_secret_access_key')
    
    if not aws_access_key:
        return PlatformStatusResponse(
            platform="aws",
            connected=False,
            message="AWS not configured"
        )
    
    try:
        import boto3
        
        regions = ['us-east-1', 'us-west-2']  # Virginia and Oregon
        all_vms = []
        summary = {"total": 0, "running": 0, "stopped": 0, "templates": 0}
        
        for region in regions:
            try:
                ec2 = boto3.client(
                    'ec2',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=region
                )
                
                response = ec2.describe_instances()
                
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        name = "Unnamed"
                        for tag in instance.get('Tags', []):
                            if tag['Key'] == 'Name':
                                name = tag['Value']
                                break
                        
                        state = instance.get('State', {}).get('Name', 'unknown')
                        instance_type = instance.get('InstanceType', '')
                        
                        vm_info = VMInfo(
                            vmid=hash(instance['InstanceId']) % 10000,
                            name=f"{name} ({region})",
                            status=state,
                            cpu=0,
                            memory=0,
                            template=False,
                            node=region
                        )
                        all_vms.append(vm_info)
                        
                        summary["total"] += 1
                        if state == "running":
                            summary["running"] += 1
                        else:
                            summary["stopped"] += 1
                            
            except Exception as e:
                logger.warning(f"Failed to get instances from {region}: {e}")
        
        return PlatformStatusResponse(
            platform="aws",
            connected=True,
            message=f"Connected to AWS ({summary['total']} instances across {len(regions)} regions)",
            vms=all_vms,
            summary=summary
        )
        
    except ImportError:
        return PlatformStatusResponse(
            platform="aws",
            connected=False,
            message="boto3 not installed"
        )
    except Exception as e:
        logger.error(f"Failed to get AWS status: {e}")
        return PlatformStatusResponse(
            platform="aws",
            connected=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# Azure Status
# ============================================================================

@router.get("/azure", response_model=PlatformStatusResponse)
async def get_azure_status():
    """Get Azure platform status and list VMs"""
    if not settings.azure_subscription_id:
        return PlatformStatusResponse(
            platform="azure",
            connected=False,
            message="Azure not configured"
        )
    
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.compute import ComputeManagementClient
        
        from glassdome.core.secrets_backend import get_secret
        credential = ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=get_secret('azure_client_secret')
        )
        
        compute_client = ComputeManagementClient(
            credential,
            settings.azure_subscription_id
        )
        
        # Get all VMs
        vms_raw = compute_client.virtual_machines.list_all()
        
        vms = []
        summary = {"total": 0, "running": 0, "stopped": 0, "templates": 0}
        
        for vm in vms_raw:
            # Get instance view for power state
            try:
                resource_group = vm.id.split('/')[4]
                instance_view = compute_client.virtual_machines.instance_view(
                    resource_group, vm.name
                )
                power_state = "unknown"
                for status in instance_view.statuses:
                    if status.code.startswith("PowerState/"):
                        power_state = status.code.split("/")[1]
                        break
            except:
                power_state = "unknown"
            
            vm_info = VMInfo(
                vmid=hash(vm.vm_id) % 10000 if vm.vm_id else 0,
                name=vm.name,
                status=power_state,
                cpu=0,
                memory=0,
                template=False
            )
            vms.append(vm_info)
            
            summary["total"] += 1
            if power_state == "running":
                summary["running"] += 1
            else:
                summary["stopped"] += 1
        
        return PlatformStatusResponse(
            platform="azure",
            connected=True,
            message=f"Connected to Azure ({summary['total']} VMs)",
            vms=vms,
            summary=summary
        )
        
    except ImportError:
        return PlatformStatusResponse(
            platform="azure",
            connected=False,
            message="Azure SDK not installed"
        )
    except Exception as e:
        logger.error(f"Failed to get Azure status: {e}")
        return PlatformStatusResponse(
            platform="azure",
            connected=False,
            message=f"Error: {str(e)}"
        )


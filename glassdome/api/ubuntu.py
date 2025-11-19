"""
Ubuntu VM API Endpoints
Handles requests for creating Ubuntu base installations
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
from glassdome.agents.manager import agent_manager
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ubuntu", tags=["Ubuntu VMs"])


# Request/Response Models
class UbuntuVMRequest(BaseModel):
    """Request model for creating Ubuntu VM"""
    
    name: str = Field(..., description="VM name")
    node: str = Field(..., description="Proxmox node")
    ubuntu_version: str = Field(default="22.04", description="Ubuntu version (22.04, 24.04, 20.04)")
    use_template: bool = Field(default=True, description="Use template for faster creation")
    
    cores: Optional[int] = Field(default=2, description="CPU cores")
    memory: Optional[int] = Field(default=2048, description="Memory in MB")
    disk_size: Optional[int] = Field(default=20, description="Disk size in GB")
    network: Optional[str] = Field(default="vmbr0", description="Network bridge")
    storage: Optional[str] = Field(default="local-lvm", description="Storage location")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "ubuntu-web-server",
                "node": "pve",
                "ubuntu_version": "22.04",
                "use_template": True,
                "cores": 2,
                "memory": 2048,
                "disk_size": 20
            }
        }


class UbuntuVMResponse(BaseModel):
    """Response model for Ubuntu VM creation"""
    
    success: bool
    message: str
    task_id: Optional[str] = None
    vm_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TemplateRequest(BaseModel):
    """Request model for creating Ubuntu template"""
    
    node: str = Field(..., description="Proxmox node")
    ubuntu_version: str = Field(default="22.04", description="Ubuntu version")
    template_vmid: Optional[int] = Field(default=None, description="Specific template VM ID")


# Initialize Ubuntu agent (will be done properly in startup)
_ubuntu_agent: Optional[UbuntuInstallerAgent] = None


def get_ubuntu_agent() -> UbuntuInstallerAgent:
    """Get or create Ubuntu installer agent"""
    global _ubuntu_agent
    
    if _ubuntu_agent is None:
        # Check if Proxmox is configured
        if not settings.proxmox_host:
            raise HTTPException(
                status_code=503,
                detail="Proxmox not configured. Set PROXMOX_HOST in environment."
            )
        
        # Create Proxmox client
        proxmox_client = ProxmoxClient(
            host=settings.proxmox_host,
            user=settings.proxmox_user,
            password=settings.proxmox_password,
            token_name=settings.proxmox_token_name,
            token_value=settings.proxmox_token_value,
            verify_ssl=settings.proxmox_verify_ssl
        )
        
        # Create and register agent
        _ubuntu_agent = UbuntuInstallerAgent("ubuntu_installer_1", proxmox_client)
        agent_manager.register_agent(_ubuntu_agent)
        
        logger.info("Ubuntu Installer Agent created and registered")
    
    return _ubuntu_agent


@router.post("/create", response_model=UbuntuVMResponse)
async def create_ubuntu_vm(request: UbuntuVMRequest, background_tasks: BackgroundTasks):
    """
    Create a new Ubuntu VM
    
    This endpoint triggers the Ubuntu Installer Agent to create a base Ubuntu installation.
    The agent will either clone from a template (fast) or create from ISO (slower).
    
    Returns immediately with a task ID. Check task status using the task ID.
    """
    try:
        agent = get_ubuntu_agent()
        
        # Prepare task for agent
        task = {
            "task_id": f"ubuntu_vm_{request.name}",
            "element_type": "ubuntu_vm",
            "agent_type": "deployment",
            "config": {
                "name": request.name,
                "node": request.node,
                "ubuntu_version": request.ubuntu_version,
                "use_template": request.use_template,
                "resources": {
                    "cores": request.cores,
                    "memory": request.memory,
                    "disk_size": request.disk_size,
                    "network": request.network,
                    "storage": request.storage,
                }
            }
        }
        
        # Submit task to agent manager
        task_id = await agent_manager.submit_task(task)
        
        logger.info(f"Ubuntu VM creation task submitted: {task_id}")
        
        return UbuntuVMResponse(
            success=True,
            message=f"Ubuntu VM creation task submitted: {task_id}",
            task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Ubuntu VM: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-sync", response_model=UbuntuVMResponse)
async def create_ubuntu_vm_sync(request: UbuntuVMRequest):
    """
    Create Ubuntu VM synchronously (waits for completion)
    
    Use this for immediate feedback, but note it may take several minutes.
    For long-running tasks, use the async endpoint instead.
    """
    try:
        agent = get_ubuntu_agent()
        
        # Prepare task
        task = {
            "task_id": f"ubuntu_vm_{request.name}_sync",
            "element_type": "ubuntu_vm",
            "config": {
                "name": request.name,
                "node": request.node,
                "ubuntu_version": request.ubuntu_version,
                "use_template": request.use_template,
                "resources": {
                    "cores": request.cores,
                    "memory": request.memory,
                    "disk_size": request.disk_size,
                    "network": request.network,
                    "storage": request.storage,
                }
            }
        }
        
        # Execute directly (blocking)
        result = await agent.run(task)
        
        if result.get("success"):
            return UbuntuVMResponse(
                success=True,
                message="Ubuntu VM created successfully",
                vm_details=result
            )
        else:
            return UbuntuVMResponse(
                success=False,
                message="Failed to create Ubuntu VM",
                error=result.get("error")
            )
        
    except Exception as e:
        logger.error(f"Error creating Ubuntu VM: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/template/create")
async def create_ubuntu_template(request: TemplateRequest):
    """
    Create an Ubuntu template for faster VM cloning
    
    Templates are pre-configured VMs that can be quickly cloned.
    This is recommended for frequently deployed Ubuntu versions.
    """
    try:
        agent = get_ubuntu_agent()
        
        result = await agent.create_template(
            node=request.node,
            ubuntu_version=request.ubuntu_version,
            template_vmid=request.template_vmid
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": f"Ubuntu {request.ubuntu_version} template created",
                "template_id": result.get("template_id")
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions")
async def list_ubuntu_versions():
    """
    List available Ubuntu versions
    
    Returns all Ubuntu versions that can be installed by the agent.
    """
    return {
        "versions": UbuntuInstallerAgent.UBUNTU_VERSIONS,
        "default_version": "22.04"
    }


@router.get("/agent/status")
async def get_agent_status():
    """
    Get Ubuntu Installer Agent status
    
    Returns the current status of the Ubuntu installer agent.
    """
    try:
        agent = get_ubuntu_agent()
        
        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type.value,
            "status": agent.status.value,
            "error": agent.error
        }
        
    except Exception as e:
        return {
            "agent_id": None,
            "status": "not_initialized",
            "error": str(e)
        }


@router.get("/defaults")
async def get_default_config():
    """
    Get default configuration for Ubuntu VMs
    
    Returns the default CPU, memory, disk, and network configuration.
    """
    return {
        "default_config": UbuntuInstallerAgent.DEFAULT_CONFIG,
        "description": "Default resources for Ubuntu VMs"
    }


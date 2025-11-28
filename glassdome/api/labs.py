"""
API endpoints for labs

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from glassdome.orchestration.lab_orchestrator import LabOrchestrator
from glassdome.platforms.proxmox_client import ProxmoxClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/labs", tags=["labs"])


class LabDeployRequest(BaseModel):
    """Lab deployment request"""
    lab_spec: Dict[str, Any] = Field(
        ...,
        description="Complete lab specification including VMs, networks, users, packages"
    )


class LabDeployResponse(BaseModel):
    """Lab deployment response"""
    lab_id: str
    status: str
    message: str
    execution_plan: Optional[List[List[str]]] = None
    result: Optional[Dict[str, Any]] = None


class LabTemplateListResponse(BaseModel):
    """List of available lab templates"""
    templates: List[Dict[str, Any]]


# In-memory lab templates (would come from database in production)
LAB_TEMPLATES = {
    "web_security": {
        "lab_id": "web_security_lab",
        "name": "Web Application Security Lab",
        "description": "Complete penetration testing environment for web applications",
        "vms": [
            {
                "vm_id": "kali_attacker",
                "name": "kali-attacker",
                "os_type": "kali",
                "os_version": "2024.1",
                "resources": {
                    "cores": 4,
                    "memory": 8192,
                    "disk_size": 80
                },
                "users": [
                    {
                        "username": "pentester",
                        "sudo": True,
                        "shell": "/bin/zsh"
                    }
                ],
                "packages": {
                    "system": ["nmap", "metasploit-framework", "burpsuite", "sqlmap"]
                }
            },
            {
                "vm_id": "dvwa_target",
                "name": "dvwa-target",
                "os_type": "ubuntu",
                "os_version": "22.04",
                "resources": {
                    "cores": 2,
                    "memory": 4096,
                    "disk_size": 40
                },
                "users": [
                    {
                        "username": "webadmin",
                        "sudo": True
                    }
                ],
                "packages": {
                    "system": ["apache2", "mysql-server", "php", "php-mysql"]
                }
            }
        ]
    },
    "network_defense": {
        "lab_id": "network_defense_lab",
        "name": "Network Defense Lab",
        "description": "Blue team defensive security environment",
        "vms": [
            {
                "vm_id": "security_onion",
                "name": "security-onion",
                "os_type": "ubuntu",
                "os_version": "22.04",
                "resources": {
                    "cores": 4,
                    "memory": 16384,
                    "disk_size": 200
                },
                "users": [
                    {
                        "username": "analyst",
                        "sudo": True
                    }
                ],
                "packages": {
                    "system": ["wireshark", "suricata", "zeek"]
                }
            },
            {
                "vm_id": "firewall",
                "name": "pfsense-firewall",
                "os_type": "pfsense",
                "os_version": "2.7",
                "resources": {
                    "cores": 2,
                    "memory": 4096,
                    "disk_size": 20
                }
            }
        ]
    },
    "malware_analysis": {
        "lab_id": "malware_analysis_lab",
        "name": "Malware Analysis Lab",
        "description": "Isolated environment for malware analysis",
        "vms": [
            {
                "vm_id": "remnux",
                "name": "remnux-analysis",
                "os_type": "ubuntu",
                "os_version": "22.04",
                "resources": {
                    "cores": 4,
                    "memory": 8192,
                    "disk_size": 100
                },
                "users": [
                    {
                        "username": "analyst",
                        "sudo": True
                    }
                ],
                "packages": {
                    "system": ["volatility", "ghidra", "radare2", "yara"]
                }
            },
            {
                "vm_id": "windows_sandbox",
                "name": "windows-sandbox",
                "os_type": "windows",
                "os_version": "10",
                "resources": {
                    "cores": 2,
                    "memory": 4096,
                    "disk_size": 60
                },
                "network": {
                    "isolated": True
                }
            }
        ]
    }
}


@router.post("/deploy", response_model=LabDeployResponse)
async def deploy_lab(
    request: LabDeployRequest,
    background_tasks: BackgroundTasks
) -> LabDeployResponse:
    """
    Deploy a complete lab with orchestration
    
    This endpoint handles complex multi-VM deployments with:
    - Multiple VMs
    - User account creation
    - Package installation
    - Network configuration
    - Dependencies
    
    The orchestrator coordinates all agents and post-configuration.
    """
    try:
        logger.info(f"Starting lab deployment: {request.lab_spec.get('name')}")
        
        # Initialize Proxmox client
        # In production, get credentials from config/env
        proxmox = ProxmoxClient(
            host="proxmox.local",
            user="root@pam",
            password="password",
            verify_ssl=False
        )
        
        # Create orchestrator
        orchestrator = LabOrchestrator(proxmox)
        
        # Build execution plan
        from glassdome.orchestration.lab_orchestrator import LabConfiguration
        lab_config = LabConfiguration(request.lab_spec)
        await orchestrator._build_tasks(lab_config)
        
        execution_plan = orchestrator.get_execution_plan()
        
        # Start deployment
        result = await orchestrator.deploy_lab(request.lab_spec)
        
        return LabDeployResponse(
            lab_id=request.lab_spec.get("lab_id", "unknown"),
            status="completed" if result["success"] else "failed",
            message=f"Lab deployment {'completed' if result['success'] else 'failed'}",
            execution_plan=execution_plan,
            result=result
        )
        
    except Exception as e:
        logger.error(f"Lab deployment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy-async", response_model=LabDeployResponse)
async def deploy_lab_async(
    request: LabDeployRequest,
    background_tasks: BackgroundTasks
) -> LabDeployResponse:
    """
    Deploy a lab asynchronously (background task)
    
    Returns immediately with lab_id, deployment continues in background
    Use GET /labs/{lab_id}/status to check progress
    """
    lab_id = request.lab_spec.get("lab_id", "unknown")
    
    # Add background task
    background_tasks.add_task(_deploy_lab_background, request.lab_spec)
    
    return LabDeployResponse(
        lab_id=lab_id,
        status="deploying",
        message=f"Lab deployment started in background: {lab_id}",
        execution_plan=None,
        result=None
    )


async def _deploy_lab_background(lab_spec: Dict[str, Any]):
    """Background task for lab deployment"""
    try:
        proxmox = ProxmoxClient(
            host="proxmox.local",
            user="root@pam",
            password="password",
            verify_ssl=False
        )
        
        orchestrator = LabOrchestrator(proxmox)
        result = await orchestrator.deploy_lab(lab_spec)
        
        logger.info(f"Background lab deployment completed: {lab_spec.get('lab_id')}")
        
        # In production: Update database with result
        # db.update_lab_status(lab_id, result)
        
    except Exception as e:
        logger.error(f"Background lab deployment failed: {str(e)}")
        # In production: Update database with error
        # db.update_lab_status(lab_id, {"success": False, "error": str(e)})


@router.get("/templates", response_model=LabTemplateListResponse)
async def list_lab_templates() -> LabTemplateListResponse:
    """
    Get list of available lab templates
    
    These templates can be deployed via POST /labs/deploy
    """
    templates = []
    
    for template_id, template in LAB_TEMPLATES.items():
        templates.append({
            "id": template_id,
            "name": template["name"],
            "description": template["description"],
            "vm_count": len(template["vms"]),
            "vms": [
                {
                    "name": vm["name"],
                    "os": f"{vm['os_type']} {vm.get('os_version', '')}",
                    "resources": vm["resources"]
                }
                for vm in template["vms"]
            ]
        })
    
    return LabTemplateListResponse(templates=templates)


@router.get("/templates/{template_id}")
async def get_lab_template(template_id: str) -> Dict[str, Any]:
    """
    Get full lab template specification
    
    Returns the complete lab_spec that can be used in deploy request
    """
    if template_id not in LAB_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    return LAB_TEMPLATES[template_id]


@router.get("/{lab_id}/status")
async def get_lab_status(lab_id: str) -> Dict[str, Any]:
    """
    Get lab deployment status
    
    In production, this would query the database for deployment status
    """
    # TODO: Implement database lookup
    return {
        "lab_id": lab_id,
        "status": "deploying",
        "message": "Lab deployment in progress",
        "progress": 0.5,
        "vms": {
            "total": 3,
            "completed": 1,
            "in_progress": 1,
            "pending": 1
        }
    }


@router.delete("/{lab_id}")
async def delete_lab(lab_id: str) -> Dict[str, Any]:
    """
    Delete entire lab (all VMs, networks)
    
    This would orchestrate cleanup of all lab components
    """
    # TODO: Implement lab deletion
    logger.info(f"Deleting lab: {lab_id}")
    
    return {
        "lab_id": lab_id,
        "status": "deleted",
        "message": f"Lab {lab_id} deleted successfully"
    }


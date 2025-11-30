"""
API endpoints for labs

Includes both:
- Lab CRUD operations (canvas-based lab definitions)
- Lab deployment orchestration

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from glassdome.core.database import get_db
from glassdome.models.lab import Lab
from glassdome.orchestration.lab_orchestrator import LabOrchestrator
from glassdome.platforms.proxmox_client import ProxmoxClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/labs", tags=["labs"])


# =============================================================================
# Lab CRUD Operations (Canvas-based lab definitions)
# =============================================================================

@router.post("")
async def create_lab(lab_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Create or update a lab configuration (upsert)."""
    lab_id = lab_data.get("id")
    name = lab_data.get("name", "Untitled Lab")
    canvas_data = lab_data.get("canvas_data")
    
    # Check if lab exists (upsert)
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.name = name
        existing.canvas_data = canvas_data
        await db.commit()
        return {"success": True, "lab_id": lab_id, "message": "Lab updated"}
    else:
        lab = Lab(id=lab_id, name=name, canvas_data=canvas_data)
        db.add(lab)
        await db.commit()
        return {"success": True, "lab_id": lab_id, "message": "Lab created"}


@router.get("")
async def list_labs(db: AsyncSession = Depends(get_db)):
    """List all lab configurations."""
    result = await db.execute(select(Lab).order_by(Lab.created_at.desc()))
    labs = result.scalars().all()
    
    return {
        "labs": [
            {
                "id": lab.id,
                "name": lab.name,
                "description": lab.description,
                "created_at": lab.created_at.isoformat() if lab.created_at else None,
                "node_count": len(lab.canvas_data.get("nodes", [])) if lab.canvas_data else 0
            }
            for lab in labs
        ],
        "total": len(labs)
    }


@router.get("/{lab_id}")
async def get_lab(lab_id: str, db: AsyncSession = Depends(get_db)):
    """Get lab configuration by ID."""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail=f"Lab {lab_id} not found")
    
    return {
        "id": lab.id,
        "name": lab.name,
        "description": lab.description,
        "canvas_data": lab.canvas_data,
        "created_at": lab.created_at.isoformat() if lab.created_at else None
    }


@router.put("/{lab_id}")
async def update_lab(lab_id: str, lab_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Update lab configuration."""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail=f"Lab {lab_id} not found")
    
    if "name" in lab_data:
        lab.name = lab_data["name"]
    if "canvas_data" in lab_data:
        lab.canvas_data = lab_data["canvas_data"]
    if "description" in lab_data:
        lab.description = lab_data["description"]
    
    await db.commit()
    return {"success": True, "lab_id": lab_id}


@router.delete("/{lab_id}")
async def delete_lab(lab_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a lab configuration."""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail=f"Lab {lab_id} not found")
    
    await db.execute(delete(Lab).where(Lab.id == lab_id))
    await db.commit()
    return {"success": True, "lab_id": lab_id}


# =============================================================================
# Lab Deployment Orchestration
# =============================================================================

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
async def get_lab_status(
    lab_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get lab deployment status with real data from database.
    """
    from glassdome.models.deployment import DeployedVM
    
    # Get lab
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    # Get deployed VMs for this lab
    result = await db.execute(
        select(DeployedVM).where(DeployedVM.lab_id == lab_id)
    )
    deployed_vms = result.scalars().all()
    
    # Calculate status
    total_elements = len(lab.elements) if lab.elements else 0
    deployed_count = len(deployed_vms)
    running_count = len([vm for vm in deployed_vms if vm.status == "running"])
    pending_count = total_elements - deployed_count
    
    # Determine overall status
    if deployed_count == 0:
        status = "draft" if lab.status == "draft" else "pending"
        progress = 0.0
    elif running_count == total_elements:
        status = "running"
        progress = 1.0
    elif deployed_count > 0:
        status = "deploying"
        progress = deployed_count / total_elements if total_elements > 0 else 0
    else:
        status = lab.status or "unknown"
        progress = 0.0
    
    return {
        "lab_id": lab_id,
        "lab_name": lab.name,
        "status": status,
        "message": _get_status_message(status, running_count, total_elements),
        "progress": round(progress, 2),
        "vms": {
            "total": total_elements,
            "deployed": deployed_count,
            "running": running_count,
            "pending": pending_count
        },
        "deployed_vms": [
            {
                "id": vm.id,
                "name": vm.name,
                "status": vm.status,
                "ip_address": vm.ip_address,
                "platform": vm.platform
            }
            for vm in deployed_vms
        ]
    }


def _get_status_message(status: str, running: int, total: int) -> str:
    """Generate human-readable status message."""
    if status == "draft":
        return "Lab is in draft mode. Add VMs and deploy."
    elif status == "pending":
        return "Lab is ready for deployment."
    elif status == "deploying":
        return f"Deployment in progress ({running}/{total} VMs running)"
    elif status == "running":
        return f"All {total} VMs running successfully"
    elif status == "stopped":
        return "Lab deployment stopped"
    elif status == "error":
        return "Deployment encountered an error"
    else:
        return f"Status: {status}"


# NOTE: delete_lab is defined above in the CRUD section (line ~115)
# The orchestrated lab deletion (with VM cleanup) is in canvas_deploy.py

"""
Glassdome Backend - FastAPI Application
Agentic Cyber Range Deployment Framework
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import os

from glassdome.core.config import settings
from glassdome.core.session import get_session
from glassdome.core.database import get_db, init_db
from glassdome.agents.manager import agent_manager
from glassdome.orchestration import OrchestrationEngine

# Import API routers
from glassdome.api.ubuntu import router as ubuntu_router
from glassdome.api.labs import router as labs_router
from glassdome.api.ansible import router as ansible_router
from glassdome.api import auth
from glassdome.api.chat import router as chat_router
from glassdome.api.platforms import router as platforms_router
from glassdome.api.reaper import router as reaper_router
from glassdome.api.whiteknight import router as whiteknight_router

# Initialize FastAPI app
app = FastAPI(
    title="Glassdome API",
    description="Agentic Cyber Range Deployment Framework",
    version="0.1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(ubuntu_router, prefix=settings.api_prefix)
app.include_router(labs_router)
app.include_router(ansible_router)
app.include_router(auth.router)
app.include_router(chat_router)  # Overseer chat interface
app.include_router(platforms_router)  # Platform status API
app.include_router(reaper_router)  # Reaper exploit library & missions
app.include_router(whiteknight_router)  # WhiteKnight validation engine


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Initialize session from cache (no password prompt if cached)
    from glassdome.core.session import get_session
    session = get_session()
    if session.initialize(use_cache=True, interactive=False):
        logger.info(f"Session loaded with {len(session.secrets)} secrets")
    
    await init_db()
    
    # Start Hot Spare Pool Manager (guardian process for spare VMs)
    try:
        from glassdome.reaper.hot_spare import get_hot_spare_pool
        pool = get_hot_spare_pool()
        await pool.start()
        logger.info("Hot Spare Pool Manager started - maintaining spare VMs")
    except Exception as e:
        logger.warning(f"Could not start Hot Spare Pool Manager: {e}")
    
    # Start agent manager in background
    # asyncio.create_task(agent_manager.start())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Stop Hot Spare Pool Manager
    try:
        from glassdome.reaper.hot_spare import get_hot_spare_pool
        pool = get_hot_spare_pool()
        await pool.stop()
        logger.info("Hot Spare Pool Manager stopped")
    except Exception as e:
        logger.warning(f"Error stopping Hot Spare Pool Manager: {e}")
    
    await agent_manager.stop()


# Health and Status Endpoints
@app.get(f"{settings.api_prefix}/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Glassdome API is running",
        "version": settings.app_version
    }


@app.get(f"{settings.api_prefix}/")
async def root():
    """Root API endpoint"""
    return {
        "message": "Glassdome - Agentic Cyber Range Deployment Framework",
        "version": settings.app_version,
        "docs": "/docs"
    }


# Lab Management Endpoints
@app.post(f"{settings.api_prefix}/labs")
async def create_lab(lab_data: Dict[str, Any]):
    """Create a new lab configuration"""
    # TODO: Implement lab creation logic
    return {
        "success": True,
        "lab_id": "lab_123",
        "message": "Lab created successfully"
    }


@app.get(f"{settings.api_prefix}/labs")
async def list_labs():
    """List all lab configurations"""
    # TODO: Implement lab listing
    return {
        "labs": [],
        "total": 0
    }


@app.get(settings.api_prefix + "/labs/{lab_id}")
async def get_lab(lab_id: str):
    """Get lab configuration by ID"""
    # TODO: Implement lab retrieval
    return {
        "lab_id": lab_id,
        "name": "Example Lab",
        "elements": []
    }


@app.put(settings.api_prefix + "/labs/{lab_id}")
async def update_lab(lab_id: str, lab_data: Dict[str, Any]):
    """Update lab configuration"""
    # TODO: Implement lab update
    return {
        "success": True,
        "lab_id": lab_id
    }


@app.delete(settings.api_prefix + "/labs/{lab_id}")
async def delete_lab(lab_id: str):
    """Delete a lab configuration"""
    # TODO: Implement lab deletion
    return {
        "success": True,
        "lab_id": lab_id
    }


# Deployment Endpoints
@app.post(f"{settings.api_prefix}/deployments")
async def create_deployment(deployment_data: Dict[str, Any]):
    """
    Create a new deployment from a lab configuration
    This triggers the agentic deployment process
    """
    import uuid
    import logging
    from glassdome.core.session import get_session
    from glassdome.platforms.aws_client import AWSClient
    
    logger = logging.getLogger(__name__)
    
    lab_id = deployment_data.get("lab_id")
    platform_id = deployment_data.get("platform_id")
    lab_data = deployment_data.get("lab_data", {})
    
    if not lab_id or not platform_id:
        raise HTTPException(status_code=400, detail="lab_id and platform_id required")
    
    nodes = lab_data.get("nodes", [])
    deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Creating deployment {deployment_id} with {len(nodes)} nodes on platform {platform_id}")
    
    # Count VMs to deploy - check both type and data.elementType
    vm_nodes = [n for n in nodes if n.get("type") == "vm" or 
                n.get("data", {}).get("elementType") in ["attack", "vulnerable", "base"]]
    network_nodes = [n for n in nodes if n.get("type") == "network" or
                     n.get("data", {}).get("elementId") in ["isolated", "nat"]]
    
    if not vm_nodes and not network_nodes:
        return {
            "success": False,
            "deployment_id": deployment_id,
            "status": "failed",
            "message": "No VMs or networks found in lab configuration"
        }
    
    # For now, deploy to AWS if platform_id indicates AWS, otherwise Proxmox
    deployed_vms = []
    errors = []
    
    try:
        session = get_session()
        
        # Platform 1 = Proxmox, 2 = AWS (based on typical ordering)
        if platform_id == "2" or "aws" in str(platform_id).lower():
            aws_key = session.secrets.get('aws_access_key_id')
            aws_secret = session.secrets.get('aws_secret_access_key')
            
            if aws_key and aws_secret:
                aws_client = AWSClient(
                    access_key_id=aws_key,
                    secret_access_key=aws_secret,
                    region="us-east-1"
                )
                
                for vm_node in vm_nodes:
                    # Get VM name from elementId or generate one
                    data = vm_node.get("data", {})
                    element_id = data.get("elementId", "ubuntu")
                    vm_name = f"{deployment_id}-{element_id}-{uuid.uuid4().hex[:4]}"
                    vm_config = {
                        "name": vm_name,
                        "os_type": "ubuntu",
                        "os_version": "22.04",
                        "instance_type": "t2.micro",
                        "disk_size_gb": 8,
                        "tags": {
                            "Name": vm_name,
                            "CreatedBy": "Glassdome-LabCanvas",
                            "DeploymentId": deployment_id
                        }
                    }
                    
                    try:
                        result = await aws_client.create_vm(vm_config)
                        deployed_vms.append({
                            "name": vm_name,
                            "instance_id": result.get("instance_id"),
                            "status": "deploying"
                        })
                        logger.info(f"Deployed VM: {vm_name} -> {result.get('instance_id')}")
                    except Exception as e:
                        errors.append(f"Failed to deploy {vm_name}: {e}")
                        logger.error(f"Failed to deploy {vm_name}: {e}")
            else:
                errors.append("AWS credentials not configured")
        else:
            # Proxmox deployment - placeholder for now
            for vm_node in vm_nodes:
                data = vm_node.get("data", {})
                element_id = data.get("elementId", "ubuntu")
                vm_name = f"{deployment_id}-{element_id}-{uuid.uuid4().hex[:4]}"
                deployed_vms.append({
                    "name": vm_name,
                    "vmid": f"proxmox-{uuid.uuid4().hex[:6]}",
                    "status": "pending",
                    "note": "Proxmox deployment not yet implemented"
                })
    
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        errors.append(str(e))
    
    return {
        "success": len(deployed_vms) > 0,
        "deployment_id": deployment_id,
        "status": "deploying" if deployed_vms else "failed",
        "message": f"Deploying {len(deployed_vms)} VMs" if deployed_vms else "Deployment failed",
        "vms": deployed_vms,
        "errors": errors if errors else None
    }


@app.get(f"{settings.api_prefix}/deployments")
async def list_deployments():
    """List all deployments"""
    # TODO: Implement deployment listing
    return {
        "deployments": [],
        "total": 0
    }


@app.get(settings.api_prefix + "/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    """Get deployment status and details"""
    # TODO: Implement deployment retrieval
    return {
        "deployment_id": deployment_id,
        "status": "in_progress",
        "progress": 45,
        "resources": []
    }


@app.post(settings.api_prefix + "/deployments/{deployment_id}/stop")
async def stop_deployment(deployment_id: str):
    """Stop all resources in a deployment"""
    # TODO: Implement deployment stop
    return {
        "success": True,
        "deployment_id": deployment_id
    }


@app.delete(settings.api_prefix + "/deployments/{deployment_id}")
async def destroy_deployment(deployment_id: str):
    """Destroy a deployment and all its resources"""
    # TODO: Implement deployment destruction
    return {
        "success": True,
        "deployment_id": deployment_id
    }


# Platform Management Endpoints
@app.get(f"{settings.api_prefix}/platforms")
async def list_platforms():
    """List all configured platforms"""
    # TODO: Implement platform listing
    return {
        "platforms": [
            {"id": "1", "name": "Proxmox", "type": "proxmox", "status": "active"},
            {"id": "2", "name": "Azure", "type": "azure", "status": "inactive"},
            {"id": "3", "name": "AWS", "type": "aws", "status": "inactive"}
        ]
    }


@app.post(f"{settings.api_prefix}/platforms")
async def add_platform(platform_data: Dict[str, Any]):
    """Add a new platform configuration"""
    # TODO: Implement platform addition
    return {
        "success": True,
        "platform_id": "platform_123"
    }


@app.post(settings.api_prefix + "/platforms/{platform_id}/test")
async def test_platform(platform_id: str):
    """Test connection to a platform"""
    # TODO: Implement platform testing
    return {
        "success": True,
        "platform_id": platform_id,
        "status": "connected"
    }


# Template Endpoints
@app.get(f"{settings.api_prefix}/templates")
async def list_templates():
    """List all lab templates"""
    # TODO: Implement template listing
    return {
        "templates": [
            {
                "id": "1",
                "name": "Basic Web Security Lab",
                "category": "Web Security",
                "description": "DVWA + Kali Linux"
            },
            {
                "id": "2",
                "name": "Network Pentesting Lab",
                "category": "Network Security",
                "description": "Multiple vulnerable VMs in isolated network"
            }
        ]
    }


@app.get(settings.api_prefix + "/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    # TODO: Implement template retrieval
    return {
        "template_id": template_id,
        "name": "Example Template",
        "elements": []
    }


@app.post(f"{settings.api_prefix}/templates")
async def create_template(template_data: Dict[str, Any]):
    """Create a new template from a lab"""
    # TODO: Implement template creation
    return {
        "success": True,
        "template_id": "template_123"
    }


# Agent Status Endpoints
@app.get(f"{settings.api_prefix}/agents/status")
async def get_agents_status():
    """Get status of all agents"""
    status = agent_manager.get_status()
    return status


@app.get(settings.api_prefix + "/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get specific agent details"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "agent_id": agent.agent_id,
        "type": agent.agent_type.value,
        "status": agent.status.value,
        "error": agent.error
    }


# Element Library Endpoints
@app.get(f"{settings.api_prefix}/elements")
async def list_elements():
    """List available lab elements (VMs, networks, services)"""
    return {
        "elements": {
            "vms": [
                {"id": "kali-2024", "name": "Kali Linux 2024", "type": "attack"},
                {"id": "dvwa", "name": "DVWA", "type": "vulnerable"},
                {"id": "metasploitable", "name": "Metasploitable 3", "type": "vulnerable"},
                {"id": "ubuntu-22", "name": "Ubuntu 22.04", "type": "base"},
            ],
            "networks": [
                {"id": "isolated", "name": "Isolated Network", "type": "internal"},
                {"id": "nat", "name": "NAT Network", "type": "nat"},
            ],
            "services": [
                {"id": "web-server", "name": "Apache Web Server", "type": "service"},
                {"id": "database", "name": "MySQL Database", "type": "service"},
            ]
        }
    }


# Statistics and Monitoring
@app.get(f"{settings.api_prefix}/stats")
async def get_statistics():
    """Get overall statistics"""
    return {
        "total_labs": 0,
        "active_deployments": 0,
        "total_deployments": 0,
        "total_templates": 0
    }


# Serve static files in production
from glassdome.core.paths import PROJECT_ROOT

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend"""
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)

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
from glassdome.core.database import get_db, init_db
from glassdome.agents.manager import agent_manager
from glassdome.orchestration import OrchestrationEngine

# Import API routers
from glassdome.api.ubuntu import router as ubuntu_router

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


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await init_db()
    # Start agent manager in background
    # asyncio.create_task(agent_manager.start())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
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


@app.get(f"{settings.api_prefix}/labs/{lab_id}")
async def get_lab(lab_id: str):
    """Get lab configuration by ID"""
    # TODO: Implement lab retrieval
    return {
        "lab_id": lab_id,
        "name": "Example Lab",
        "elements": []
    }


@app.put(f"{settings.api_prefix}/labs/{lab_id}")
async def update_lab(lab_id: str, lab_data: Dict[str, Any]):
    """Update lab configuration"""
    # TODO: Implement lab update
    return {
        "success": True,
        "lab_id": lab_id
    }


@app.delete(f"{settings.api_prefix}/labs/{lab_id}")
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
    lab_id = deployment_data.get("lab_id")
    platform_id = deployment_data.get("platform_id")
    
    if not lab_id or not platform_id:
        raise HTTPException(status_code=400, detail="lab_id and platform_id required")
    
    # TODO: Implement deployment creation and orchestration
    return {
        "success": True,
        "deployment_id": "deploy_123",
        "status": "pending",
        "message": "Deployment initiated"
    }


@app.get(f"{settings.api_prefix}/deployments")
async def list_deployments():
    """List all deployments"""
    # TODO: Implement deployment listing
    return {
        "deployments": [],
        "total": 0
    }


@app.get(f"{settings.api_prefix}/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    """Get deployment status and details"""
    # TODO: Implement deployment retrieval
    return {
        "deployment_id": deployment_id,
        "status": "in_progress",
        "progress": 45,
        "resources": []
    }


@app.post(f"{settings.api_prefix}/deployments/{deployment_id}/stop")
async def stop_deployment(deployment_id: str):
    """Stop all resources in a deployment"""
    # TODO: Implement deployment stop
    return {
        "success": True,
        "deployment_id": deployment_id
    }


@app.delete(f"{settings.api_prefix}/deployments/{deployment_id}")
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


@app.post(f"{settings.api_prefix}/platforms/{platform_id}/test")
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


@app.get(f"{settings.api_prefix}/templates/{template_id}")
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


@app.get(f"{settings.api_prefix}/agents/{agent_id}")
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
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend"""
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        file_path = f"frontend/dist/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        return FileResponse("frontend/dist/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)

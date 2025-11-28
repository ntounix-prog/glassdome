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
from sqlalchemy.ext.asyncio import AsyncSession
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
from glassdome.api.networks import router as networks_router
from glassdome.api.whitepawn import router as whitepawn_router
from glassdome.api.canvas_deploy import router as canvas_deploy_router
from glassdome.api.container_dispatch import router as dispatch_router
from glassdome.api.registry import router as registry_router

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
app.include_router(networks_router)  # Network management
app.include_router(whitepawn_router)  # WhitePawn continuous monitoring
app.include_router(canvas_deploy_router)  # Canvas lab deployment
app.include_router(dispatch_router)  # Container worker dispatch
app.include_router(registry_router)  # Lab Registry - source of truth


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
    
    # Start background services (non-blocking to allow fast startup)
    import asyncio
    
    # Start Hot Spare Pool Manager (guardian process for spare VMs)
    try:
        from glassdome.reaper.hot_spare import get_hot_spare_pool
        pool = get_hot_spare_pool()
        asyncio.create_task(pool.start())
        logger.info("Hot Spare Pool Manager starting (background)")
    except Exception as e:
        logger.warning(f"Could not start Hot Spare Pool Manager: {e}")
    
    # Start Network Reconciler (checks DB state vs platform state every 30s)
    try:
        from glassdome.networking.reconciler import get_network_reconciler
        reconciler = get_network_reconciler(interval=30)
        asyncio.create_task(reconciler.start())
        logger.info("Network Reconciler starting (background)")
    except Exception as e:
        logger.warning(f"Could not start Network Reconciler: {e}")
    
    # Start WhitePawn Orchestrator (continuous network monitoring)
    try:
        from glassdome.whitepawn.orchestrator import get_whitepawn_orchestrator
        whitepawn = get_whitepawn_orchestrator()
        asyncio.create_task(whitepawn.start())
        logger.info("WhitePawn Orchestrator starting (background)")
    except Exception as e:
        logger.warning(f"Could not start WhitePawn Orchestrator: {e}")
    
    # Start Lab Registry (central source of truth)
    # Use create_task to avoid blocking startup on slow network connections
    try:
        import asyncio
        from glassdome.registry.core import init_registry
        from glassdome.registry.agents.proxmox_agent import create_proxmox_agents
        from glassdome.registry.agents.unifi_agent import get_unifi_agent
        from glassdome.registry.controllers.lab_controller import get_lab_controller
        
        # Initialize registry (Redis connection)
        registry = await init_registry()
        logger.info("Lab Registry initialized - Redis connected")
        
        # Start Proxmox agents in background (don't block startup)
        proxmox_agents = create_proxmox_agents()
        for agent in proxmox_agents:
            asyncio.create_task(agent.start())
        logger.info(f"Started {len(proxmox_agents)} Proxmox agents (background)")
        
        # Start Unifi agent in background
        unifi_agent = get_unifi_agent()
        asyncio.create_task(unifi_agent.start())
        logger.info("Unifi agent started (background)")
        
        # Start Lab Controller in background
        lab_controller = get_lab_controller()
        asyncio.create_task(lab_controller.start())
        logger.info("Lab Controller started (background)")
        
    except Exception as e:
        logger.warning(f"Could not start Lab Registry: {e}")
    
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
    
    # Stop Network Reconciler
    try:
        from glassdome.networking.reconciler import get_network_reconciler
        reconciler = get_network_reconciler()
        await reconciler.stop()
        logger.info("Network Reconciler stopped")
    except Exception as e:
        logger.warning(f"Error stopping Network Reconciler: {e}")
    
    # Stop WhitePawn Orchestrator
    try:
        from glassdome.whitepawn.orchestrator import get_whitepawn_orchestrator
        whitepawn = get_whitepawn_orchestrator()
        await whitepawn.stop()
        logger.info("WhitePawn Orchestrator stopped")
    except Exception as e:
        logger.warning(f"Error stopping WhitePawn Orchestrator: {e}")
    
    # Stop Lab Registry components
    try:
        from glassdome.registry.controllers.lab_controller import get_lab_controller
        from glassdome.registry.agents.unifi_agent import get_unifi_agent
        from glassdome.registry.core import get_registry
        
        # Stop controller
        lab_controller = get_lab_controller()
        await lab_controller.stop()
        
        # Stop Unifi agent
        unifi_agent = get_unifi_agent()
        await unifi_agent.stop()
        
        # Disconnect registry
        registry = get_registry()
        await registry.disconnect()
        
        logger.info("Lab Registry stopped")
    except Exception as e:
        logger.warning(f"Error stopping Lab Registry: {e}")
    
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
async def create_lab(lab_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Create or update a lab configuration"""
    from glassdome.models.lab import Lab
    from sqlalchemy import select
    
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


@app.get(f"{settings.api_prefix}/labs")
async def list_labs(db: AsyncSession = Depends(get_db)):
    """List all lab configurations"""
    from glassdome.models.lab import Lab
    from sqlalchemy import select
    
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


@app.get(settings.api_prefix + "/labs/{lab_id}")
async def get_lab(lab_id: str, db: AsyncSession = Depends(get_db)):
    """Get lab configuration by ID"""
    from glassdome.models.lab import Lab
    from sqlalchemy import select
    
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


@app.put(settings.api_prefix + "/labs/{lab_id}")
async def update_lab(lab_id: str, lab_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Update lab configuration"""
    from glassdome.models.lab import Lab
    from sqlalchemy import select
    
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


@app.delete(settings.api_prefix + "/labs/{lab_id}")
async def delete_lab(lab_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a lab configuration"""
    from glassdome.models.lab import Lab
    from sqlalchemy import select, delete
    
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail=f"Lab {lab_id} not found")
    
    await db.execute(delete(Lab).where(Lab.id == lab_id))
    await db.commit()
    return {"success": True, "lab_id": lab_id}


# NOTE: Canvas lab deployment endpoints moved to glassdome/api/canvas_deploy.py
# Uses hot spare pool (fast) or build agents (fallback)


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

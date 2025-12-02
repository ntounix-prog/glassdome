"""
Glassdome Main Application Module

Agentic Cyber Range Deployment Framework

This is the main FastAPI application entry point. All route handlers
are organized in separate modules under glassdome/api/.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from glassdome.core.config import settings
from glassdome.core.database import init_db
from glassdome.core.paths import PROJECT_ROOT
from glassdome.agents.manager import agent_manager
from glassdome.api.v1 import setup_v1_routes

logger = logging.getLogger(__name__)

# =============================================================================
# Application Initialization
# =============================================================================

app = FastAPI(
    title="Glassdome API",
    description="Agentic Cyber Range Deployment Framework",
    version=settings.app_version,
)

# CORS Configuration
# Note: When using wildcard "*" origins, credentials must be False (CORS spec requirement)
_cors_origins = settings.backend_cors_origins
_allow_credentials = "*" not in _cors_origins  # Disable credentials if using wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up all API routes (v1 + legacy)
setup_v1_routes(app)


# =============================================================================
# Health and Root Endpoints (legacy /api/ prefix)
# =============================================================================

@app.get(f"{settings.api_prefix}/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Glassdome API is running",
        "version": settings.app_version
    }


@app.get(f"{settings.api_prefix}/")
async def root():
    """Root API endpoint."""
    return {
        "message": "Glassdome - Agentic Cyber Range Deployment Framework",
        "version": settings.app_version,
        "docs": "/docs"
    }


# =============================================================================
# Startup and Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Initialize session from cache (no password prompt if cached)
    from glassdome.core.session import get_session
    session = get_session()
    if session.initialize(use_cache=True, interactive=False):
        logger.info(f"Session loaded with {len(session.secrets)} secrets")
    
    await init_db()
    
    # Start background services (non-blocking)
    await _start_background_services()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await _stop_background_services()
    await agent_manager.stop()


async def _start_background_services():
    """Start all background services."""
    # Hot Spare Pool Managers (one per OS type)
    # Set HOT_SPARE_ENABLED=false to disable (e.g., to stop clone storms)
    import os
    hot_spare_enabled = os.getenv("HOT_SPARE_ENABLED", "true").lower() != "false"
    if hot_spare_enabled:
        try:
            from glassdome.reaper.hot_spare import initialize_all_pools, POOL_CONFIGS
            asyncio.create_task(initialize_all_pools())
            logger.info(f"Hot Spare Pool Managers starting for: {list(POOL_CONFIGS.keys())}")
        except Exception as e:
            logger.warning(f"Could not start Hot Spare Pool Managers: {e}")
    else:
        logger.info("Hot Spare Pool Managers DISABLED via HOT_SPARE_ENABLED=false")
    
    # Network Reconciler
    try:
        from glassdome.networking.reconciler import get_network_reconciler
        reconciler = get_network_reconciler(interval=30)
        asyncio.create_task(reconciler.start())
        logger.info("Network Reconciler starting (background)")
    except Exception as e:
        logger.warning(f"Could not start Network Reconciler: {e}")
    
    # WhitePawn Orchestrator
    try:
        from glassdome.whitepawn.orchestrator import get_whitepawn_orchestrator
        whitepawn = get_whitepawn_orchestrator()
        asyncio.create_task(whitepawn.start())
        logger.info("WhitePawn Orchestrator starting (background)")
    except Exception as e:
        logger.warning(f"Could not start WhitePawn Orchestrator: {e}")
    
    # Lab Registry
    try:
        from glassdome.registry.core import init_registry
        from glassdome.registry.agents.proxmox_agent import create_proxmox_agents
        from glassdome.registry.agents.unifi_agent import get_unifi_agent
        from glassdome.registry.controllers.lab_controller import get_lab_controller
        
        registry = await init_registry()
        logger.info("Lab Registry initialized - Redis connected")
        
        # Start Proxmox agents
        proxmox_agents = create_proxmox_agents()
        for agent in proxmox_agents:
            asyncio.create_task(agent.start())
        logger.info(f"Started {len(proxmox_agents)} Proxmox agents (background)")
        
        # Start Unifi agent
        unifi_agent = get_unifi_agent()
        asyncio.create_task(unifi_agent.start())
        logger.info("Unifi agent started (background)")
        
        # Start Lab Controller
        lab_controller = get_lab_controller()
        asyncio.create_task(lab_controller.start())
        logger.info("Lab Controller started (background)")
        
    except Exception as e:
        logger.warning(f"Could not start Lab Registry: {e}")
    
    # Registry Reconciler (keeps Redis in sync with all platforms)
    # DISABLED: Causing Redis WRONGTYPE errors - needs debugging
    # try:
    #     from glassdome.registry import get_reconciler
    #     reconciler = get_reconciler()
    #     asyncio.create_task(reconciler.start_background_reconciliation(interval_seconds=300))
    #     logger.info("Registry Reconciler starting (5 min interval)")
    # except Exception as e:
    #     logger.warning(f"Could not start Registry Reconciler: {e}")
    logger.info("Registry Reconciler DISABLED - manual reconciliation available at /api/reconciler/run")
    
    # Pre-warm Chat Agent (so it's instant when modal opens)
    try:
        from glassdome.api.chat import get_chat_agent
        logger.info("Pre-warming Chat Agent...")
        chat_agent = get_chat_agent()
        providers = chat_agent.llm.list_available_providers()
        logger.info(f"✓ Chat Agent ready with providers: {providers}")
    except Exception as e:
        logger.warning(f"Could not pre-warm Chat Agent: {e}")
    
    # Overseer State Sync (DB reconciliation with Proxmox)
    try:
        from glassdome.overseer.state_sync import get_state_sync, get_sync_scheduler
        state_sync = get_state_sync(backend_url="http://localhost:8000")
        sync_scheduler = get_sync_scheduler(interval=300)  # 5 minutes
        asyncio.create_task(sync_scheduler.start())
        logger.info("✓ Overseer State Sync starting (5 min interval)")
    except Exception as e:
        logger.warning(f"Could not start Overseer State Sync: {e}")


async def _stop_background_services():
    """Stop all background services."""
    # Hot Spare Pool Managers (all OS types)
    try:
        from glassdome.reaper.hot_spare import get_all_pools
        pools = get_all_pools()
        for os_type, pool in pools.items():
            await pool.stop()
            logger.info(f"Hot Spare Pool Manager stopped for {os_type}")
    except Exception as e:
        logger.warning(f"Error stopping Hot Spare Pool Managers: {e}")
    
    # Network Reconciler
    try:
        from glassdome.networking.reconciler import get_network_reconciler
        reconciler = get_network_reconciler()
        await reconciler.stop()
        logger.info("Network Reconciler stopped")
    except Exception as e:
        logger.warning(f"Error stopping Network Reconciler: {e}")
    
    # WhitePawn Orchestrator
    try:
        from glassdome.whitepawn.orchestrator import get_whitepawn_orchestrator
        whitepawn = get_whitepawn_orchestrator()
        await whitepawn.stop()
        logger.info("WhitePawn Orchestrator stopped")
    except Exception as e:
        logger.warning(f"Error stopping WhitePawn Orchestrator: {e}")
    
    # Registry Reconciler
    try:
        from glassdome.registry import get_reconciler
        reconciler = get_reconciler()
        await reconciler.stop()
        logger.info("Registry Reconciler stopped")
    except Exception as e:
        logger.warning(f"Error stopping Registry Reconciler: {e}")
    
    # Overseer State Sync Scheduler
    try:
        from glassdome.overseer.state_sync import get_sync_scheduler
        scheduler = get_sync_scheduler()
        await scheduler.stop()
        logger.info("Overseer State Sync stopped")
    except Exception as e:
        logger.warning(f"Error stopping Overseer State Sync: {e}")
    
    # Lab Registry
    try:
        from glassdome.registry.controllers.lab_controller import get_lab_controller
        from glassdome.registry.agents.unifi_agent import get_unifi_agent
        from glassdome.registry.core import get_registry
        
        lab_controller = get_lab_controller()
        await lab_controller.stop()
        
        unifi_agent = get_unifi_agent()
        await unifi_agent.stop()
        
        registry = get_registry()
        await registry.disconnect()
        
        logger.info("Lab Registry stopped")
    except Exception as e:
        logger.warning(f"Error stopping Lab Registry: {e}")


# =============================================================================
# Static File Serving (Frontend)
# =============================================================================

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend."""
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        return FileResponse(str(FRONTEND_DIST / "index.html"))


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)

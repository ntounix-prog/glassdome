"""
Overseer Service - Central Control Plane for Glassdome

Manages:
- Health monitoring of all services (frontend, backend, whitepawn, proxmox)
- State synchronization between DB and infrastructure
- Reconciliation of orphaned records
- Observability and alerting

Author: Brett Turner (ntounix)
Created: November 2025
Updated: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from glassdome.overseer.entity import OverseerEntity
from glassdome.overseer.health_monitor import get_health_monitor, HealthMonitor, ServiceStatus
from glassdome.overseer.state_sync import get_state_sync, get_sync_scheduler, StateSync

logger = logging.getLogger(__name__)

# Configuration from environment
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
STATE_SYNC_INTERVAL = int(os.getenv("STATE_SYNC_INTERVAL", "300"))


# ═══════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════

class DeployVMRequest(BaseModel):
    platform: str
    os: str
    specs: Optional[Dict[str, Any]] = None
    user: str = "api-user"


class DestroyVMRequest(BaseModel):
    vm_id: str
    force_production: bool = False
    user: str = "api-user"


class StartStopVMRequest(BaseModel):
    vm_id: str
    user: str = "api-user"


class GenericRequest(BaseModel):
    action: str
    params: Dict[str, Any]
    user: str = "api-user"


class ReaperMissionRequest(BaseModel):
    mission_id: str
    lab_id: str
    mission_type: str
    target_vms: List[Dict[str, str]]


class SyncResponse(BaseModel):
    success: bool
    message: str
    stats: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    overall: str
    services: Dict[str, Any]
    unhealthy_count: int
    degraded_count: int
    last_check: str


# ═══════════════════════════════════════════════════
# Global State
# ═══════════════════════════════════════════════════

overseer: Optional[OverseerEntity] = None
health_monitor: Optional[HealthMonitor] = None
state_sync: Optional[StateSync] = None


# ═══════════════════════════════════════════════════
# Lifecycle Management
# ═══════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage Overseer lifecycle.
    
    Starts:
    - OverseerEntity (infrastructure management)
    - HealthMonitor (service health checks)
    - StateSyncScheduler (periodic DB reconciliation)
    """
    global overseer, health_monitor, state_sync
    
    print("\n" + "="*60)
    print("🚀 Starting Glassdome Overseer Service")
    print("="*60)
    
    # Initialize Overseer Entity
    try:
        from glassdome.core.security import get_secure_settings
        settings = get_secure_settings()
        overseer = OverseerEntity(settings)
        overseer_task = asyncio.create_task(overseer.run())
        logger.info("✓ OverseerEntity started")
    except Exception as e:
        logger.warning(f"OverseerEntity failed to start: {e}")
        overseer = None
        overseer_task = None
    
    # Initialize Health Monitor
    health_monitor = get_health_monitor(
        frontend_url=FRONTEND_URL,
        backend_url=BACKEND_URL,
        check_interval=HEALTH_CHECK_INTERVAL
    )
    await health_monitor.start()
    logger.info(f"✓ HealthMonitor started (interval: {HEALTH_CHECK_INTERVAL}s)")
    
    # Initialize State Sync Scheduler
    state_sync = get_state_sync(backend_url=BACKEND_URL)
    sync_scheduler = get_sync_scheduler(interval=STATE_SYNC_INTERVAL)
    await sync_scheduler.start()
    logger.info(f"✓ StateSyncScheduler started (interval: {STATE_SYNC_INTERVAL}s)")
    
    print("\n✓ Overseer Service Ready")
    print(f"  - Health checks every {HEALTH_CHECK_INTERVAL}s")
    print(f"  - State sync every {STATE_SYNC_INTERVAL}s")
    print(f"  - Backend URL: {BACKEND_URL}")
    print(f"  - Frontend URL: {FRONTEND_URL}")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n🛑 Stopping Overseer Service...")
    
    await sync_scheduler.stop()
    await health_monitor.stop()
    
    if overseer:
        overseer.shutdown()
        if overseer_task:
            overseer_task.cancel()
            try:
                await overseer_task
            except asyncio.CancelledError:
                pass
    
    print("✓ Overseer Service stopped\n")


# ═══════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════

app = FastAPI(
    title="Glassdome Overseer",
    description="Central control plane for Glassdome infrastructure management",
    version="0.2.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════
# Health & Status Endpoints
# ═══════════════════════════════════════════════════

@app.get("/")
async def root():
    """Health check for the Overseer service itself"""
    return {
        "service": "Glassdome Overseer",
        "status": "running",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def get_health():
    """Get health status of all monitored services"""
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Health monitor not initialized")
    
    status = health_monitor.get_status()
    return HealthResponse(**status)


@app.get("/health/history")
async def get_health_history(limit: int = 100):
    """Get health check history"""
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Health monitor not initialized")
    
    return {
        "history": health_monitor.get_history(limit=limit),
        "count": len(health_monitor.get_history(limit=limit))
    }


@app.get("/health/{service_name}")
async def get_service_health(service_name: str):
    """Get health status of a specific service"""
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Health monitor not initialized")
    
    service = health_monitor.services.get(service_name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    return service.to_dict()


# ═══════════════════════════════════════════════════
# State Sync Endpoints
# ═══════════════════════════════════════════════════

@app.post("/sync", response_model=SyncResponse)
async def force_state_sync(background_tasks: BackgroundTasks):
    """
    Force immediate state synchronization.
    
    Reconciles database with actual Proxmox state:
    - Removes orphaned deployed_vms records
    - Cleans up stale hot_spares
    - Updates VM IP addresses
    
    Runs in background to avoid timeout.
    """
    if not state_sync:
        raise HTTPException(status_code=503, detail="State sync not initialized")
    
    async def do_sync():
        result = await state_sync.sync_all()
        if result.success:
            logger.info(f"Manual sync complete: {result.deployed_vms_cleaned} cleaned")
        else:
            logger.error(f"Manual sync failed: {result.errors}")
    
    background_tasks.add_task(do_sync)
    
    return SyncResponse(
        success=True,
        message="State sync started in background"
    )


@app.post("/sync/now", response_model=SyncResponse)
async def force_state_sync_blocking():
    """
    Force immediate state synchronization (blocking).
    
    Waits for sync to complete before returning.
    WARNING: Can take several seconds.
    """
    if not state_sync:
        raise HTTPException(status_code=503, detail="State sync not initialized")
    
    result = await state_sync.sync_all()
    
    return SyncResponse(
        success=result.success,
        message="State sync complete" if result.success else "State sync failed",
        stats=result.to_dict()
    )


@app.get("/sync/status")
async def get_sync_status():
    """Get last sync result and history"""
    if not state_sync:
        raise HTTPException(status_code=503, detail="State sync not initialized")
    
    return {
        "last_sync": state_sync.get_last_sync(),
        "history": state_sync.get_sync_history(limit=20),
        "scheduler": {
            "interval_seconds": STATE_SYNC_INTERVAL,
            "running": True
        }
    }


# ═══════════════════════════════════════════════════
# Overseer Entity Status
# ═══════════════════════════════════════════════════

@app.get("/status")
async def get_status():
    """Get comprehensive Overseer status"""
    status = {
        "overseer": {
            "initialized": overseer is not None,
            "stats": overseer.stats if overseer else None
        },
        "health_monitor": {
            "running": health_monitor._running if health_monitor else False,
            "services": len(health_monitor.services) if health_monitor else 0
        },
        "state_sync": {
            "last_sync": state_sync.get_last_sync() if state_sync else None
        },
        "config": {
            "frontend_url": FRONTEND_URL,
            "backend_url": BACKEND_URL,
            "health_check_interval": HEALTH_CHECK_INTERVAL,
            "state_sync_interval": STATE_SYNC_INTERVAL
        }
    }
    
    return status


@app.get("/state/summary")
async def get_state_summary():
    """Get state summary from OverseerEntity"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return overseer.state.get_summary()


@app.get("/state/vms")
async def get_vms():
    """Get all VMs tracked by Overseer"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return {
        "vms": [
            {
                "id": vm.id,
                "name": vm.name,
                "platform": vm.platform,
                "status": vm.status.value,
                "ip": vm.ip,
                "is_production": vm.is_production
            }
            for vm in overseer.state.vms.values()
        ]
    }


@app.get("/state/hosts")
async def get_hosts():
    """Get all hosts tracked by Overseer"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return {
        "hosts": [
            {
                "platform": host.platform,
                "identifier": host.identifier,
                "status": host.status.value,
                "resources": host.resources,
                "vm_count": len(host.vms)
            }
            for host in overseer.state.hosts.values()
        ]
    }


# ═══════════════════════════════════════════════════
# Request Submission (VM Operations)
# ═══════════════════════════════════════════════════

@app.post("/request/deploy_vm")
async def request_deploy_vm(request: DeployVMRequest):
    """Submit VM deployment request"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    result = await overseer.receive_request(
        action='deploy_vm',
        params={
            'platform': request.platform,
            'os': request.os,
            'specs': request.specs or {}
        },
        user=request.user
    )
    return result


@app.post("/request/destroy_vm")
async def request_destroy_vm(request: DestroyVMRequest):
    """Submit VM destruction request"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    result = await overseer.receive_request(
        action='destroy_vm',
        params={
            'vm_id': request.vm_id,
            'force_production': request.force_production
        },
        user=request.user
    )
    return result


@app.post("/request/start_vm")
async def request_start_vm(request: StartStopVMRequest):
    """Submit VM start request"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    result = await overseer.receive_request(
        action='start_vm',
        params={'vm_id': request.vm_id},
        user=request.user
    )
    return result


@app.post("/request/stop_vm")
async def request_stop_vm(request: StartStopVMRequest):
    """Submit VM stop request"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    result = await overseer.receive_request(
        action='stop_vm',
        params={'vm_id': request.vm_id},
        user=request.user
    )
    return result


# ═══════════════════════════════════════════════════
# Admin Endpoints
# ═══════════════════════════════════════════════════

@app.get("/admin/stats")
async def get_stats():
    """Get Overseer statistics"""
    if not overseer:
        return {"error": "Overseer not initialized", "stats": None}
    
    return overseer.stats


@app.get("/requests/pending")
async def get_pending_requests():
    """Get all pending requests"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return {
        "requests": [
            {
                "request_id": req.request_id,
                "action": req.action,
                "user": req.user,
                "status": req.status,
                "submitted_at": req.submitted_at
            }
            for req in overseer.state.get_pending_requests()
        ]
    }


# ═══════════════════════════════════════════════════
# Reaper Mission Endpoints
# ═══════════════════════════════════════════════════

@app.post("/reaper/missions")
async def create_reaper_mission(request: ReaperMissionRequest):
    """Create a new Reaper vulnerability injection mission"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    result = overseer.create_reaper_mission(
        mission_id=request.mission_id,
        lab_id=request.lab_id,
        mission_type=request.mission_type,
        target_vms=request.target_vms
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.get("/reaper/missions")
async def list_reaper_missions():
    """List all Reaper missions"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return {"missions": overseer.list_reaper_missions()}


@app.get("/reaper/missions/{mission_id}")
async def get_reaper_mission_status(mission_id: str):
    """Get status of a Reaper mission"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    status = overseer.get_reaper_mission_status(mission_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

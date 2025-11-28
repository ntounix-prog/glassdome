"""
API endpoints for container_dispatch

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


# ============================================================================
# Request Models
# ============================================================================

class LabDeployRequest(BaseModel):
    lab_id: str
    lab_data: Dict[str, Any]
    platform_id: str = "1"


class MissionRequest(BaseModel):
    mission_id: str
    target_vms: List[Dict[str, Any]]
    exploits: List[str]
    vlan_id: Optional[int] = None


class ValidationRequest(BaseModel):
    mission_id: str
    target_vms: List[Dict[str, Any]]
    exploits: List[str]
    vlan_id: Optional[int] = None


# ============================================================================
# Dispatch Endpoints
# ============================================================================

@router.post("/lab")
async def dispatch_lab_deployment(request: LabDeployRequest):
    """
    Dispatch a lab deployment to the container orchestrator.
    
    The orchestrator will:
    1. Allocate a VLAN (100-170)
    2. Deploy all VMs in PARALLEL
    3. Configure networking (net0 on vmbr{vlan})
    4. Start WhitePawn monitoring
    
    Returns task_id for tracking. Poll /api/dispatch/task/{task_id} for status.
    """
    try:
        from glassdome.workers.orchestrator import deploy_lab
        
        logger.info(f"Dispatching lab deployment: {request.lab_id}")
        
        task = deploy_lab.delay(
            lab_id=request.lab_id,
            lab_data=request.lab_data,
            platform_id=request.platform_id
        )
        
        logger.info(f"Lab {request.lab_id} queued as task {task.id}")
        
        return {
            "success": True,
            "task_id": task.id,
            "lab_id": request.lab_id,
            "status": "queued",
            "message": "Lab deployment dispatched to container orchestrator",
            "track_url": f"/api/dispatch/task/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to dispatch lab deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mission")
async def dispatch_reaper_mission(request: MissionRequest):
    """
    Dispatch a Reaper mission to inject vulnerabilities.
    
    Reaper worker containers:
    1. Attach to lab VLAN (if specified)
    2. SSH into target VMs
    3. Execute exploit install scripts
    4. Verify injection
    5. Detach from VLAN
    """
    try:
        from glassdome.workers.reaper import run_mission
        
        logger.info(f"Dispatching Reaper mission: {request.mission_id} -> {len(request.target_vms)} VMs, {len(request.exploits)} exploits")
        
        task = run_mission.delay(
            mission_id=request.mission_id,
            target_vms=request.target_vms,
            exploits=request.exploits,
            vlan_id=request.vlan_id
        )
        
        return {
            "success": True,
            "task_id": task.id,
            "mission_id": request.mission_id,
            "status": "queued",
            "message": "Reaper mission dispatched",
            "track_url": f"/api/dispatch/task/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to dispatch Reaper mission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def dispatch_whiteknight_validation(request: ValidationRequest):
    """
    Dispatch a WhiteKnight validation to verify vulnerabilities are exploitable.
    
    WhiteKnight worker containers:
    1. Attach to lab VLAN
    2. Run validation tests (SSH, SQL injection, web scans)
    3. Report exploitability status
    4. Detach from VLAN
    """
    try:
        from glassdome.workers.whiteknight import validate_mission
        
        logger.info(f"Dispatching WhiteKnight validation: {request.mission_id}")
        
        task = validate_mission.delay(
            mission_id=request.mission_id,
            target_vms=request.target_vms,
            exploits=request.exploits,
            vlan_id=request.vlan_id
        )
        
        return {
            "success": True,
            "task_id": task.id,
            "mission_id": request.mission_id,
            "status": "queued",
            "message": "WhiteKnight validation dispatched",
            "track_url": f"/api/dispatch/task/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to dispatch WhiteKnight validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a dispatched task.
    """
    try:
        from glassdome.workers.celery_app import celery_app
        
        result = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready()
        }
        
        if result.ready():
            if result.successful():
                response["result"] = result.get()
            else:
                response["error"] = str(result.result)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers")
async def get_workers():
    """
    Get the status of all container workers.
    """
    try:
        from glassdome.workers.celery_app import celery_app
        
        # Get active workers
        inspect = celery_app.control.inspect()
        
        active = inspect.active() or {}
        stats = inspect.stats() or {}
        
        workers = []
        for worker_name, info in stats.items():
            workers.append({
                "name": worker_name,
                "pool": info.get("pool", {}).get("implementation", "unknown"),
                "concurrency": info.get("pool", {}).get("max-concurrency"),
                "active_tasks": len(active.get(worker_name, [])),
                "total_tasks": info.get("total", {})
            })
        
        return {
            "workers": workers,
            "total": len(workers)
        }
        
    except Exception as e:
        logger.error(f"Failed to get workers: {e}")
        # Redis not available - containers not running
        return {
            "workers": [],
            "total": 0,
            "message": "Container workers not running. Start with: docker-compose up -d"
        }


@router.get("/health")
async def get_dispatch_health():
    """
    Health check for the container dispatch system.
    
    Returns status of:
    - Redis (task queue)
    - Celery workers (by type)
    - Recent task stats
    
    If this returns unhealthy, check:
    - docker-compose ps (are containers running?)
    - docker-compose logs redis
    - docker-compose logs orchestrator
    """
    health = {
        "status": "healthy",
        "redis": {"status": "unknown"},
        "workers": {},
        "issues": []
    }
    
    # Check Redis
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        if r.ping():
            health["redis"] = {
                "status": "healthy",
                "connected": True,
                "queue_lengths": {
                    "deploy": r.llen("deploy") if r.exists("deploy") else 0,
                    "inject": r.llen("inject") if r.exists("inject") else 0,
                    "validate": r.llen("validate") if r.exists("validate") else 0,
                }
            }
        else:
            health["redis"]["status"] = "unhealthy"
            health["issues"].append("Redis not responding to ping")
    except Exception as e:
        health["redis"] = {"status": "unhealthy", "error": str(e)}
        health["issues"].append(f"Redis connection failed: {e}")
    
    # Check workers
    try:
        from glassdome.workers.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=2.0)
        
        stats = inspect.stats() or {}
        active = inspect.active() or {}
        
        for worker_name, info in stats.items():
            worker_type = "unknown"
            if "orchestrator" in worker_name:
                worker_type = "orchestrator"
            elif "reaper" in worker_name:
                worker_type = "reaper"
            elif "whiteknight" in worker_name:
                worker_type = "whiteknight"
            elif "whitepawn" in worker_name:
                worker_type = "whitepawn"
            
            health["workers"][worker_name] = {
                "type": worker_type,
                "status": "healthy",
                "concurrency": info.get("pool", {}).get("max-concurrency"),
                "active_tasks": len(active.get(worker_name, []))
            }
        
        if not stats:
            health["issues"].append("No Celery workers connected")
            
    except Exception as e:
        health["issues"].append(f"Celery inspection failed: {e}")
    
    # Determine overall status
    if health["issues"]:
        health["status"] = "unhealthy" if "Redis" in str(health["issues"]) else "degraded"
    
    return health

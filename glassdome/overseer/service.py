"""
Overseer Service - FastAPI wrapper for autonomous entity

Provides REST API for:
- Submitting requests
- Checking status
- Querying state
- Administrative control
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
from contextlib import asynccontextmanager

from glassdome.overseer.entity import OverseerEntity
from glassdome.core.security import get_secure_settings


# Pydantic models for API
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


# Global Overseer instance
overseer: Optional[OverseerEntity] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage Overseer lifecycle
    Start on app startup, shutdown gracefully on exit
    """
    global overseer
    
    print("\n🚀 Starting Overseer Service...")
    # Ensure security context and get Settings from authenticated session
    settings = get_secure_settings()
    overseer = OverseerEntity(settings)
    
    # Start overseer in background
    overseer_task = asyncio.create_task(overseer.run())
    
    yield
    
    # Shutdown
    print("\n🛑 Stopping Overseer Service...")
    overseer.shutdown()
    overseer_task.cancel()
    try:
        await overseer_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Glassdome Overseer",
    description="Autonomous infrastructure management entity",
    version="0.1.0",
    lifespan=lifespan
)


# ═══════════════════════════════════════════════════
# Status & Information Endpoints
# ═══════════════════════════════════════════════════

@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Glassdome Overseer",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/status")
async def get_status():
    """Get Overseer status"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return overseer.get_status()


@app.get("/state/summary")
async def get_state_summary():
    """Get state summary"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return overseer.state.get_summary()


@app.get("/state/vms")
async def get_vms():
    """Get all VMs"""
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


@app.get("/state/vms/{vm_id}")
async def get_vm(vm_id: str):
    """Get specific VM"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    vm = overseer.state.get_vm(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM {vm_id} not found")
    
    return {
        "id": vm.id,
        "name": vm.name,
        "platform": vm.platform,
        "status": vm.status.value,
        "ip": vm.ip,
        "specs": vm.specs,
        "services": vm.services,
        "is_production": vm.is_production,
        "deployed_at": vm.deployed_at,
        "deployed_by": vm.deployed_by
    }


@app.get("/state/hosts")
async def get_hosts():
    """Get all hosts"""
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
# Request Submission Endpoints
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


@app.post("/request/generic")
async def request_generic(request: GenericRequest):
    """Submit generic request"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    result = await overseer.receive_request(
        action=request.action,
        params=request.params,
        user=request.user
    )
    
    return result


# ═══════════════════════════════════════════════════
# Request Tracking
# ═══════════════════════════════════════════════════

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


@app.get("/requests/{request_id}")
async def get_request_status(request_id: str):
    """Get request status"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    request = overseer.state.requests.get(request_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    return {
        "request_id": request.request_id,
        "action": request.action,
        "user": request.user,
        "params": request.params,
        "status": request.status,
        "submitted_at": request.submitted_at,
        "approved_at": request.approved_at,
        "completed_at": request.completed_at,
        "result": request.result,
        "denial_reason": request.denial_reason
    }


# ═══════════════════════════════════════════════════
# Administrative Endpoints
# ═══════════════════════════════════════════════════

@app.get("/admin/stats")
async def get_stats():
    """Get Overseer statistics"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    return overseer.stats


@app.post("/admin/force_state_sync")
async def force_state_sync():
    """Force immediate state synchronization"""
    if not overseer:
        raise HTTPException(status_code=503, detail="Overseer not initialized")
    
    # TODO: Trigger immediate sync
    return {"message": "State sync triggered (not yet implemented)"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


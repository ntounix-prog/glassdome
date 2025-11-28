"""
API endpoints for whitepawn

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.core.database import get_db
from glassdome.whitepawn.orchestrator import get_whitepawn_orchestrator
from glassdome.networking.reconciler import get_network_reconciler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whitepawn", tags=["whitepawn"])


# ============================================================================
# Pydantic Models
# ============================================================================

class DeployRequest(BaseModel):
    lab_id: str
    lab_name: Optional[str] = None
    config: Optional[dict] = None


class AlertAcknowledge(BaseModel):
    user: str


# ============================================================================
# Orchestrator Endpoints
# ============================================================================

@router.get("/status")
async def get_status():
    """Get WhitePawn orchestrator status"""
    orchestrator = get_whitepawn_orchestrator()
    return await orchestrator.get_status()


@router.post("/start")
async def start_orchestrator():
    """Start the WhitePawn orchestrator"""
    orchestrator = get_whitepawn_orchestrator()
    await orchestrator.start()
    return {"success": True, "message": "WhitePawn orchestrator started"}


@router.post("/stop")
async def stop_orchestrator():
    """Stop the WhitePawn orchestrator"""
    orchestrator = get_whitepawn_orchestrator()
    await orchestrator.stop()
    return {"success": True, "message": "WhitePawn orchestrator stopped"}


# ============================================================================
# Deployment Endpoints
# ============================================================================

@router.get("/deployments")
async def list_deployments():
    """List all WhitePawn deployments"""
    orchestrator = get_whitepawn_orchestrator()
    deployments = await orchestrator.get_all_deployments()
    return {
        "deployments": deployments,
        "total": len(deployments)
    }


@router.post("/deploy")
async def deploy_whitepawn(request: DeployRequest):
    """Deploy WhitePawn monitoring for a lab"""
    orchestrator = get_whitepawn_orchestrator()
    
    # Ensure orchestrator is running
    if not orchestrator._running:
        await orchestrator.start()
    
    deployment = await orchestrator.deploy_for_lab(
        lab_id=request.lab_id,
        lab_name=request.lab_name,
        config=request.config
    )
    
    return {
        "success": True,
        "deployment": deployment.to_dict()
    }


@router.get("/labs/{lab_id}")
async def get_lab_deployment(lab_id: str):
    """Get WhitePawn deployment for a specific lab"""
    orchestrator = get_whitepawn_orchestrator()
    deployment = await orchestrator.get_deployment(lab_id)
    
    if not deployment:
        raise HTTPException(status_code=404, detail=f"No WhitePawn deployment for lab {lab_id}")
    
    return deployment


@router.post("/labs/{lab_id}/stop")
async def stop_lab_monitoring(lab_id: str):
    """Stop WhitePawn monitoring for a lab"""
    orchestrator = get_whitepawn_orchestrator()
    success = await orchestrator.stop_for_lab(lab_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"No WhitePawn deployment for lab {lab_id}")
    
    return {"success": True, "message": f"WhitePawn stopped for lab {lab_id}"}


@router.post("/labs/{lab_id}/restart")
async def restart_lab_monitoring(lab_id: str):
    """Restart WhitePawn monitoring for a lab"""
    orchestrator = get_whitepawn_orchestrator()
    
    # Stop first
    await orchestrator.stop_for_lab(lab_id)
    
    # Re-deploy
    deployment = await orchestrator.deploy_for_lab(lab_id)
    
    return {
        "success": True,
        "deployment": deployment.to_dict()
    }


# ============================================================================
# Alert Endpoints
# ============================================================================

@router.get("/alerts")
async def get_alerts(
    lab_id: Optional[str] = None,
    severity: Optional[str] = None,
    unresolved_only: bool = True,
    limit: int = 100
):
    """Get network alerts"""
    orchestrator = get_whitepawn_orchestrator()
    alerts = await orchestrator.get_alerts(
        lab_id=lab_id,
        severity=severity,
        unresolved_only=unresolved_only,
        limit=limit
    )
    
    return {
        "alerts": alerts,
        "total": len(alerts)
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, request: AlertAcknowledge):
    """Acknowledge an alert"""
    orchestrator = get_whitepawn_orchestrator()
    success = await orchestrator.acknowledge_alert(alert_id, request.user)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return {"success": True, "message": f"Alert {alert_id} acknowledged"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Resolve an alert"""
    orchestrator = get_whitepawn_orchestrator()
    success = await orchestrator.resolve_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return {"success": True, "message": f"Alert {alert_id} resolved"}


# ============================================================================
# Connectivity Endpoints
# ============================================================================

@router.get("/labs/{lab_id}/matrix")
async def get_connectivity_matrix(lab_id: str):
    """Get the latest connectivity matrix for a lab"""
    orchestrator = get_whitepawn_orchestrator()
    matrix = await orchestrator.get_connectivity_matrix(lab_id)
    
    if not matrix:
        return {"lab_id": lab_id, "matrix": None, "message": "No connectivity data yet"}
    
    return matrix


# ============================================================================
# Reconciler Endpoints
# ============================================================================

@router.get("/reconciler/status")
async def get_reconciler_status():
    """Get network reconciler status"""
    reconciler = get_network_reconciler()
    return reconciler.get_status()


@router.post("/reconciler/start")
async def start_reconciler():
    """Start the network reconciler"""
    reconciler = get_network_reconciler(interval=30)  # 30 second interval
    await reconciler.start()
    return {"success": True, "message": "Network reconciler started"}


@router.post("/reconciler/stop")
async def stop_reconciler():
    """Stop the network reconciler"""
    reconciler = get_network_reconciler()
    await reconciler.stop()
    return {"success": True, "message": "Network reconciler stopped"}


@router.get("/reconciler/drifts")
async def get_drift_history(limit: int = 50):
    """Get recent drift events"""
    reconciler = get_network_reconciler()
    drifts = reconciler.get_drift_history(limit=limit)
    return {
        "drifts": drifts,
        "total": len(drifts)
    }


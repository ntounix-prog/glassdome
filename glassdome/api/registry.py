"""
API endpoints for registry

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import json
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from glassdome.registry.core import get_registry, LabRegistry
from glassdome.registry.models import (
    Resource, ResourceType, ResourceState,
    StateChange, EventType, Drift, LabSnapshot
)
from glassdome.registry.controllers.lab_controller import get_lab_controller

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/registry", tags=["registry"])


# =============================================================================
# Models
# =============================================================================

class ResourceResponse(BaseModel):
    """Resource response model"""
    id: str
    resource_type: str
    name: str
    platform: str
    platform_instance: Optional[str]
    platform_id: Optional[str]
    state: str
    state_detail: Optional[str]
    lab_id: Optional[str]
    config: dict
    tier: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class DriftResponse(BaseModel):
    """Drift response model"""
    resource_id: str
    resource_type: str
    drift_type: str
    expected: str
    actual: str
    severity: str
    auto_fix: bool
    fix_action: Optional[str]
    lab_id: Optional[str]
    detected_at: str


class ReconcileRequest(BaseModel):
    """Reconciliation request"""
    auto_fix: bool = True


class ReconcileResponse(BaseModel):
    """Reconciliation response"""
    success: bool
    lab_id: str
    vms_checked: int
    drifts_detected: int
    drifts_fixed: int
    errors: List[str]
    duration_ms: int


class RegistryStatus(BaseModel):
    """Registry status"""
    connected: bool
    resource_counts: dict
    total_resources: int
    lab_count: int
    active_drifts: int
    agents: int
    agent_names: List[str]


# =============================================================================
# Status Endpoints
# =============================================================================

@router.get("/status", response_model=RegistryStatus)
async def get_registry_status():
    """Get registry status and health"""
    registry = get_registry()
    status = await registry.get_status()
    return status


@router.get("/agents")
async def list_agents():
    """List all registered agents"""
    registry = get_registry()
    agents = await registry.list_agents()
    return {"agents": agents}


# =============================================================================
# Resource Endpoints
# =============================================================================

@router.get("/resources")
async def list_resources(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    lab_id: Optional[str] = Query(None, description="Filter by lab ID")
):
    """
    List all resources in the registry.
    
    Filters can be combined.
    """
    registry = get_registry()
    
    if lab_id:
        resources = await registry.list_by_lab(lab_id)
    elif resource_type:
        try:
            rt = ResourceType(resource_type)
            resources = await registry.list_by_type(rt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource type: {resource_type}")
    elif platform:
        resources = await registry.list_by_platform(platform)
    else:
        # Get all resources (aggregate from all types)
        resources = []
        for rt in ResourceType:
            resources.extend(await registry.list_by_type(rt))
    
    return {
        "count": len(resources),
        "resources": [r.to_dict() for r in resources]
    }


@router.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    """Get a specific resource by ID"""
    registry = get_registry()
    resource = await registry.get(resource_id)
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource.to_dict()


@router.delete("/resources/{resource_id}")
async def delete_resource(resource_id: str):
    """Delete a resource from the registry"""
    registry = get_registry()
    success = await registry.delete(resource_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return {"success": True, "message": f"Resource {resource_id} deleted"}


# =============================================================================
# Lab Endpoints
# =============================================================================

@router.get("/labs")
async def list_labs():
    """List all labs in the registry"""
    registry = get_registry()
    labs = await registry.list_labs()
    
    # Get snapshot for each lab
    lab_summaries = []
    for lab_id in labs:
        snapshot = await registry.get_lab_snapshot(lab_id)
        if snapshot:
            lab_summaries.append({
                "lab_id": lab_id,
                "name": snapshot.name,
                "total_vms": snapshot.total_vms,
                "running_vms": snapshot.running_vms,
                "healthy": snapshot.healthy,
                "drift_count": snapshot.drift_count,
            })
    
    return {"labs": lab_summaries}


@router.get("/labs/{lab_id}")
async def get_lab(lab_id: str):
    """Get full lab snapshot"""
    registry = get_registry()
    snapshot = await registry.get_lab_snapshot(lab_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    return snapshot.to_dict()


@router.post("/labs/{lab_id}/reconcile", response_model=ReconcileResponse)
async def reconcile_lab(lab_id: str, request: ReconcileRequest = None):
    """
    Trigger reconciliation for a lab.
    
    Checks all VMs for drift and attempts to fix issues.
    """
    controller = get_lab_controller()
    
    if request:
        # Temporarily override auto_fix setting
        original_auto_fix = controller.auto_fix
        controller.auto_fix = request.auto_fix
    
    try:
        result = await controller.reconcile_lab(lab_id)
        return result
    finally:
        if request:
            controller.auto_fix = original_auto_fix


# =============================================================================
# Drift Endpoints
# =============================================================================

@router.get("/drift")
async def get_drifts(
    lab_id: Optional[str] = Query(None, description="Filter by lab ID")
):
    """Get all active drift records"""
    registry = get_registry()
    drifts = await registry.get_drifts(lab_id=lab_id)
    
    return {
        "count": len(drifts),
        "drifts": [d.to_dict() for d in drifts]
    }


@router.post("/drift/{resource_id}/resolve")
async def resolve_drift(resource_id: str):
    """Manually mark a drift as resolved"""
    registry = get_registry()
    await registry.resolve_drift(resource_id)
    return {"success": True, "message": f"Drift resolved for {resource_id}"}


# =============================================================================
# Events Endpoints
# =============================================================================

@router.get("/events")
async def get_events(
    limit: int = Query(100, le=1000),
    lab_id: Optional[str] = Query(None)
):
    """Get recent events from the registry"""
    registry = get_registry()
    events = await registry.get_recent_events(limit=limit, lab_id=lab_id)
    
    return {
        "count": len(events),
        "events": [e.to_dict() for e in events]
    }


# =============================================================================
# WebSocket for Real-time Events
# =============================================================================

@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket, lab_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time event streaming.
    
    Optional query param:
    - lab_id: Only receive events for a specific lab
    """
    await websocket.accept()
    
    registry = get_registry()
    
    try:
        # Subscribe to events
        async for event in registry.subscribe_events(lab_id=lab_id):
            # Send event as JSON
            await websocket.send_json(event.to_dict())
            
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# =============================================================================
# Webhook Endpoints (for Proxmox notifications)
# =============================================================================

class ProxmoxWebhook(BaseModel):
    """Proxmox webhook payload"""
    type: str
    vmid: Optional[int]
    node: Optional[str]
    action: Optional[str]
    status: Optional[str]


@router.post("/webhook/proxmox")
async def proxmox_webhook(payload: ProxmoxWebhook):
    """
    Receive webhooks from Proxmox notifications.
    
    Configure in Proxmox:
    pvesh create /cluster/notifications/endpoints/webhook/glassdome \
      --url "http://agentx:8011/api/registry/webhook/proxmox"
    """
    logger.info(f"Received Proxmox webhook: {payload}")
    
    # TODO: Process webhook and update registry immediately
    # For now, just log it - the polling agents will pick up changes
    
    return {"received": True}


# =============================================================================
# Controller Endpoints
# =============================================================================

@router.get("/controller/status")
async def get_controller_status():
    """Get lab controller status"""
    controller = get_lab_controller()
    return controller.get_status()


@router.post("/controller/start")
async def start_controller():
    """Start the lab controller reconciliation loop"""
    controller = get_lab_controller()
    await controller.start()
    return {"success": True, "message": "Controller started"}


@router.post("/controller/stop")
async def stop_controller():
    """Stop the lab controller reconciliation loop"""
    controller = get_lab_controller()
    await controller.stop()
    return {"success": True, "message": "Controller stopped"}


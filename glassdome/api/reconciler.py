"""
Registry Reconciler API Endpoints

Provides endpoints to manage and monitor the registry reconciler.

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional

from glassdome.registry import get_reconciler, force_reconcile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reconciler", tags=["reconciler"])


class ReconcileResponse(BaseModel):
    success: bool
    message: str
    stats: Optional[Dict[str, Any]] = None


class ReconcilerStatus(BaseModel):
    running: bool
    last_reconcile: Optional[str]
    last_stats: Optional[Dict[str, Any]]
    scanners: list


@router.get("/status", response_model=ReconcilerStatus)
async def get_status():
    """Get the current status of the registry reconciler"""
    try:
        reconciler = get_reconciler()
        status = await reconciler.get_status()
        return ReconcilerStatus(**status)
    except Exception as e:
        logger.error(f"Error getting reconciler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=ReconcileResponse)
async def run_reconciliation(background_tasks: BackgroundTasks):
    """
    Trigger immediate reconciliation.
    
    Scans all configured platforms and syncs Redis with actual state.
    Returns immediately and runs reconciliation in background.
    """
    try:
        # Run in background to avoid timeout
        async def do_reconcile():
            try:
                stats = await force_reconcile()
                logger.info(f"Background reconciliation complete: {stats}")
            except Exception as e:
                logger.error(f"Background reconciliation failed: {e}")
        
        background_tasks.add_task(do_reconcile)
        
        return ReconcileResponse(
            success=True,
            message="Reconciliation started in background"
        )
    except Exception as e:
        logger.error(f"Error starting reconciliation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-sync", response_model=ReconcileResponse)
async def run_reconciliation_sync():
    """
    Trigger immediate reconciliation and wait for completion.
    
    WARNING: This can take several seconds depending on platform count.
    """
    try:
        stats = await force_reconcile()
        return ReconcileResponse(
            success=True,
            message="Reconciliation complete",
            stats=stats
        )
    except Exception as e:
        logger.error(f"Error during reconciliation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


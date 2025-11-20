"""
Overseer API Endpoints
Monitor and manage deployed infrastructure
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from glassdome.agents.overseer import OverseerAgent
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/overseer", tags=["overseer"])

# Global overseer instance (in production, would be properly managed)
overseer_instance: Optional[OverseerAgent] = None


def get_overseer() -> OverseerAgent:
    """Get or create overseer instance"""
    global overseer_instance
    
    if overseer_instance is None:
        proxmox = ProxmoxClient(
            host=settings.proxmox_host,
            user=settings.proxmox_user,
            token_name=settings.proxmox_token_name,
            token_value=settings.proxmox_token_value,
            verify_ssl=settings.proxmox_verify_ssl
        )
        
        overseer_instance = OverseerAgent("overseer-001", proxmox)
    
    return overseer_instance


@router.get("/status")
async def get_overseer_status():
    """
    Get overseer agent status
    """
    overseer = get_overseer()
    
    return {
        "agent_id": overseer.agent_id,
        "status": overseer.status.value,
        "last_check": overseer.last_check.isoformat() if overseer.last_check else None,
        "monitoring": True
    }


@router.get("/inventory")
async def get_inventory():
    """
    Get complete infrastructure inventory
    
    Returns current state of all monitored infrastructure
    """
    overseer = get_overseer()
    inventory = await overseer.get_inventory()
    
    return inventory


@router.post("/check/{node}")
async def check_node(node: str):
    """
    Manually trigger check for specific node
    
    Args:
        node: Node name (e.g., pve01)
    """
    overseer = get_overseer()
    
    try:
        report = await overseer.check_node(node)
        return {
            "success": True,
            "node": node,
            "report": report
        }
    except Exception as e:
        logger.error(f"Failed to check node {node}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vm/{node}/{vmid}")
async def get_vm_status(node: str, vmid: int):
    """
    Get detailed status for specific VM
    
    Args:
        node: Node name
        vmid: VM ID
    """
    overseer = get_overseer()
    
    try:
        vm_status = await overseer.check_vm(node, vmid)
        return {
            "success": True,
            "vm": vm_status
        }
    except Exception as e:
        logger.error(f"Failed to check VM {vmid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vm/{node}/{vmid}/history")
async def get_vm_history(node: str, vmid: int, hours: int = 24):
    """
    Get VM historical metrics
    
    Args:
        node: Node name
        vmid: VM ID
        hours: Hours of history to retrieve
    """
    overseer = get_overseer()
    
    try:
        history = await overseer.get_vm_history(node, vmid, hours)
        return {
            "success": True,
            "vmid": vmid,
            "hours": hours,
            "history": history
        }
    except Exception as e:
        logger.error(f"Failed to get VM history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(acknowledged: Optional[bool] = None):
    """
    Get all alerts
    
    Args:
        acknowledged: Filter by acknowledged status (None = all)
    """
    overseer = get_overseer()
    
    alerts = overseer.alerts
    
    if acknowledged is not None:
        alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
    
    return {
        "total": len(alerts),
        "alerts": alerts
    }


@router.post("/alerts/{alert_index}/acknowledge")
async def acknowledge_alert(alert_index: int):
    """
    Acknowledge an alert
    
    Args:
        alert_index: Index of alert to acknowledge
    """
    overseer = get_overseer()
    
    if alert_index < 0 or alert_index >= len(overseer.alerts):
        raise HTTPException(status_code=404, detail="Alert not found")
    
    overseer.alerts[alert_index]["acknowledged"] = True
    
    return {
        "success": True,
        "alert": overseer.alerts[alert_index]
    }


@router.post("/remediate/{node}/{vmid}")
async def remediate_vm(node: str, vmid: int, issue: str):
    """
    Attempt automatic remediation for VM
    
    Args:
        node: Node name
        vmid: VM ID
        issue: Issue description
    """
    overseer = get_overseer()
    
    try:
        result = await overseer.auto_remediate(node, vmid, issue)
        return result
    except Exception as e:
        logger.error(f"Failed to remediate VM {vmid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_report(node: Optional[str] = None):
    """
    Generate infrastructure health report
    
    Args:
        node: Specific node or None for all nodes
    """
    overseer = get_overseer()
    
    try:
        report = await overseer.generate_report(node)
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-monitoring")
async def start_monitoring(
    background_tasks: BackgroundTasks,
    nodes: List[str] = ["pve01"],
    interval: int = 60
):
    """
    Start continuous monitoring
    
    Args:
        nodes: List of nodes to monitor
        interval: Check interval in seconds
    """
    overseer = get_overseer()
    
    # Start monitoring in background
    background_tasks.add_task(overseer.start_monitoring, nodes, interval)
    
    return {
        "success": True,
        "message": f"Monitoring started for nodes: {nodes}",
        "interval": interval
    }


@router.post("/stop-monitoring")
async def stop_monitoring():
    """Stop monitoring (not implemented - would need task management)"""
    return {
        "success": False,
        "message": "Stop monitoring not yet implemented"
    }


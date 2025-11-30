"""
API endpoints for agent status.

Extracted from main.py for cleaner organization.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from glassdome.agents.manager import agent_manager

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/status")
async def get_agents_status() -> Dict[str, Any]:
    """Get status of all agents."""
    status = agent_manager.get_status()
    return status


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    """Get specific agent details."""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "agent_id": agent.agent_id,
        "type": agent.agent_type.value,
        "status": agent.status.value,
        "error": agent.error
    }

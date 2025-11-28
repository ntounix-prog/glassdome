"""
Base module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional

from glassdome.registry.core import LabRegistry, get_registry
from glassdome.registry.models import Resource, StateChange

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for registry agents.
    
    Agents poll infrastructure platforms and publish state changes to the registry.
    Each agent has a configurable poll interval based on its tier.
    """
    
    def __init__(
        self,
        name: str,
        tier: int = 2,
        poll_interval: float = 5.0,
        registry: LabRegistry = None
    ):
        """
        Initialize the agent.
        
        Args:
            name: Agent identifier
            tier: 1 (labs, 1s), 2 (VMs, 5-10s), 3 (infra, 30-60s)
            poll_interval: Seconds between polls
            registry: Registry instance (uses singleton if not provided)
        """
        self.name = name
        self.tier = tier
        self.poll_interval = poll_interval
        self.registry = registry or get_registry()
        
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_poll: Optional[datetime] = None
        self._poll_count = 0
        self._error_count = 0
        self._last_error: Optional[str] = None
    
    # =========================================================================
    # Abstract Methods
    # =========================================================================
    
    @abstractmethod
    async def poll(self) -> List[Resource]:
        """
        Poll the platform and return current resources.
        
        Returns:
            List of Resource objects representing current state
        """
        pass
    
    @abstractmethod
    async def get_resource(self, resource_id: str) -> Optional[Resource]:
        """
        Get a single resource by ID.
        
        Args:
            resource_id: The resource identifier
            
        Returns:
            Resource if found, None otherwise
        """
        pass
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self):
        """Start the agent polling loop"""
        if self._running:
            return
        
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(f"Agent {self.name} started (tier={self.tier}, interval={self.poll_interval}s)")
    
    async def stop(self):
        """Stop the agent polling loop"""
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Agent {self.name} stopped")
    
    async def _poll_loop(self):
        """Main polling loop"""
        logger.info(f"Agent {self.name} poll loop starting")
        while self._running:
            try:
                await self._do_poll()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_count += 1
                self._last_error = str(e)
                logger.error(f"Agent {self.name} poll error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _do_poll(self):
        """Execute a single poll cycle"""
        self._last_poll = datetime.utcnow()
        self._poll_count += 1
        
        # Poll for resources
        resources = await self.poll()
        
        # Register each resource
        for resource in resources:
            resource.tier = self.tier
            await self.registry.register(resource)
        
        # Send heartbeat
        await self.registry.agent_heartbeat(self.name, {
            "tier": self.tier,
            "poll_interval": self.poll_interval,
            "poll_count": self._poll_count,
            "resources_count": len(resources),
            "error_count": self._error_count,
            "last_error": self._last_error,
        })
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.name,
            "tier": self.tier,
            "poll_interval": self.poll_interval,
            "running": self._running,
            "last_poll": self._last_poll.isoformat() if self._last_poll else None,
            "poll_count": self._poll_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
        }


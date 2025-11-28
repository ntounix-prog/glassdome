"""
Lab Controller

Reconciliation controller for lab resources (Tier 1).
Monitors lab VMs for drift and performs self-healing actions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from glassdome.registry.core import LabRegistry, get_registry
from glassdome.registry.models import (
    Resource, ResourceType, ResourceState,
    StateChange, EventType, Drift, DriftType, LabSnapshot
)
from glassdome.registry.agents.proxmox_agent import ProxmoxAgent

logger = logging.getLogger(__name__)


class LabController:
    """
    Reconciliation controller for lab resources.
    
    Tier 1 Controller - Runs every ~1 second for lab VMs
    
    Responsibilities:
    - Monitor lab VMs for state drift
    - Detect naming issues
    - Auto-fix common problems:
        - VM not running -> start it
        - VM wrong name -> rename it
        - VM missing -> alert (can't auto-recreate without context)
    """
    
    def __init__(
        self,
        registry: LabRegistry = None,
        check_interval: float = 1.0,
        auto_fix: bool = True
    ):
        """
        Initialize lab controller.
        
        Args:
            registry: Registry instance
            check_interval: Seconds between reconciliation checks
            auto_fix: Whether to automatically fix drift
        """
        self.registry = registry or get_registry()
        self.check_interval = check_interval
        self.auto_fix = auto_fix
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._proxmox_agents: Dict[str, ProxmoxAgent] = {}
        
        # Stats
        self._check_count = 0
        self._fix_count = 0
        self._last_check: Optional[datetime] = None
    
    async def start(self):
        """Start the reconciliation loop"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._reconcile_loop())
        logger.info(f"LabController started (interval={self.check_interval}s, auto_fix={self.auto_fix})")
    
    async def stop(self):
        """Stop the reconciliation loop"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("LabController stopped")
    
    async def _reconcile_loop(self):
        """Main reconciliation loop"""
        while self._running:
            try:
                await self._do_reconcile()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"LabController reconcile error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _do_reconcile(self):
        """Execute a single reconciliation cycle"""
        self._last_check = datetime.utcnow()
        self._check_count += 1
        
        # Get all labs
        labs = await self.registry.list_labs()
        
        for lab_id in labs:
            try:
                await self._reconcile_lab(lab_id)
            except Exception as e:
                logger.error(f"Error reconciling lab {lab_id}: {e}")
    
    async def _reconcile_lab(self, lab_id: str):
        """
        Reconcile a single lab.
        
        Checks:
        1. All expected VMs exist
        2. All VMs have correct names
        3. All VMs are in correct state
        4. Gateway is running and reachable
        """
        snapshot = await self.registry.get_lab_snapshot(lab_id)
        if not snapshot:
            return
        
        for vm in snapshot.vms:
            # Check for drift
            drift = await self.registry.detect_drift(vm)
            
            if drift:
                await self.registry.record_drift(drift)
                
                # Attempt auto-fix for Tier 1 resources
                if self.auto_fix and drift.auto_fix:
                    await self._fix_drift(vm, drift)
    
    async def _fix_drift(self, resource: Resource, drift: Drift) -> bool:
        """
        Attempt to fix detected drift.
        
        Args:
            resource: The resource with drift
            drift: The detected drift
            
        Returns:
            True if fix was successful
        """
        logger.info(f"Attempting to fix drift: {drift.drift_type.value} on {resource.name}")
        
        try:
            if drift.drift_type == DriftType.STATE_MISMATCH:
                return await self._fix_state_drift(resource, drift)
            
            elif drift.drift_type == DriftType.NAME_MISMATCH:
                return await self._fix_name_drift(resource, drift)
            
            else:
                logger.warning(f"No auto-fix available for drift type: {drift.drift_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to fix drift: {e}")
            return False
    
    async def _fix_state_drift(self, resource: Resource, drift: Drift) -> bool:
        """Fix VM state drift (start/stop VM)"""
        agent = await self._get_proxmox_agent(resource.platform_instance)
        if not agent:
            logger.error(f"No Proxmox agent for instance {resource.platform_instance}")
            return False
        
        vmid = int(resource.platform_id)
        node = resource.config.get("node")
        
        if drift.expected == ResourceState.RUNNING.value:
            # VM should be running but isn't
            logger.info(f"Starting VM {resource.name} (vmid={vmid})")
            success = await agent.start_vm(vmid, node)
            
            if success:
                self._fix_count += 1
                await self.registry.resolve_drift(resource.id)
                
                # Publish fix event
                await self.registry.publish_event(StateChange(
                    event_type=EventType.RECONCILE_COMPLETE,
                    resource_id=resource.id,
                    resource_type=resource.resource_type,
                    old_state=resource.state,
                    new_state=ResourceState.RUNNING,
                    lab_id=resource.lab_id,
                ))
            
            return success
        
        elif drift.expected == ResourceState.STOPPED.value:
            # VM should be stopped but is running
            logger.info(f"Stopping VM {resource.name} (vmid={vmid})")
            success = await agent.stop_vm(vmid, node)
            
            if success:
                self._fix_count += 1
                await self.registry.resolve_drift(resource.id)
            
            return success
        
        return False
    
    async def _fix_name_drift(self, resource: Resource, drift: Drift) -> bool:
        """Fix VM name drift (rename VM)"""
        agent = await self._get_proxmox_agent(resource.platform_instance)
        if not agent:
            logger.error(f"No Proxmox agent for instance {resource.platform_instance}")
            return False
        
        vmid = int(resource.platform_id)
        node = resource.config.get("node")
        expected_name = drift.expected
        
        logger.info(f"Renaming VM {resource.name} -> {expected_name} (vmid={vmid})")
        success = await agent.rename_vm(vmid, expected_name, node)
        
        if success:
            self._fix_count += 1
            await self.registry.resolve_drift(resource.id)
            
            # Update resource in registry
            resource.name = expected_name
            await self.registry.register(resource)
            
            logger.info(f"Successfully renamed VM {vmid} to {expected_name}")
        
        return success
    
    async def _get_proxmox_agent(self, instance_id: str) -> Optional[ProxmoxAgent]:
        """Get or create Proxmox agent for an instance"""
        if instance_id not in self._proxmox_agents:
            try:
                agent = ProxmoxAgent(instance_id=instance_id or "01", tier=1)
                # Don't start the polling loop - we just need the action methods
                self._proxmox_agents[instance_id] = agent
            except Exception as e:
                logger.error(f"Failed to create Proxmox agent for {instance_id}: {e}")
                return None
        
        return self._proxmox_agents.get(instance_id)
    
    # =========================================================================
    # Manual Reconciliation
    # =========================================================================
    
    async def reconcile_lab(self, lab_id: str) -> Dict[str, Any]:
        """
        Manually trigger reconciliation for a specific lab.
        
        Returns:
            Reconciliation results
        """
        start_time = datetime.utcnow()
        
        # Publish start event
        await self.registry.publish_event(StateChange(
            event_type=EventType.RECONCILE_START,
            resource_id=lab_id,
            resource_type=ResourceType.LAB,
            lab_id=lab_id,
        ))
        
        snapshot = await self.registry.get_lab_snapshot(lab_id)
        if not snapshot:
            return {"success": False, "error": "Lab not found"}
        
        results = {
            "lab_id": lab_id,
            "vms_checked": 0,
            "drifts_detected": 0,
            "drifts_fixed": 0,
            "errors": [],
        }
        
        for vm in snapshot.vms:
            results["vms_checked"] += 1
            
            drift = await self.registry.detect_drift(vm)
            if drift:
                results["drifts_detected"] += 1
                await self.registry.record_drift(drift)
                
                if self.auto_fix and drift.auto_fix:
                    try:
                        fixed = await self._fix_drift(vm, drift)
                        if fixed:
                            results["drifts_fixed"] += 1
                    except Exception as e:
                        results["errors"].append(f"Failed to fix {vm.name}: {str(e)}")
        
        # Publish complete event
        await self.registry.publish_event(StateChange(
            event_type=EventType.RECONCILE_COMPLETE,
            resource_id=lab_id,
            resource_type=ResourceType.LAB,
            lab_id=lab_id,
        ))
        
        results["duration_ms"] = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        results["success"] = len(results["errors"]) == 0
        
        return results
    
    async def set_desired_state(
        self,
        resource_id: str,
        desired_state: ResourceState = None,
        desired_config: Dict[str, Any] = None
    ):
        """
        Set desired state for a resource.
        
        This enables drift detection and auto-fix for the resource.
        
        Args:
            resource_id: Resource ID
            desired_state: Expected state (RUNNING, STOPPED)
            desired_config: Expected config (name, network, etc.)
        """
        resource = await self.registry.get(resource_id)
        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")
        
        if desired_state:
            resource.desired_state = desired_state
        
        if desired_config:
            resource.desired_config.update(desired_config)
        
        await self.registry.register(resource)
        
        logger.info(f"Set desired state for {resource_id}: state={desired_state}, config={desired_config}")
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get controller status"""
        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "auto_fix": self.auto_fix,
            "check_count": self._check_count,
            "fix_count": self._fix_count,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }


# =============================================================================
# Singleton Access
# =============================================================================

_lab_controller: Optional[LabController] = None


def get_lab_controller() -> LabController:
    """Get or create the lab controller singleton"""
    global _lab_controller
    if _lab_controller is None:
        _lab_controller = LabController()
    return _lab_controller


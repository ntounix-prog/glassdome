"""
Network State Reconciler

Continuously compares DB state to actual platform state.
Detects drift and triggers alerts/remediation.

Runs every 30 seconds to ensure accuracy over resources.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.core.database import AsyncSessionLocal
from glassdome.networking.models import (
    NetworkDefinition, 
    PlatformNetworkMapping, 
    VMInterface,
    DeployedVM
)
from glassdome.networking.proxmox_handler import get_proxmox_network_handler

logger = logging.getLogger(__name__)


class ReconciliationResult:
    """Result of a single reconciliation check"""
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        platform: str,
        expected_state: str,
        actual_state: str,
        drifted: bool,
        details: Optional[str] = None
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.platform = platform
        self.expected_state = expected_state
        self.actual_state = actual_state
        self.drifted = drifted
        self.details = details
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "platform": self.platform,
            "expected_state": self.expected_state,
            "actual_state": self.actual_state,
            "drifted": self.drifted,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class NetworkReconciler:
    """
    Reconciles network state between Glassdome DB and actual platforms.
    
    Runs continuously, checking for:
    - Networks that should exist but don't
    - Networks that exist but shouldn't
    - VM interfaces that have changed
    - IP addresses that have drifted
    """
    
    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._drift_callbacks: List[callable] = []
        self._results_history: List[ReconciliationResult] = []
        self._max_history = 1000
        
        # Platform handlers
        self._handlers = {
            "proxmox": get_proxmox_network_handler()
        }
    
    def register_drift_callback(self, callback: callable):
        """Register a callback to be called when drift is detected"""
        self._drift_callbacks.append(callback)
    
    async def start(self):
        """Start the reconciliation loop"""
        if self._running:
            logger.warning("Reconciler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._reconcile_loop())
        logger.info(f"Network reconciler started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the reconciliation loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Network reconciler stopped")
    
    async def _reconcile_loop(self):
        """Main reconciliation loop"""
        while self._running:
            try:
                await self._run_reconciliation()
                self._last_run = datetime.utcnow()
            except Exception as e:
                logger.error(f"Reconciliation error: {e}")
            
            await asyncio.sleep(self.interval)
    
    async def _run_reconciliation(self):
        """Run a single reconciliation cycle"""
        async with AsyncSessionLocal() as session:
            results = []
            
            # Reconcile network mappings
            results.extend(await self._reconcile_network_mappings(session))
            
            # Reconcile VM interfaces
            results.extend(await self._reconcile_vm_interfaces(session))
            
            # Reconcile deployed VMs
            results.extend(await self._reconcile_deployed_vms(session))
            
            # Store results
            for result in results:
                self._results_history.append(result)
                if result.drifted:
                    logger.warning(f"DRIFT DETECTED: {result.resource_type} {result.resource_id} on {result.platform}")
                    await self._notify_drift(result)
            
            # Trim history
            if len(self._results_history) > self._max_history:
                self._results_history = self._results_history[-self._max_history:]
            
            # Log summary
            drift_count = sum(1 for r in results if r.drifted)
            if drift_count > 0:
                logger.warning(f"Reconciliation complete: {drift_count} drifts detected out of {len(results)} checks")
            else:
                logger.debug(f"Reconciliation complete: {len(results)} checks, no drift")
    
    async def _reconcile_network_mappings(self, session: AsyncSession) -> List[ReconciliationResult]:
        """Check that provisioned networks still exist on platforms"""
        results = []
        
        # Get all provisioned network mappings
        query = select(PlatformNetworkMapping).where(
            PlatformNetworkMapping.provisioned == True
        )
        result = await session.execute(query)
        mappings = result.scalars().all()
        
        for mapping in mappings:
            handler = self._handlers.get(mapping.platform)
            if not handler:
                continue
            
            try:
                # Get the network definition
                net_query = select(NetworkDefinition).where(
                    NetworkDefinition.id == mapping.network_id
                )
                net_result = await session.execute(net_query)
                network = net_result.scalar_one_or_none()
                
                if not network:
                    results.append(ReconciliationResult(
                        resource_type="network_mapping",
                        resource_id=str(mapping.id),
                        platform=mapping.platform,
                        expected_state="network_exists",
                        actual_state="network_deleted",
                        drifted=True,
                        details=f"Parent network {mapping.network_id} deleted but mapping remains"
                    ))
                    continue
                
                # Verify network exists on platform
                exists = await handler.create_network(network, mapping.platform_config, mapping.platform_instance)
                
                results.append(ReconciliationResult(
                    resource_type="network",
                    resource_id=network.name,
                    platform=mapping.platform,
                    expected_state="provisioned",
                    actual_state="provisioned" if exists else "missing",
                    drifted=not exists,
                    details=f"Bridge: {mapping.platform_config.get('bridge')}"
                ))
                
            except Exception as e:
                results.append(ReconciliationResult(
                    resource_type="network",
                    resource_id=str(mapping.network_id),
                    platform=mapping.platform,
                    expected_state="provisioned",
                    actual_state="error",
                    drifted=True,
                    details=str(e)
                ))
        
        return results
    
    async def _reconcile_vm_interfaces(self, session: AsyncSession) -> List[ReconciliationResult]:
        """Check that VM interfaces match actual platform state"""
        results = []
        
        # Get all VM interfaces
        query = select(VMInterface)
        result = await session.execute(query)
        interfaces = result.scalars().all()
        
        # Group by VM for efficiency
        vm_interfaces: Dict[str, List[VMInterface]] = {}
        for iface in interfaces:
            key = f"{iface.platform}:{iface.platform_instance}:{iface.vm_id}"
            if key not in vm_interfaces:
                vm_interfaces[key] = []
            vm_interfaces[key].append(iface)
        
        for key, ifaces in vm_interfaces.items():
            platform, instance, vm_id = key.split(":", 2)
            handler = self._handlers.get(platform)
            if not handler:
                continue
            
            try:
                # Get actual interfaces from platform
                actual_interfaces = await handler.get_vm_interfaces(vm_id, instance)
                
                for db_iface in ifaces:
                    # Find matching actual interface
                    actual = next(
                        (a for a in actual_interfaces 
                         if a.get("index") == db_iface.interface_index),
                        None
                    )
                    
                    if not actual:
                        results.append(ReconciliationResult(
                            resource_type="vm_interface",
                            resource_id=f"{vm_id}:net{db_iface.interface_index}",
                            platform=platform,
                            expected_state=f"exists (MAC: {db_iface.mac_address})",
                            actual_state="missing",
                            drifted=True,
                            details=f"Interface net{db_iface.interface_index} not found on VM"
                        ))
                        continue
                    
                    # Check for IP drift
                    actual_ip = actual.get("ip_address")
                    if db_iface.ip_address and actual_ip and db_iface.ip_address != actual_ip:
                        results.append(ReconciliationResult(
                            resource_type="vm_interface_ip",
                            resource_id=f"{vm_id}:net{db_iface.interface_index}",
                            platform=platform,
                            expected_state=db_iface.ip_address,
                            actual_state=actual_ip,
                            drifted=True,
                            details="IP address has changed"
                        ))
                        
                        # Auto-update DB with actual IP
                        db_iface.ip_address = actual_ip
                        await session.commit()
                    else:
                        results.append(ReconciliationResult(
                            resource_type="vm_interface",
                            resource_id=f"{vm_id}:net{db_iface.interface_index}",
                            platform=platform,
                            expected_state="configured",
                            actual_state="configured",
                            drifted=False,
                            details=f"IP: {actual_ip or 'DHCP pending'}"
                        ))
                        
            except Exception as e:
                results.append(ReconciliationResult(
                    resource_type="vm_interfaces",
                    resource_id=vm_id,
                    platform=platform,
                    expected_state="accessible",
                    actual_state="error",
                    drifted=True,
                    details=str(e)
                ))
        
        return results
    
    async def _reconcile_deployed_vms(self, session: AsyncSession) -> List[ReconciliationResult]:
        """Check that deployed VMs are still running"""
        results = []
        
        # Get all deployed VMs
        query = select(DeployedVM).where(DeployedVM.status == "deployed")
        result = await session.execute(query)
        vms = result.scalars().all()
        
        for vm in vms:
            handler = self._handlers.get(vm.platform)
            if not handler:
                continue
            
            try:
                # Check if VM exists and is running
                interfaces = await handler.get_vm_interfaces(vm.vm_id, vm.platform_instance)
                
                if interfaces is None:
                    results.append(ReconciliationResult(
                        resource_type="deployed_vm",
                        resource_id=f"{vm.name} ({vm.vm_id})",
                        platform=vm.platform,
                        expected_state="deployed",
                        actual_state="missing",
                        drifted=True,
                        details=f"VM {vm.vm_id} not found on {vm.platform}"
                    ))
                else:
                    # Check for IP changes
                    primary_ip = None
                    for iface in interfaces:
                        if iface.get("ip_address"):
                            primary_ip = iface.get("ip_address")
                            break
                    
                    if vm.ip_address and primary_ip and vm.ip_address != primary_ip:
                        vm.ip_address = primary_ip
                        await session.commit()
                        
                        results.append(ReconciliationResult(
                            resource_type="deployed_vm_ip",
                            resource_id=f"{vm.name} ({vm.vm_id})",
                            platform=vm.platform,
                            expected_state=vm.ip_address,
                            actual_state=primary_ip,
                            drifted=True,
                            details="IP address updated"
                        ))
                    else:
                        results.append(ReconciliationResult(
                            resource_type="deployed_vm",
                            resource_id=f"{vm.name} ({vm.vm_id})",
                            platform=vm.platform,
                            expected_state="deployed",
                            actual_state="deployed",
                            drifted=False,
                            details=f"IP: {primary_ip or 'pending'}"
                        ))
                        
            except Exception as e:
                results.append(ReconciliationResult(
                    resource_type="deployed_vm",
                    resource_id=f"{vm.name} ({vm.vm_id})",
                    platform=vm.platform,
                    expected_state="deployed",
                    actual_state="error",
                    drifted=True,
                    details=str(e)
                ))
        
        return results
    
    async def _notify_drift(self, result: ReconciliationResult):
        """Notify callbacks of detected drift"""
        for callback in self._drift_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Drift callback error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current reconciler status"""
        recent_drifts = [
            r.to_dict() for r in self._results_history[-100:]
            if r.drifted
        ]
        
        return {
            "running": self._running,
            "interval_seconds": self.interval,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "total_checks": len(self._results_history),
            "recent_drifts": recent_drifts,
            "drift_count": len(recent_drifts)
        }
    
    def get_drift_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent drift events"""
        drifts = [r for r in self._results_history if r.drifted]
        return [d.to_dict() for d in drifts[-limit:]]


# ============================================================================
# Singleton Instance
# ============================================================================

_reconciler: Optional[NetworkReconciler] = None


def get_network_reconciler(interval: int = 30) -> NetworkReconciler:
    """Get or create the network reconciler singleton"""
    global _reconciler
    if _reconciler is None:
        _reconciler = NetworkReconciler(interval_seconds=interval)
    return _reconciler


"""
State Sync module for Overseer

Reconciles database state with actual infrastructure:
- Removes orphaned VM records
- Cleans up stale hot spares
- Syncs deployed_vms with Proxmox
- Updates IP addresses from actual state

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a state sync operation"""
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deployed_vms_cleaned: int = 0
    hot_spares_cleaned: int = 0
    networks_cleaned: int = 0
    vms_updated: int = 0
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "deployed_vms_cleaned": self.deployed_vms_cleaned,
            "hot_spares_cleaned": self.hot_spares_cleaned,
            "networks_cleaned": self.networks_cleaned,
            "vms_updated": self.vms_updated,
            "errors": self.errors,
            "details": self.details
        }


class StateSync:
    """
    Synchronizes Glassdome database state with actual infrastructure.
    
    Responsibilities:
    - Query Proxmox for actual VM list
    - Compare with deployed_vms and hot_spares tables
    - Remove orphaned records (VMs that don't exist)
    - Update IP addresses for running VMs
    - Clean up stale network definitions
    """
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self._last_sync: Optional[SyncResult] = None
        self._sync_history: List[SyncResult] = []
        self._max_history = 100
    
    async def sync_all(self) -> SyncResult:
        """
        Perform full state synchronization.
        
        Returns:
            SyncResult with details of what was cleaned/updated
        """
        result = SyncResult(success=True)
        
        try:
            # Get actual VMs from Proxmox
            actual_vms = await self._get_proxmox_vms()
            actual_vmids = {vm['vmid'] for vm in actual_vms}
            
            result.details['proxmox_vm_count'] = len(actual_vmids)
            logger.info(f"Found {len(actual_vmids)} VMs on Proxmox")
            
            # Sync deployed_vms table
            deployed_cleaned = await self._sync_deployed_vms(actual_vmids)
            result.deployed_vms_cleaned = deployed_cleaned
            
            # Sync hot_spares table
            spares_cleaned = await self._sync_hot_spares(actual_vmids)
            result.hot_spares_cleaned = spares_cleaned
            
            # Update IP addresses for existing VMs
            vms_updated = await self._update_vm_ips(actual_vms)
            result.vms_updated = vms_updated
            
            # Clean orphaned networks (no VMs attached)
            # networks_cleaned = await self._clean_orphaned_networks()
            # result.networks_cleaned = networks_cleaned
            
            logger.info(
                f"State sync complete: {deployed_cleaned} deployed VMs cleaned, "
                f"{spares_cleaned} hot spares cleaned, {vms_updated} VMs updated"
            )
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"State sync failed: {e}")
        
        # Store result
        self._last_sync = result
        self._sync_history.append(result)
        if len(self._sync_history) > self._max_history:
            self._sync_history = self._sync_history[-self._max_history:]
        
        return result
    
    async def _get_proxmox_vms(self) -> List[Dict[str, Any]]:
        """Get all VMs from Proxmox cluster"""
        import httpx
        
        all_vms = []
        
        # Get VMs from both nodes via backend API
        for instance in ["01", "02"]:
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(
                        f"{self.backend_url}/api/platforms/proxmox/{instance}/vms"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        vms = data.get("vms", [])
                        for vm in vms:
                            vm['instance'] = instance
                        all_vms.extend(vms)
                        logger.debug(f"Got {len(vms)} VMs from pve{instance}")
                    else:
                        logger.warning(f"Failed to get VMs from pve{instance}: HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"Error getting VMs from pve{instance}: {e}")
        
        return all_vms
    
    async def _sync_deployed_vms(self, actual_vmids: Set[int]) -> int:
        """Remove deployed_vms records for VMs that don't exist"""
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.networking.models import DeployedVM
        from sqlalchemy import select, delete
        
        cleaned = 0
        
        async with AsyncSessionLocal() as session:
            # Get all deployed VMs
            result = await session.execute(select(DeployedVM))
            deployed_vms = result.scalars().all()
            
            orphaned_ids = []
            for vm in deployed_vms:
                try:
                    vmid = int(vm.vm_id)
                    if vmid not in actual_vmids:
                        orphaned_ids.append(vm.id)
                        logger.info(f"Orphaned deployed VM: {vm.name} (VMID {vm.vm_id})")
                except (ValueError, TypeError):
                    # Invalid VMID format
                    orphaned_ids.append(vm.id)
            
            if orphaned_ids:
                result = await session.execute(
                    delete(DeployedVM).where(DeployedVM.id.in_(orphaned_ids))
                )
                cleaned = result.rowcount
                await session.commit()
                logger.info(f"Cleaned {cleaned} orphaned deployed VM records")
        
        return cleaned
    
    async def _sync_hot_spares(self, actual_vmids: Set[int]) -> int:
        """Remove hot_spares records for VMs that don't exist"""
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.reaper.hot_spare import HotSpare
        from sqlalchemy import select, delete
        
        cleaned = 0
        
        async with AsyncSessionLocal() as session:
            # Get all hot spares
            result = await session.execute(select(HotSpare))
            spares = result.scalars().all()
            
            orphaned_ids = []
            for spare in spares:
                if spare.vmid not in actual_vmids:
                    orphaned_ids.append(spare.id)
                    logger.info(f"Orphaned hot spare: {spare.name} (VMID {spare.vmid})")
            
            if orphaned_ids:
                result = await session.execute(
                    delete(HotSpare).where(HotSpare.id.in_(orphaned_ids))
                )
                cleaned = result.rowcount
                await session.commit()
                logger.info(f"Cleaned {cleaned} orphaned hot spare records")
        
        return cleaned
    
    async def _update_vm_ips(self, actual_vms: List[Dict[str, Any]]) -> int:
        """Update IP addresses for VMs from actual Proxmox state"""
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.networking.models import DeployedVM
        from sqlalchemy import select
        
        updated = 0
        
        # Build VMID -> IP mapping from actual VMs
        vmid_to_ip = {}
        for vm in actual_vms:
            vmid = vm.get('vmid')
            # Try to get IP from various sources
            ip = vm.get('ip') or vm.get('ip_address')
            if not ip and 'network' in vm:
                # Try to extract from network config
                net = vm.get('network', {})
                ip = net.get('ip_address')
            if vmid and ip:
                vmid_to_ip[vmid] = ip
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DeployedVM))
            deployed_vms = result.scalars().all()
            
            for vm in deployed_vms:
                try:
                    vmid = int(vm.vm_id)
                    actual_ip = vmid_to_ip.get(vmid)
                    if actual_ip and vm.ip_address != actual_ip:
                        vm.ip_address = actual_ip
                        updated += 1
                        logger.debug(f"Updated IP for {vm.name}: {actual_ip}")
                except (ValueError, TypeError):
                    pass
            
            if updated > 0:
                await session.commit()
                logger.info(f"Updated IP addresses for {updated} VMs")
        
        return updated
    
    async def _clean_orphaned_networks(self) -> int:
        """Remove network definitions with no associated VMs"""
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.networking.models import NetworkDefinition, DeployedVM
        from sqlalchemy import select, delete, func
        
        cleaned = 0
        
        async with AsyncSessionLocal() as session:
            # Get lab_ids that have VMs
            result = await session.execute(
                select(DeployedVM.lab_id).distinct()
            )
            active_lab_ids = {row[0] for row in result.fetchall() if row[0]}
            
            # Get network definitions
            result = await session.execute(select(NetworkDefinition))
            networks = result.scalars().all()
            
            orphaned_ids = []
            for net in networks:
                if net.lab_id and net.lab_id not in active_lab_ids:
                    orphaned_ids.append(net.id)
                    logger.info(f"Orphaned network: {net.name} (lab_id: {net.lab_id})")
            
            if orphaned_ids:
                result = await session.execute(
                    delete(NetworkDefinition).where(NetworkDefinition.id.in_(orphaned_ids))
                )
                cleaned = result.rowcount
                await session.commit()
                logger.info(f"Cleaned {cleaned} orphaned network definitions")
        
        return cleaned
    
    def get_last_sync(self) -> Optional[Dict[str, Any]]:
        """Get result of last sync"""
        if self._last_sync:
            return self._last_sync.to_dict()
        return None
    
    def get_sync_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get sync history"""
        return [s.to_dict() for s in self._sync_history[-limit:]]


class StateSyncScheduler:
    """
    Schedules periodic state synchronization.
    """
    
    def __init__(
        self,
        sync: StateSync,
        interval_seconds: int = 300  # 5 minutes default
    ):
        self.sync = sync
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the sync scheduler"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"State sync scheduler started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the sync scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("State sync scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                result = await self.sync.sync_all()
                if not result.success:
                    logger.warning(f"Sync failed: {result.errors}")
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            await asyncio.sleep(self.interval)


# Singleton instances
_sync: Optional[StateSync] = None
_scheduler: Optional[StateSyncScheduler] = None


def get_state_sync(backend_url: str = "http://localhost:8000") -> StateSync:
    """Get or create the state sync singleton"""
    global _sync
    if _sync is None:
        _sync = StateSync(backend_url=backend_url)
    return _sync


def get_sync_scheduler(interval: int = 300) -> StateSyncScheduler:
    """Get or create the sync scheduler singleton"""
    global _scheduler
    if _scheduler is None:
        sync = get_state_sync()
        _scheduler = StateSyncScheduler(sync=sync, interval_seconds=interval)
    return _scheduler


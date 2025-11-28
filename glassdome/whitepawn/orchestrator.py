"""
Orchestrator module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.core.database import AsyncSessionLocal
from glassdome.whitepawn.models import (
    WhitePawnDeployment,
    NetworkAlert,
    MonitoringEvent,
    ConnectivityMatrix,
    AlertSeverity,
    AlertType
)
from glassdome.whitepawn.monitor import WhitePawnMonitor
from glassdome.networking.models import NetworkDefinition, DeployedVM

logger = logging.getLogger(__name__)


class WhitePawnOrchestrator:
    """
    Central orchestrator for all WhitePawn monitoring instances.
    
    Responsibilities:
    - Auto-deploy WhitePawn when labs are deployed
    - Manage monitor lifecycle
    - Aggregate alerts across all deployments
    - Provide unified status view
    """
    
    def __init__(self):
        self._monitors: Dict[int, WhitePawnMonitor] = {}  # deployment_id -> monitor
        self._running = False
        self._guardian_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the orchestrator and all existing monitors"""
        if self._running:
            return
        
        self._running = True
        
        # Start guardian task (checks for new deployments, restarts failed monitors)
        self._guardian_task = asyncio.create_task(self._guardian_loop())
        
        # Load and start existing deployments
        await self._restore_monitors()
        
        logger.info("WhitePawn orchestrator started")
    
    async def stop(self):
        """Stop the orchestrator and all monitors"""
        self._running = False
        
        if self._guardian_task:
            self._guardian_task.cancel()
            try:
                await self._guardian_task
            except asyncio.CancelledError:
                pass
        
        # Stop all monitors
        for monitor in self._monitors.values():
            await monitor.stop()
        
        self._monitors.clear()
        logger.info("WhitePawn orchestrator stopped")
    
    async def _guardian_loop(self):
        """Guardian loop that monitors monitor health"""
        while self._running:
            try:
                await self._check_monitor_health()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Guardian loop error: {e}")
                await asyncio.sleep(10)
    
    async def _check_monitor_health(self):
        """Check health of all monitors, restart if needed"""
        async with AsyncSessionLocal() as session:
            # Get all active deployments
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.status.in_(["active", "pending", "deploying"])
                )
            )
            deployments = result.scalars().all()
            
            for deployment in deployments:
                monitor = self._monitors.get(deployment.id)
                
                # Check if monitor exists and is running
                if not monitor or not monitor._running:
                    logger.info(f"Starting monitor for deployment {deployment.id} (lab: {deployment.lab_id})")
                    await self._start_monitor(deployment)
                    continue
                
                # Check heartbeat
                if deployment.last_heartbeat:
                    stale_threshold = datetime.utcnow() - timedelta(minutes=2)
                    if deployment.last_heartbeat < stale_threshold:
                        logger.warning(f"Monitor {deployment.id} heartbeat stale, restarting")
                        await self._restart_monitor(deployment.id)
    
    async def _restore_monitors(self):
        """Restore monitors for existing active deployments"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.status == "active"
                )
            )
            deployments = result.scalars().all()
            
            for deployment in deployments:
                await self._start_monitor(deployment)
            
            logger.info(f"Restored {len(deployments)} WhitePawn monitors")
    
    async def _start_monitor(self, deployment: WhitePawnDeployment):
        """Start a monitor for a deployment"""
        if deployment.id in self._monitors:
            return
        
        monitor = WhitePawnMonitor(
            deployment_id=deployment.id,
            config=deployment.config
        )
        
        self._monitors[deployment.id] = monitor
        await monitor.start()
        
        # Update status
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.id == deployment.id
                )
            )
            dep = result.scalar_one_or_none()
            if dep:
                dep.status = "active"
                await session.commit()
    
    async def _restart_monitor(self, deployment_id: int):
        """Restart a monitor"""
        monitor = self._monitors.get(deployment_id)
        if monitor:
            await monitor.stop()
            del self._monitors[deployment_id]
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.id == deployment_id
                )
            )
            deployment = result.scalar_one_or_none()
            if deployment:
                await self._start_monitor(deployment)
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    async def deploy_for_lab(
        self,
        lab_id: str,
        lab_name: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> WhitePawnDeployment:
        """
        Deploy WhitePawn monitoring for a lab.
        
        Called automatically when a lab is deployed.
        """
        async with AsyncSessionLocal() as session:
            # Check if already deployed
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.lab_id == lab_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Restart if stopped
                if existing.status == "stopped":
                    existing.status = "pending"
                    await session.commit()
                    await self._start_monitor(existing)
                return existing
            
            # Create new deployment
            deployment = WhitePawnDeployment(
                lab_id=lab_id,
                lab_name=lab_name,
                deployment_type="agent",  # Runs as async task, not separate container
                config=config or {},
                status="pending"
            )
            
            session.add(deployment)
            await session.commit()
            await session.refresh(deployment)
            
            # Start the monitor
            await self._start_monitor(deployment)
            
            logger.info(f"Deployed WhitePawn for lab {lab_id}")
            return deployment
    
    async def stop_for_lab(self, lab_id: str) -> bool:
        """Stop WhitePawn monitoring for a lab"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.lab_id == lab_id
                )
            )
            deployment = result.scalar_one_or_none()
            
            if not deployment:
                return False
            
            # Stop the monitor
            monitor = self._monitors.get(deployment.id)
            if monitor:
                await monitor.stop()
                del self._monitors[deployment.id]
            
            deployment.status = "stopped"
            await session.commit()
            
            return True
    
    async def get_deployment(self, lab_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment info for a lab"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.lab_id == lab_id
                )
            )
            deployment = result.scalar_one_or_none()
            
            if not deployment:
                return None
            
            # Get monitor status
            monitor = self._monitors.get(deployment.id)
            monitor_status = await monitor.get_status() if monitor else None
            
            return {
                **deployment.to_dict(),
                "monitor_status": monitor_status
            }
    
    async def get_all_deployments(self) -> List[Dict[str, Any]]:
        """Get all WhitePawn deployments"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).order_by(
                    WhitePawnDeployment.created_at.desc()
                )
            )
            deployments = result.scalars().all()
            
            return [d.to_dict() for d in deployments]
    
    async def get_alerts(
        self,
        lab_id: Optional[str] = None,
        severity: Optional[str] = None,
        unresolved_only: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered"""
        async with AsyncSessionLocal() as session:
            query = select(NetworkAlert)
            
            if lab_id:
                # Get deployment for lab
                dep_result = await session.execute(
                    select(WhitePawnDeployment).where(
                        WhitePawnDeployment.lab_id == lab_id
                    )
                )
                deployment = dep_result.scalar_one_or_none()
                if deployment:
                    query = query.where(NetworkAlert.deployment_id == deployment.id)
            
            if severity:
                query = query.where(NetworkAlert.severity == severity)
            
            if unresolved_only:
                query = query.where(NetworkAlert.resolved == False)
            
            query = query.order_by(NetworkAlert.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            alerts = result.scalars().all()
            
            return [a.to_dict() for a in alerts]
    
    async def acknowledge_alert(self, alert_id: int, user: str) -> bool:
        """Acknowledge an alert"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(NetworkAlert).where(NetworkAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            
            if not alert:
                return False
            
            alert.acknowledged = True
            alert.acknowledged_by = user
            alert.acknowledged_at = datetime.utcnow()
            await session.commit()
            
            return True
    
    async def resolve_alert(self, alert_id: int, auto: bool = False) -> bool:
        """Resolve an alert"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(NetworkAlert).where(NetworkAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            
            if not alert:
                return False
            
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.auto_resolved = auto
            await session.commit()
            
            return True
    
    async def get_connectivity_matrix(self, lab_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest connectivity matrix for a lab"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConnectivityMatrix).where(
                    ConnectivityMatrix.lab_id == lab_id
                ).order_by(ConnectivityMatrix.created_at.desc()).limit(1)
            )
            matrix = result.scalar_one_or_none()
            
            if matrix:
                return matrix.to_dict()
            return None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        async with AsyncSessionLocal() as session:
            # Count deployments
            result = await session.execute(select(WhitePawnDeployment))
            deployments = result.scalars().all()
            
            active = sum(1 for d in deployments if d.status == "active")
            
            # Count unresolved alerts
            alert_result = await session.execute(
                select(NetworkAlert).where(NetworkAlert.resolved == False)
            )
            unresolved_alerts = len(alert_result.scalars().all())
            
            return {
                "running": self._running,
                "total_deployments": len(deployments),
                "active_monitors": active,
                "running_monitors": len(self._monitors),
                "unresolved_alerts": unresolved_alerts
            }


# ============================================================================
# Singleton Instance
# ============================================================================

_orchestrator: Optional[WhitePawnOrchestrator] = None


def get_whitepawn_orchestrator() -> WhitePawnOrchestrator:
    """Get or create the WhitePawn orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WhitePawnOrchestrator()
    return _orchestrator


async def auto_deploy_whitepawn(lab_id: str, lab_name: Optional[str] = None):
    """
    Convenience function to auto-deploy WhitePawn for a lab.
    
    Call this from lab deployment code.
    """
    orchestrator = get_whitepawn_orchestrator()
    
    if not orchestrator._running:
        await orchestrator.start()
    
    return await orchestrator.deploy_for_lab(lab_id, lab_name)


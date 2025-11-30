"""
Celery worker for whitepawn_monitor

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, List, Set

import redis

logger = logging.getLogger(__name__)


class WhitePawnMonitor:
    """
    Continuous network monitoring for deployed labs.
    
    Each WhitePawn instance monitors multiple labs.
    Uses Redis pub/sub for receiving new monitoring assignments.
    """
    
    def __init__(self):
        self.worker_id = os.getenv("WORKER_ID", "whitepawn-1")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.monitor_interval = int(os.getenv("MONITOR_INTERVAL", "15"))
        
        self.redis_client = redis.from_url(self.redis_url)
        self.assigned_labs: Dict[str, Dict] = {}
        self.running = True
        
        # Handle shutdown signals
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        logger.info(f"[{self.worker_id}] Received shutdown signal")
        self.running = False
    
    async def start(self):
        """Start the monitoring loop"""
        logger.info(f"[{self.worker_id}] Starting WhitePawn monitor")
        logger.info(f"  Monitor interval: {self.monitor_interval}s")
        
        # Register with orchestrator
        self._register()
        
        # Start monitoring loop and subscription listener
        await asyncio.gather(
            self._monitoring_loop(),
            self._listen_for_assignments()
        )
    
    def _register(self):
        """Register this worker with the orchestrator"""
        self.redis_client.hset(
            "whitepawn:workers",
            self.worker_id,
            datetime.now(timezone.utc).isoformat()
        )
        logger.info(f"[{self.worker_id}] Registered with orchestrator")
    
    async def _listen_for_assignments(self):
        """Listen for new lab monitoring assignments via Redis pub/sub"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("whitepawn:assignments")
        
        while self.running:
            try:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    await self._handle_assignment(message["data"])
            except Exception as e:
                logger.error(f"Subscription error: {e}")
            await asyncio.sleep(0.1)
    
    async def _handle_assignment(self, data: bytes):
        """Handle a new lab assignment"""
        import json
        try:
            assignment = json.loads(data)
            lab_id = assignment.get("lab_id")
            action = assignment.get("action", "start")
            
            if action == "start":
                self.assigned_labs[lab_id] = assignment
                logger.info(f"[{self.worker_id}] Now monitoring lab: {lab_id}")
            elif action == "stop":
                self.assigned_labs.pop(lab_id, None)
                logger.info(f"[{self.worker_id}] Stopped monitoring lab: {lab_id}")
        except Exception as e:
            logger.error(f"Failed to handle assignment: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop - checks all assigned labs"""
        while self.running:
            for lab_id, lab_info in list(self.assigned_labs.items()):
                try:
                    await self._check_lab(lab_id, lab_info)
                except Exception as e:
                    logger.error(f"Error checking lab {lab_id}: {e}")
            
            await asyncio.sleep(self.monitor_interval)
    
    async def _check_lab(self, lab_id: str, lab_info: Dict):
        """Check all VMs in a lab"""
        from .reaper import attach_to_vlan, detach_from_vlan
        
        vlan_id = lab_info.get("vlan_id")
        vms = lab_info.get("vms", [])
        
        if not vms:
            return
        
        # Attach to VLAN if specified
        if vlan_id:
            attach_to_vlan(vlan_id)
        
        try:
            results = await self._ping_sweep(vms)
            await self._store_results(lab_id, results)
            await self._check_for_alerts(lab_id, results)
        finally:
            if vlan_id:
                detach_from_vlan(vlan_id)
    
    async def _ping_sweep(self, vms: List[Dict]) -> List[Dict]:
        """Ping all VMs in parallel"""
        import subprocess
        
        results = []
        
        for vm in vms:
            vm_ip = vm.get("lab_ip") or vm.get("ip_address")
            if not vm_ip:
                continue
            
            try:
                start = datetime.now(timezone.utc)
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", vm_ip],
                    capture_output=True,
                    timeout=5
                )
                latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                results.append({
                    "vm_id": vm.get("vm_id"),
                    "ip": vm_ip,
                    "reachable": result.returncode == 0,
                    "latency_ms": latency_ms if result.returncode == 0 else None
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "vm_id": vm.get("vm_id"),
                    "ip": vm_ip,
                    "reachable": False,
                    "latency_ms": None
                })
        
        return results
    
    async def _store_results(self, lab_id: str, results: List[Dict]):
        """Store monitoring results in Redis and database"""
        import json
        
        # Store in Redis for real-time access
        key = f"whitepawn:results:{lab_id}"
        self.redis_client.setex(
            key,
            300,  # 5 minute expiry
            json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": results
            })
        )
        
        # Also store in database for history
        try:
            from glassdome.core.database import async_session_factory
            from glassdome.whitepawn.models import NetworkMonitorResult
            
            async with async_session_factory() as session:
                for result in results:
                    record = NetworkMonitorResult(
                        lab_id=lab_id,
                        vm_id=result.get("vm_id"),
                        ip_address=result.get("ip"),
                        reachable=result.get("reachable"),
                        latency_ms=result.get("latency_ms")
                    )
                    session.add(record)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to store results in DB: {e}")
    
    async def _check_for_alerts(self, lab_id: str, results: List[Dict]):
        """Check results for alert conditions"""
        import json
        
        for result in results:
            if not result.get("reachable"):
                # VM unreachable - create alert
                alert = {
                    "lab_id": lab_id,
                    "vm_id": result.get("vm_id"),
                    "ip": result.get("ip"),
                    "type": "unreachable",
                    "severity": "critical",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self.redis_client.publish("whitepawn:alerts", json.dumps(alert))
                logger.warning(f"ALERT: VM {result.get('vm_id')} unreachable")
            
            elif result.get("latency_ms", 0) > 500:
                # High latency
                alert = {
                    "lab_id": lab_id,
                    "vm_id": result.get("vm_id"),
                    "ip": result.get("ip"),
                    "type": "high_latency",
                    "severity": "warning",
                    "latency_ms": result.get("latency_ms"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self.redis_client.publish("whitepawn:alerts", json.dumps(alert))


def main():
    """Entry point for WhitePawn monitor"""
    # Use centralized logging
    from glassdome.core.logging import setup_logging_from_settings
    setup_logging_from_settings()
    
    monitor = WhitePawnMonitor()
    asyncio.run(monitor.start())


if __name__ == "__main__":
    main()


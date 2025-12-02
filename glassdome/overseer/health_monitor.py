"""
Health Monitor module for Overseer

Monitors health of all Glassdome services:
- Frontend (Vite dev server)
- Backend (FastAPI)
- WhitePawn (Network monitoring)
- Proxmox cluster
- Database

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealth:
    """Health status of a single service"""
    def __init__(
        self,
        name: str,
        status: ServiceStatus = ServiceStatus.UNKNOWN,
        response_time_ms: Optional[float] = None,
        last_check: Optional[datetime] = None,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.status = status
        self.response_time_ms = response_time_ms
        self.last_check = last_check or datetime.now(timezone.utc)
        self.error = error
        self.details = details or {}
        self.consecutive_failures = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error": self.error,
            "details": self.details,
            "consecutive_failures": self.consecutive_failures
        }


class HealthMonitor:
    """
    Monitors health of all Glassdome services.
    
    Runs periodic health checks and maintains status for:
    - Frontend (React/Vite)
    - Backend (FastAPI)
    - WhitePawn monitors
    - Proxmox cluster nodes
    - PostgreSQL database
    - Redis cache
    """
    
    def __init__(
        self,
        frontend_url: str = "http://localhost:5174",
        backend_url: str = "http://localhost:8000",
        check_interval: int = 30,
        timeout: int = 10
    ):
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.check_interval = check_interval
        self.timeout = timeout
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Service health states
        self.services: Dict[str, ServiceHealth] = {
            "frontend": ServiceHealth("frontend"),
            "backend": ServiceHealth("backend"),
            "whitepawn": ServiceHealth("whitepawn"),
            "proxmox_01": ServiceHealth("proxmox_01"),
            "proxmox_02": ServiceHealth("proxmox_02"),
            "database": ServiceHealth("database"),
            "redis": ServiceHealth("redis"),
        }
        
        # Alert callbacks
        self._alert_callbacks: List[callable] = []
        
        # Health history for trends
        self._health_history: List[Dict[str, Any]] = []
        self._max_history = 1000
    
    def register_alert_callback(self, callback: callable):
        """Register callback for health alerts"""
        self._alert_callbacks.append(callback)
    
    async def start(self):
        """Start the health monitoring loop"""
        if self._running:
            logger.warning("Health monitor already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Health monitor started (interval: {self.check_interval}s)")
    
    async def stop(self):
        """Stop the health monitoring loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._run_all_checks()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _run_all_checks(self):
        """Run all health checks in parallel"""
        checks = [
            self._check_frontend(),
            self._check_backend(),
            self._check_whitepawn(),
            self._check_proxmox(),
            self._check_database(),
            self._check_redis(),
        ]
        
        await asyncio.gather(*checks, return_exceptions=True)
        
        # Record history
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {name: svc.to_dict() for name, svc in self.services.items()}
        }
        self._health_history.append(snapshot)
        
        # Trim history
        if len(self._health_history) > self._max_history:
            self._health_history = self._health_history[-self._max_history:]
        
        # Check for alerts
        await self._check_alerts()
    
    async def _check_frontend(self):
        """Check frontend health"""
        service = self.services["frontend"]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start = asyncio.get_event_loop().time()
                resp = await client.get(self.frontend_url)
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                
                if resp.status_code == 200:
                    service.status = ServiceStatus.HEALTHY
                    service.response_time_ms = elapsed
                    service.error = None
                    service.consecutive_failures = 0
                else:
                    service.status = ServiceStatus.DEGRADED
                    service.error = f"HTTP {resp.status_code}"
                    service.consecutive_failures += 1
                    
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.error = str(e)
            service.consecutive_failures += 1
        
        service.last_check = datetime.now(timezone.utc)
    
    async def _check_backend(self):
        """Check backend health"""
        service = self.services["backend"]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start = asyncio.get_event_loop().time()
                resp = await client.get(f"{self.backend_url}/api/v1/health")
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    service.status = ServiceStatus.HEALTHY
                    service.response_time_ms = elapsed
                    service.error = None
                    service.details = data
                    service.consecutive_failures = 0
                else:
                    service.status = ServiceStatus.DEGRADED
                    service.error = f"HTTP {resp.status_code}"
                    service.consecutive_failures += 1
                    
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.error = str(e)
            service.consecutive_failures += 1
        
        service.last_check = datetime.now(timezone.utc)
    
    async def _check_whitepawn(self):
        """Check WhitePawn status via backend API"""
        service = self.services["whitepawn"]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start = asyncio.get_event_loop().time()
                resp = await client.get(f"{self.backend_url}/api/whitepawn/status")
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    active_monitors = data.get("active_monitors", 0)
                    
                    if active_monitors > 0:
                        service.status = ServiceStatus.HEALTHY
                    else:
                        service.status = ServiceStatus.DEGRADED
                    
                    service.response_time_ms = elapsed
                    service.error = None
                    service.details = data
                    service.consecutive_failures = 0
                else:
                    service.status = ServiceStatus.DEGRADED
                    service.error = f"HTTP {resp.status_code}"
                    service.consecutive_failures += 1
                    
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.error = str(e)
            service.consecutive_failures += 1
        
        service.last_check = datetime.now(timezone.utc)
    
    async def _check_proxmox(self):
        """Check Proxmox cluster health via backend API"""
        for node in ["proxmox_01", "proxmox_02"]:
            service = self.services[node]
            instance = node.split("_")[1]
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    start = asyncio.get_event_loop().time()
                    resp = await client.get(f"{self.backend_url}/api/v1/platforms/proxmox/{instance}")
                    elapsed = (asyncio.get_event_loop().time() - start) * 1000
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("connected"):
                            service.status = ServiceStatus.HEALTHY
                        else:
                            service.status = ServiceStatus.UNHEALTHY
                        
                        service.response_time_ms = elapsed
                        service.error = None
                        service.details = data
                        service.consecutive_failures = 0
                    else:
                        service.status = ServiceStatus.DEGRADED
                        service.error = f"HTTP {resp.status_code}"
                        service.consecutive_failures += 1
                        
            except Exception as e:
                service.status = ServiceStatus.UNHEALTHY
                service.error = str(e)
                service.consecutive_failures += 1
            
            service.last_check = datetime.now(timezone.utc)
    
    async def _check_database(self):
        """Check database health via backend API"""
        service = self.services["database"]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start = asyncio.get_event_loop().time()
                resp = await client.get(f"{self.backend_url}/api/v1/health")
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    db_status = data.get("database", {})
                    
                    if db_status.get("connected"):
                        service.status = ServiceStatus.HEALTHY
                    else:
                        service.status = ServiceStatus.UNHEALTHY
                    
                    service.response_time_ms = elapsed
                    service.error = None
                    service.details = db_status
                    service.consecutive_failures = 0
                else:
                    service.status = ServiceStatus.DEGRADED
                    service.consecutive_failures += 1
                    
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.error = str(e)
            service.consecutive_failures += 1
        
        service.last_check = datetime.now(timezone.utc)
    
    async def _check_redis(self):
        """Check Redis health via backend API"""
        service = self.services["redis"]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start = asyncio.get_event_loop().time()
                resp = await client.get(f"{self.backend_url}/api/v1/health")
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    redis_status = data.get("redis", {})
                    
                    if redis_status.get("connected"):
                        service.status = ServiceStatus.HEALTHY
                    else:
                        service.status = ServiceStatus.UNHEALTHY
                    
                    service.response_time_ms = elapsed
                    service.error = None
                    service.details = redis_status
                    service.consecutive_failures = 0
                else:
                    service.status = ServiceStatus.DEGRADED
                    service.consecutive_failures += 1
                    
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.error = str(e)
            service.consecutive_failures += 1
        
        service.last_check = datetime.now(timezone.utc)
    
    async def _check_alerts(self):
        """Check for alert conditions and notify"""
        for name, service in self.services.items():
            # Alert on 3+ consecutive failures
            if service.consecutive_failures >= 3:
                await self._send_alert(
                    level="critical",
                    service=name,
                    message=f"Service {name} has failed {service.consecutive_failures} consecutive health checks",
                    error=service.error
                )
            # Alert on degraded status
            elif service.status == ServiceStatus.DEGRADED and service.consecutive_failures >= 2:
                await self._send_alert(
                    level="warning",
                    service=name,
                    message=f"Service {name} is degraded",
                    error=service.error
                )
    
    async def _send_alert(self, level: str, service: str, message: str, error: Optional[str] = None):
        """Send alert to registered callbacks"""
        alert = {
            "level": level,
            "service": service,
            "message": message,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.warning(f"ALERT [{level.upper()}] {service}: {message}")
        
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        services_status = {name: svc.to_dict() for name, svc in self.services.items()}
        
        # Calculate overall status
        unhealthy_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.UNHEALTHY)
        degraded_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.DEGRADED)
        
        if unhealthy_count > 0:
            overall = ServiceStatus.UNHEALTHY
        elif degraded_count > 0:
            overall = ServiceStatus.DEGRADED
        else:
            overall = ServiceStatus.HEALTHY
        
        return {
            "overall": overall.value,
            "services": services_status,
            "unhealthy_count": unhealthy_count,
            "degraded_count": degraded_count,
            "last_check": datetime.now(timezone.utc).isoformat()
        }
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get health check history"""
        return self._health_history[-limit:]


# Singleton instance
_monitor: Optional[HealthMonitor] = None


def get_health_monitor(
    frontend_url: str = "http://localhost:5174",
    backend_url: str = "http://localhost:8000",
    check_interval: int = 30
) -> HealthMonitor:
    """Get or create the health monitor singleton"""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor(
            frontend_url=frontend_url,
            backend_url=backend_url,
            check_interval=check_interval
        )
    return _monitor


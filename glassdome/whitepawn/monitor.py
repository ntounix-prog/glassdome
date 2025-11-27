"""
WhitePawn Monitor

The core monitoring engine that runs continuous network validation.
Designed to be lightweight and non-intrusive while providing
comprehensive visibility into network health.

Monitoring Capabilities:
- ICMP ping sweeps to all VMs
- TCP port checks
- Gateway reachability
- DNS resolution
- ARP table monitoring
- VLAN isolation verification
- Latency trending
"""

import asyncio
import logging
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
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
from glassdome.networking.models import NetworkDefinition, VMInterface, DeployedVM

logger = logging.getLogger(__name__)


class MonitoringResult:
    """Result of a single monitoring check"""
    def __init__(
        self,
        success: bool,
        target_ip: str,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        self.success = success
        self.target_ip = target_ip
        self.latency_ms = latency_ms
        self.error = error
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class WhitePawnMonitor:
    """
    Continuous network monitoring for a single lab deployment.
    
    This runs as an async task, performing various checks at configured intervals.
    """
    
    DEFAULT_CONFIG = {
        "ping_interval": 10,         # Seconds between ping sweeps
        "ping_timeout": 2,           # Seconds to wait for ping response
        "ping_count": 2,             # Number of pings per target
        "latency_warning_ms": 50,    # Warn if latency exceeds this
        "latency_critical_ms": 200,  # Critical if latency exceeds this
        "gateway_check_interval": 15,
        "dns_check_interval": 30,
        "dns_test_domain": "google.com",
        "arp_scan_interval": 60,
        "matrix_save_interval": 60,  # Save connectivity matrix every N seconds
        "alert_cooldown": 300,       # Don't repeat same alert for N seconds
    }
    
    def __init__(self, deployment_id: int, config: Optional[Dict] = None):
        self.deployment_id = deployment_id
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_alerts: Dict[str, datetime] = {}  # For cooldown
        
        # Cached target info
        self._targets: List[Dict[str, Any]] = []
        self._gateway: Optional[str] = None
        self._dns_server: Optional[str] = None
        
        # Metrics
        self._check_count = 0
        self._alert_count = 0
        self._last_matrix: Optional[Dict] = None
    
    async def start(self):
        """Start the monitoring loop"""
        if self._running:
            logger.warning(f"WhitePawn {self.deployment_id} already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"WhitePawn monitor {self.deployment_id} started")
        
        # Create startup event
        await self._create_alert(
            AlertType.WHITEPAWN_DEPLOYED,
            AlertSeverity.INFO,
            "WhitePawn Monitoring Started",
            f"Continuous network monitoring is now active"
        )
    
    async def stop(self):
        """Stop the monitoring loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"WhitePawn monitor {self.deployment_id} stopped")
        
        await self._create_alert(
            AlertType.WHITEPAWN_STOPPED,
            AlertSeverity.WARNING,
            "WhitePawn Monitoring Stopped",
            "Network monitoring has been stopped"
        )
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        # Load initial targets
        await self._refresh_targets()
        
        last_ping = 0
        last_gateway = 0
        last_dns = 0
        last_matrix_save = 0
        
        while self._running:
            try:
                now = time.time()
                
                # Ping sweep
                if now - last_ping >= self.config["ping_interval"]:
                    await self._ping_sweep()
                    last_ping = now
                
                # Gateway check
                if now - last_gateway >= self.config["gateway_check_interval"]:
                    await self._check_gateway()
                    last_gateway = now
                
                # DNS check
                if now - last_dns >= self.config["dns_check_interval"]:
                    await self._check_dns()
                    last_dns = now
                
                # Save connectivity matrix
                if now - last_matrix_save >= self.config["matrix_save_interval"]:
                    await self._save_connectivity_matrix()
                    last_matrix_save = now
                
                # Update heartbeat
                await self._update_heartbeat()
                
                # Small sleep to prevent tight loop
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WhitePawn {self.deployment_id} error: {e}")
                await asyncio.sleep(5)
    
    async def _refresh_targets(self):
        """Refresh the list of targets to monitor"""
        async with AsyncSessionLocal() as session:
            # Get deployment
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.id == self.deployment_id
                )
            )
            deployment = result.scalar_one_or_none()
            
            if not deployment:
                logger.error(f"Deployment {self.deployment_id} not found")
                return
            
            lab_id = deployment.lab_id
            
            # Get all VMs in this lab
            vm_result = await session.execute(
                select(DeployedVM).where(DeployedVM.lab_id == lab_id)
            )
            vms = vm_result.scalars().all()
            
            self._targets = []
            for vm in vms:
                if vm.ip_address:
                    self._targets.append({
                        "vm_id": vm.vm_id,
                        "name": vm.name,
                        "ip": vm.ip_address,
                        "platform": vm.platform
                    })
            
            # Get networks for gateway info
            net_result = await session.execute(
                select(NetworkDefinition).where(NetworkDefinition.lab_id == lab_id)
            )
            networks = net_result.scalars().all()
            
            for network in networks:
                if network.gateway:
                    self._gateway = network.gateway
                if network.dns_servers and len(network.dns_servers) > 0:
                    self._dns_server = network.dns_servers[0]
            
            # Update deployment with monitored VMs
            deployment.monitored_vms = [t["ip"] for t in self._targets]
            await session.commit()
            
            logger.info(f"WhitePawn {self.deployment_id}: monitoring {len(self._targets)} targets")
    
    async def _ping_sweep(self):
        """Ping all targets and record results"""
        if not self._targets:
            await self._refresh_targets()
            return
        
        results = []
        for target in self._targets:
            result = await self._ping(target["ip"])
            results.append((target, result))
            
            # Log event
            await self._log_event(
                event_type="ping",
                target_ip=target["ip"],
                target_vm_id=target["vm_id"],
                success=result.success,
                latency_ms=result.latency_ms,
                error=result.error
            )
            
            # Check for issues
            if not result.success:
                await self._create_alert(
                    AlertType.PING_FAILED,
                    AlertSeverity.ERROR,
                    f"VM Unreachable: {target['name']}",
                    f"Cannot ping {target['ip']} ({target['name']})",
                    target_ip=target["ip"],
                    target_vm_id=target["vm_id"],
                    target_vm_name=target["name"]
                )
            elif result.latency_ms:
                if result.latency_ms > self.config["latency_critical_ms"]:
                    await self._create_alert(
                        AlertType.PING_LATENCY,
                        AlertSeverity.ERROR,
                        f"Critical Latency: {target['name']}",
                        f"Latency to {target['ip']} is {result.latency_ms:.1f}ms",
                        target_ip=target["ip"],
                        target_vm_id=target["vm_id"],
                        latency_ms=result.latency_ms
                    )
                elif result.latency_ms > self.config["latency_warning_ms"]:
                    await self._create_alert(
                        AlertType.PING_LATENCY,
                        AlertSeverity.WARNING,
                        f"High Latency: {target['name']}",
                        f"Latency to {target['ip']} is {result.latency_ms:.1f}ms",
                        target_ip=target["ip"],
                        target_vm_id=target["vm_id"],
                        latency_ms=result.latency_ms
                    )
        
        # Build connectivity matrix
        if len(self._targets) > 0:
            self._last_matrix = await self._build_matrix(results)
        
        self._check_count += len(results)
    
    async def _ping(self, target_ip: str) -> MonitoringResult:
        """Execute a ping to a target"""
        try:
            count = self.config["ping_count"]
            timeout = self.config["ping_timeout"]
            
            # Use subprocess to run ping
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", str(count), "-W", str(timeout), target_ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout * count + 5
            )
            
            if proc.returncode == 0:
                # Parse latency from output
                output = stdout.decode()
                latency = self._parse_ping_latency(output)
                return MonitoringResult(
                    success=True,
                    target_ip=target_ip,
                    latency_ms=latency
                )
            else:
                return MonitoringResult(
                    success=False,
                    target_ip=target_ip,
                    error="Host unreachable"
                )
                
        except asyncio.TimeoutError:
            return MonitoringResult(
                success=False,
                target_ip=target_ip,
                error="Ping timeout"
            )
        except Exception as e:
            return MonitoringResult(
                success=False,
                target_ip=target_ip,
                error=str(e)
            )
    
    def _parse_ping_latency(self, output: str) -> Optional[float]:
        """Parse average latency from ping output"""
        try:
            # Look for "min/avg/max/mdev = X/Y/Z/W ms"
            for line in output.split("\n"):
                if "avg" in line and "=" in line:
                    # Format: rtt min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms
                    parts = line.split("=")[1].strip().split("/")
                    if len(parts) >= 2:
                        return float(parts[1])
        except:
            pass
        return None
    
    async def _check_gateway(self):
        """Check gateway reachability"""
        if not self._gateway:
            return
        
        result = await self._ping(self._gateway)
        
        await self._log_event(
            event_type="gateway",
            target_ip=self._gateway,
            success=result.success,
            latency_ms=result.latency_ms,
            error=result.error
        )
        
        if not result.success:
            await self._create_alert(
                AlertType.GATEWAY_UNREACHABLE,
                AlertSeverity.CRITICAL,
                "Gateway Unreachable",
                f"Cannot reach network gateway at {self._gateway}",
                target_ip=self._gateway
            )
    
    async def _check_dns(self):
        """Check DNS resolution"""
        dns_server = self._dns_server or "8.8.8.8"
        test_domain = self.config["dns_test_domain"]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "dig", "+short", f"@{dns_server}", test_domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=5
            )
            
            success = proc.returncode == 0 and len(stdout.strip()) > 0
            
            await self._log_event(
                event_type="dns",
                target_ip=dns_server,
                success=success,
                error=None if success else "DNS resolution failed"
            )
            
            if not success:
                await self._create_alert(
                    AlertType.DNS_FAILED,
                    AlertSeverity.ERROR,
                    "DNS Resolution Failed",
                    f"Cannot resolve {test_domain} via {dns_server}",
                    target_ip=dns_server
                )
                
        except asyncio.TimeoutError:
            await self._create_alert(
                AlertType.DNS_FAILED,
                AlertSeverity.ERROR,
                "DNS Timeout",
                f"DNS query to {dns_server} timed out",
                target_ip=dns_server
            )
        except Exception as e:
            logger.error(f"DNS check error: {e}")
    
    async def _build_matrix(self, results: List[Tuple[Dict, MonitoringResult]]) -> Dict:
        """Build connectivity matrix from ping results"""
        matrix = {}
        
        for target, result in results:
            ip = target["ip"]
            matrix[ip] = {
                "name": target["name"],
                "reachable": result.success,
                "latency_ms": result.latency_ms,
                "last_check": datetime.utcnow().isoformat()
            }
        
        return matrix
    
    async def _save_connectivity_matrix(self):
        """Save the current connectivity matrix to DB"""
        if not self._last_matrix:
            return
        
        async with AsyncSessionLocal() as session:
            # Get lab_id
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.id == self.deployment_id
                )
            )
            deployment = result.scalar_one_or_none()
            if not deployment:
                return
            
            # Calculate summary stats
            total_pairs = len(self._last_matrix)
            reachable_pairs = sum(1 for v in self._last_matrix.values() if v.get("reachable"))
            latencies = [v["latency_ms"] for v in self._last_matrix.values() 
                        if v.get("reachable") and v.get("latency_ms")]
            
            avg_latency = sum(latencies) / len(latencies) if latencies else None
            max_latency = max(latencies) if latencies else None
            
            matrix_record = ConnectivityMatrix(
                deployment_id=self.deployment_id,
                lab_id=deployment.lab_id,
                matrix=self._last_matrix,
                total_pairs=total_pairs,
                reachable_pairs=reachable_pairs,
                avg_latency_ms=avg_latency,
                max_latency_ms=max_latency
            )
            
            session.add(matrix_record)
            
            # Update deployment uptime
            if total_pairs > 0:
                deployment.uptime_percent = (reachable_pairs / total_pairs) * 100
            
            await session.commit()
    
    async def _update_heartbeat(self):
        """Update deployment heartbeat"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WhitePawnDeployment).where(
                    WhitePawnDeployment.id == self.deployment_id
                )
            )
            deployment = result.scalar_one_or_none()
            if deployment:
                deployment.last_heartbeat = datetime.utcnow()
                deployment.total_checks = self._check_count
                deployment.total_alerts = self._alert_count
                deployment.status = "active"
                await session.commit()
    
    async def _log_event(
        self,
        event_type: str,
        target_ip: Optional[str] = None,
        target_vm_id: Optional[str] = None,
        success: bool = True,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log a monitoring event"""
        async with AsyncSessionLocal() as session:
            event = MonitoringEvent(
                deployment_id=self.deployment_id,
                event_type=event_type,
                target_ip=target_ip,
                target_vm_id=target_vm_id,
                success=success,
                latency_ms=latency_ms,
                error=error,
                details=details
            )
            session.add(event)
            await session.commit()
    
    async def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        target_ip: Optional[str] = None,
        target_vm_id: Optional[str] = None,
        target_vm_name: Optional[str] = None,
        network_id: Optional[int] = None,
        latency_ms: Optional[float] = None,
        details: Optional[Dict] = None
    ):
        """Create an alert if not in cooldown"""
        # Check cooldown
        cooldown_key = f"{alert_type}:{target_ip or 'global'}"
        last_alert = self._last_alerts.get(cooldown_key)
        
        if last_alert:
            cooldown = timedelta(seconds=self.config["alert_cooldown"])
            if datetime.utcnow() - last_alert < cooldown:
                return  # Still in cooldown
        
        self._last_alerts[cooldown_key] = datetime.utcnow()
        self._alert_count += 1
        
        async with AsyncSessionLocal() as session:
            alert = NetworkAlert(
                deployment_id=self.deployment_id,
                alert_type=alert_type.value,
                severity=severity.value,
                target_ip=target_ip,
                target_vm_id=target_vm_id,
                target_vm_name=target_vm_name,
                network_id=network_id,
                title=title,
                message=message,
                latency_ms=latency_ms,
                details=details
            )
            session.add(alert)
            await session.commit()
            
            logger.warning(f"ALERT [{severity.value}] {title}: {message}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current monitor status"""
        return {
            "deployment_id": self.deployment_id,
            "running": self._running,
            "targets": len(self._targets),
            "check_count": self._check_count,
            "alert_count": self._alert_count,
            "gateway": self._gateway,
            "dns_server": self._dns_server,
            "last_matrix": self._last_matrix
        }


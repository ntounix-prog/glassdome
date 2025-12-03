"""
Network Probes API

Monitors critical network links and VPN tunnels.
Provides real-time status for dashboard and Overseer chat.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/probes", tags=["network-probes"])

# ============================================================================
# Configuration - Network Probes
# ============================================================================

NETWORK_PROBES = {
    "mxwest": {
        "name": "MXWest Gateway",
        "host": "10.30.0.1",
        "description": "VPN tunnel to MXWest datacenter",
        "critical": True,
        "via_gateway": "192.168.3.99"
    },
    "mxwest-gateway": {
        "name": "VPN Gateway",
        "host": "192.168.3.99",
        "description": "Local gateway that routes to MXWest",
        "critical": True,
    },
}

# State tracking for uptime/downtime history
_probe_history: Dict[str, List[Dict]] = {}
_last_check: Dict[str, Dict] = {}


# ============================================================================
# Pydantic Models
# ============================================================================

class ProbeStatus(BaseModel):
    probe_id: str
    name: str
    host: str
    status: str  # "up", "down", "error"
    reachable: bool
    latency_ms: Optional[float] = None
    last_check: str
    description: Optional[str] = None
    critical: bool = False
    via_gateway: Optional[str] = None


class ProbeResult(BaseModel):
    timestamp: str
    probes: Dict[str, ProbeStatus]
    all_healthy: bool
    critical_down: List[str]


class ProbeHistoryEntry(BaseModel):
    timestamp: str
    status: str
    latency_ms: Optional[float] = None


# ============================================================================
# Helper Functions
# ============================================================================

async def ping_host(host: str, count: int = 2, timeout: int = 3) -> tuple[bool, Optional[float]]:
    """
    Ping a host and return (reachable, latency_ms)
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), "-W", str(timeout), host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
        
        if proc.returncode == 0:
            # Parse latency from ping output
            output = stdout.decode()
            # Look for "time=XX.X ms" pattern
            import re
            match = re.search(r'time[=<](\d+\.?\d*)\s*ms', output)
            latency = float(match.group(1)) if match else None
            return True, latency
        else:
            return False, None
            
    except asyncio.TimeoutError:
        return False, None
    except Exception as e:
        logger.error(f"Ping error for {host}: {e}")
        return False, None


def record_history(probe_id: str, status: str, latency: Optional[float]):
    """Record probe result in history (keep last 100 entries)"""
    if probe_id not in _probe_history:
        _probe_history[probe_id] = []
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "latency_ms": latency
    }
    
    _probe_history[probe_id].append(entry)
    
    # Keep only last 100 entries
    if len(_probe_history[probe_id]) > 100:
        _probe_history[probe_id] = _probe_history[probe_id][-100:]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/")
async def list_probes():
    """List all configured network probes"""
    return {
        "probes": [
            {
                "id": probe_id,
                "name": config["name"],
                "host": config["host"],
                "description": config.get("description"),
                "critical": config.get("critical", False)
            }
            for probe_id, config in NETWORK_PROBES.items()
        ]
    }


@router.get("/status", response_model=ProbeResult)
async def get_all_probe_status():
    """
    Check all network probes and return current status.
    
    This is the main endpoint for dashboard integration.
    """
    results = {}
    critical_down = []
    
    for probe_id, config in NETWORK_PROBES.items():
        host = config["host"]
        reachable, latency = await ping_host(host)
        status = "up" if reachable else "down"
        
        # Record in history
        record_history(probe_id, status, latency)
        
        # Track critical failures
        if not reachable and config.get("critical", False):
            critical_down.append(probe_id)
        
        probe_status = ProbeStatus(
            probe_id=probe_id,
            name=config["name"],
            host=host,
            status=status,
            reachable=reachable,
            latency_ms=latency,
            last_check=datetime.now().isoformat(),
            description=config.get("description"),
            critical=config.get("critical", False),
            via_gateway=config.get("via_gateway")
        )
        
        results[probe_id] = probe_status
        _last_check[probe_id] = probe_status.dict()
    
    return ProbeResult(
        timestamp=datetime.now().isoformat(),
        probes=results,
        all_healthy=len(critical_down) == 0,
        critical_down=critical_down
    )


@router.get("/status/{probe_id}")
async def get_probe_status(probe_id: str):
    """Check a single probe"""
    if probe_id not in NETWORK_PROBES:
        raise HTTPException(status_code=404, detail=f"Probe '{probe_id}' not found")
    
    config = NETWORK_PROBES[probe_id]
    reachable, latency = await ping_host(config["host"])
    status = "up" if reachable else "down"
    
    record_history(probe_id, status, latency)
    
    return ProbeStatus(
        probe_id=probe_id,
        name=config["name"],
        host=config["host"],
        status=status,
        reachable=reachable,
        latency_ms=latency,
        last_check=datetime.now().isoformat(),
        description=config.get("description"),
        critical=config.get("critical", False),
        via_gateway=config.get("via_gateway")
    )


@router.get("/history/{probe_id}")
async def get_probe_history(probe_id: str, limit: int = 50):
    """Get recent history for a probe"""
    if probe_id not in NETWORK_PROBES:
        raise HTTPException(status_code=404, detail=f"Probe '{probe_id}' not found")
    
    history = _probe_history.get(probe_id, [])
    
    return {
        "probe_id": probe_id,
        "name": NETWORK_PROBES[probe_id]["name"],
        "history": history[-limit:],
        "total_entries": len(history)
    }


@router.get("/mxwest")
async def mxwest_quick_status():
    """
    Quick status check for MXWest link.
    
    Returns simple status for easy monitoring.
    Designed for mobile/quick checks.
    """
    gateway_up, gateway_latency = await ping_host("192.168.3.99")
    mxwest_up, mxwest_latency = await ping_host("10.30.0.1")
    
    # Determine overall status
    if gateway_up and mxwest_up:
        status = "healthy"
        emoji = "🟢"
        message = f"Link healthy (latency: {mxwest_latency:.1f}ms)" if mxwest_latency else "Link healthy"
    elif gateway_up and not mxwest_up:
        status = "vpn_down"
        emoji = "🔴"
        message = "VPN tunnel appears down - gateway reachable but MXWest is not"
    else:
        status = "gateway_down"
        emoji = "🔴"
        message = "Gateway unreachable at 192.168.3.99"
    
    return {
        "status": status,
        "emoji": emoji,
        "message": message,
        "gateway": {
            "host": "192.168.3.99",
            "reachable": gateway_up,
            "latency_ms": gateway_latency
        },
        "mxwest": {
            "host": "10.30.0.1",
            "reachable": mxwest_up,
            "latency_ms": mxwest_latency
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/watchdog/log")
async def get_watchdog_log(lines: int = 50):
    """Get recent watchdog log entries"""
    log_paths = [
        Path("/var/log/mxwest-watchdog.log"),
        Path("/tmp/mxwest-watchdog.log")
    ]
    
    for log_path in log_paths:
        if log_path.exists():
            try:
                content = log_path.read_text()
                log_lines = content.strip().split('\n')
                return {
                    "log_file": str(log_path),
                    "lines": log_lines[-lines:],
                    "total_lines": len(log_lines)
                }
            except Exception as e:
                logger.error(f"Error reading log: {e}")
    
    return {
        "log_file": None,
        "lines": [],
        "message": "No watchdog log found"
    }


@router.get("/mxwest/mailq")
async def check_mxwest_mailq():
    """
    Check the mail queue on mxwest.
    
    Returns the current state of the Postfix mail queue.
    If there are queued messages, shows count and can optionally flush.
    """
    try:
        result = await asyncio.create_subprocess_exec(
            "ssh", "-i", "/home/nomad/.ssh/mxwest_key",
            "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
            "ubuntu@10.30.0.1",
            "mailq 2>/dev/null || postqueue -p 2>/dev/null",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=20)
        
        if result.returncode == 0:
            output = stdout.decode().strip()
            
            # Parse queue status
            is_empty = "is empty" in output.lower()
            queue_count = 0
            
            if not is_empty:
                # Count queued messages (lines starting with hex ID)
                import re
                queue_count = len(re.findall(r'^[A-F0-9]+', output, re.MULTILINE))
            
            return {
                "success": True,
                "queue_empty": is_empty,
                "queue_count": queue_count,
                "raw_output": output,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": stderr.decode().strip() or "Failed to check mail queue",
                "timestamp": datetime.now().isoformat()
            }
            
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "SSH command timed out",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to check mail queue: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/mxwest/mailq/flush")
async def flush_mxwest_mailq():
    """
    Flush the mail queue on mxwest.
    
    Forces Postfix to attempt immediate delivery of all queued messages.
    """
    try:
        result = await asyncio.create_subprocess_exec(
            "ssh", "-i", "/home/nomad/.ssh/mxwest_key",
            "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
            "ubuntu@10.30.0.1",
            "sudo postqueue -f && sleep 2 && mailq | head -10",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=30)
        
        if result.returncode == 0:
            return {
                "success": True,
                "action": "Mail queue flush initiated",
                "output": stdout.decode().strip(),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": stderr.decode().strip() or "Failed to flush queue",
                "timestamp": datetime.now().isoformat()
            }
            
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "SSH command timed out",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to flush mail queue: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/mxwest/restart")
async def restart_mxwest_wireguard():
    """
    Manually restart WireGuard on Rome to restore MXWest link.
    
    Use this if the auto-healing didn't work or you want to force a restart.
    """
    import subprocess
    
    try:
        # SSH to Rome and restart WireGuard
        result = await asyncio.create_subprocess_exec(
            "ssh", "-i", "/home/nomad/.ssh/rome_key",
            "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
            "nomad@192.168.3.99",
            "sudo systemctl restart wg-quick@wg0 && sleep 2 && sudo wg show wg0 | head -8",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=30)
        
        if result.returncode == 0:
            # Verify link is back
            await asyncio.sleep(3)
            mxwest_up, latency = await ping_host("10.30.0.1")
            
            return {
                "success": True,
                "action": "WireGuard restarted on Rome",
                "wireguard_status": stdout.decode().strip(),
                "mxwest_reachable": mxwest_up,
                "mxwest_latency_ms": latency,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": stderr.decode().strip() or "SSH command failed",
                "timestamp": datetime.now().isoformat()
            }
            
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "SSH command timed out",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to restart WireGuard: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


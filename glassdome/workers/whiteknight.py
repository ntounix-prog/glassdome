"""
WhiteKnight Worker
==================

Handles vulnerability validation tasks.
Verifies that injected vulnerabilities are exploitable.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional

from .celery_app import celery_app
from .reaper import attach_to_vlan, detach_from_vlan

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="whiteknight.validate_vulnerability")
def validate_vulnerability(
    self,
    vm_id: str,
    vm_ip: str,
    exploit_id: str,
    vlan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate that a vulnerability is exploitable on the target VM.
    """
    worker_id = os.getenv("WORKER_ID", "whiteknight")
    logger.info(f"[{worker_id}] Validating {exploit_id} on VM {vm_id} at {vm_ip}")
    
    try:
        if vlan_id:
            attach_to_vlan(vlan_id)
        
        result = asyncio.run(_validate_async(vm_id, vm_ip, exploit_id))
        
        if vlan_id:
            detach_from_vlan(vlan_id)
        
        return result
        
    except Exception as e:
        logger.error(f"[{worker_id}] Validation failed: {e}")
        if vlan_id:
            detach_from_vlan(vlan_id)
        return {"success": False, "exploitable": False, "error": str(e)}


async def _validate_async(vm_id: str, vm_ip: str, exploit_id: str) -> Dict[str, Any]:
    """Async vulnerability validation"""
    from glassdome.core.database import async_session_factory
    from glassdome.reaper.exploit_library import Exploit
    from sqlalchemy import select
    import asyncssh
    import subprocess
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(Exploit).where(Exploit.id == exploit_id)
        )
        exploit = result.scalar_one_or_none()
        
        if not exploit:
            return {"success": False, "error": f"Exploit {exploit_id} not found"}
        
        # Run validation based on exploit type
        exploit_type = exploit.exploit_type or "generic"
        
        if exploit_type == "ssh":
            # Test SSH with weak credentials
            return await _validate_ssh(vm_ip, exploit)
        elif exploit_type == "sql":
            # Test SQL injection
            return await _validate_sql(vm_ip, exploit)
        elif exploit_type == "web":
            # Test web vulnerability
            return await _validate_web(vm_ip, exploit)
        else:
            # Generic - run verification script if available
            return await _validate_generic(vm_ip, exploit)


async def _validate_ssh(vm_ip: str, exploit) -> Dict[str, Any]:
    """Validate SSH vulnerability (weak password)"""
    import asyncssh
    
    test_credentials = [
        ("root", "root"),
        ("root", "toor"),
        ("admin", "admin"),
        ("ubuntu", "ubuntu"),
        ("test", "test"),
    ]
    
    for username, password in test_credentials:
        try:
            async with asyncssh.connect(
                vm_ip,
                username=username,
                password=password,
                known_hosts=None,
                connect_timeout=10
            ) as conn:
                # Successfully connected with weak creds
                result = await conn.run("whoami", check=False)
                return {
                    "success": True,
                    "exploitable": True,
                    "message": f"SSH login succeeded with {username}:{password}",
                    "evidence": f"Logged in as: {result.stdout.strip()}"
                }
        except asyncssh.Error:
            continue
    
    return {
        "success": True,
        "exploitable": False,
        "message": "No weak SSH credentials found"
    }


async def _validate_sql(vm_ip: str, exploit) -> Dict[str, Any]:
    """Validate SQL injection vulnerability"""
    import subprocess
    
    # Use sqlmap to test for SQL injection
    target_url = f"http://{vm_ip}/"
    
    try:
        result = subprocess.run(
            ["sqlmap", "-u", target_url, "--batch", "--level=1", "--risk=1", "--timeout=10"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if "injectable" in result.stdout.lower() or "vulnerable" in result.stdout.lower():
            return {
                "success": True,
                "exploitable": True,
                "message": "SQL injection vulnerability confirmed",
                "evidence": result.stdout[:500]
            }
        else:
            return {
                "success": True,
                "exploitable": False,
                "message": "No SQL injection found"
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "sqlmap timeout"}
    except FileNotFoundError:
        return {"success": False, "error": "sqlmap not installed"}


async def _validate_web(vm_ip: str, exploit) -> Dict[str, Any]:
    """Validate web vulnerability"""
    import subprocess
    
    target_url = f"http://{vm_ip}/"
    
    try:
        result = subprocess.run(
            ["nikto", "-h", target_url, "-Tuning", "x", "-timeout", "5"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        vulnerabilities = []
        for line in result.stdout.split("\n"):
            if "OSVDB" in line or "vulnerability" in line.lower():
                vulnerabilities.append(line.strip())
        
        return {
            "success": True,
            "exploitable": len(vulnerabilities) > 0,
            "message": f"Found {len(vulnerabilities)} potential vulnerabilities",
            "evidence": "\n".join(vulnerabilities[:10])
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "nikto timeout"}
    except FileNotFoundError:
        return {"success": False, "error": "nikto not installed"}


async def _validate_generic(vm_ip: str, exploit) -> Dict[str, Any]:
    """Generic validation using exploit's verification script"""
    import asyncssh
    
    if not exploit.verification_script:
        return {"success": True, "exploitable": None, "message": "No verification script"}
    
    try:
        # Try to connect with default creds
        async with asyncssh.connect(
            vm_ip,
            username="ubuntu",
            password="ubuntu",
            known_hosts=None,
            connect_timeout=30
        ) as conn:
            result = await conn.run(exploit.verification_script, check=False)
            
            return {
                "success": True,
                "exploitable": result.exit_status == 0,
                "message": result.stdout.strip() if result.stdout else "Verification complete",
                "evidence": result.stdout[:500] if result.stdout else None
            }
    except asyncssh.Error as e:
        return {"success": False, "error": f"SSH error: {e}"}


@celery_app.task(bind=True, name="whiteknight.validate_mission")
def validate_mission(
    self,
    mission_id: str,
    target_vms: List[Dict[str, Any]],
    exploits: List[str],
    vlan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate all exploits on all VMs for a mission.
    """
    worker_id = os.getenv("WORKER_ID", "whiteknight")
    logger.info(f"[{worker_id}] Validating mission {mission_id}")
    
    results = []
    
    if vlan_id:
        attach_to_vlan(vlan_id)
    
    try:
        for vm in target_vms:
            vm_id = vm.get("vm_id")
            vm_ip = vm.get("ip_address") or vm.get("lab_ip")
            
            for exploit_id in exploits:
                result = asyncio.run(_validate_async(vm_id, vm_ip, exploit_id))
                results.append({
                    "vm_id": vm_id,
                    "exploit_id": exploit_id,
                    **result
                })
    finally:
        if vlan_id:
            detach_from_vlan(vlan_id)
    
    exploitable = sum(1 for r in results if r.get("exploitable"))
    
    return {
        "mission_id": mission_id,
        "total_tests": len(results),
        "exploitable": exploitable,
        "not_exploitable": len(results) - exploitable,
        "results": results
    }


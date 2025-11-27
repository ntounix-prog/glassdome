"""
Reaper Worker
=============

Handles vulnerability injection tasks.
Can attach to lab VLANs to configure VMs directly.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="reaper.inject_vulnerability")
def inject_vulnerability(
    self,
    vm_id: str,
    vm_ip: str,
    exploit_id: str,
    credentials: Dict[str, str],
    vlan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Inject a vulnerability into a target VM.
    
    If vlan_id is provided, the worker will attach to that VLAN
    before attempting the injection.
    """
    worker_id = os.getenv("WORKER_ID", "reaper")
    logger.info(f"[{worker_id}] Injecting {exploit_id} into VM {vm_id} at {vm_ip}")
    
    try:
        # If VLAN specified, attach to it first
        if vlan_id:
            attach_to_vlan(vlan_id)
        
        # Run the injection
        result = asyncio.run(_inject_async(
            vm_id=vm_id,
            vm_ip=vm_ip,
            exploit_id=exploit_id,
            credentials=credentials
        ))
        
        # Detach from VLAN
        if vlan_id:
            detach_from_vlan(vlan_id)
        
        return result
        
    except Exception as e:
        logger.error(f"[{worker_id}] Injection failed: {e}")
        if vlan_id:
            detach_from_vlan(vlan_id)
        return {"success": False, "error": str(e)}


async def _inject_async(
    vm_id: str,
    vm_ip: str,
    exploit_id: str,
    credentials: Dict[str, str]
) -> Dict[str, Any]:
    """Async vulnerability injection"""
    import asyncssh
    from glassdome.core.database import async_session_factory
    from glassdome.reaper.exploit_library import Exploit
    from sqlalchemy import select
    
    async with async_session_factory() as session:
        # Get exploit details
        result = await session.execute(
            select(Exploit).where(Exploit.id == exploit_id)
        )
        exploit = result.scalar_one_or_none()
        
        if not exploit:
            return {"success": False, "error": f"Exploit {exploit_id} not found"}
        
        # Connect to VM
        username = credentials.get("username", "ubuntu")
        password = credentials.get("password")
        
        try:
            async with asyncssh.connect(
                vm_ip,
                username=username,
                password=password,
                known_hosts=None,
                connect_timeout=30
            ) as conn:
                # Run the install script
                if exploit.install_script:
                    result = await conn.run(exploit.install_script, check=False)
                    if result.exit_status != 0:
                        return {
                            "success": False,
                            "error": f"Install script failed: {result.stderr}"
                        }
                
                # Verify the injection
                if exploit.verification_script:
                    result = await conn.run(exploit.verification_script, check=False)
                    verified = result.exit_status == 0
                else:
                    verified = True
                
                return {
                    "success": True,
                    "exploit_id": exploit_id,
                    "vm_id": vm_id,
                    "verified": verified
                }
                
        except asyncssh.Error as e:
            return {"success": False, "error": f"SSH error: {e}"}


@celery_app.task(bind=True, name="reaper.run_mission")
def run_mission(
    self,
    mission_id: str,
    target_vms: List[Dict[str, Any]],
    exploits: List[str],
    vlan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run a complete Reaper mission across multiple VMs.
    Injects all specified exploits into all target VMs.
    """
    worker_id = os.getenv("WORKER_ID", "reaper")
    logger.info(f"[{worker_id}] Running mission {mission_id}: {len(exploits)} exploits on {len(target_vms)} VMs")
    
    results = []
    
    # Attach to VLAN once for entire mission
    if vlan_id:
        attach_to_vlan(vlan_id)
    
    try:
        for vm in target_vms:
            vm_id = vm.get("vm_id")
            vm_ip = vm.get("ip_address") or vm.get("lab_ip")
            credentials = vm.get("credentials", {"username": "ubuntu", "password": "ubuntu"})
            
            for exploit_id in exploits:
                result = asyncio.run(_inject_async(
                    vm_id=vm_id,
                    vm_ip=vm_ip,
                    exploit_id=exploit_id,
                    credentials=credentials
                ))
                results.append({
                    "vm_id": vm_id,
                    "exploit_id": exploit_id,
                    **result
                })
    finally:
        if vlan_id:
            detach_from_vlan(vlan_id)
    
    successes = sum(1 for r in results if r.get("success"))
    
    return {
        "mission_id": mission_id,
        "total": len(results),
        "successes": successes,
        "failures": len(results) - successes,
        "results": results
    }


# ============================================================================
# VLAN Attachment (Container Network Magic)
# ============================================================================

def attach_to_vlan(vlan_id: int) -> bool:
    """
    Attach this container to a VLAN.
    
    Creates a VLAN interface on the container's network interface
    to communicate with VMs on that isolated network.
    """
    import subprocess
    
    interface = "eth0"  # Default Docker interface
    vlan_interface = f"eth0.{vlan_id}"
    
    try:
        # Create VLAN interface
        subprocess.run(
            ["ip", "link", "add", "link", interface, "name", vlan_interface, "type", "vlan", "id", str(vlan_id)],
            check=True, capture_output=True
        )
        
        # Bring it up
        subprocess.run(
            ["ip", "link", "set", vlan_interface, "up"],
            check=True, capture_output=True
        )
        
        # Add IP on that VLAN (use .250 to avoid conflicts)
        ip_addr = f"192.168.{vlan_id}.250/24"
        subprocess.run(
            ["ip", "addr", "add", ip_addr, "dev", vlan_interface],
            check=True, capture_output=True
        )
        
        logger.info(f"Attached to VLAN {vlan_id} as {ip_addr}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to attach to VLAN {vlan_id}: {e}")
        return False


def detach_from_vlan(vlan_id: int) -> bool:
    """Remove VLAN interface from container"""
    import subprocess
    
    vlan_interface = f"eth0.{vlan_id}"
    
    try:
        subprocess.run(
            ["ip", "link", "delete", vlan_interface],
            check=True, capture_output=True
        )
        logger.info(f"Detached from VLAN {vlan_id}")
        return True
    except subprocess.CalledProcessError:
        return False


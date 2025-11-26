"""
Reaper API Endpoints

REST API for managing the exploit library and running injection missions.
This is the interface between the Reaper UI and the Reaper engine.

Overseer can only call: POST /missions/{id}/start
All other operations require direct Reaper UI access (architect role)
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging
import asyncio

from glassdome.core.database import get_db as get_async_session, AsyncSessionLocal as async_session_factory
from glassdome.reaper.exploit_library import (
    Exploit, ExploitMission, ExploitType, ExploitSeverity, ExploitOS,
    seed_default_exploits
)
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reaper", tags=["reaper"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ExploitCreate(BaseModel):
    """Create a new exploit definition"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    cve_id: Optional[str] = None
    exploit_type: str = ExploitType.CUSTOM.value
    severity: str = ExploitSeverity.MEDIUM.value
    cvss_score: Optional[str] = None
    target_os: str = ExploitOS.LINUX.value
    target_services: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    package_name: Optional[str] = None
    install_script: Optional[str] = None
    verify_script: Optional[str] = None
    cleanup_script: Optional[str] = None
    exploitation_steps: Optional[str] = None
    remediation_steps: Optional[str] = None
    references: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class ExploitUpdate(BaseModel):
    """Update an existing exploit"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    cve_id: Optional[str] = None
    exploit_type: Optional[str] = None
    severity: Optional[str] = None
    cvss_score: Optional[str] = None
    target_os: Optional[str] = None
    target_services: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    package_name: Optional[str] = None
    install_script: Optional[str] = None
    verify_script: Optional[str] = None
    cleanup_script: Optional[str] = None
    exploitation_steps: Optional[str] = None
    remediation_steps: Optional[str] = None
    references: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    verified: Optional[bool] = None
    enabled: Optional[bool] = None


class MissionCreate(BaseModel):
    """Create a new exploit mission"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    platform: str = "proxmox"  # proxmox, aws, esxi, azure
    target_vm_id: Optional[str] = None  # Use existing VM
    target_vm_config: Optional[Dict[str, Any]] = None  # Create new VM
    exploit_ids: List[int] = Field(..., min_items=1)


class MissionResponse(BaseModel):
    """Mission response with status"""
    id: int
    mission_id: str
    name: str
    description: Optional[str]
    platform: str
    status: str
    progress: int
    current_step: Optional[str]
    exploit_ids: List[int]
    results: Optional[Dict[str, Any]]
    created_at: str


# ============================================================================
# Exploit Library Endpoints
# ============================================================================

@router.get("/exploits")
async def list_exploits(
    exploit_type: Optional[str] = None,
    severity: Optional[str] = None,
    target_os: Optional[str] = None,
    enabled_only: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all exploits in the library
    
    Filters:
    - exploit_type: web, network, privesc, credential, misconfig, malware, ad, custom
    - severity: critical, high, medium, low, info
    - target_os: linux, windows, macos, any
    - enabled_only: Only show enabled exploits (default: true)
    """
    query = select(Exploit)
    
    if exploit_type:
        query = query.where(Exploit.exploit_type == exploit_type)
    if severity:
        query = query.where(Exploit.severity == severity)
    if target_os:
        query = query.where(Exploit.target_os == target_os)
    if enabled_only:
        query = query.where(Exploit.enabled == True)
    
    query = query.order_by(Exploit.severity.desc(), Exploit.name)
    
    result = await session.execute(query)
    exploits = result.scalars().all()
    
    return {
        "total": len(exploits),
        "exploits": [e.to_dict() for e in exploits]
    }


@router.get("/exploits/{exploit_id}")
async def get_exploit(
    exploit_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a single exploit by ID"""
    result = await session.execute(
        select(Exploit).where(Exploit.id == exploit_id)
    )
    exploit = result.scalar_one_or_none()
    
    if not exploit:
        raise HTTPException(status_code=404, detail="Exploit not found")
    
    # Include full scripts for detail view
    data = exploit.to_dict()
    data["install_script"] = exploit.install_script
    data["verify_script"] = exploit.verify_script
    data["cleanup_script"] = exploit.cleanup_script
    
    return data


@router.post("/exploits")
async def create_exploit(
    exploit: ExploitCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new exploit definition"""
    # Check for duplicate name
    result = await session.execute(
        select(Exploit).where(Exploit.name == exploit.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Exploit with this name already exists")
    
    new_exploit = Exploit(**exploit.model_dump())
    session.add(new_exploit)
    await session.commit()
    await session.refresh(new_exploit)
    
    logger.info(f"Created exploit: {exploit.name}")
    return new_exploit.to_dict()


@router.put("/exploits/{exploit_id}")
async def update_exploit(
    exploit_id: int,
    exploit: ExploitUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """Update an existing exploit"""
    result = await session.execute(
        select(Exploit).where(Exploit.id == exploit_id)
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Exploit not found")
    
    # Update only provided fields
    update_data = exploit.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing, key, value)
    
    await session.commit()
    await session.refresh(existing)
    
    logger.info(f"Updated exploit: {existing.name}")
    return existing.to_dict()


@router.delete("/exploits/{exploit_id}")
async def delete_exploit(
    exploit_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete an exploit from the library"""
    result = await session.execute(
        select(Exploit).where(Exploit.id == exploit_id)
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Exploit not found")
    
    name = existing.name
    await session.execute(
        delete(Exploit).where(Exploit.id == exploit_id)
    )
    await session.commit()
    
    logger.info(f"Deleted exploit: {name}")
    return {"message": f"Exploit '{name}' deleted"}


@router.post("/exploits/seed")
async def seed_exploits(
    session: AsyncSession = Depends(get_async_session)
):
    """Seed the database with default exploits"""
    await seed_default_exploits(session)
    return {"message": "Default exploits seeded"}


# ============================================================================
# Mission Endpoints
# ============================================================================

@router.get("/missions")
async def list_missions(
    status: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all missions
    
    Filters:
    - status: pending, deploying_vm, injecting, verifying, completed, failed
    """
    query = select(ExploitMission)
    
    if status:
        query = query.where(ExploitMission.status == status)
    
    query = query.order_by(ExploitMission.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    missions = result.scalars().all()
    
    return {
        "total": len(missions),
        "missions": [m.to_dict() for m in missions]
    }


@router.get("/missions/{mission_id}")
async def get_mission(
    mission_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get mission status by ID"""
    result = await session.execute(
        select(ExploitMission).where(ExploitMission.mission_id == mission_id)
    )
    mission = result.scalar_one_or_none()
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    # Include exploit details
    exploit_result = await session.execute(
        select(Exploit).where(Exploit.id.in_(mission.exploit_ids))
    )
    exploits = exploit_result.scalars().all()
    
    data = mission.to_dict()
    data["exploits"] = [e.to_dict() for e in exploits]
    
    return data


@router.post("/missions")
async def create_mission(
    mission: MissionCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new exploit mission
    
    Either provide:
    - target_vm_id: Use an existing VM
    - target_vm_config: Create a new VM (will deploy automatically)
    """
    # Validate exploits exist
    exploit_result = await session.execute(
        select(Exploit).where(Exploit.id.in_(mission.exploit_ids))
    )
    exploits = exploit_result.scalars().all()
    
    if len(exploits) != len(mission.exploit_ids):
        raise HTTPException(status_code=400, detail="One or more exploit IDs not found")
    
    # Generate mission ID
    mission_id = f"mission-{uuid.uuid4().hex[:8]}"
    
    new_mission = ExploitMission(
        mission_id=mission_id,
        name=mission.name,
        description=mission.description,
        platform=mission.platform,
        target_vm_id=mission.target_vm_id,
        target_vm_config=mission.target_vm_config,
        exploit_ids=mission.exploit_ids,
        status="pending",
        progress=0,
    )
    
    session.add(new_mission)
    await session.commit()
    await session.refresh(new_mission)
    
    logger.info(f"Created mission: {mission_id} with {len(mission.exploit_ids)} exploits")
    
    return new_mission.to_dict()


@router.post("/missions/{mission_id}/start")
async def start_mission(
    mission_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Start executing a mission
    
    This is the ONLY endpoint Overseer can call on Reaper.
    Kicks off the VM deployment → exploit injection → verification workflow.
    """
    result = await session.execute(
        select(ExploitMission).where(ExploitMission.mission_id == mission_id)
    )
    mission = result.scalar_one_or_none()
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    if mission.status not in ["pending", "failed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot start mission with status '{mission.status}'"
        )
    
    # Update status
    mission.status = "starting"
    mission.started_at = datetime.utcnow()
    await session.commit()
    
    # Run mission in background
    background_tasks.add_task(execute_mission, mission_id)
    
    logger.info(f"Starting mission: {mission_id}")
    
    return {
        "message": "Mission started",
        "mission_id": mission_id,
        "status": "starting"
    }


@router.post("/missions/{mission_id}/cancel")
async def cancel_mission(
    mission_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Cancel a running mission"""
    result = await session.execute(
        select(ExploitMission).where(ExploitMission.mission_id == mission_id)
    )
    mission = result.scalar_one_or_none()
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    mission.status = "cancelled"
    await session.commit()
    
    logger.info(f"Cancelled mission: {mission_id}")
    
    return {"message": "Mission cancelled", "mission_id": mission_id}


# ============================================================================
# Mission Execution (Background Task)
# ============================================================================

async def execute_mission(mission_id: str):
    """
    Background task to execute a mission
    
    Workflow:
    1. If no target VM, deploy one
    2. Connect to VM via SSH
    3. For each exploit: install → verify
    4. Report results
    """
    from glassdome.db.session import async_session_factory
    
    async with async_session_factory() as session:
        try:
            result = await session.execute(
                select(ExploitMission).where(ExploitMission.mission_id == mission_id)
            )
            mission = result.scalar_one_or_none()
            
            if not mission:
                logger.error(f"Mission {mission_id} not found")
                return
            
            # Get exploits
            exploit_result = await session.execute(
                select(Exploit).where(Exploit.id.in_(mission.exploit_ids))
            )
            exploits = exploit_result.scalars().all()
            
            mission.status = "deploying_vm"
            mission.current_step = "Preparing target VM..."
            mission.progress = 10
            await session.commit()
            
            # Step 1: Get or create target VM
            vm_ip = None
            if mission.target_vm_id:
                # Use existing VM - need to get its IP
                mission.current_step = f"Using existing VM: {mission.target_vm_id}"
                # TODO: Get IP from platform
                vm_ip = mission.vm_ip_address  # Assume already set
            elif mission.target_vm_config:
                # Deploy new VM
                mission.current_step = "Deploying new VM..."
                await session.commit()
                
                vm_result = await deploy_mission_vm(
                    mission.platform,
                    mission.target_vm_config
                )
                
                if vm_result.get("success"):
                    mission.vm_created_id = vm_result.get("vm_id")
                    vm_ip = vm_result.get("ip_address")
                    mission.vm_ip_address = vm_ip
                    mission.progress = 30
                else:
                    raise Exception(f"VM deployment failed: {vm_result.get('error')}")
            else:
                raise Exception("No target VM specified")
            
            if not vm_ip:
                raise Exception("Could not determine VM IP address")
            
            mission.status = "injecting"
            mission.progress = 40
            await session.commit()
            
            # Step 2: Inject exploits
            results = {}
            progress_per_exploit = 40 / len(exploits)  # 40-80% for injection
            
            for i, exploit in enumerate(exploits):
                mission.current_step = f"Injecting: {exploit.display_name}"
                await session.commit()
                
                inject_result = await inject_exploit(vm_ip, exploit)
                results[str(exploit.id)] = inject_result
                
                mission.progress = int(40 + ((i + 1) * progress_per_exploit))
                await session.commit()
            
            # Step 3: Verify exploits
            mission.status = "verifying"
            mission.progress = 85
            mission.current_step = "Verifying exploits..."
            await session.commit()
            
            for exploit in exploits:
                if exploit.verify_script:
                    verify_result = await verify_exploit(vm_ip, exploit)
                    results[str(exploit.id)]["verified"] = verify_result.get("success", False)
                    results[str(exploit.id)]["verify_output"] = verify_result.get("output", "")
            
            # Complete
            mission.status = "completed"
            mission.progress = 100
            mission.current_step = "Mission complete"
            mission.results = results
            mission.completed_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"Mission {mission_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Mission {mission_id} failed: {e}", exc_info=True)
            
            # Update mission status
            mission.status = "failed"
            mission.error_message = str(e)
            mission.current_step = f"Failed: {str(e)}"
            await session.commit()


async def deploy_mission_vm(platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deploy a VM for the mission
    
    Args:
        platform: Target platform (proxmox, aws, esxi, azure)
        config: VM configuration
        
    Returns:
        Dict with vm_id, ip_address, success/error
    """
    from glassdome.core.config import settings
    
    try:
        if platform == "proxmox":
            from glassdome.platforms.proxmox_client import ProxmoxClient
            
            # Get first available Proxmox instance
            instances = settings.list_proxmox_instances()
            if not instances:
                return {"success": False, "error": "No Proxmox instances configured"}
            
            instance_id = instances[0]
            pve_config = settings.get_proxmox_config(instance_id)
            
            client = ProxmoxClient(
                host=pve_config["host"],
                user=pve_config["user"],
                password=pve_config.get("password"),
                token_name=pve_config.get("token_name"),
                token_value=pve_config.get("token_value"),
                verify_ssl=pve_config.get("verify_ssl", False),
                node=pve_config.get("node", "pve")
            )
            
            # Create VM
            result = await client.create_vm(config)
            
            return {
                "success": True,
                "vm_id": result.get("vm_id"),
                "ip_address": result.get("ip_address"),
                "platform": "proxmox"
            }
            
        elif platform == "aws":
            from glassdome.platforms.aws_client import AWSClient
            
            client = AWSClient(
                access_key=settings.aws_access_key_id,
                secret_key=settings.aws_secret_access_key,
                region=config.get("region", settings.aws_region)
            )
            
            result = await client.create_vm(config)
            
            return {
                "success": True,
                "vm_id": result.get("vm_id"),
                "ip_address": result.get("ip_address"),
                "platform": "aws"
            }
        
        else:
            return {"success": False, "error": f"Platform '{platform}' not yet supported"}
            
    except Exception as e:
        logger.error(f"Failed to deploy VM: {e}")
        return {"success": False, "error": str(e)}


async def inject_exploit(vm_ip: str, exploit: Exploit) -> Dict[str, Any]:
    """
    Inject a single exploit into a VM
    
    Args:
        vm_ip: Target VM IP address
        exploit: Exploit to inject
        
    Returns:
        Dict with status, output
    """
    import asyncssh
    
    try:
        # Connect via SSH (assumes ubuntu user with key-based auth)
        async with asyncssh.connect(
            vm_ip,
            username="ubuntu",
            known_hosts=None,
            connect_timeout=30
        ) as conn:
            
            # If package-based install
            if exploit.package_name:
                result = await conn.run(
                    f"sudo apt-get update && sudo apt-get install -y {exploit.package_name}",
                    check=False
                )
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "output": result.stdout + result.stderr
                }
            
            # If script-based install
            elif exploit.install_script:
                # Upload and run script
                script_content = exploit.install_script
                result = await conn.run(
                    f"echo '{script_content}' | sudo bash",
                    check=False
                )
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "output": result.stdout + result.stderr
                }
            
            else:
                return {
                    "status": "error",
                    "output": "No installation method defined"
                }
                
    except Exception as e:
        logger.error(f"Failed to inject exploit {exploit.name}: {e}")
        return {
            "status": "error",
            "output": str(e)
        }


async def verify_exploit(vm_ip: str, exploit: Exploit) -> Dict[str, Any]:
    """
    Verify an exploit works on the target
    
    Args:
        vm_ip: Target VM IP address
        exploit: Exploit to verify
        
    Returns:
        Dict with success, output
    """
    import asyncssh
    
    if not exploit.verify_script:
        return {"success": True, "output": "No verification script"}
    
    try:
        async with asyncssh.connect(
            vm_ip,
            username="ubuntu",
            known_hosts=None,
            connect_timeout=30
        ) as conn:
            
            result = await conn.run(
                f"echo '{exploit.verify_script}' | sudo bash",
                check=False
            )
            
            success = "SUCCESS" in result.stdout or result.returncode == 0
            
            return {
                "success": success,
                "output": result.stdout + result.stderr
            }
            
    except Exception as e:
        logger.error(f"Failed to verify exploit {exploit.name}: {e}")
        return {
            "success": False,
            "output": str(e)
        }


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats")
async def get_reaper_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """Get Reaper statistics"""
    # Count exploits
    exploit_result = await session.execute(select(Exploit))
    exploits = exploit_result.scalars().all()
    
    # Count missions
    mission_result = await session.execute(select(ExploitMission))
    missions = mission_result.scalars().all()
    
    # Categorize
    by_type = {}
    by_severity = {}
    for e in exploits:
        by_type[e.exploit_type] = by_type.get(e.exploit_type, 0) + 1
        by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
    
    mission_by_status = {}
    for m in missions:
        mission_by_status[m.status] = mission_by_status.get(m.status, 0) + 1
    
    return {
        "exploits": {
            "total": len(exploits),
            "enabled": sum(1 for e in exploits if e.enabled),
            "verified": sum(1 for e in exploits if e.verified),
            "by_type": by_type,
            "by_severity": by_severity,
        },
        "missions": {
            "total": len(missions),
            "by_status": mission_by_status,
        }
    }


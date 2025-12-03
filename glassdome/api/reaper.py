"""
API endpoints for reaper

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import logging
import asyncio

from glassdome.core.database import get_db as get_async_session, AsyncSessionLocal as async_session_factory
from glassdome.auth.models import User
from glassdome.auth.dependencies import (
    get_current_user, get_current_user_optional,
    require_engineer, require_architect, require_level
)
from glassdome.reaper.exploit_library import (
    Exploit, ExploitMission, ExploitType, ExploitSeverity, ExploitOS,
    seed_default_exploits
)
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
import os
from pathlib import Path

# Reaper logger - uses centralized logging configuration
logger = logging.getLogger("glassdome.reaper")

router = APIRouter(prefix="/reaper", tags=["reaper"])


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
    # Ansible integration - engineers can reference playbooks directly
    ansible_playbook: Optional[str] = None  # e.g., "web/inject_sqli.yml"
    ansible_role: Optional[str] = None      # Ansible role name
    ansible_vars: Optional[Dict[str, Any]] = None  # Default playbook variables
    exploitation_steps: Optional[str] = None
    remediation_steps: Optional[str] = None
    references: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class ExploitBulkImport(BaseModel):
    """Bulk import exploits from JSON"""
    exploits: List[ExploitCreate]
    overwrite: bool = False  # If true, update existing exploits by name


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
    ansible_playbook: Optional[str] = None
    ansible_role: Optional[str] = None
    ansible_vars: Optional[Dict[str, Any]] = None
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user_optional)  # Public read
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can view
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can create
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can modify
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can delete
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can seed
):
    """Seed the database with default exploits"""
    await seed_default_exploits(session)
    return {"message": "Default exploits seeded"}


@router.post("/exploits/import")
async def import_exploits(
    data: ExploitBulkImport,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can import
):
    """
    Bulk import exploits from JSON
    
    Engineers/architects can prepare exploit definitions offline
    and import them in bulk. Supports both script-based and
    Ansible playbook-based exploits.
    
    Example JSON format available at GET /api/reaper/exploits/template
    """
    imported = 0
    updated = 0
    errors = []
    
    for exploit_data in data.exploits:
        try:
            # Check for existing
            result = await session.execute(
                select(Exploit).where(Exploit.name == exploit_data.name)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                if data.overwrite:
                    # Update existing
                    update_dict = exploit_data.model_dump(exclude_unset=True)
                    for key, value in update_dict.items():
                        setattr(existing, key, value)
                    updated += 1
                    logger.info(f"Updated exploit: {exploit_data.name}")
                else:
                    errors.append(f"Exploit '{exploit_data.name}' already exists (use overwrite=true)")
            else:
                # Create new
                new_exploit = Exploit(**exploit_data.model_dump())
                session.add(new_exploit)
                imported += 1
                logger.info(f"Imported exploit: {exploit_data.name}")
                
        except Exception as e:
            errors.append(f"Error importing '{exploit_data.name}': {str(e)}")
    
    await session.commit()
    
    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
        "total_processed": len(data.exploits)
    }


@router.get("/exploits/template")
async def get_exploit_template(
    current_user: User = Depends(require_engineer)  # Engineer+ can view templates
):
    """
    Get example JSON template for creating exploits
    
    Engineers/architects can use this template to build
    exploit definitions offline, then import via POST /api/reaper/exploits/import
    
    Two approaches supported:
    1. Script-based: Use install_script field with bash/powershell
    2. Ansible-based: Reference ansible_playbook path (recommended for complex scenarios)
    """
    return {
        "description": "Example exploit definitions for Reaper import",
        "usage": "POST this to /api/reaper/exploits/import",
        "exploits": [
            {
                "name": "custom-weak-ssh",
                "display_name": "Custom Weak SSH Credentials",
                "description": "Creates user 'trainee' with weak password for SSH brute-force training",
                "cve_id": None,
                "exploit_type": "credential",
                "severity": "high",
                "cvss_score": "7.5",
                "target_os": "linux",
                "target_services": ["ssh"],
                "prerequisites": ["ssh_server"],
                "install_script": """#!/bin/bash
# Create vulnerable user for training
useradd -m -s /bin/bash trainee
echo 'trainee:trainee123' | chpasswd
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh
echo 'Weak SSH user created: trainee:trainee123'
""",
                "verify_script": """#!/bin/bash
sshpass -p 'trainee123' ssh -o StrictHostKeyChecking=no trainee@localhost echo 'SUCCESS'
""",
                "exploitation_steps": "1. Use hydra: hydra -l trainee -P /usr/share/wordlists/rockyou.txt ssh://target\n2. Or try: ssh trainee@target with password trainee123",
                "remediation_steps": "1. Enforce strong passwords\n2. Disable password auth\n3. Use SSH keys only",
                "tags": ["credential", "ssh", "training"],
            },
            {
                "name": "ansible-sqli-dvwa",
                "display_name": "SQL Injection Lab (Ansible)",
                "description": "Deploys DVWA for SQL injection training using Ansible playbook",
                "exploit_type": "web",
                "severity": "high",
                "cvss_score": "8.0",
                "target_os": "linux",
                "target_services": ["apache2", "mysql"],
                "ansible_playbook": "web/inject_sqli.yml",
                "ansible_vars": {
                    "dvwa_security_level": "low",
                    "mysql_root_password": "training123"
                },
                "exploitation_steps": "1. Navigate to http://target/dvwa\n2. Login: admin/password\n3. Go to SQL Injection\n4. Enter: ' OR '1'='1' --",
                "remediation_steps": "Use parameterized queries and input validation",
                "tags": ["web", "sqli", "owasp-top-10", "ansible"],
            },
            {
                "name": "ansible-priv-escalation",
                "display_name": "Privilege Escalation Lab (Ansible)",
                "description": "Multiple Linux privesc vulnerabilities via Ansible role",
                "exploit_type": "privesc",
                "severity": "high",
                "target_os": "linux",
                "ansible_playbook": "system/weak_sudo.yml",
                "ansible_vars": {
                    "create_suid_binary": True,
                    "weak_sudo_command": "/usr/bin/vim"
                },
                "exploitation_steps": "1. Find SUID binaries: find / -perm -4000 2>/dev/null\n2. Check sudo: sudo -l\n3. Exploit vim: sudo vim -c ':!bash'",
                "tags": ["privesc", "sudo", "suid", "ansible"],
            }
        ],
        "notes": {
            "script_based": "Use install_script for simple bash/powershell commands",
            "ansible_based": "Use ansible_playbook to reference playbooks in glassdome/vulnerabilities/playbooks/",
            "ansible_vars": "Pass variables to the playbook via ansible_vars",
            "playbook_location": "Ansible playbooks should be placed in glassdome/vulnerabilities/playbooks/"
        }
    }


@router.get("/exploits/export")
async def export_exploits(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can export
):
    """
    Export all exploits as JSON for backup or sharing
    
    Engineers can download this, modify, and re-import to another instance.
    """
    result = await session.execute(select(Exploit))
    exploits = result.scalars().all()
    
    export_data = []
    for e in exploits:
        export_data.append({
            "name": e.name,
            "display_name": e.display_name,
            "description": e.description,
            "cve_id": e.cve_id,
            "exploit_type": e.exploit_type,
            "severity": e.severity,
            "cvss_score": e.cvss_score,
            "target_os": e.target_os,
            "target_services": e.target_services,
            "prerequisites": e.prerequisites,
            "package_name": e.package_name,
            "install_script": e.install_script,
            "verify_script": e.verify_script,
            "cleanup_script": e.cleanup_script,
            "ansible_playbook": e.ansible_playbook,
            "ansible_role": e.ansible_role,
            "ansible_vars": e.ansible_vars,
            "exploitation_steps": e.exploitation_steps,
            "remediation_steps": e.remediation_steps,
            "references": e.references,
            "tags": e.tags,
        })
    
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(export_data),
        "exploits": export_data
    }


# ============================================================================
# Mission Endpoints
# ============================================================================

@router.get("/missions")
async def list_missions(
    status: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user_optional)  # Public read
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can view
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can create missions
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can start
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
    mission.started_at = datetime.now(timezone.utc)
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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can cancel
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
    logger.info("=" * 60)
    logger.info(f"[MISSION START] {mission_id}")
    logger.info("=" * 60)
    
    async with async_session_factory() as session:
        try:
            result = await session.execute(
                select(ExploitMission).where(ExploitMission.mission_id == mission_id)
            )
            mission = result.scalar_one_or_none()
            
            if not mission:
                logger.error(f"[MISSION ERROR] {mission_id} - Mission not found in database")
                return
            
            logger.info(f"[MISSION] {mission_id} - Name: {mission.name}")
            logger.info(f"[MISSION] {mission_id} - Platform: {mission.platform}")
            logger.info(f"[MISSION] {mission_id} - Exploits: {mission.exploit_ids}")
            
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
            logger.info(f"[MISSION] {mission_id} - Step 1: Acquiring target VM")
            vm_ip = None
            acquired_spare = None
            
            if mission.target_vm_id:
                # Use existing VM - need to get its IP
                logger.info(f"[MISSION] {mission_id} - Using existing VM: {mission.target_vm_id}")
                mission.current_step = f"Using existing VM: {mission.target_vm_id}"
                # TODO: Get IP from platform
                vm_ip = mission.vm_ip_address  # Assume already set
                logger.info(f"[MISSION] {mission_id} - VM IP: {vm_ip}")
            elif mission.target_vm_config:
                # Try to get a hot spare first (instant!)
                vm_config = mission.target_vm_config
                os_type = vm_config.get("os_type", "ubuntu")
                use_hot_spare = vm_config.get("use_hot_spare", True)  # Default to using spares
                
                if use_hot_spare:
                    logger.info(f"[MISSION] {mission_id} - Checking for available hot spare ({os_type})")
                    mission.current_step = "Checking hot spare pool..."
                    await session.commit()
                    
                    pool = get_hot_spare_pool()
                    acquired_spare = await pool.acquire_spare(session, os_type=os_type, mission_id=mission_id)
                    
                    if acquired_spare:
                        # Got a spare! Use it immediately
                        mission.vm_created_id = str(acquired_spare.vmid)
                        vm_ip = acquired_spare.ip_address
                        mission.vm_ip_address = vm_ip
                        mission.progress = 30
                        logger.info(f"[MISSION] {mission_id} - ⚡ Hot spare acquired: {acquired_spare.name} (VMID {acquired_spare.vmid}, IP {vm_ip})")
                        
                        # Rename the spare VM to reflect the mission
                        # mission_id is like "mission-a5d86d20", extract just the hash part
                        mission_hash = mission_id.replace("mission-", "")[:8]
                        new_vm_name = f"reaper-{mission_hash}"
                        try:
                            from glassdome.platforms.proxmox_client import ProxmoxClient
                            from glassdome.core.config import Settings
                            settings = Settings()
                            pve_config = settings.get_proxmox_config(acquired_spare.platform_instance)
                            pve_client = ProxmoxClient(
                                host=pve_config["host"],
                                user=pve_config["user"],
                                password=pve_config.get("password"),
                                token_name=pve_config.get("token_name"),
                                token_value=pve_config.get("token_value"),
                                verify_ssl=pve_config.get("verify_ssl", False),
                                default_node=acquired_spare.node
                            )
                            await pve_client.configure_vm(
                                acquired_spare.node,
                                acquired_spare.vmid,
                                {"name": new_vm_name}
                            )
                            # Update spare record with new name
                            acquired_spare.name = new_vm_name
                            await session.commit()
                            logger.info(f"[MISSION] {mission_id} - Renamed VM to {new_vm_name}")
                        except Exception as e:
                            logger.warning(f"[MISSION] {mission_id} - Could not rename VM: {e}")
                    else:
                        logger.info(f"[MISSION] {mission_id} - No hot spares available, falling back to clone")
                
                if not vm_ip:
                    # No spare available or hot spare disabled - deploy new VM (slow path)
                    logger.info(f"[MISSION] {mission_id} - Deploying new VM on {mission.platform}")
                    logger.debug(f"[MISSION] {mission_id} - VM Config: {vm_config}")
                    mission.current_step = "Deploying new VM (this may take a few minutes)..."
                    await session.commit()
                    
                    vm_result = await deploy_mission_vm(
                        mission.platform,
                        vm_config
                    )
                    
                    if vm_result.get("success"):
                        mission.vm_created_id = vm_result.get("vm_id")
                        vm_ip = vm_result.get("ip_address")
                        mission.vm_ip_address = vm_ip
                        mission.progress = 30
                        logger.info(f"[MISSION] {mission_id} - VM deployed: ID={mission.vm_created_id}, IP={vm_ip}")
                    else:
                        error_msg = vm_result.get('error', 'Unknown error')
                        logger.error(f"[MISSION] {mission_id} - VM deployment failed: {error_msg}")
                        raise Exception(f"VM deployment failed: {error_msg}")
            else:
                logger.error(f"[MISSION] {mission_id} - No target VM specified")
                raise Exception("No target VM specified")
            
            if not vm_ip:
                raise Exception("Could not determine VM IP address")
            
            mission.status = "injecting"
            mission.progress = 40
            await session.commit()
            
            # Step 2: Inject exploits
            logger.info(f"[MISSION] {mission_id} - Step 2: Injecting {len(exploits)} exploits")
            results = {}
            progress_per_exploit = 40 / len(exploits)  # 40-80% for injection
            
            for i, exploit in enumerate(exploits):
                logger.info(f"[MISSION] {mission_id} - [{i+1}/{len(exploits)}] Injecting: {exploit.display_name}")
                logger.debug(f"[MISSION] {mission_id} - Exploit details: type={exploit.exploit_type}, severity={exploit.severity}")
                mission.current_step = f"Injecting: {exploit.display_name}"
                await session.commit()
                
                inject_result = await inject_exploit(vm_ip, exploit, mission_id)
                results[str(exploit.id)] = inject_result
                
                if inject_result.get("status") == "success":
                    logger.info(f"[MISSION] {mission_id} - ✓ {exploit.display_name} injected successfully")
                else:
                    logger.warning(f"[MISSION] {mission_id} - ✗ {exploit.display_name} injection failed: {inject_result.get('output', 'Unknown error')}")
                
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
            mission.completed_at = datetime.now(timezone.utc)
            await session.commit()
            
            # Log completion summary
            successful = sum(1 for r in results.values() if r.get("status") == "success")
            failed = len(results) - successful
            logger.info("=" * 60)
            logger.info(f"[MISSION COMPLETE] {mission_id}")
            logger.info(f"  Duration: {(mission.completed_at - mission.started_at).total_seconds():.1f}s")
            logger.info(f"  VM IP: {vm_ip}")
            logger.info(f"  Exploits: {successful} success, {failed} failed")
            logger.info(f"  Results: {results}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"[MISSION FAILED] {mission_id}")
            logger.error(f"  Error: {e}")
            logger.error("=" * 60, exc_info=True)
            
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
            
            # Use instance from config parameter, or fall back to configured lab instance
            instance_id = config.get("proxmox_instance")
            if not instance_id:
                try:
                    instance_id = settings.get_lab_proxmox_instance()
                except ValueError as e:
                    return {"success": False, "error": str(e)}
            
            logger.info(f"Using Proxmox instance: {instance_id}")
            pve_config = settings.get_proxmox_config(instance_id)
            
            # Node name matches instance (pve01 for 01, pve02 for 02)
            node_name = f"pve{instance_id}" if instance_id.isdigit() else pve_config.get("node", "pve")
            
            client = ProxmoxClient(
                host=pve_config["host"],
                user=pve_config["user"],
                password=pve_config.get("password"),
                token_name=pve_config.get("token_name"),
                token_value=pve_config.get("token_value"),
                verify_ssl=pve_config.get("verify_ssl", False),
                default_node=node_name
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
            from glassdome.core.secrets_backend import get_secret
            
            client = AWSClient(
                access_key=get_secret('aws_access_key_id'),
                secret_key=get_secret('aws_secret_access_key'),
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


async def inject_exploit(vm_ip: str, exploit: Exploit, mission_id: str = "") -> Dict[str, Any]:
    """
    Inject a single exploit into a VM
    
    Args:
        vm_ip: Target VM IP address
        exploit: Exploit to inject
        mission_id: Mission ID for logging
        
    Returns:
        Dict with status, output
    """
    import asyncssh
    
    log_prefix = f"[INJECT] {mission_id}" if mission_id else "[INJECT]"
    logger.debug(f"{log_prefix} Connecting to {vm_ip} for exploit: {exploit.name}")
    
    try:
        # Connect via SSH (assumes ubuntu user with key-based auth)
        logger.debug(f"{log_prefix} SSH connection attempt to {vm_ip}:22 as ubuntu")
        async with asyncssh.connect(
            vm_ip,
            username="ubuntu",
            known_hosts=None,
            connect_timeout=30
        ) as conn:
            logger.debug(f"{log_prefix} SSH connected successfully")
            
            # If package-based install
            if exploit.package_name:
                cmd = f"sudo apt-get update && sudo apt-get install -y {exploit.package_name}"
                logger.debug(f"{log_prefix} Running package install: {exploit.package_name}")
                result = await conn.run(cmd, check=False)
                logger.debug(f"{log_prefix} Package install exit code: {result.returncode}")
                logger.debug(f"{log_prefix} STDOUT: {result.stdout[:500] if result.stdout else 'empty'}")
                if result.stderr:
                    logger.debug(f"{log_prefix} STDERR: {result.stderr[:500]}")
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "output": result.stdout + result.stderr,
                    "exit_code": result.returncode
                }
            
            # If script-based install
            elif exploit.install_script:
                logger.debug(f"{log_prefix} Running custom install script ({len(exploit.install_script)} bytes)")
                # Upload and run script
                script_content = exploit.install_script
                result = await conn.run(
                    f"echo '{script_content}' | sudo bash",
                    check=False
                )
                logger.debug(f"{log_prefix} Script exit code: {result.returncode}")
                logger.debug(f"{log_prefix} STDOUT: {result.stdout[:500] if result.stdout else 'empty'}")
                if result.stderr:
                    logger.debug(f"{log_prefix} STDERR: {result.stderr[:500]}")
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "output": result.stdout + result.stderr,
                    "exit_code": result.returncode
                }
            
            else:
                logger.warning(f"{log_prefix} No installation method defined for {exploit.name}")
                return {
                    "status": "error",
                    "output": "No installation method defined"
                }
                
    except asyncssh.Error as e:
        logger.error(f"{log_prefix} SSH error for {exploit.name}: {e}")
        return {
            "status": "error",
            "output": f"SSH connection failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"{log_prefix} Failed to inject exploit {exploit.name}: {e}", exc_info=True)
        return {
            "status": "error",
            "output": str(e)
        }


async def verify_exploit(vm_ip: str, exploit: Exploit, use_whiteknight: bool = True) -> Dict[str, Any]:
    """
    Verify an exploit works on the target
    
    Args:
        vm_ip: Target VM IP address
        exploit: Exploit to verify
        use_whiteknight: Use WhiteKnight container for validation
        
    Returns:
        Dict with success, output
    """
    
    # Try WhiteKnight first if enabled
    if use_whiteknight:
        try:
            result = await verify_with_whiteknight(vm_ip, exploit)
            if result.get("status") != "error":
                return result
            # Fall through to legacy verification if WhiteKnight fails
            logger.warning(f"WhiteKnight verification failed, trying legacy method")
        except Exception as e:
            logger.warning(f"WhiteKnight not available: {e}")
    
    # Legacy SSH-based verification
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


async def verify_with_whiteknight(vm_ip: str, exploit: Exploit) -> Dict[str, Any]:
    """
    Verify exploit using WhiteKnight container
    
    WhiteKnight runs automated attack tools (nmap, sshpass, sqlmap, etc.)
    to validate that vulnerabilities are actually exploitable.
    """
    from glassdome.whiteknight import WhiteKnightClient, ValidationResult
    
    logger.info(f"🛡️ WhiteKnight validating: {exploit.name} on {vm_ip}")
    
    # Build exploit config for WhiteKnight
    exploit_config = {
        "exploit_type": exploit.exploit_type,
        "name": exploit.name,
        "tags": exploit.tags or [],
    }
    
    # Add specific config based on exploit type
    if exploit.exploit_type == "CREDENTIAL":
        # Extract credentials if in the exploit config
        exploit_config["username"] = "user"
        exploit_config["password"] = "password123"
    
    # If exploit has a custom verify command, use it
    if exploit.verify_script:
        exploit_config["verify_command"] = exploit.verify_script.replace("{target}", vm_ip)
    
    try:
        client = WhiteKnightClient(use_docker=True)
        result = await client.validate(vm_ip, exploit_config, timeout=120)
        
        logger.info(f"🛡️ WhiteKnight result: {result.status.value}")
        
        return {
            "success": result.status.value == "success",
            "output": result.evidence,
            "status": result.status.value,
            "whiteknight": True,
            "details": result.details
        }
    except Exception as e:
        logger.error(f"WhiteKnight validation error: {e}")
        return {
            "success": False,
            "output": str(e),
            "status": "error",
            "whiteknight": True
        }


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats")
async def get_reaper_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user_optional)  # Public read
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


# ============================================================================
# Live Log Streaming
# ============================================================================

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

@router.get("/logs")
async def get_recent_logs(
    lines: int = 100,
    current_user: User = Depends(require_engineer)  # Engineer+ can view logs
):
    """Get recent Reaper log entries"""
    try:
        if reaper_log_file.exists():
            with open(reaper_log_file, 'r') as f:
                all_lines = f.readlines()
                return {
                    "logs": all_lines[-lines:],
                    "total_lines": len(all_lines)
                }
        return {"logs": [], "total_lines": 0}
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {"logs": [], "error": str(e)}


@router.websocket("/logs/stream")
async def stream_logs(websocket: WebSocket):
    """WebSocket endpoint for live log streaming"""
    await websocket.accept()
    logger.info("Log stream client connected")
    
    try:
        last_position = 0
        if reaper_log_file.exists():
            last_position = reaper_log_file.stat().st_size
        
        while True:
            await asyncio.sleep(1)  # Check every second
            
            if reaper_log_file.exists():
                current_size = reaper_log_file.stat().st_size
                
                if current_size > last_position:
                    with open(reaper_log_file, 'r') as f:
                        f.seek(last_position)
                        new_lines = f.read()
                        if new_lines:
                            await websocket.send_text(new_lines)
                        last_position = f.tell()
                elif current_size < last_position:
                    # File was truncated/rotated
                    last_position = 0
                    
    except WebSocketDisconnect:
        logger.info("Log stream client disconnected")
    except Exception as e:
        logger.debug(f"Log stream error: {e}")
    finally:
        logger.info("Log stream closed")


# ============================================================================
# Hot Spare Pool Endpoints
# ============================================================================

from glassdome.reaper.hot_spare import (
    HotSpare, HotSparePool, HotSparePoolConfig, SpareStatus,
    get_hot_spare_pool, initialize_pool
)


class SpareResponse(BaseModel):
    """Response for a single spare"""
    id: int
    vmid: int
    name: str
    platform: str
    platform_instance: str
    node: str
    os_type: str
    ip_address: Optional[str]
    status: str
    assigned_to_mission: Optional[str]
    created_at: Optional[str]
    ready_at: Optional[str]


class PoolStatusResponse(BaseModel):
    """Response for pool status"""
    platform_instance: str
    os_type: str
    min_spares: int
    max_spares: int
    counts: Dict[str, int]
    ip_range: str
    spares: List[SpareResponse]


@router.get("/pool/status")
async def get_pool_status(
    os_type: str = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user_optional)  # Public read
):
    """
    Get hot spare pool status.
    
    Args:
        os_type: Specific OS type to get status for, or None for all pools
    """
    from glassdome.reaper.hot_spare import get_all_pools, POOL_CONFIGS
    
    if os_type:
        # Get status for specific OS type
        pool = get_hot_spare_pool(os_type)
        status = await pool.get_pool_status(session)
        
        # Get spares for this OS type
        result = await session.execute(
            select(HotSpare).where(
                HotSpare.os_type == os_type
            ).order_by(HotSpare.vmid)
        )
        spares = result.scalars().all()
        
        status["spares"] = [
            {
                "id": s.id,
                "vmid": s.vmid,
                "name": s.name,
                "platform": s.platform,
                "platform_instance": s.platform_instance,
                "node": s.node,
                "os_type": s.os_type,
                "ip_address": s.ip_address,
                "status": s.status,
                "assigned_to_mission": s.assigned_to_mission,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "ready_at": s.ready_at.isoformat() if s.ready_at else None,
            }
            for s in spares
        ]
        
        return status
    
    # Get status for all pools
    all_status = {"pools": {}, "configured_types": list(POOL_CONFIGS.keys())}
    
    for os_name in POOL_CONFIGS.keys():
        pool = get_hot_spare_pool(os_name)
        pool_status = await pool.get_pool_status(session)
        
        # Get spares for this OS type
        result = await session.execute(
            select(HotSpare).where(
                HotSpare.os_type == os_name
            ).order_by(HotSpare.vmid)
        )
        spares = result.scalars().all()
        
        pool_status["spares"] = [
            {
                "id": s.id,
                "vmid": s.vmid,
                "name": s.name,
                "os_type": s.os_type,
                "ip_address": s.ip_address,
                "status": s.status,
            }
            for s in spares
        ]
        
        all_status["pools"][os_name] = pool_status
    
    return all_status


@router.post("/pool/provision")
async def provision_spare(
    count: int = 1,
    os_type: str = "ubuntu",
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can provision
):
    """
    Manually provision new spares.
    
    This bypasses the automatic pool management and immediately
    starts provisioning the requested number of spares.
    
    Args:
        count: Number of spares to provision
        os_type: OS type to provision ("ubuntu", "windows10", etc.)
    """
    pool = get_hot_spare_pool(os_type)
    
    provisioned = []
    for _ in range(count):
        spare = await pool._provision_spare(session)
        if spare:
            provisioned.append({
                "id": spare.id,
                "vmid": spare.vmid,
                "name": spare.name,
                "os_type": os_type,
                "ip_address": spare.ip_address,
                "status": spare.status,
            })
    
    logger.info(f"Manually provisioned {len(provisioned)} {os_type} spares")
    
    return {
        "message": f"Provisioning {len(provisioned)} {os_type} spares",
        "spares": provisioned
    }


@router.post("/pool/start")
async def start_pool_manager(
    os_type: str = None,
    current_user: User = Depends(require_architect)  # Architect+ can start pool
):
    """
    Start the pool manager background task.
    
    Args:
        os_type: Specific OS type to start, or None to start all pools
    """
    from glassdome.reaper.hot_spare import initialize_all_pools, POOL_CONFIGS
    
    if os_type:
        pool = get_hot_spare_pool(os_type)
        await pool.start()
        return {"message": f"Pool manager started for {os_type}"}
    
    # Start all pools
    await initialize_all_pools()
    return {"message": f"Pool managers started for: {list(POOL_CONFIGS.keys())}"}


@router.post("/pool/stop")
async def stop_pool_manager(
    os_type: str = None,
    current_user: User = Depends(require_architect)  # Architect+ can stop pool
):
    """
    Stop the pool manager background task.
    
    Args:
        os_type: Specific OS type to stop, or None to stop all pools
    """
    from glassdome.reaper.hot_spare import get_all_pools
    
    if os_type:
        pool = get_hot_spare_pool(os_type)
        await pool.stop()
        return {"message": f"Pool manager stopped for {os_type}"}
    
    # Stop all pools
    pools = get_all_pools()
    stopped = []
    for name, pool in pools.items():
        await pool.stop()
        stopped.append(name)
    
    return {"message": f"Pool managers stopped for: {stopped}"}


@router.delete("/pool/spare/{spare_id}")
async def delete_spare(
    spare_id: int,
    os_type: str = "ubuntu",
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can delete
):
    """Delete a spare from the pool"""
    pool = get_hot_spare_pool(os_type)
    await pool.release_spare(session, spare_id, destroy=True)
    return {"message": f"Spare {spare_id} deleted"}


@router.post("/pool/spare/{spare_id}/acquire")
async def acquire_spare(
    spare_id: int,
    mission_id: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can acquire
):
    """Manually acquire a specific spare"""
    result = await session.execute(select(HotSpare).where(HotSpare.id == spare_id))
    spare = result.scalar_one_or_none()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare not found")
    
    if spare.status != SpareStatus.READY.value:
        raise HTTPException(status_code=400, detail=f"Spare is not ready (status: {spare.status})")
    
    spare.status = SpareStatus.IN_USE.value
    spare.assigned_to_mission = mission_id
    spare.assigned_at = datetime.now(timezone.utc)
    await session.commit()
    
    return {
        "message": f"Spare {spare.name} acquired",
        "spare": spare.to_dict()
    }


# ============================================================================
# Mission History & Logs
# ============================================================================

from glassdome.reaper.exploit_library import MissionLog, ValidationResult
from datetime import timedelta


@router.get("/missions/{mission_id}/logs")
async def get_mission_logs(
    mission_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can view logs
):
    """Get all logs for a specific mission"""
    result = await session.execute(
        select(MissionLog)
        .where(MissionLog.mission_id == mission_id)
        .order_by(MissionLog.timestamp.asc())
    )
    logs = result.scalars().all()
    
    return {
        "mission_id": mission_id,
        "logs": [log.to_dict() for log in logs],
        "total": len(logs)
    }


@router.get("/missions/{mission_id}/validations")
async def get_mission_validations(
    mission_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can view
):
    """Get all WhiteKnight validation results for a mission"""
    result = await session.execute(
        select(ValidationResult)
        .where(ValidationResult.mission_id == mission_id)
        .order_by(ValidationResult.validated_at.desc())
    )
    validations = result.scalars().all()
    
    return {
        "mission_id": mission_id,
        "validations": [v.to_dict() for v in validations],
        "total": len(validations),
        "summary": {
            "success": sum(1 for v in validations if v.status == "success"),
            "failed": sum(1 for v in validations if v.status == "failed"),
            "error": sum(1 for v in validations if v.status == "error")
        }
    }


@router.get("/history")
async def get_mission_history(
    days: int = 14,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_engineer)  # Engineer+ can view history
):
    """
    Get mission history with logs and validation summary
    Default: last 14 days, max 100 missions
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await session.execute(
        select(ExploitMission)
        .where(ExploitMission.created_at >= cutoff)
        .order_by(ExploitMission.created_at.desc())
        .limit(limit)
    )
    missions = result.scalars().all()
    
    history = []
    for mission in missions:
        # Get log count
        log_result = await session.execute(
            select(MissionLog).where(MissionLog.mission_id == mission.mission_id)
        )
        log_count = len(log_result.scalars().all())
        
        # Get validation summary
        val_result = await session.execute(
            select(ValidationResult).where(ValidationResult.mission_id == mission.mission_id)
        )
        validations = val_result.scalars().all()
        
        history.append({
            **mission.to_dict(),
            "log_count": log_count,
            "validation_count": len(validations),
            "validation_summary": {
                "success": sum(1 for v in validations if v.status == "success"),
                "failed": sum(1 for v in validations if v.status == "failed"),
            } if validations else None
        })
    
    return {
        "history": history,
        "total": len(history),
        "retention_days": days
    }


@router.delete("/missions/{mission_id}/destroy")
async def destroy_mission_vm(
    mission_id: str,
    delete_mission: bool = False,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can destroy
):
    """
    Destroy the VM associated with a mission and optionally delete the mission record.
    
    - Stops and destroys the VM in Proxmox
    - Optionally deletes the mission record from the database
    """
    # Find the mission
    result = await session.execute(
        select(ExploitMission).where(ExploitMission.mission_id == mission_id)
    )
    mission = result.scalar_one_or_none()
    
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    
    if not mission.vm_created_id:
        raise HTTPException(status_code=400, detail="Mission has no VM to destroy")
    
    vm_destroyed = False
    destroy_error = None
    
    # Try to destroy the VM
    try:
        from glassdome.platforms.proxmox_client import ProxmoxClient
        from glassdome.core.config import settings as app_settings
        
        # Get lab deployment configuration (no hardcoded defaults)
        try:
            lab_instance = app_settings.get_lab_proxmox_instance()
            node_name = app_settings.get_lab_node_name()
            pve_config = app_settings.get_lab_proxmox_config()
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Lab configuration error: {e}")
        
        client = ProxmoxClient(
            host=pve_config["host"],
            user=pve_config["user"],
            password=pve_config.get("password"),
            token_name=pve_config.get("token_name"),
            token_value=pve_config.get("token_value"),
            verify_ssl=False,
            default_node=node_name
        )
        
        vmid = mission.vm_created_id  # Keep as string
        
        # Stop the VM first
        logger.info(f"[DESTROY] Stopping VM {vmid} for mission {mission_id}")
        try:
            await client.stop_vm(vmid)
            # Wait a bit for it to stop
            import asyncio
            await asyncio.sleep(5)
        except Exception as stop_error:
            logger.warning(f"[DESTROY] Could not stop VM {vmid}: {stop_error}")
        
        # Destroy the VM
        logger.info(f"[DESTROY] Destroying VM {vmid} for mission {mission_id}")
        deleted = await client.delete_vm(vmid)
        if deleted:
            vm_destroyed = True
            logger.info(f"[DESTROY] VM {vmid} destroyed successfully")
        else:
            raise Exception("delete_vm returned False")
        
    except Exception as e:
        destroy_error = str(e)
        logger.error(f"[DESTROY] Failed to destroy VM for mission {mission_id}: {e}")
    
    # Update mission status
    mission.status = "destroyed" if vm_destroyed else "destroy_failed"
    mission.current_step = f"VM destroyed" if vm_destroyed else f"Destroy failed: {destroy_error}"
    
    # Optionally delete the mission record
    if delete_mission and vm_destroyed:
        await session.execute(
            delete(MissionLog).where(MissionLog.mission_id == mission_id)
        )
        await session.execute(
            delete(ValidationResult).where(ValidationResult.mission_id == mission_id)
        )
        await session.execute(
            delete(ExploitMission).where(ExploitMission.mission_id == mission_id)
        )
        await session.commit()
        return {
            "success": True,
            "message": f"VM {mission.vm_created_id} destroyed and mission deleted",
            "vm_destroyed": True,
            "mission_deleted": True
        }
    
    await session.commit()
    
    return {
        "success": vm_destroyed,
        "message": f"VM {mission.vm_created_id} destroyed" if vm_destroyed else f"Failed to destroy VM: {destroy_error}",
        "vm_destroyed": vm_destroyed,
        "mission_deleted": False,
        "error": destroy_error
    }


@router.delete("/history/cleanup")
async def cleanup_old_missions(
    days: int = 14,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_architect)  # Architect+ can cleanup
):
    """
    Delete missions older than specified days (default 14)
    This also deletes associated logs and validation results via CASCADE
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get count of missions to delete
    result = await session.execute(
        select(ExploitMission).where(ExploitMission.created_at < cutoff)
    )
    missions_to_delete = result.scalars().all()
    count = len(missions_to_delete)
    
    if count > 0:
        # Delete logs first (in case CASCADE doesn't work with async)
        for mission in missions_to_delete:
            await session.execute(
                delete(MissionLog).where(MissionLog.mission_id == mission.mission_id)
            )
            await session.execute(
                delete(ValidationResult).where(ValidationResult.mission_id == mission.mission_id)
            )
        
        # Delete missions
        await session.execute(
            delete(ExploitMission).where(ExploitMission.created_at < cutoff)
        )
        await session.commit()
        
        logger.info(f"Cleaned up {count} missions older than {days} days")
    
    return {
        "deleted": count,
        "cutoff_date": cutoff.isoformat(),
        "message": f"Deleted {count} missions older than {days} days"
    }


async def add_mission_log(
    session: AsyncSession,
    mission_id: str,
    message: str,
    level: str = "INFO",
    step: str = None,
    exploit_id: int = None,
    details: Dict = None
):
    """Helper function to add a log entry for a mission"""
    log = MissionLog(
        mission_id=mission_id,
        level=level,
        message=message,
        step=step,
        exploit_id=exploit_id,
        details=details
    )
    session.add(log)
    await session.commit()
    return log


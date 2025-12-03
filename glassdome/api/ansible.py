"""
API endpoints for ansible

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging

from glassdome.integrations.ansible_bridge import AnsibleBridge
from glassdome.integrations.ansible_executor import AnsibleExecutor

router = APIRouter(prefix="/ansible", tags=["ansible"])
logger = logging.getLogger(__name__)

# Initialize executor
ansible_executor = AnsibleExecutor()


class AnsiblePlaybookRequest(BaseModel):
    """Request to run an Ansible playbook"""
    playbook_name: str
    inventory_path: Optional[str] = None
    vms: Optional[List[Dict[str, Any]]] = None
    extra_vars: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    skip_tags: Optional[List[str]] = None
    limit: Optional[str] = None
    verbose: int = 0


class AnsibleInventoryRequest(BaseModel):
    """Request to generate Ansible inventory"""
    vms: List[Dict[str, Any]]
    format: str = "ini"
    groups: Optional[Dict[str, List[str]]] = None
    output_path: Optional[str] = None


class AnsibleCommandRequest(BaseModel):
    """Request to run an ad-hoc Ansible command"""
    command: str
    inventory_path: Optional[str] = None
    vms: Optional[List[Dict[str, Any]]] = None
    pattern: str = "all"
    extra_args: Optional[List[str]] = None


@router.post("/playbook/run")
async def run_playbook(request: AnsiblePlaybookRequest, background_tasks: BackgroundTasks):
    """
    Run an Ansible playbook
    
    Either provide an existing inventory_path OR a list of vms.
    If vms are provided, inventory will be generated automatically.
    
    Example:
        POST /api/ansible/playbook/run
        {
            "playbook_name": "web/inject_sqli.yml",
            "vms": [
                {
                    "vm_id": "100",
                    "ip_address": "192.168.3.100",
                    "ansible_connection": {
                        "host": "192.168.3.100",
                        "user": "ubuntu",
                        "ssh_key_path": "/root/.ssh/id_rsa",
                        "port": 22
                    }
                }
            ],
            "extra_vars": {"cve_id": "CVE-2023-12345"}
        }
    """
    try:
        # Generate inventory if VMs provided
        if request.vms and not request.inventory_path:
            request.inventory_path = AnsibleBridge.create_inventory(
                vms=request.vms,
                format="ini"
            )
            logger.info(f"Generated temporary inventory: {request.inventory_path}")
        
        if not request.inventory_path:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'inventory_path' or 'vms'"
            )
        
        # Run playbook
        result = await ansible_executor.run_playbook(
            playbook_name=request.playbook_name,
            inventory_path=request.inventory_path,
            extra_vars=request.extra_vars,
            tags=request.tags,
            skip_tags=request.skip_tags,
            limit=request.limit,
            verbose=request.verbose
        )
        
        return {
            "status": "success" if result["success"] else "failed",
            "playbook": request.playbook_name,
            "result": result
        }
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/playbook/run-multiple")
async def run_multiple_playbooks(
    playbooks: List[AnsiblePlaybookRequest],
    inventory_path: Optional[str] = None,
    vms: Optional[List[Dict[str, Any]]] = None,
    stop_on_failure: bool = True
):
    """
    Run multiple Ansible playbooks in sequence
    
    Shares the same inventory across all playbooks.
    
    Example:
        POST /api/ansible/playbook/run-multiple
        {
            "vms": [...],
            "playbooks": [
                {"playbook_name": "web/install_apache.yml"},
                {"playbook_name": "web/inject_sqli.yml", "extra_vars": {"cve": "CVE-2023-12345"}}
            ],
            "stop_on_failure": true
        }
    """
    try:
        # Generate inventory once for all playbooks
        if vms and not inventory_path:
            inventory_path = AnsibleBridge.create_inventory(vms=vms, format="ini")
            logger.info(f"Generated shared inventory: {inventory_path}")
        
        if not inventory_path:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'inventory_path' or 'vms'"
            )
        
        # Build playbook configs
        playbook_configs = []
        for pb_request in playbooks:
            playbook_configs.append({
                "name": pb_request.playbook_name,
                "vars": pb_request.extra_vars,
                "tags": pb_request.tags,
                "skip_tags": pb_request.skip_tags,
                "limit": pb_request.limit,
                "verbose": pb_request.verbose
            })
        
        # Run all playbooks
        results = await ansible_executor.run_playbooks(
            playbooks=playbook_configs,
            inventory_path=inventory_path,
            stop_on_failure=stop_on_failure
        )
        
        return {
            "status": "success",
            "playbooks_run": len(results),
            "playbooks_success": sum(1 for r in results if r["success"]),
            "playbooks_failed": sum(1 for r in results if not r["success"]),
            "results": results,
            "inventory_path": inventory_path
        }
        
    except Exception as e:
        logger.error(f"Failed to run playbooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inventory/generate")
async def generate_inventory(request: AnsibleInventoryRequest):
    """
    Generate Ansible inventory from VM deployment data
    
    Example:
        POST /api/ansible/inventory/generate
        {
            "vms": [
                {
                    "vm_id": "100",
                    "name": "web-server",
                    "ip_address": "192.168.3.100",
                    "group": "web_servers",
                    "ansible_connection": {
                        "host": "192.168.3.100",
                        "user": "ubuntu",
                        "ssh_key_path": "/root/.ssh/id_rsa",
                        "port": 22
                    }
                }
            ],
            "format": "ini",
            "output_path": "/tmp/my_inventory.ini"
        }
    """
    try:
        inventory_path = AnsibleBridge.create_inventory(
            vms=request.vms,
            format=request.format,
            groups=request.groups,
            output_path=request.output_path
        )
        
        # Read inventory content for preview
        with open(inventory_path, 'r') as f:
            inventory_content = f.read()
        
        return {
            "status": "success",
            "inventory_path": inventory_path,
            "format": request.format,
            "vm_count": len(request.vms),
            "preview": inventory_content[:500] + "..." if len(inventory_content) > 500 else inventory_content
        }
        
    except Exception as e:
        logger.error(f"Failed to generate inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command/run")
async def run_ad_hoc_command(request: AnsibleCommandRequest):
    """
    Run an ad-hoc Ansible command
    
    Example:
        POST /api/ansible/command/run
        {
            "command": "systemctl status apache2",
            "vms": [...],
            "pattern": "web_servers"
        }
    """
    try:
        # Generate inventory if VMs provided
        if request.vms and not request.inventory_path:
            request.inventory_path = AnsibleBridge.create_inventory(
                vms=request.vms,
                format="ini"
            )
        
        if not request.inventory_path:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'inventory_path' or 'vms'"
            )
        
        # Run command
        result = await ansible_executor.run_command(
            command=request.command,
            inventory_path=request.inventory_path,
            pattern=request.pattern,
            extra_args=request.extra_args
        )
        
        return {
            "status": "success" if result["success"] else "failed",
            "command": request.command,
            "pattern": request.pattern,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to run command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/playbooks/list")
async def list_playbooks(category: Optional[str] = None):
    """
    List available Ansible playbooks
    
    Example:
        GET /api/ansible/playbooks/list?category=web
    """
    try:
        playbooks = ansible_executor.list_playbooks(category=category)
        
        return {
            "status": "success",
            "playbooks": playbooks,
            "count": len(playbooks)
        }
        
    except Exception as e:
        logger.error(f"Failed to list playbooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


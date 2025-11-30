"""
API endpoints for elements library and statistics.

Extracted from main.py for cleaner organization.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(tags=["elements"])


@router.get("/api/elements")
async def list_elements() -> Dict[str, Any]:
    """List available lab elements (VMs, networks, services)."""
    return {
        "elements": {
            "vms": [
                {"id": "kali-2024", "name": "Kali Linux 2024", "type": "attack"},
                {"id": "dvwa", "name": "DVWA", "type": "vulnerable"},
                {"id": "metasploitable", "name": "Metasploitable 3", "type": "vulnerable"},
                {"id": "ubuntu-22", "name": "Ubuntu 22.04", "type": "base"},
            ],
            "networks": [
                {"id": "isolated", "name": "Isolated Network", "type": "internal"},
                {"id": "nat", "name": "NAT Network", "type": "nat"},
            ],
            "services": [
                {"id": "web-server", "name": "Apache Web Server", "type": "service"},
                {"id": "database", "name": "MySQL Database", "type": "service"},
            ]
        }
    }


@router.get("/api/stats")
async def get_statistics() -> Dict[str, Any]:
    """Get overall statistics."""
    return {
        "total_labs": 0,
        "active_deployments": 0,
        "total_deployments": 0,
        "total_templates": 0
    }

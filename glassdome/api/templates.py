"""
API endpoints for lab templates.

Extracted from main.py for cleaner organization.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uuid

from glassdome.core.database import get_db
from glassdome.models.lab import LabTemplate

router = APIRouter(prefix="/templates", tags=["templates"])


# Pydantic models for request/response
class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    template_data: Dict[str, Any]
    is_public: bool = False


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    template_data: Dict[str, Any]
    is_public: bool
    usage_count: int

    class Config:
        from_attributes = True


@router.get("")
async def list_templates(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all lab templates."""
    query = select(LabTemplate).order_by(LabTemplate.name)
    
    if category:
        query = query.where(LabTemplate.category == category)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    # If no templates in DB, return some defaults
    if not templates:
        return {
            "templates": [
                {
                    "id": "default-web-security",
                    "name": "Basic Web Security Lab",
                    "category": "Web Security",
                    "description": "DVWA + Kali Linux",
                    "is_builtin": True
                },
                {
                    "id": "default-network",
                    "name": "Network Pentesting Lab",
                    "category": "Network Security",
                    "description": "Multiple vulnerable VMs in isolated network",
                    "is_builtin": True
                }
            ],
            "note": "Showing built-in templates. Create custom templates via the API."
        }
    
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "is_public": t.is_public,
                "usage_count": t.usage_count or 0
            }
            for t in templates
        ]
    }


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get template details."""
    result = await db.execute(
        select(LabTemplate).where(LabTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        # Check for built-in templates
        if template_id == "default-web-security":
            return {
                "id": "default-web-security",
                "name": "Basic Web Security Lab",
                "category": "Web Security",
                "description": "DVWA + Kali Linux for web application security testing",
                "template_data": {
                    "elements": [
                        {"type": "vm", "name": "DVWA", "os": "linux", "template": "dvwa"},
                        {"type": "vm", "name": "Kali", "os": "linux", "template": "kali"}
                    ],
                    "networks": [
                        {"name": "lab-net", "subnet": "10.10.10.0/24"}
                    ]
                },
                "is_builtin": True
            }
        elif template_id == "default-network":
            return {
                "id": "default-network",
                "name": "Network Pentesting Lab",
                "category": "Network Security",
                "description": "Multiple vulnerable VMs in isolated network",
                "template_data": {
                    "elements": [
                        {"type": "vm", "name": "Target-1", "os": "linux"},
                        {"type": "vm", "name": "Target-2", "os": "windows"},
                        {"type": "vm", "name": "Attacker", "os": "linux", "template": "kali"}
                    ],
                    "networks": [
                        {"name": "attack-net", "subnet": "10.20.0.0/24"}
                    ]
                },
                "is_builtin": True
            }
        
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "template_data": template.template_data,
        "is_public": template.is_public,
        "usage_count": template.usage_count or 0,
        "created_at": template.created_at.isoformat() if template.created_at else None
    }


@router.post("")
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new template."""
    template_id = f"tmpl-{uuid.uuid4().hex[:8]}"
    
    template = LabTemplate(
        id=template_id,
        name=data.name,
        description=data.description,
        category=data.category,
        template_data=data.template_data,
        is_public=data.is_public,
        usage_count=0
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    return {
        "success": True,
        "template_id": template_id,
        "message": f"Template '{data.name}' created successfully"
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a template."""
    result = await db.execute(
        select(LabTemplate).where(LabTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.delete(template)
    await db.commit()
    
    return {
        "success": True,
        "message": f"Template '{template.name}' deleted"
    }


@router.post("/{template_id}/use")
async def use_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Record template usage and return template data for lab creation."""
    result = await db.execute(
        select(LabTemplate).where(LabTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Increment usage count
    template.usage_count = (template.usage_count or 0) + 1
    await db.commit()
    
    return {
        "success": True,
        "template_data": template.template_data,
        "message": f"Using template '{template.name}'"
    }

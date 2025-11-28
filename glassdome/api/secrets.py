"""
Secrets Management API

Provides admin-only endpoints for managing secrets.
Uses the SecretsManager backend (keyring, file, or Vault).

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from glassdome.core.secrets import get_secrets_manager
from glassdome.auth.models import User
from glassdome.auth.dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


class SecretCreate(BaseModel):
    key: str
    value: str


class SecretListResponse(BaseModel):
    secrets: List[str]


@router.get("", response_model=SecretListResponse)
async def list_secrets(
    current_user: User = Depends(require_admin)
):
    """
    List all stored secret keys (not values).
    Admin only.
    """
    try:
        secrets_manager = get_secrets_manager()
        keys = secrets_manager.list_secrets()
        return SecretListResponse(secrets=keys)
    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list secrets")


@router.post("")
async def set_secret(
    secret_data: SecretCreate,
    current_user: User = Depends(require_admin)
):
    """
    Set a secret value.
    Admin only.
    """
    try:
        secrets_manager = get_secrets_manager()
        
        if secrets_manager.set_secret(secret_data.key, secret_data.value):
            logger.info(f"Secret '{secret_data.key}' set by {current_user.username}")
            return {"success": True, "message": f"Secret '{secret_data.key}' saved"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save secret")
    except Exception as e:
        logger.error(f"Failed to set secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key}")
async def delete_secret(
    key: str,
    current_user: User = Depends(require_admin)
):
    """
    Delete a secret.
    Admin only.
    """
    try:
        secrets_manager = get_secrets_manager()
        
        if secrets_manager.delete_secret(key):
            logger.info(f"Secret '{key}' deleted by {current_user.username}")
            return {"success": True, "message": f"Secret '{key}' deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Secret '{key}' not found")
    except Exception as e:
        logger.error(f"Failed to delete secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


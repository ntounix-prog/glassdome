"""
Authentication and Session Management API
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from glassdome.core.session import get_session, GlassdomeSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    master_password: str


class SessionStatus(BaseModel):
    authenticated: bool
    authenticated_at: Optional[str] = None
    secrets_loaded: int = 0
    session_timeout_hours: float = 8.0


@router.post("/login")
async def login(request: LoginRequest):
    """
    Initialize Glassdome session with master password.
    
    This unlocks all secrets and allows agents to execute.
    """
    session = get_session()
    
    # Check if already authenticated
    if session.authenticated and session._is_session_valid():
        return {
            "success": True,
            "message": "Already authenticated",
            "session": {
                "authenticated": True,
                "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
                "secrets_loaded": len(session.secrets),
            }
        }
    
    # Initialize with provided password
    success = session.initialize(master_password=request.master_password, interactive=False)
    
    if success:
        return {
            "success": True,
            "message": "Session initialized successfully",
            "session": {
                "authenticated": True,
                "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
                "secrets_loaded": len(session.secrets),
            }
        }
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Check your master password."
        )


@router.get("/status")
async def get_session_status():
    """Get current session status"""
    session = get_session()
    
    return SessionStatus(
        authenticated=session.authenticated and session._is_session_valid(),
        authenticated_at=session.authenticated_at.isoformat() if session.authenticated_at else None,
        secrets_loaded=len(session.secrets),
        session_timeout_hours=session.session_timeout.total_seconds() / 3600,
    )


@router.post("/logout")
async def logout():
    """Logout and clear session"""
    session = get_session()
    session.logout()
    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_session(request: LoginRequest):
    """Refresh session (re-authenticate)"""
    session = get_session()
    session.logout()
    
    success = session.initialize(master_password=request.master_password, interactive=False)
    
    if success:
        return {
            "success": True,
            "message": "Session refreshed successfully",
            "session": {
                "authenticated": True,
                "authenticated_at": session.authenticated_at.isoformat() if session.authenticated_at else None,
                "secrets_loaded": len(session.secrets),
            }
        }
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Check your master password."
        )


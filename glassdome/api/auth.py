"""
Authentication & Authorization API

Provides both:
- Session-based auth (legacy, for secrets/agent access)
- Token-based user auth (RBAC for UI/API access)

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from glassdome.core.session import get_session, GlassdomeSession
from glassdome.core.database import get_db
from glassdome.auth.models import User, UserRole, ROLE_LEVELS, ROLE_PERMISSIONS
from glassdome.auth.schemas import (
    Token, UserCreate, UserUpdate, UserResponse, UserListResponse,
    LoginRequest as UserLoginRequest, RegisterRequest, UserPasswordChange,
    RoleInfo,
)
from glassdome.auth.service import (
    authenticate_user, create_access_token, create_user,
    get_user_by_id, list_users, update_user_password, verify_password,
    get_password_hash, create_initial_admin,
)
from glassdome.auth.dependencies import (
    get_current_user, get_current_user_optional,
    require_admin, require_level,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ============================================================================
# Pydantic Models for Legacy Session Auth
# ============================================================================

class MasterPasswordRequest(BaseModel):
    master_password: str


class SessionStatus(BaseModel):
    authenticated: bool
    authenticated_at: Optional[str] = None
    secrets_loaded: int = 0
    session_timeout_hours: float = 8.0


# ============================================================================
# Token-Based User Authentication (RBAC)
# ============================================================================

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login.
    
    Authenticate with username/email and password to get a JWT token.
    """
    user = await authenticate_user(session, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),  # JWT requires sub to be a string
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "level": user.level,
        }
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes in seconds
    )


@router.post("/login/user", response_model=Token)
async def login_user(
    login_data: UserLoginRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Login with username/email and password.
    
    Alternative to OAuth2 form for JSON API clients.
    """
    user = await authenticate_user(session, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token = create_access_token(
        data={
            "sub": str(user.id),  # JWT requires sub to be a string
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "level": user.level,
        }
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        level=current_user.level,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        permissions=current_user.permissions,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.put("/me/password")
async def change_my_password(
    password_data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    await update_user_password(session, current_user, password_data.new_password)
    
    return {"success": True, "message": "Password updated successfully"}


# ============================================================================
# User Management (Admin only)
# ============================================================================

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Register a new user.
    
    - If no users exist: Creates first user as admin
    - If not logged in: Creates observer account (if self-registration enabled)
    - If admin: Can specify any role
    """
    # Check if this is first user (bootstrap admin)
    from sqlalchemy import select, func
    count_result = await session.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar()
    
    if user_count == 0:
        # First user is admin
        admin_data = UserCreate(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
            role=UserRole.ADMIN,
        )
        user = await create_user(session, admin_data)
        user.is_superuser = True
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"Created initial admin user: {user.username}")
    else:
        # Normal registration - observer by default
        try:
            user = await create_user(
                session,
                UserCreate(
                    email=user_data.email,
                    username=user_data.username,
                    password=user_data.password,
                    full_name=user_data.full_name,
                    role=UserRole.OBSERVER,
                ),
                created_by=current_user,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        permissions=user.permissions,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.get("/users", response_model=UserListResponse)
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users (admin only)."""
    users, total = await list_users(session, skip=skip, limit=limit, active_only=False)
    
    return UserListResponse(
        users=[
            UserResponse(
                id=u.id,
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                role=u.role,
                level=u.level,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                permissions=u.permissions,
                created_at=u.created_at,
                last_login=u.last_login,
            )
            for u in users
        ],
        total=total,
    )


@router.post("/users", response_model=UserResponse)
async def create_new_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new user (admin only)."""
    try:
        user = await create_user(session, user_data, created_by=current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        permissions=user.permissions,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get user by ID (admin only)."""
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        permissions=user.permissions,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update user (admin only)."""
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update fields
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        user.role = user_update.role.value
        user.level = ROLE_LEVELS.get(user_update.role, 25)
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.extra_permissions is not None:
        user.extra_permissions = user_update.extra_permissions
    
    await session.commit()
    await session.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        permissions=user.permissions,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete/deactivate user (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Soft delete - deactivate instead of removing
    user.is_active = False
    await session.commit()
    
    return {"success": True, "message": f"User {user.username} deactivated"}


# ============================================================================
# Role & Permission Info
# ============================================================================

@router.get("/roles", response_model=List[RoleInfo])
async def list_roles():
    """List all available roles and their permissions."""
    return [
        RoleInfo(
            role=role.value,
            level=ROLE_LEVELS[role],
            permissions=ROLE_PERMISSIONS[role],
        )
        for role in UserRole
    ]


@router.get("/permissions")
async def check_my_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get current user's permissions."""
    return {
        "role": current_user.role,
        "level": current_user.level,
        "permissions": current_user.permissions,
        "is_superuser": current_user.is_superuser,
    }


# ============================================================================
# Legacy Session-Based Auth (for secrets/agents)
# ============================================================================

@router.post("/session/login")
async def session_login(request: MasterPasswordRequest):
    """
    Initialize Glassdome session with master password.
    
    This unlocks all secrets and allows agents to execute.
    (Legacy endpoint - kept for backwards compatibility)
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


@router.get("/session/status")
async def get_session_status():
    """Get current session status (legacy)."""
    session = get_session()
    
    return SessionStatus(
        authenticated=session.authenticated and session._is_session_valid(),
        authenticated_at=session.authenticated_at.isoformat() if session.authenticated_at else None,
        secrets_loaded=len(session.secrets),
        session_timeout_hours=session.session_timeout.total_seconds() / 3600,
    )


@router.post("/session/logout")
async def session_logout():
    """Logout and clear session (legacy)."""
    session = get_session()
    session.logout()
    return {"success": True, "message": "Session cleared"}


# ============================================================================
# Backward Compatibility Aliases
# ============================================================================

# Keep old /login endpoint working (redirects to session login)
@router.post("/login")
async def legacy_login(request: MasterPasswordRequest):
    """Legacy login endpoint - use /session/login or /token instead."""
    return await session_login(request)


@router.get("/status")
async def legacy_status():
    """Legacy status endpoint - use /session/status or /me instead."""
    return await get_session_status()


@router.post("/logout")
async def legacy_logout():
    """Legacy logout endpoint."""
    return await session_logout()

"""
FastAPI Dependencies for Authentication

Provides dependency injection for route protection.
"""

import logging
from typing import Optional, List, Callable
from functools import wraps

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.core.database import get_db
from glassdome.auth.models import User, UserRole, ROLE_LEVELS
from glassdome.auth.service import decode_access_token, get_user_by_id

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

# HTTP Bearer for API clients
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    session: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Accepts token from:
    - OAuth2 Bearer token (Authorization: Bearer <token>)
    - HTTP Bearer header
    
    Raises:
        HTTPException 401: If not authenticated or token invalid
    """
    # Get token from either source
    auth_token = token or (bearer.credentials if bearer else None)
    
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    token_data = decode_access_token(auth_token)
    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = await get_user_by_id(session, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    session: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Use for routes that work both authenticated and anonymous.
    """
    auth_token = token or (bearer.credentials if bearer else None)
    
    if not auth_token:
        return None
    
    try:
        token_data = decode_access_token(auth_token)
        if token_data is None or token_data.user_id is None:
            return None
        
        user = await get_user_by_id(session, token_data.user_id)
        if user and user.is_active:
            return user
    except Exception:
        pass
    
    return None


def require_permission(permission: str):
    """
    Dependency that requires a specific permission.
    
    Usage:
        @router.post("/exploits")
        async def create_exploit(
            user: User = Depends(require_permission("reaper:create_exploit"))
        ):
            ...
    """
    async def permission_checker(
        user: User = Depends(get_current_user)
    ) -> User:
        if not user.has_permission(permission):
            logger.warning(f"Permission denied: {user.username} lacks '{permission}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        return user
    
    return permission_checker


def require_level(min_level: int):
    """
    Dependency that requires a minimum user level.
    
    Levels:
        100 = Admin
        75 = Architect
        50 = Engineer
        25 = Observer
    
    Usage:
        @router.delete("/labs/{lab_id}")
        async def delete_lab(
            user: User = Depends(require_level(75))  # Architect+
        ):
            ...
    """
    async def level_checker(
        user: User = Depends(get_current_user)
    ) -> User:
        if not user.has_level(min_level):
            role_name = "Unknown"
            for role, level in ROLE_LEVELS.items():
                if level == min_level:
                    role_name = role.value
                    break
            
            logger.warning(f"Level denied: {user.username} (level {user.level}) < {min_level}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {role_name} or higher (level {min_level}+)",
            )
        return user
    
    return level_checker


def require_role(role: UserRole):
    """
    Dependency that requires a specific role or higher.
    
    Usage:
        @router.post("/users")
        async def create_user(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """
    min_level = ROLE_LEVELS.get(role, 100)
    return require_level(min_level)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency for admin-only routes."""
    if not user.is_superuser and user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_architect(user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency for architect+ routes."""
    if user.level < 75:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Architect or higher required",
        )
    return user


def require_engineer(user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency for engineer+ routes."""
    if user.level < 50:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Engineer or higher required",
        )
    return user


class PermissionChecker:
    """
    Class-based permission checker for more complex scenarios.
    
    Usage:
        checker = PermissionChecker(["lab:create", "lab:delete"], require_all=True)
        
        @router.post("/labs")
        async def create_lab(user: User = Depends(checker)):
            ...
    """
    
    def __init__(
        self,
        permissions: List[str],
        require_all: bool = False,
        min_level: Optional[int] = None
    ):
        self.permissions = permissions
        self.require_all = require_all
        self.min_level = min_level
    
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        # Check level first
        if self.min_level and not user.has_level(self.min_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires level {self.min_level}+",
            )
        
        # Check permissions
        if self.require_all:
            # Must have ALL permissions
            missing = [p for p in self.permissions if not user.has_permission(p)]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permissions: {', '.join(missing)}",
                )
        else:
            # Must have ANY permission
            if not any(user.has_permission(p) for p in self.permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {', '.join(self.permissions)}",
                )
        
        return user


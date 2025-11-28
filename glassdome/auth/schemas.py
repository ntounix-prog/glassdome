"""
Pydantic Schemas for Authentication

Request/response models for auth API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from glassdome.auth.models import UserRole


# ============================================================================
# Token Schemas
# ============================================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    level: Optional[int] = None


# ============================================================================
# User Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Create a new user."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: UserRole = UserRole.OBSERVER


class UserUpdate(BaseModel):
    """Update user details."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    extra_permissions: Optional[List[str]] = None


class UserPasswordChange(BaseModel):
    """Change password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User response (public info)."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    level: int
    is_active: bool
    is_superuser: bool
    permissions: List[str]
    created_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """List of users."""
    users: List[UserResponse]
    total: int


# ============================================================================
# Auth Request Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Login with username/email and password."""
    username: str  # Can be email or username
    password: str


class RegisterRequest(BaseModel):
    """Self-registration (if enabled)."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


# ============================================================================
# Permission Schemas
# ============================================================================

class PermissionCheck(BaseModel):
    """Check if user has permission."""
    permission: str
    has_permission: bool


class RoleInfo(BaseModel):
    """Role information."""
    role: str
    level: int
    permissions: List[str]


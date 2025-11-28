"""
User and Role Models

Database models for RBAC.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from typing import Optional, List

from glassdome.core.database import Base


class UserRole(str, Enum):
    """User roles with associated permission levels."""
    ADMIN = "admin"          # Level 100 - Full access
    ARCHITECT = "architect"  # Level 75 - Design & create
    ENGINEER = "engineer"    # Level 50 - Operate & deploy
    OBSERVER = "observer"    # Level 25 - Read-only


# Role to level mapping
ROLE_LEVELS = {
    UserRole.ADMIN: 100,
    UserRole.ARCHITECT: 75,
    UserRole.ENGINEER: 50,
    UserRole.OBSERVER: 25,
}

# Permissions by role
ROLE_PERMISSIONS = {
    UserRole.ADMIN: ["*"],  # Wildcard - all permissions
    UserRole.ARCHITECT: [
        "lab:create", "lab:delete", "lab:design", "lab:deploy", "lab:view",
        "vm:create", "vm:destroy", "vm:deploy", "vm:start", "vm:stop", "vm:restart", "vm:view",
        "reaper:create_exploit", "reaper:create_mission", "reaper:run_mission", "reaper:view",
        "network:create", "network:delete", "network:modify", "network:view",
        "whiteknight:create", "whiteknight:run", "whiteknight:view",
        "whitepawn:deploy", "whitepawn:view",
        "logs:view",
        "user:view",
    ],
    UserRole.ENGINEER: [
        "lab:deploy", "lab:view", "lab:operate",
        "vm:deploy", "vm:start", "vm:stop", "vm:restart", "vm:view",
        "reaper:run_mission", "reaper:view",
        "network:attach", "network:view",
        "whiteknight:run", "whiteknight:view",
        "whitepawn:view",
        "logs:view",
    ],
    UserRole.OBSERVER: [
        "lab:view",
        "vm:view",
        "reaper:view",
        "network:view",
        "whiteknight:view",
        "whitepawn:view",
        "logs:view",
    ],
}


class User(Base):
    """
    User model for authentication and authorization.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    
    # Role-based access
    role = Column(String(50), default=UserRole.OBSERVER.value, nullable=False)
    level = Column(Integer, default=25, nullable=False)  # Derived from role, but can be tweaked
    
    # Optional: extra permissions beyond role
    extra_permissions = Column(JSON, nullable=True)  # ["reaper:create_exploit"]
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, nullable=True)  # User who created this user
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    @property
    def role_enum(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)
    
    @property
    def permissions(self) -> List[str]:
        """Get all permissions for this user."""
        base_permissions = ROLE_PERMISSIONS.get(self.role_enum, [])
        extra = self.extra_permissions or []
        return list(set(base_permissions + extra))
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.is_superuser:
            return True
        perms = self.permissions
        if "*" in perms:
            return True
        return permission in perms
    
    def has_level(self, min_level: int) -> bool:
        """Check if user meets minimum level requirement."""
        return self.level >= min_level or self.is_superuser
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary."""
        data = {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "level": self.level,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
        if include_sensitive:
            data["extra_permissions"] = self.extra_permissions
        return data


"""
Glassdome Authentication & Authorization

Role-Based Access Control (RBAC) for the Glassdome platform.

Roles:
    - admin (100): Full system access, user management
    - architect (75): Design labs, create exploits, manage networks
    - engineer (50): Deploy labs, run missions, operate VMs
    - observer (25): Read-only access to dashboards and logs
"""

from glassdome.auth.models import User, UserRole
from glassdome.auth.dependencies import get_current_user, require_permission, require_level
from glassdome.auth.service import (
    create_user,
    authenticate_user,
    create_access_token,
    get_password_hash,
)

__all__ = [
    "User",
    "UserRole",
    "get_current_user",
    "require_permission",
    "require_level",
    "create_user",
    "authenticate_user",
    "create_access_token",
    "get_password_hash",
]


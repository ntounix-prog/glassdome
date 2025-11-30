"""
Authentication Flow Tests.

Tests the complete authentication workflow:
- User registration (first user becomes admin)
- Login and token generation
- JWT protection of routes
- Role/level-based access control
- Password changes

Author: Brett Turner (ntounix)
Created: November 2025
"""

import pytest
from httpx import AsyncClient


class TestUserRegistration:
    """Test user registration flows."""
    
    @pytest.mark.asyncio
    async def test_first_user_becomes_admin(self, async_client: AsyncClient):
        """First registered user should become admin."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "firstuser@glassdome.local",
                "username": "firstuser",
                "password": "SecurePass123!",
                "full_name": "First User",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["level"] == 100
        assert data["is_superuser"] is True
    
    @pytest.mark.asyncio
    async def test_subsequent_user_becomes_observer(
        self, async_client: AsyncClient, admin_user
    ):
        """Subsequent users should become observers by default."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "newuser@glassdome.local",
                "username": "newuser",
                "password": "SecurePass123!",
                "full_name": "New User",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "observer"
        assert data["level"] == 25
    
    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(
        self, async_client: AsyncClient, test_user
    ):
        """Duplicate email should be rejected."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@glassdome.local",  # Same as test_user
                "username": "different",
                "password": "SecurePass123!",
                "full_name": "Duplicate Email",
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_duplicate_username_rejected(
        self, async_client: AsyncClient, test_user
    ):
        """Duplicate username should be rejected."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "different@glassdome.local",
                "username": "testuser",  # Same as test_user
                "password": "SecurePass123!",
                "full_name": "Duplicate Username",
            }
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()


class TestUserLogin:
    """Test user login flows."""
    
    @pytest.mark.asyncio
    async def test_login_with_username(self, async_client: AsyncClient, test_user):
        """User can login with username."""
        response = await async_client.post(
            "/api/auth/login/user",
            json={
                "username": "testuser",
                "password": "testpass123",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_login_with_email(self, async_client: AsyncClient, test_user):
        """User can login with email."""
        response = await async_client.post(
            "/api/auth/login/user",
            json={
                "username": "test@glassdome.local",  # Email in username field
                "password": "testpass123",
            }
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        """Login with wrong password should fail."""
        response = await async_client.post(
            "/api/auth/login/user",
            json={
                "username": "testuser",
                "password": "wrongpassword",
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Login with nonexistent user should fail."""
        response = await async_client.post(
            "/api/auth/login/user",
            json={
                "username": "nonexistent",
                "password": "anypassword",
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_oauth2_token_endpoint(self, async_client: AsyncClient, test_user):
        """OAuth2 /token endpoint works with form data."""
        response = await async_client.post(
            "/api/auth/token",
            data={
                "username": "testuser",
                "password": "testpass123",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestJWTProtection:
    """Test JWT token protection of routes."""
    
    @pytest.mark.asyncio
    async def test_protected_route_no_token(self, async_client: AsyncClient):
        """Protected route should reject requests without token."""
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_protected_route_invalid_token(self, async_client: AsyncClient):
        """Protected route should reject invalid tokens."""
        headers = {"Authorization": "Bearer invalid-token-here"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_protected_route_valid_token(
        self, async_client: AsyncClient, test_user
    ):
        """Protected route should accept valid token."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_malformed_auth_header(self, async_client: AsyncClient):
        """Malformed Authorization header should be rejected."""
        # Missing "Bearer" prefix
        headers = {"Authorization": "some-token"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401


class TestRoleBasedAccess:
    """Test role/level-based access control."""
    
    @pytest.mark.asyncio
    async def test_admin_route_requires_admin(
        self, async_client: AsyncClient, test_user
    ):
        """Admin routes should reject non-admin users."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = await async_client.get("/api/auth/users", headers=headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_admin_route_allows_admin(
        self, async_client: AsyncClient, admin_user
    ):
        """Admin routes should allow admin users."""
        headers = {"Authorization": f"Bearer {admin_user['token']}"}
        response = await async_client.get("/api/auth/users", headers=headers)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_secrets_requires_admin(
        self, async_client: AsyncClient, test_user, admin_user
    ):
        """Secrets endpoint requires admin."""
        # Non-admin should be rejected
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = await async_client.get("/api/secrets", headers=headers)
        assert response.status_code == 403
        
        # Admin should be allowed
        headers = {"Authorization": f"Bearer {admin_user['token']}"}
        response = await async_client.get("/api/secrets", headers=headers)
        assert response.status_code == 200


class TestUserManagement:
    """Test user management by admin."""
    
    @pytest.mark.asyncio
    async def test_admin_can_create_user(
        self, async_client: AsyncClient, admin_user
    ):
        """Admin can create new users with specific roles."""
        headers = {"Authorization": f"Bearer {admin_user['token']}"}
        response = await async_client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "email": "newengineer@glassdome.local",
                "username": "newengineer",
                "password": "SecurePass123!",
                "full_name": "New Engineer",
                "role": "engineer",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "engineer"
        assert data["level"] == 50
    
    @pytest.mark.asyncio
    async def test_admin_can_update_user(
        self, async_client: AsyncClient, admin_user, test_user
    ):
        """Admin can update user roles."""
        headers = {"Authorization": f"Bearer {admin_user['token']}"}
        user_id = test_user["user"].id
        
        response = await async_client.put(
            f"/api/auth/users/{user_id}",
            headers=headers,
            json={
                "full_name": "Updated Name",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert True
    
    @pytest.mark.asyncio
    async def test_admin_can_deactivate_user(
        self, async_client: AsyncClient, admin_user, test_user
    ):
        """Admin can deactivate users."""
        headers = {"Authorization": f"Bearer {admin_user['token']}"}
        user_id = test_user["user"].id
        
        response = await async_client.delete(
            f"/api/auth/users/{user_id}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(
        self, async_client: AsyncClient, admin_user
    ):
        """Admin cannot delete themselves."""
        headers = {"Authorization": f"Bearer {admin_user['token']}"}
        user_id = admin_user["user"].id
        
        response = await async_client.delete(
            f"/api/auth/users/{user_id}",
            headers=headers
        )
        assert response.status_code == 400
        assert "cannot delete yourself" in response.json()["detail"].lower()


class TestPasswordChange:
    """Test password change functionality."""
    
    @pytest.mark.asyncio
    async def test_change_password_success(
        self, async_client: AsyncClient, test_user
    ):
        """User can change their own password."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = await async_client.put(
            "/api/auth/me/password",
            headers=headers,
            json={
                "current_password": "testpass123",
                "new_password": "NewSecurePass456!",
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, test_user
    ):
        """Password change fails with wrong current password."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = await async_client.put(
            "/api/auth/me/password",
            headers=headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewSecurePass456!",
            }
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()


class TestPermissionsEndpoint:
    """Test permissions info endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_my_permissions(
        self, async_client: AsyncClient, test_user
    ):
        """User can check their permissions."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = await async_client.get(
            "/api/auth/permissions",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "role" in data
        assert "level" in data
        assert "permissions" in data

"""
Pytest fixtures for Glassdome test suite.

Provides mock database, Redis, Proxmox client, and authenticated test clients.

Author: Brett Turner (ntounix)
Created: November 2025
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Use DB 15 for testing
os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-signing-12345"


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Import models to register them
    from glassdome.core.database import Base
    from glassdome.auth.models import User
    from glassdome.models.lab import Lab
    from glassdome.networking.models import NetworkDefinition, DeployedVM
    from glassdome.reaper.exploit_library import Exploit, ExploitMission
    from glassdome.whitepawn.models import WhitePawnDeployment
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


# =============================================================================
# Redis Mock Fixture
# =============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.sadd = AsyncMock(return_value=1)
    redis_mock.srem = AsyncMock(return_value=1)
    redis_mock.smembers = AsyncMock(return_value=set())
    redis_mock.scard = AsyncMock(return_value=0)
    redis_mock.lpush = AsyncMock(return_value=1)
    redis_mock.ltrim = AsyncMock(return_value=True)
    redis_mock.lrange = AsyncMock(return_value=[])
    redis_mock.publish = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    
    # Make scan_iter return an async generator
    async def mock_scan_iter(*args, **kwargs):
        return
        yield  # Make it a generator
    
    redis_mock.scan_iter = mock_scan_iter
    
    return redis_mock


# =============================================================================
# Proxmox Mock Fixture
# =============================================================================

@pytest.fixture
def mock_proxmox_client():
    """Mock ProxmoxClient for testing without real API calls."""
    client = MagicMock()
    
    # Mock cluster methods
    client.client.cluster.nextid.get.return_value = 100
    
    # Mock node methods
    node_mock = MagicMock()
    node_mock.qemu.return_value.config.get.return_value = {
        "name": "test-vm",
        "cores": 2,
        "memory": 2048,
        "net0": "virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr0",
    }
    node_mock.qemu.return_value.clone.create.return_value = None
    node_mock.qemu.return_value.status.current.get.return_value = {"status": "running"}
    client.client.nodes.return_value = node_mock
    
    # Mock async methods
    client.start_vm = AsyncMock(return_value=True)
    client.stop_vm = AsyncMock(return_value=True)
    client.delete_vm = AsyncMock(return_value=True)
    client.configure_vm = AsyncMock(return_value=True)
    client.get_vm_status = AsyncMock(return_value="running")
    client.get_vm_ip = AsyncMock(return_value="192.168.1.100")
    client.create_vm = AsyncMock(return_value={
        "vm_id": "100",
        "ip_address": "192.168.1.100",
        "status": "running",
    })
    
    return client


# =============================================================================
# App and Test Client Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def app(db_session, mock_redis):
    """Create FastAPI app with mocked dependencies."""
    from glassdome.main import app as fastapi_app
    from glassdome.core.database import get_db
    from glassdome.registry.core import get_registry
    
    # Override database dependency
    async def override_get_db():
        yield db_session
    
    # Override registry
    def override_get_registry():
        registry = MagicMock()
        registry._redis = mock_redis
        registry.connect = AsyncMock()
        registry.disconnect = AsyncMock()
        registry.register = AsyncMock(return_value=True)
        registry.get = AsyncMock(return_value=None)
        registry.delete = AsyncMock(return_value=True)
        registry.list_by_lab = AsyncMock(return_value=[])
        registry.list_by_type = AsyncMock(return_value=[])
        registry.get_status = AsyncMock(return_value={
            "connected": True,
            "resource_counts": {},
            "total_resources": 0,
            "lab_count": 0,
            "active_drifts": 0,
            "agents": 0,
            "agent_names": [],
        })
        return registry
    
    fastapi_app.dependency_overrides[get_db] = override_get_db
    
    # Patch registry singleton
    with patch("glassdome.registry.core.get_registry", override_get_registry):
        with patch("glassdome.registry.core._registry", None):
            yield fastapi_app
    
    # Clear overrides after test
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    """Synchronous test client for simple endpoint tests."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async test client for testing async endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


# =============================================================================
# User and Auth Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_user(db_session) -> dict:
    """Create a test user and return user data with token."""
    from glassdome.auth.models import User, UserRole, ROLE_LEVELS
    from glassdome.auth.service import get_password_hash, create_access_token
    
    user = User(
        email="test@glassdome.local",
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role=UserRole.ENGINEER.value,
        level=ROLE_LEVELS[UserRole.ENGINEER],
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create access token
    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "level": user.level,
        }
    )
    
    return {
        "user": user,
        "token": token,
        "password": "testpass123",
    }


@pytest_asyncio.fixture
async def admin_user(db_session) -> dict:
    """Create an admin test user and return user data with token."""
    from glassdome.auth.models import User, UserRole, ROLE_LEVELS
    from glassdome.auth.service import get_password_hash, create_access_token
    
    user = User(
        email="admin@glassdome.local",
        username="adminuser",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        level=ROLE_LEVELS[UserRole.ADMIN],
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create access token
    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "level": user.level,
        }
    )
    
    return {
        "user": user,
        "token": token,
        "password": "adminpass123",
    }


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Return authorization headers for test user."""
    return {"Authorization": f"Bearer {test_user['token']}"}


@pytest.fixture
def admin_auth_headers(admin_user) -> dict:
    """Return authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_user['token']}"}


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def sample_lab(db_session) -> dict:
    """Create a sample lab for testing."""
    from glassdome.models.lab import Lab
    
    lab = Lab(
        id="test-lab-001",
        name="Test Lab",
        description="A test lab for unit tests",
        canvas_data={
            "nodes": [
                {"id": "node-1", "type": "vm", "elementId": "ubuntu"},
                {"id": "node-2", "type": "vm", "elementId": "kali"},
            ],
            "edges": [],
        },
    )
    db_session.add(lab)
    await db_session.commit()
    await db_session.refresh(lab)
    
    return {
        "id": lab.id,
        "name": lab.name,
        "description": lab.description,
        "canvas_data": lab.canvas_data,
    }


@pytest_asyncio.fixture
async def sample_network(db_session) -> dict:
    """Create a sample network definition for testing."""
    from glassdome.networking.models import NetworkDefinition
    
    network = NetworkDefinition(
        name="test-net",
        display_name="Test Network",
        cidr="10.100.0.0/24",
        vlan_id=100,
        gateway="10.100.0.1",
        network_type="isolated",
        lab_id="test-lab-001",
    )
    db_session.add(network)
    await db_session.commit()
    await db_session.refresh(network)
    
    return {
        "id": network.id,
        "name": network.name,
        "vlan_id": network.vlan_id,
        "cidr": network.cidr,
    }


# =============================================================================
# Environment Cleanup
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    yield
    
    # Reset registry singleton
    try:
        import glassdome.registry.core as registry_module
        registry_module._registry = None
    except:
        pass
    
    # Reset session singleton
    try:
        import glassdome.core.session as session_module
        session_module._session = None
    except:
        pass

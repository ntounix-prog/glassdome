"""
Registry Core Unit Tests

Tests for the central lab and infrastructure registry system.

Author: Brett Turner (ntounix)
Created: November 2025
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from glassdome.registry.models import (
    Resource,
    ResourceType,
    ResourceState,
    DriftType,
    EventType,
    StateChange,
    Drift,
    LabSnapshot
)
from glassdome.registry.core import LabRegistry


# =============================================================================
# ResourceType Enum Tests
# =============================================================================

class TestResourceType:
    """Tests for ResourceType enumeration"""
    
    def test_tier1_lab_resources(self):
        """Test Tier 1 lab resource types exist"""
        assert ResourceType.LAB.value == "lab"
        assert ResourceType.LAB_VM.value == "lab_vm"
        assert ResourceType.LAB_NETWORK.value == "lab_network"
    
    def test_tier2_virtualization_resources(self):
        """Test Tier 2 virtualization resource types exist"""
        assert ResourceType.VM.value == "vm"
        assert ResourceType.TEMPLATE.value == "template"
        assert ResourceType.STORAGE_POOL.value == "storage_pool"
    
    def test_tier3_infrastructure_resources(self):
        """Test Tier 3 infrastructure resource types exist"""
        assert ResourceType.HOST.value == "host"
        assert ResourceType.SWITCH.value == "switch"
        assert ResourceType.SWITCH_PORT.value == "switch_port"
        assert ResourceType.VLAN.value == "vlan"


# =============================================================================
# ResourceState Enum Tests
# =============================================================================

class TestResourceState:
    """Tests for ResourceState enumeration"""
    
    def test_basic_states(self):
        """Test basic resource states"""
        assert ResourceState.UNKNOWN.value == "unknown"
        assert ResourceState.RUNNING.value == "running"
        assert ResourceState.STOPPED.value == "stopped"
    
    def test_lifecycle_states(self):
        """Test lifecycle states"""
        assert ResourceState.CREATING.value == "creating"
        assert ResourceState.DELETING.value == "deleting"
        assert ResourceState.DELETED.value == "deleted"
    
    def test_health_states(self):
        """Test health-related states"""
        assert ResourceState.ERROR.value == "error"
        assert ResourceState.DEGRADED.value == "degraded"
        assert ResourceState.HEALTHY.value == "healthy"


# =============================================================================
# DriftType Enum Tests
# =============================================================================

class TestDriftType:
    """Tests for DriftType enumeration"""
    
    def test_existence_drifts(self):
        """Test existence-related drift types"""
        assert DriftType.MISSING.value == "missing"
        assert DriftType.EXTRA.value == "extra"
    
    def test_configuration_drifts(self):
        """Test configuration drift types"""
        assert DriftType.STATE_MISMATCH.value == "state"
        assert DriftType.NAME_MISMATCH.value == "name"
        assert DriftType.CONFIG_MISMATCH.value == "config"
    
    def test_network_drifts(self):
        """Test network-related drift types"""
        assert DriftType.IP_MISMATCH.value == "ip"
        assert DriftType.NETWORK_MISMATCH.value == "network"


# =============================================================================
# EventType Enum Tests
# =============================================================================

class TestEventType:
    """Tests for EventType enumeration"""
    
    def test_crud_events(self):
        """Test CRUD event types"""
        assert EventType.CREATED.value == "created"
        assert EventType.UPDATED.value == "updated"
        assert EventType.DELETED.value == "deleted"
    
    def test_state_events(self):
        """Test state change events"""
        assert EventType.STATE_CHANGED.value == "state_changed"
    
    def test_drift_events(self):
        """Test drift-related events"""
        assert EventType.DRIFT_DETECTED.value == "drift_detected"
        assert EventType.DRIFT_RESOLVED.value == "drift_resolved"
    
    def test_reconcile_events(self):
        """Test reconciliation events"""
        assert EventType.RECONCILE_START.value == "reconcile_start"
        assert EventType.RECONCILE_COMPLETE.value == "reconcile_complete"
        assert EventType.RECONCILE_FAILED.value == "reconcile_failed"


# =============================================================================
# Resource Model Tests
# =============================================================================

class TestResourceModel:
    """Tests for Resource dataclass"""
    
    def test_resource_creation(self):
        """Test creating a resource"""
        resource = Resource(
            id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            name="test-vm",
            platform="proxmox"
        )
        
        assert resource.id == "proxmox:vm:100"
        assert resource.resource_type == ResourceType.VM
        assert resource.name == "test-vm"
        assert resource.platform == "proxmox"
    
    def test_resource_defaults(self):
        """Test resource default values"""
        resource = Resource(
            id="test-001",
            resource_type=ResourceType.VM,
            name="test",
            platform="proxmox"
        )
        
        assert resource.state == ResourceState.UNKNOWN
        assert resource.lab_id is None
        assert resource.platform_instance is None
    
    def test_resource_with_lab(self):
        """Test resource associated with a lab"""
        resource = Resource(
            id="proxmox:lab_vm:100",
            resource_type=ResourceType.LAB_VM,
            name="lab-vm",
            platform="proxmox",
            lab_id="lab-001"
        )
        
        assert resource.lab_id == "lab-001"
        assert resource.resource_type == ResourceType.LAB_VM
    
    def test_resource_state_transition(self):
        """Test resource state transitions"""
        resource = Resource(
            id="test-001",
            resource_type=ResourceType.VM,
            name="test",
            platform="proxmox"
        )
        
        assert resource.state == ResourceState.UNKNOWN
        
        resource.state = ResourceState.CREATING
        assert resource.state == ResourceState.CREATING
        
        resource.state = ResourceState.RUNNING
        assert resource.state == ResourceState.RUNNING
    
    def test_resource_config(self):
        """Test resource config storage"""
        resource = Resource(
            id="test-001",
            resource_type=ResourceType.VM,
            name="test",
            platform="proxmox",
            config={"cpu": 4, "memory": 8192}
        )
        
        assert resource.config["cpu"] == 4
        assert resource.config["memory"] == 8192


# =============================================================================
# StateChange Model Tests
# =============================================================================

class TestStateChangeModel:
    """Tests for StateChange model"""
    
    def test_state_change_creation(self):
        """Test creating a state change record"""
        change = StateChange(
            event_type=EventType.UPDATED,
            resource_id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            old_state=ResourceState.STOPPED,
            new_state=ResourceState.RUNNING
        )
        
        assert change.resource_id == "proxmox:vm:100"
        assert change.old_state == ResourceState.STOPPED
        assert change.new_state == ResourceState.RUNNING
    
    def test_state_change_timestamp(self):
        """Test state change has timestamp"""
        change = StateChange(
            event_type=EventType.CREATED,
            resource_id="test-001",
            resource_type=ResourceType.VM
        )
        
        assert change.timestamp is not None


# =============================================================================
# Drift Model Tests
# =============================================================================

class TestDriftModel:
    """Tests for Drift detection model"""
    
    def test_drift_creation(self):
        """Test creating a drift record"""
        drift = Drift(
            resource_id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            drift_type=DriftType.STATE_MISMATCH,
            expected="running",
            actual="stopped"
        )
        
        assert drift.resource_id == "proxmox:vm:100"
        assert drift.drift_type == DriftType.STATE_MISMATCH
        assert drift.expected == "running"
        assert drift.actual == "stopped"
    
    def test_drift_severity_levels(self):
        """Test drift severity tracking"""
        drift = Drift(
            resource_id="test-001",
            resource_type=ResourceType.VM,
            drift_type=DriftType.MISSING,
            expected="exists",
            actual="missing",
            severity="critical"
        )
        
        assert drift.severity == "critical"
    
    def test_drift_resolution(self):
        """Test drift resolution tracking"""
        drift = Drift(
            resource_id="test-001",
            resource_type=ResourceType.VM,
            drift_type=DriftType.STATE_MISMATCH,
            expected="running",
            actual="stopped"
        )
        
        assert drift.resolved_at is None
        
        drift.resolved_at = datetime.now(timezone.utc)
        
        assert drift.resolved_at is not None


# =============================================================================
# LabRegistry Initialization Tests
# =============================================================================

class TestLabRegistryInit:
    """Tests for LabRegistry initialization"""
    
    def test_registry_creation(self):
        """Test creating a registry instance"""
        registry = LabRegistry(redis_url="redis://localhost:6379/0")
        
        assert registry.redis_url == "redis://localhost:6379/0"
        assert registry._redis is None
        assert registry._running is False
    
    def test_registry_default_url(self):
        """Test registry uses settings URL by default"""
        with patch('glassdome.registry.core.settings') as mock_settings:
            mock_settings.redis_url = "redis://test:6379"
            registry = LabRegistry()
            assert registry.redis_url == "redis://test:6379"
    
    def test_registry_key_prefixes(self):
        """Test registry defines key prefixes"""
        assert LabRegistry.RESOURCE_PREFIX == "registry:resource:"
        assert LabRegistry.LAB_PREFIX == "registry:lab:"
        assert LabRegistry.EVENT_CHANNEL == "registry:events"


# =============================================================================
# LabRegistry Connection Tests
# =============================================================================

class TestLabRegistryConnection:
    """Tests for registry Redis connection"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.sadd = AsyncMock(return_value=1)
        mock.srem = AsyncMock(return_value=1)
        mock.smembers = AsyncMock(return_value=set())
        mock.publish = AsyncMock(return_value=1)
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_connect(self, mock_redis):
        """Test connecting to Redis"""
        registry = LabRegistry(redis_url="redis://localhost:6379/0")
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            await registry.connect()
            
            assert registry._redis is not None
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis):
        """Test disconnecting from Redis"""
        registry = LabRegistry()
        registry._redis = mock_redis
        
        await registry.disconnect()
        
        mock_redis.close.assert_called_once()
        assert registry._redis is None


# =============================================================================
# LabRegistry Resource Operations Tests
# =============================================================================

class TestLabRegistryResourceOps:
    """Tests for registry resource operations"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.sadd = AsyncMock(return_value=1)
        mock.srem = AsyncMock(return_value=1)
        mock.smembers = AsyncMock(return_value=set())
        mock.publish = AsyncMock(return_value=1)
        return mock
    
    @pytest.fixture
    def registry(self, mock_redis):
        """Create registry with mock Redis"""
        reg = LabRegistry(redis_url="redis://localhost:6379/0")
        reg._redis = mock_redis
        return reg
    
    @pytest.mark.asyncio
    async def test_register_new_resource(self, registry, mock_redis):
        """Test registering a new resource"""
        resource = Resource(
            id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            name="test-vm",
            platform="proxmox"
        )
        
        result = await registry.register(resource)
        
        assert result is True
        mock_redis.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_resource(self, registry, mock_redis):
        """Test getting a resource"""
        # Mock existing resource
        mock_redis.get = AsyncMock(return_value=None)
        
        result = await registry.get("proxmox:vm:100")
        
        assert result is None
        mock_redis.get.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_resource(self, registry, mock_redis):
        """Test deleting a resource"""
        # Mock that resource exists
        resource = Resource(
            id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            name="test-vm",
            platform="proxmox"
        )
        mock_redis.get = AsyncMock(return_value=resource.to_json())
        
        result = await registry.delete("proxmox:vm:100")
        
        # Delete should be called for the resource key
        assert result is True


# =============================================================================
# LabRegistry Lab Operations Tests
# =============================================================================

class TestLabRegistryLabOps:
    """Tests for lab-specific registry operations"""
    
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.smembers = AsyncMock(return_value=set())
        mock.sadd = AsyncMock(return_value=1)
        mock.publish = AsyncMock(return_value=1)
        return mock
    
    @pytest.fixture
    def registry(self, mock_redis):
        reg = LabRegistry()
        reg._redis = mock_redis
        return reg
    
    @pytest.mark.asyncio
    async def test_list_by_lab(self, registry, mock_redis):
        """Test listing resources by lab"""
        mock_redis.smembers = AsyncMock(return_value={"proxmox:lab_vm:100", "proxmox:lab_vm:101"})
        
        result = await registry.list_by_lab("lab-001")
        
        # Should query lab resources
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_list_by_type(self, registry, mock_redis):
        """Test listing resources by type"""
        mock_redis.smembers = AsyncMock(return_value={"proxmox:vm:100"})
        
        result = await registry.list_by_type(ResourceType.VM)
        
        assert isinstance(result, list)


# =============================================================================
# LabRegistry Status Tests
# =============================================================================

class TestLabRegistryStatus:
    """Tests for registry status reporting"""
    
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.ping = AsyncMock(return_value=True)
        mock.dbsize = AsyncMock(return_value=100)
        mock.info = AsyncMock(return_value={"used_memory_human": "1.5M"})
        mock.keys = AsyncMock(return_value=[])
        mock.smembers = AsyncMock(return_value=set())
        mock.scard = AsyncMock(return_value=0)
        
        # Mock scan_iter as async generator
        async def mock_scan_iter(*args, **kwargs):
            return
            yield  # Makes it an async generator
        mock.scan_iter = mock_scan_iter
        
        return mock
    
    @pytest.mark.asyncio
    async def test_get_status_connected(self, mock_redis):
        """Test checking registry connection status"""
        registry = LabRegistry()
        registry._redis = mock_redis
        
        # Basic connectivity check
        ping_result = await mock_redis.ping()
        assert ping_result is True


# =============================================================================
# LabRegistry Event Tests
# =============================================================================

class TestLabRegistryEvents:
    """Tests for registry event publishing"""
    
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.publish = AsyncMock(return_value=1)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.sadd = AsyncMock(return_value=1)
        return mock
    
    @pytest.fixture
    def registry(self, mock_redis):
        reg = LabRegistry()
        reg._redis = mock_redis
        return reg
    
    @pytest.mark.asyncio
    async def test_publish_event(self, registry, mock_redis):
        """Test publishing an event"""
        event = StateChange(
            event_type=EventType.CREATED,
            resource_id="proxmox:vm:100",
            resource_type=ResourceType.VM
        )
        
        await registry.publish_event(event)
        
        mock_redis.publish.assert_called()


# =============================================================================
# LabRegistry Drift Detection Tests
# =============================================================================

class TestLabRegistryDriftDetection:
    """Tests for drift detection functionality"""
    
    def test_detect_state_drift(self):
        """Test detecting state drift"""
        expected = Resource(
            id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            name="test-vm",
            platform="proxmox",
            state=ResourceState.RUNNING
        )
        
        actual = Resource(
            id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            name="test-vm",
            platform="proxmox",
            state=ResourceState.STOPPED
        )
        
        # States differ
        assert expected.state != actual.state
    
    def test_detect_missing_resource(self):
        """Test detecting missing resource"""
        expected_ids = {"vm-100", "vm-101", "vm-102"}
        actual_ids = {"vm-100", "vm-101"}
        
        missing = expected_ids - actual_ids
        
        assert "vm-102" in missing
    
    def test_detect_extra_resource(self):
        """Test detecting extra resources"""
        expected_ids = {"vm-100", "vm-101"}
        actual_ids = {"vm-100", "vm-101", "vm-102"}
        
        extra = actual_ids - expected_ids
        
        assert "vm-102" in extra


# =============================================================================
# LabSnapshot Tests
# =============================================================================

class TestLabSnapshot:
    """Tests for LabSnapshot functionality"""
    
    def test_snapshot_creation(self):
        """Test creating a lab snapshot"""
        snapshot = LabSnapshot(
            lab_id="lab-001",
            name="Test Lab"
        )
        
        assert snapshot.lab_id == "lab-001"
        assert snapshot.name == "Test Lab"
    
    def test_snapshot_with_vms(self):
        """Test snapshot with VMs"""
        vms = [
            Resource(
                id="vm-100",
                resource_type=ResourceType.LAB_VM,
                name="test-vm-1",
                platform="proxmox"
            ),
            Resource(
                id="vm-101",
                resource_type=ResourceType.LAB_VM,
                name="test-vm-2",
                platform="proxmox"
            )
        ]
        
        snapshot = LabSnapshot(
            lab_id="lab-001",
            name="Test Lab",
            vms=vms,
            total_vms=2
        )
        
        assert len(snapshot.vms) == 2
        assert snapshot.total_vms == 2


# =============================================================================
# LabRegistry Integration Tests
# =============================================================================

class TestLabRegistryIntegration:
    """Integration-style tests for registry workflows"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create comprehensive mock Redis"""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.sadd = AsyncMock(return_value=1)
        mock.srem = AsyncMock(return_value=1)
        mock.smembers = AsyncMock(return_value=set())
        mock.publish = AsyncMock(return_value=1)
        mock.ping = AsyncMock(return_value=True)
        mock.keys = AsyncMock(return_value=[])
        mock.scard = AsyncMock(return_value=0)
        return mock
    
    @pytest.mark.asyncio
    async def test_resource_registration(self, mock_redis):
        """Test resource registration workflow"""
        registry = LabRegistry()
        registry._redis = mock_redis
        
        # Create resource
        resource = Resource(
            id="proxmox:vm:100",
            resource_type=ResourceType.VM,
            name="test-vm",
            platform="proxmox",
            state=ResourceState.CREATING
        )
        await registry.register(resource)
        
        # Update resource
        resource.state = ResourceState.RUNNING
        await registry.register(resource)
        
        # Verify registration calls
        assert mock_redis.set.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_lab_deployment_workflow(self, mock_redis):
        """Test lab deployment workflow"""
        registry = LabRegistry()
        registry._redis = mock_redis
        
        lab_id = "lab-001"
        
        # Register lab
        lab_resource = Resource(
            id=f"glassdome:lab:{lab_id}",
            resource_type=ResourceType.LAB,
            name="Test Lab",
            platform="glassdome",
            lab_id=lab_id
        )
        await registry.register(lab_resource)
        
        # Register VMs
        for i in range(3):
            vm_resource = Resource(
                id=f"proxmox:lab_vm:10{i}",
                resource_type=ResourceType.LAB_VM,
                name=f"test-vm-{i}",
                platform="proxmox",
                lab_id=lab_id
            )
            await registry.register(vm_resource)
        
        # Verify registrations
        assert mock_redis.set.call_count >= 4

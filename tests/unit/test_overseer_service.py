"""
Overseer Service Unit Tests

Tests for the Overseer health monitoring and state sync components.

Author: Brett Turner (ntounix)
Created: December 2025
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from glassdome.overseer.health_monitor import (
    HealthMonitor,
    ServiceHealth,
    ServiceStatus,
    get_health_monitor
)
from glassdome.overseer.state_sync import (
    StateSync,
    SyncResult,
    StateSyncScheduler,
    get_state_sync,
    get_sync_scheduler
)


# =============================================================================
# ServiceHealth Tests
# =============================================================================

class TestServiceHealth:
    """Tests for ServiceHealth class"""
    
    def test_service_health_creation(self):
        """Test creating a service health object"""
        health = ServiceHealth(
            name="backend",
            status=ServiceStatus.HEALTHY,
            response_time_ms=25.5
        )
        
        assert health.name == "backend"
        assert health.status == ServiceStatus.HEALTHY
        assert health.response_time_ms == 25.5
        assert health.consecutive_failures == 0
    
    def test_service_health_defaults(self):
        """Test default values"""
        health = ServiceHealth(name="test")
        
        assert health.status == ServiceStatus.UNKNOWN
        assert health.error is None
        assert health.details == {}
        assert health.consecutive_failures == 0
    
    def test_service_health_to_dict(self):
        """Test serialization"""
        health = ServiceHealth(
            name="frontend",
            status=ServiceStatus.HEALTHY,
            response_time_ms=50.0
        )
        
        result = health.to_dict()
        
        assert isinstance(result, dict)
        assert result["name"] == "frontend"
        assert result["status"] == "healthy"
        assert result["response_time_ms"] == 50.0
    
    def test_service_status_enum(self):
        """Test all status values"""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.UNKNOWN.value == "unknown"


# =============================================================================
# HealthMonitor Tests
# =============================================================================

class TestHealthMonitor:
    """Tests for HealthMonitor class"""
    
    def test_health_monitor_creation(self):
        """Test creating a health monitor"""
        monitor = HealthMonitor(
            frontend_url="http://localhost:5174",
            backend_url="http://localhost:8000",
            check_interval=30
        )
        
        assert monitor.frontend_url == "http://localhost:5174"
        assert monitor.backend_url == "http://localhost:8000"
        assert monitor.check_interval == 30
        assert monitor._running is False
    
    def test_health_monitor_services_initialized(self):
        """Test all services are initialized"""
        monitor = HealthMonitor()
        
        expected_services = [
            "frontend", "backend", "whitepawn",
            "proxmox_01", "proxmox_02", "database", "redis"
        ]
        
        for service in expected_services:
            assert service in monitor.services
            assert isinstance(monitor.services[service], ServiceHealth)
    
    def test_health_monitor_get_status(self):
        """Test getting overall status"""
        monitor = HealthMonitor()
        
        # Set some states
        monitor.services["frontend"].status = ServiceStatus.HEALTHY
        monitor.services["backend"].status = ServiceStatus.HEALTHY
        monitor.services["whitepawn"].status = ServiceStatus.DEGRADED
        
        status = monitor.get_status()
        
        assert "overall" in status
        assert "services" in status
        assert "unhealthy_count" in status
        assert "degraded_count" in status
        assert status["degraded_count"] >= 1
    
    def test_health_monitor_overall_healthy(self):
        """Test overall status is healthy when all healthy"""
        monitor = HealthMonitor()
        
        for service in monitor.services.values():
            service.status = ServiceStatus.HEALTHY
        
        status = monitor.get_status()
        assert status["overall"] == "healthy"
    
    def test_health_monitor_overall_degraded(self):
        """Test overall status is degraded when any degraded"""
        monitor = HealthMonitor()
        
        for service in monitor.services.values():
            service.status = ServiceStatus.HEALTHY
        monitor.services["whitepawn"].status = ServiceStatus.DEGRADED
        
        status = monitor.get_status()
        assert status["overall"] == "degraded"
    
    def test_health_monitor_overall_unhealthy(self):
        """Test overall status is unhealthy when any unhealthy"""
        monitor = HealthMonitor()
        
        for service in monitor.services.values():
            service.status = ServiceStatus.HEALTHY
        monitor.services["database"].status = ServiceStatus.UNHEALTHY
        
        status = monitor.get_status()
        assert status["overall"] == "unhealthy"
    
    def test_health_monitor_singleton(self):
        """Test singleton pattern"""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        
        # Same instance
        assert monitor1 is monitor2


# =============================================================================
# SyncResult Tests
# =============================================================================

class TestSyncResult:
    """Tests for SyncResult dataclass"""
    
    def test_sync_result_creation(self):
        """Test creating a sync result"""
        result = SyncResult(
            success=True,
            deployed_vms_cleaned=5,
            hot_spares_cleaned=2
        )
        
        assert result.success is True
        assert result.deployed_vms_cleaned == 5
        assert result.hot_spares_cleaned == 2
    
    def test_sync_result_defaults(self):
        """Test default values"""
        result = SyncResult(success=True)
        
        assert result.deployed_vms_cleaned == 0
        assert result.hot_spares_cleaned == 0
        assert result.networks_cleaned == 0
        assert result.vms_updated == 0
        assert result.errors == []
    
    def test_sync_result_to_dict(self):
        """Test serialization"""
        result = SyncResult(
            success=True,
            deployed_vms_cleaned=3,
            errors=["Error 1"]
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["success"] is True
        assert data["deployed_vms_cleaned"] == 3
        assert "Error 1" in data["errors"]


# =============================================================================
# StateSync Tests
# =============================================================================

class TestStateSync:
    """Tests for StateSync class"""
    
    def test_state_sync_creation(self):
        """Test creating a state sync"""
        sync = StateSync(backend_url="http://localhost:8000")
        
        assert sync.backend_url == "http://localhost:8000"
        assert sync._last_sync is None
    
    def test_state_sync_get_last_sync_none(self):
        """Test getting last sync when none"""
        sync = StateSync()
        
        assert sync.get_last_sync() is None
    
    def test_state_sync_history(self):
        """Test sync history storage"""
        sync = StateSync()
        
        # Manually add to history
        sync._sync_history.append(SyncResult(success=True))
        sync._sync_history.append(SyncResult(success=False))
        
        history = sync.get_sync_history(limit=10)
        
        assert len(history) == 2
    
    def test_state_sync_singleton(self):
        """Test singleton pattern"""
        sync1 = get_state_sync()
        sync2 = get_state_sync()
        
        assert sync1 is sync2


# =============================================================================
# StateSyncScheduler Tests
# =============================================================================

class TestStateSyncScheduler:
    """Tests for StateSyncScheduler class"""
    
    def test_scheduler_creation(self):
        """Test creating a scheduler"""
        sync = StateSync()
        scheduler = StateSyncScheduler(sync=sync, interval_seconds=300)
        
        assert scheduler.sync is sync
        assert scheduler.interval == 300
        assert scheduler._running is False
    
    def test_scheduler_default_interval(self):
        """Test default interval"""
        scheduler = get_sync_scheduler()
        
        assert scheduler.interval == 300  # 5 minutes
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler"""
        sync = StateSync()
        scheduler = StateSyncScheduler(sync=sync, interval_seconds=60)
        
        # Start
        await scheduler.start()
        assert scheduler._running is True
        
        # Stop
        await scheduler.stop()
        assert scheduler._running is False


# =============================================================================
# Integration Tests (Mock HTTP)
# =============================================================================

class TestHealthMonitorChecks:
    """Tests for health check methods with mocked HTTP"""
    
    @pytest.mark.asyncio
    async def test_check_frontend_healthy(self):
        """Test frontend check when healthy"""
        monitor = HealthMonitor(frontend_url="http://localhost:5174")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            await monitor._check_frontend()
            
            assert monitor.services["frontend"].status == ServiceStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_check_frontend_unhealthy(self):
        """Test frontend check when down"""
        monitor = HealthMonitor(frontend_url="http://localhost:5174")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            await monitor._check_frontend()
            
            assert monitor.services["frontend"].status == ServiceStatus.UNHEALTHY
            assert monitor.services["frontend"].consecutive_failures == 1


class TestStateSyncOperations:
    """Tests for state sync operations with mocked dependencies"""
    
    @pytest.mark.asyncio
    async def test_sync_all_success(self):
        """Test successful sync all"""
        sync = StateSync(backend_url="http://localhost:8000")
        
        with patch.object(sync, '_get_proxmox_vms', return_value=[]):
            with patch.object(sync, '_sync_deployed_vms', return_value=0):
                with patch.object(sync, '_sync_hot_spares', return_value=0):
                    with patch.object(sync, '_update_vm_ips', return_value=0):
                        result = await sync.sync_all()
        
        assert result.success is True
        assert sync._last_sync is not None
    
    @pytest.mark.asyncio
    async def test_sync_all_with_errors(self):
        """Test sync all with errors"""
        sync = StateSync(backend_url="http://localhost:8000")
        
        with patch.object(sync, '_get_proxmox_vms', side_effect=Exception("API error")):
            result = await sync.sync_all()
        
        assert result.success is False
        assert len(result.errors) > 0


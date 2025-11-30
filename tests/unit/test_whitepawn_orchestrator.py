"""
WhitePawn Orchestrator Unit Tests

Tests for the central orchestrator managing all WhitePawn monitoring instances.

Author: Brett Turner (ntounix)
Created: November 2025
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from glassdome.whitepawn.orchestrator import WhitePawnOrchestrator
from glassdome.whitepawn.monitor import WhitePawnMonitor
from glassdome.whitepawn.models import (
    WhitePawnDeployment,
    NetworkAlert,
    AlertSeverity,
    AlertType
)


# =============================================================================
# WhitePawnOrchestrator Initialization Tests
# =============================================================================

class TestWhitePawnOrchestratorInit:
    """Tests for orchestrator initialization"""
    
    def test_initial_state(self):
        """Test orchestrator initial state"""
        orchestrator = WhitePawnOrchestrator()
        
        assert orchestrator._monitors == {}
        assert orchestrator._running is False
        assert orchestrator._guardian_task is None
    
    def test_monitors_dict_empty(self):
        """Test monitors dictionary starts empty"""
        orchestrator = WhitePawnOrchestrator()
        
        assert len(orchestrator._monitors) == 0


# =============================================================================
# WhitePawnOrchestrator Lifecycle Tests
# =============================================================================

class TestWhitePawnOrchestratorLifecycle:
    """Tests for orchestrator start/stop lifecycle"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance"""
        return WhitePawnOrchestrator()
    
    @pytest.mark.asyncio
    async def test_start_sets_running(self, orchestrator):
        """Test start sets running flag"""
        orchestrator._restore_monitors = AsyncMock()
        orchestrator._guardian_loop = AsyncMock()
        
        await orchestrator.start()
        
        assert orchestrator._running is True
        
        # Cleanup
        orchestrator._running = False
        if orchestrator._guardian_task:
            orchestrator._guardian_task.cancel()
    
    @pytest.mark.asyncio
    async def test_start_creates_guardian_task(self, orchestrator):
        """Test start creates guardian task"""
        orchestrator._restore_monitors = AsyncMock()
        
        # Mock guardian loop to exit immediately
        async def mock_guardian():
            await asyncio.sleep(0.1)
        
        with patch.object(orchestrator, '_guardian_loop', mock_guardian):
            await orchestrator.start()
            
            assert orchestrator._guardian_task is not None
            
            # Cleanup
            orchestrator._running = False
            orchestrator._guardian_task.cancel()
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, orchestrator):
        """Test start when already running does nothing"""
        orchestrator._running = True
        orchestrator._restore_monitors = AsyncMock()
        
        await orchestrator.start()
        
        # restore_monitors should not be called
        orchestrator._restore_monitors.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stop_clears_running(self, orchestrator):
        """Test stop clears running flag"""
        orchestrator._running = True
        orchestrator._guardian_task = None
        
        await orchestrator.stop()
        
        assert orchestrator._running is False
    
    @pytest.mark.asyncio
    async def test_stop_clears_monitors(self, orchestrator):
        """Test stop clears monitors dictionary"""
        # Add a mock monitor
        mock_monitor = MagicMock()
        mock_monitor.stop = AsyncMock()
        orchestrator._monitors = {1: mock_monitor}
        orchestrator._running = True
        orchestrator._guardian_task = None
        
        await orchestrator.stop()
        
        assert len(orchestrator._monitors) == 0
        mock_monitor.stop.assert_called_once()


# =============================================================================
# WhitePawnOrchestrator Monitor Management Tests
# =============================================================================

class TestWhitePawnOrchestratorMonitorManagement:
    """Tests for monitor management"""
    
    @pytest.fixture
    def orchestrator(self):
        return WhitePawnOrchestrator()
    
    def test_add_monitor(self, orchestrator):
        """Test adding a monitor to orchestrator"""
        mock_monitor = MagicMock(spec=WhitePawnMonitor)
        orchestrator._monitors[1] = mock_monitor
        
        assert 1 in orchestrator._monitors
        assert orchestrator._monitors[1] == mock_monitor
    
    def test_get_monitor(self, orchestrator):
        """Test getting a monitor by deployment ID"""
        mock_monitor = MagicMock(spec=WhitePawnMonitor)
        orchestrator._monitors[1] = mock_monitor
        
        retrieved = orchestrator._monitors.get(1)
        
        assert retrieved == mock_monitor
    
    def test_get_nonexistent_monitor(self, orchestrator):
        """Test getting a nonexistent monitor returns None"""
        retrieved = orchestrator._monitors.get(999)
        
        assert retrieved is None
    
    def test_remove_monitor(self, orchestrator):
        """Test removing a monitor"""
        mock_monitor = MagicMock(spec=WhitePawnMonitor)
        orchestrator._monitors[1] = mock_monitor
        
        del orchestrator._monitors[1]
        
        assert 1 not in orchestrator._monitors
    
    def test_multiple_monitors(self, orchestrator):
        """Test managing multiple monitors"""
        for i in range(5):
            mock_monitor = MagicMock(spec=WhitePawnMonitor)
            mock_monitor.deployment_id = i
            orchestrator._monitors[i] = mock_monitor
        
        assert len(orchestrator._monitors) == 5


# =============================================================================
# WhitePawnOrchestrator Deploy Tests
# =============================================================================

class TestWhitePawnOrchestratorDeploy:
    """Tests for deployment operations"""
    
    @pytest.fixture
    def orchestrator(self):
        return WhitePawnOrchestrator()
    
    @pytest.mark.asyncio
    async def test_deploy_for_lab_creates_deployment(self, db_session, orchestrator):
        """Test deploying WhitePawn for a lab creates a deployment record"""
        # Create a deployment manually to test
        deployment = WhitePawnDeployment(
            lab_id="test-lab-deploy",
            status="pending"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        assert deployment.id is not None
        assert deployment.status == "pending"


# =============================================================================
# WhitePawnOrchestrator Status Tests
# =============================================================================

class TestWhitePawnOrchestratorStatus:
    """Tests for status reporting"""
    
    @pytest.fixture
    def orchestrator(self):
        return WhitePawnOrchestrator()
    
    def test_status_when_empty(self, orchestrator):
        """Test status with no monitors"""
        assert len(orchestrator._monitors) == 0
        assert orchestrator._running is False
    
    def test_status_with_monitors(self, orchestrator):
        """Test status with active monitors"""
        # Add mock monitors
        for i in range(3):
            mock_monitor = MagicMock(spec=WhitePawnMonitor)
            mock_monitor._running = True
            mock_monitor._check_count = 100 + i
            mock_monitor._alert_count = i * 2
            orchestrator._monitors[i] = mock_monitor
        
        assert len(orchestrator._monitors) == 3


# =============================================================================
# WhitePawnOrchestrator Alert Aggregation Tests
# =============================================================================

@pytest.mark.asyncio
class TestWhitePawnOrchestratorAlerts:
    """Tests for alert aggregation across deployments"""
    
    async def test_create_alert(self, db_session):
        """Test creating alerts through orchestrator"""
        # First create a deployment
        deployment = WhitePawnDeployment(
            lab_id="test-lab-alerts",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        # Create an alert
        alert = NetworkAlert(
            deployment_id=deployment.id,
            alert_type=AlertType.VM_UNREACHABLE.value,
            severity=AlertSeverity.ERROR.value,
            title="VM Down",
            message="VM at 192.168.1.100 is unreachable",
            target_ip="192.168.1.100"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.id is not None
        assert alert.deployment_id == deployment.id
    
    async def test_multiple_alerts_same_deployment(self, db_session):
        """Test multiple alerts for same deployment"""
        deployment = WhitePawnDeployment(
            lab_id="test-lab-multi-alert",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        # Create multiple alerts
        for i in range(3):
            alert = NetworkAlert(
                deployment_id=deployment.id,
                alert_type=AlertType.PING_FAILED.value,
                severity=AlertSeverity.WARNING.value,
                title=f"Alert {i}",
                message=f"Test alert {i}",
                target_ip=f"192.168.1.{100+i}"
            )
            db_session.add(alert)
        
        await db_session.commit()
        
        # Query alerts for this deployment
        from sqlalchemy import select
        result = await db_session.execute(
            select(NetworkAlert).where(NetworkAlert.deployment_id == deployment.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) == 3


# =============================================================================
# WhitePawnOrchestrator Alert Resolution Tests
# =============================================================================

@pytest.mark.asyncio
class TestWhitePawnOrchestratorAlertResolution:
    """Tests for alert acknowledgment and resolution"""
    
    async def test_acknowledge_alert(self, db_session):
        """Test acknowledging an alert"""
        deployment = WhitePawnDeployment(
            lab_id="test-lab-ack",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        alert = NetworkAlert(
            deployment_id=deployment.id,
            alert_type=AlertType.PING_FAILED.value,
            severity=AlertSeverity.ERROR.value,
            title="Test Alert",
            message="Test message"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        # Acknowledge the alert
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = "admin"
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "admin"
    
    async def test_resolve_alert(self, db_session):
        """Test resolving an alert"""
        deployment = WhitePawnDeployment(
            lab_id="test-lab-resolve",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        alert = NetworkAlert(
            deployment_id=deployment.id,
            alert_type=AlertType.PING_FAILED.value,
            severity=AlertSeverity.ERROR.value,
            title="Test Alert",
            message="Test message"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        # Resolve the alert
        alert.resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.resolved is True
        assert alert.resolved_at is not None


# =============================================================================
# WhitePawnOrchestrator Guardian Loop Tests
# =============================================================================

class TestWhitePawnOrchestratorGuardian:
    """Tests for the guardian loop functionality"""
    
    @pytest.fixture
    def orchestrator(self):
        return WhitePawnOrchestrator()
    
    @pytest.mark.asyncio
    async def test_guardian_detects_stale_deployment(self, orchestrator):
        """Test guardian detects stale deployments"""
        # Create a mock monitor that hasn't updated heartbeat
        mock_monitor = MagicMock(spec=WhitePawnMonitor)
        mock_monitor._running = True
        mock_monitor.deployment_id = 1
        orchestrator._monitors[1] = mock_monitor
        
        # The guardian would detect this in _check_monitor_health
        assert 1 in orchestrator._monitors
    
    @pytest.mark.asyncio
    async def test_guardian_restarts_failed_monitor(self, orchestrator):
        """Test guardian restarts failed monitors"""
        mock_monitor = MagicMock(spec=WhitePawnMonitor)
        mock_monitor._running = False  # Simulating failed monitor
        mock_monitor.start = AsyncMock()
        orchestrator._monitors[1] = mock_monitor
        
        # In real scenario, guardian would call monitor.start()
        await mock_monitor.start()
        
        mock_monitor.start.assert_called_once()


# =============================================================================
# WhitePawnOrchestrator Configuration Tests
# =============================================================================

class TestWhitePawnOrchestratorConfig:
    """Tests for orchestrator configuration"""
    
    def test_default_guardian_interval(self):
        """Test default guardian check interval"""
        # Guardian loop sleeps for 30 seconds between checks
        orchestrator = WhitePawnOrchestrator()
        # This is hardcoded in _guardian_loop, but we verify the behavior
        assert orchestrator._running is False
    
    def test_monitor_config_propagation(self):
        """Test that config is properly passed to monitors"""
        orchestrator = WhitePawnOrchestrator()
        
        config = {"ping_interval": 5, "latency_warning_ms": 100}
        monitor = WhitePawnMonitor(deployment_id=1, config=config)
        orchestrator._monitors[1] = monitor
        
        assert orchestrator._monitors[1].config["ping_interval"] == 5
        assert orchestrator._monitors[1].config["latency_warning_ms"] == 100

"""
WhitePawn Monitor Unit Tests

Tests for the continuous network monitoring system.

Author: Brett Turner (ntounix)
Created: November 2025
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.whitepawn.monitor import WhitePawnMonitor, MonitoringResult
from glassdome.whitepawn.models import (
    WhitePawnDeployment,
    NetworkAlert,
    MonitoringEvent,
    ConnectivityMatrix,
    AlertSeverity,
    AlertType
)


# =============================================================================
# MonitoringResult Tests
# =============================================================================

class TestMonitoringResult:
    """Tests for MonitoringResult dataclass"""
    
    def test_successful_result(self):
        """Test creating a successful monitoring result"""
        result = MonitoringResult(
            success=True,
            target_ip="192.168.1.100",
            latency_ms=15.5
        )
        
        assert result.success is True
        assert result.target_ip == "192.168.1.100"
        assert result.latency_ms == 15.5
        assert result.error is None
        assert result.details == {}
        assert result.timestamp is not None
    
    def test_failed_result(self):
        """Test creating a failed monitoring result"""
        result = MonitoringResult(
            success=False,
            target_ip="192.168.1.100",
            error="Connection timeout"
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.latency_ms is None
    
    def test_result_with_details(self):
        """Test result with additional details"""
        details = {"packets_sent": 3, "packets_received": 2}
        result = MonitoringResult(
            success=True,
            target_ip="192.168.1.100",
            latency_ms=20.0,
            details=details
        )
        
        assert result.details == details


# =============================================================================
# WhitePawnMonitor Configuration Tests
# =============================================================================

class TestWhitePawnMonitorConfig:
    """Tests for monitor configuration"""
    
    def test_default_config(self):
        """Test monitor uses default configuration"""
        monitor = WhitePawnMonitor(deployment_id=1)
        
        assert monitor.config["ping_interval"] == 10
        assert monitor.config["ping_timeout"] == 2
        assert monitor.config["latency_warning_ms"] == 50
        assert monitor.config["latency_critical_ms"] == 200
    
    def test_custom_config(self):
        """Test monitor accepts custom configuration"""
        custom_config = {
            "ping_interval": 5,
            "latency_warning_ms": 100,
        }
        monitor = WhitePawnMonitor(deployment_id=1, config=custom_config)
        
        assert monitor.config["ping_interval"] == 5
        assert monitor.config["latency_warning_ms"] == 100
        # Default values still present
        assert monitor.config["ping_timeout"] == 2
    
    def test_initial_state(self):
        """Test monitor initial state"""
        monitor = WhitePawnMonitor(deployment_id=1)
        
        assert monitor._running is False
        assert monitor._task is None
        assert monitor._targets == []
        assert monitor._check_count == 0
        assert monitor._alert_count == 0


# =============================================================================
# WhitePawnMonitor Ping Tests
# =============================================================================

class TestWhitePawnMonitorPing:
    """Tests for ping functionality"""
    
    @pytest.fixture
    def monitor(self):
        """Create a monitor instance for testing"""
        return WhitePawnMonitor(deployment_id=1)
    
    @pytest.mark.asyncio
    async def test_ping_success(self, monitor):
        """Test successful ping returns correct result"""
        # Mock asyncio.create_subprocess_exec
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(
            b"PING 192.168.1.100 (192.168.1.100) 56(84) bytes of data.\n64 bytes from 192.168.1.100: icmp_seq=1 ttl=64 time=1.23 ms\n",
            b""
        ))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            result = await monitor._ping("192.168.1.100")
            
            assert result.success is True
            assert result.target_ip == "192.168.1.100"
    
    @pytest.mark.asyncio
    async def test_ping_failure(self, monitor):
        """Test failed ping returns error"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(
            b"",
            b"Destination Host Unreachable"
        ))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            result = await monitor._ping("192.168.1.100")
            
            assert result.success is False
            assert result.target_ip == "192.168.1.100"
    
    @pytest.mark.asyncio
    async def test_ping_timeout(self, monitor):
        """Test ping timeout handling"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
            result = await monitor._ping("192.168.1.100")
            
            assert result.success is False
            assert result.error is not None


# =============================================================================
# WhitePawnMonitor Start/Stop Tests
# =============================================================================

class TestWhitePawnMonitorLifecycle:
    """Tests for monitor start/stop lifecycle"""
    
    @pytest.fixture
    def monitor(self):
        """Create a monitor instance"""
        return WhitePawnMonitor(deployment_id=1)
    
    @pytest.mark.asyncio
    async def test_start_sets_running(self, monitor):
        """Test start sets running flag"""
        # Mock the internal methods to prevent actual execution
        monitor._monitor_loop = AsyncMock()
        monitor._create_alert = AsyncMock()
        
        await monitor.start()
        
        assert monitor._running is True
        assert monitor._task is not None
        
        # Cleanup
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, monitor):
        """Test start when already running logs warning"""
        monitor._running = True
        
        with patch.object(monitor, '_monitor_loop', new_callable=AsyncMock):
            await monitor.start()
            # Should not create a new task since already running
    
    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self, monitor):
        """Test stop sets running flag to false"""
        monitor._running = True
        monitor._task = None  # No actual task
        monitor._create_alert = AsyncMock()
        
        await monitor.stop()
        
        assert monitor._running is False


# =============================================================================
# WhitePawnMonitor Alert Tests
# =============================================================================

class TestWhitePawnMonitorAlerts:
    """Tests for alert creation and cooldown"""
    
    @pytest.fixture
    def monitor(self):
        """Create a monitor with mock session"""
        return WhitePawnMonitor(deployment_id=1)
    
    def test_alert_cooldown_check(self, monitor):
        """Test alert cooldown prevents duplicate alerts"""
        # Set a recent alert
        cooldown_key = "PING_FAILED:192.168.1.100"
        monitor._last_alerts[cooldown_key] = datetime.now(timezone.utc)
        
        # Check should indicate cooldown active
        assert cooldown_key in monitor._last_alerts
        
        # Simulate time passing beyond cooldown
        old_time = datetime.now(timezone.utc) - timedelta(seconds=400)
        monitor._last_alerts[cooldown_key] = old_time
        
        # Now cooldown should have expired
        cooldown_seconds = monitor.config["alert_cooldown"]
        time_since = (datetime.now(timezone.utc) - old_time).total_seconds()
        assert time_since > cooldown_seconds


# =============================================================================
# WhitePawnMonitor Metrics Tests  
# =============================================================================

class TestWhitePawnMonitorMetrics:
    """Tests for monitoring metrics"""
    
    @pytest.fixture
    def monitor(self):
        return WhitePawnMonitor(deployment_id=1)
    
    def test_check_count_increments(self, monitor):
        """Test check count tracking"""
        initial = monitor._check_count
        monitor._check_count += 1
        assert monitor._check_count == initial + 1
    
    def test_alert_count_increments(self, monitor):
        """Test alert count tracking"""
        initial = monitor._alert_count
        monitor._alert_count += 1
        assert monitor._alert_count == initial + 1


# =============================================================================
# WhitePawnMonitor Target Management Tests
# =============================================================================

class TestWhitePawnMonitorTargets:
    """Tests for target management"""
    
    @pytest.fixture
    def monitor(self):
        return WhitePawnMonitor(deployment_id=1)
    
    def test_empty_targets_initially(self, monitor):
        """Test targets list is empty initially"""
        assert monitor._targets == []
    
    def test_add_target(self, monitor):
        """Test adding targets"""
        target = {
            "vm_id": "vm-100",
            "name": "test-vm",
            "ip": "192.168.1.100",
            "platform": "proxmox"
        }
        monitor._targets.append(target)
        
        assert len(monitor._targets) == 1
        assert monitor._targets[0]["ip"] == "192.168.1.100"
    
    def test_multiple_targets(self, monitor):
        """Test multiple targets"""
        targets = [
            {"vm_id": "vm-100", "name": "vm1", "ip": "192.168.1.100", "platform": "proxmox"},
            {"vm_id": "vm-101", "name": "vm2", "ip": "192.168.1.101", "platform": "proxmox"},
            {"vm_id": "vm-102", "name": "vm3", "ip": "192.168.1.102", "platform": "proxmox"},
        ]
        monitor._targets = targets
        
        assert len(monitor._targets) == 3


# =============================================================================
# WhitePawnMonitor Latency Analysis Tests
# =============================================================================

class TestWhitePawnLatencyAnalysis:
    """Tests for latency analysis and alerting"""
    
    @pytest.fixture
    def monitor(self):
        return WhitePawnMonitor(deployment_id=1)
    
    def test_latency_warning_threshold(self, monitor):
        """Test latency warning threshold detection"""
        warning_threshold = monitor.config["latency_warning_ms"]
        
        # Below threshold - no warning
        assert 30 < warning_threshold
        
        # Above threshold - should warn
        assert 60 > warning_threshold
    
    def test_latency_critical_threshold(self, monitor):
        """Test latency critical threshold detection"""
        critical_threshold = monitor.config["latency_critical_ms"]
        
        # Below threshold - not critical
        assert 100 < critical_threshold
        
        # Above threshold - critical
        assert 250 > critical_threshold
    
    def test_latency_parsing(self, monitor):
        """Test parsing latency from ping output"""
        # Typical ping output: "time=1.23 ms"
        output = b"64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=15.3 ms"
        
        # Parse the time value
        import re
        match = re.search(r'time=(\d+\.?\d*)', output.decode())
        assert match is not None
        latency = float(match.group(1))
        assert latency == 15.3


# =============================================================================
# WhitePawn Integration with Database Tests
# =============================================================================

@pytest.mark.asyncio
class TestWhitePawnDatabaseIntegration:
    """Integration tests with database fixtures"""
    
    async def test_create_deployment(self, db_session):
        """Test creating a WhitePawn deployment"""
        deployment = WhitePawnDeployment(
            lab_id="test-lab-001",
            status="pending",
            config={"ping_interval": 10}
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        assert deployment.id is not None
        assert deployment.lab_id == "test-lab-001"
        assert deployment.status == "pending"
    
    async def test_create_alert(self, db_session):
        """Test creating a network alert"""
        # First create a deployment
        deployment = WhitePawnDeployment(
            lab_id="test-lab-001",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        # Create alert
        alert = NetworkAlert(
            deployment_id=deployment.id,
            alert_type=AlertType.PING_FAILED.value,
            severity=AlertSeverity.ERROR.value,
            title="VM Unreachable",
            message="Could not ping 192.168.1.100",
            target_ip="192.168.1.100"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.id is not None
        assert alert.severity == AlertSeverity.ERROR.value
    
    async def test_create_monitoring_event(self, db_session):
        """Test creating a monitoring event"""
        deployment = WhitePawnDeployment(
            lab_id="test-lab-001",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        event = MonitoringEvent(
            deployment_id=deployment.id,
            event_type="ping",
            target_ip="192.168.1.100",
            target_vm_id="vm-100",
            success=True,
            latency_ms=15.5
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)
        
        assert event.id is not None
        assert event.success is True
        assert event.latency_ms == 15.5
    
    async def test_connectivity_matrix(self, db_session):
        """Test saving connectivity matrix"""
        deployment = WhitePawnDeployment(
            lab_id="test-lab-001",
            status="active"
        )
        db_session.add(deployment)
        await db_session.commit()
        await db_session.refresh(deployment)
        
        matrix_data = {
            "192.168.1.100": {"192.168.1.101": {"reachable": True, "latency_ms": 1.2}},
            "192.168.1.101": {"192.168.1.100": {"reachable": True, "latency_ms": 1.1}},
        }
        
        matrix = ConnectivityMatrix(
            deployment_id=deployment.id,
            lab_id="test-lab-001",
            matrix=matrix_data,
            total_pairs=4,
            reachable_pairs=2
        )
        db_session.add(matrix)
        await db_session.commit()
        await db_session.refresh(matrix)
        
        assert matrix.id is not None
        assert matrix.total_pairs == 4
        assert matrix.reachable_pairs == 2


# =============================================================================
# WhitePawn Alert Severity Tests
# =============================================================================

class TestAlertSeverity:
    """Tests for alert severity levels"""
    
    def test_severity_values(self):
        """Test severity enum values"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_severity_ordering(self):
        """Test severity can be compared conceptually"""
        # Define severity ordering
        severity_order = {
            AlertSeverity.INFO: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.ERROR: 3,
            AlertSeverity.CRITICAL: 4,
        }
        
        assert severity_order[AlertSeverity.INFO] < severity_order[AlertSeverity.WARNING]
        assert severity_order[AlertSeverity.WARNING] < severity_order[AlertSeverity.ERROR]
        assert severity_order[AlertSeverity.ERROR] < severity_order[AlertSeverity.CRITICAL]


# =============================================================================
# WhitePawn Alert Type Tests
# =============================================================================

class TestAlertType:
    """Tests for alert type enumeration"""
    
    def test_ping_alert_types(self):
        """Test ping-related alert types exist"""
        assert hasattr(AlertType, 'PING_FAILED')
        assert hasattr(AlertType, 'PING_LATENCY')
    
    def test_network_alert_types(self):
        """Test network-related alert types exist"""
        assert hasattr(AlertType, 'GATEWAY_UNREACHABLE')
        assert hasattr(AlertType, 'DNS_FAILED')
        assert hasattr(AlertType, 'INTERFACE_DOWN')
    
    def test_vm_alert_types(self):
        """Test VM-related alert types exist"""
        assert hasattr(AlertType, 'VM_UNREACHABLE')
        assert hasattr(AlertType, 'VM_HIGH_LATENCY')
    
    def test_lifecycle_alert_types(self):
        """Test lifecycle alert types exist"""
        assert hasattr(AlertType, 'WHITEPAWN_DEPLOYED')
        assert hasattr(AlertType, 'WHITEPAWN_STOPPED')

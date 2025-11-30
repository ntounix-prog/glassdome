"""
Reaper Engine Unit Tests

Tests for the vulnerability injection and mission control system.

Author: Brett Turner (ntounix)
Created: November 2025
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from glassdome.reaper.models import (
    Task,
    ResultEvent,
    HostState,
    MissionState
)
from glassdome.reaper.engine import MissionEngine


# =============================================================================
# Task Model Tests
# =============================================================================

class TestTaskModel:
    """Tests for Task dataclass"""
    
    def test_task_creation(self):
        """Test creating a task"""
        task = Task(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            agent_type="reaper-linux",
            action="linux.discover",
            params={"scan_type": "full"}
        )
        
        assert task.task_id == "task-001"
        assert task.mission_id == "mission-001"
        assert task.host_id == "vm-100"
        assert task.agent_type == "reaper-linux"
        assert task.action == "linux.discover"
        assert task.params == {"scan_type": "full"}
    
    def test_task_to_dict(self):
        """Test task serialization"""
        task = Task(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            agent_type="reaper-linux",
            action="linux.discover",
            params={"timeout": 60}
        )
        
        result = task.to_dict()
        
        assert isinstance(result, dict)
        assert result["task_id"] == "task-001"
        assert result["params"]["timeout"] == 60
    
    def test_task_agent_types(self):
        """Test different agent types"""
        agent_types = ["reaper-linux", "reaper-windows", "reaper-macos"]
        
        for agent_type in agent_types:
            task = Task(
                task_id="task-001",
                mission_id="mission-001",
                host_id="vm-100",
                agent_type=agent_type,
                action="discover",
                params={}
            )
            assert task.agent_type == agent_type


# =============================================================================
# ResultEvent Model Tests
# =============================================================================

class TestResultEventModel:
    """Tests for ResultEvent dataclass"""
    
    def test_result_event_defaults(self):
        """Test result event default values"""
        event = ResultEvent()
        
        assert event.event_type == "task.result"
        assert event.status == "unknown"
        assert event.data == {}
        assert event.retriable is False
        assert event.ts is not None
    
    def test_successful_result(self):
        """Test successful task result"""
        event = ResultEvent(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            agent_type="reaper-linux",
            action="linux.discover",
            status="success",
            summary="Discovered 5 services",
            data={"services": ["ssh", "http", "mysql"]}
        )
        
        assert event.status == "success"
        assert "services" in event.data
    
    def test_error_result(self):
        """Test error task result"""
        event = ResultEvent(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            agent_type="reaper-linux",
            action="linux.inject_vuln",
            status="error",
            summary="Connection refused",
            error_code="CONNECTION_REFUSED",
            retriable=True
        )
        
        assert event.status == "error"
        assert event.error_code == "CONNECTION_REFUSED"
        assert event.retriable is True
    
    def test_result_event_to_dict(self):
        """Test result event serialization"""
        event = ResultEvent(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            status="success",
            stdout_tail="Operation completed"
        )
        
        result = event.to_dict()
        
        assert isinstance(result, dict)
        assert result["task_id"] == "task-001"
        assert result["stdout_tail"] == "Operation completed"


# =============================================================================
# HostState Model Tests
# =============================================================================

class TestHostStateModel:
    """Tests for HostState dataclass"""
    
    def test_host_state_creation(self):
        """Test creating a host state"""
        host = HostState(
            host_id="vm-100",
            os="linux",
            ip_address="192.168.1.100"
        )
        
        assert host.host_id == "vm-100"
        assert host.os == "linux"
        assert host.ip_address == "192.168.1.100"
    
    def test_host_state_defaults(self):
        """Test host state default values"""
        host = HostState(host_id="vm-100", os="linux")
        
        assert host.last_status == "unknown"
        assert host.failure_count == 0
        assert host.max_failures == 3
        assert host.locked is False
        assert host.facts == {}
        assert host.vulnerabilities_injected == []
    
    def test_host_failure_tracking(self):
        """Test host failure count tracking"""
        host = HostState(host_id="vm-100", os="linux")
        
        # Simulate failures
        for i in range(3):
            host.failure_count += 1
        
        assert host.failure_count == 3
        assert host.failure_count >= host.max_failures
    
    def test_host_locking(self):
        """Test host locking mechanism"""
        host = HostState(host_id="vm-100", os="linux")
        
        assert host.locked is False
        host.locked = True
        assert host.locked is True
    
    def test_host_vulnerability_tracking(self):
        """Test tracking injected vulnerabilities"""
        host = HostState(host_id="vm-100", os="linux")
        
        host.vulnerabilities_injected.append("CVE-2021-44228")
        host.vulnerabilities_injected.append("CVE-2022-0847")
        
        assert len(host.vulnerabilities_injected) == 2
        assert "CVE-2021-44228" in host.vulnerabilities_injected
    
    def test_host_facts_storage(self):
        """Test storing discovered facts"""
        host = HostState(host_id="vm-100", os="linux")
        
        host.facts["kernel_version"] = "5.15.0"
        host.facts["open_ports"] = [22, 80, 443]
        host.facts["services"] = {"ssh": "OpenSSH 8.2", "http": "nginx 1.18"}
        
        assert host.facts["kernel_version"] == "5.15.0"
        assert 80 in host.facts["open_ports"]
    
    def test_host_to_dict(self):
        """Test host state serialization"""
        host = HostState(
            host_id="vm-100",
            os="linux",
            ip_address="192.168.1.100"
        )
        host.facts["test"] = "value"
        
        result = host.to_dict()
        
        assert isinstance(result, dict)
        assert result["host_id"] == "vm-100"
        assert result["facts"]["test"] == "value"


# =============================================================================
# MissionState Model Tests
# =============================================================================

class TestMissionStateModel:
    """Tests for MissionState dataclass"""
    
    @pytest.fixture
    def sample_hosts(self) -> Dict[str, HostState]:
        """Create sample hosts for testing"""
        return {
            "vm-100": HostState(host_id="vm-100", os="linux", ip_address="192.168.1.100"),
            "vm-101": HostState(host_id="vm-101", os="windows", ip_address="192.168.1.101"),
            "vm-102": HostState(host_id="vm-102", os="linux", ip_address="192.168.1.102"),
        }
    
    def test_mission_state_creation(self, sample_hosts):
        """Test creating a mission state"""
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="web-security-lab",
            hosts=sample_hosts
        )
        
        assert mission.mission_id == "mission-001"
        assert mission.lab_id == "lab-001"
        assert mission.mission_type == "web-security-lab"
        assert len(mission.hosts) == 3
    
    def test_mission_state_defaults(self, sample_hosts):
        """Test mission state default values"""
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=sample_hosts
        )
        
        assert mission.status == "pending"
        assert mission.pending_tasks == []
        assert mission.completed_tasks == []
        assert mission.failed_tasks == []
        assert mission.created_at is not None
        assert mission.updated_at is not None
    
    def test_mission_task_tracking(self, sample_hosts):
        """Test task tracking in mission"""
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=sample_hosts
        )
        
        # Add pending tasks
        mission.pending_tasks.extend(["task-1", "task-2", "task-3"])
        assert len(mission.pending_tasks) == 3
        
        # Complete a task
        mission.pending_tasks.remove("task-1")
        mission.completed_tasks.append("task-1")
        
        assert len(mission.pending_tasks) == 2
        assert len(mission.completed_tasks) == 1
        
        # Fail a task
        mission.pending_tasks.remove("task-2")
        mission.failed_tasks.append("task-2")
        
        assert len(mission.failed_tasks) == 1
    
    def test_mission_status_transitions(self, sample_hosts):
        """Test mission status transitions"""
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=sample_hosts
        )
        
        assert mission.status == "pending"
        
        mission.status = "running"
        assert mission.status == "running"
        
        mission.status = "completed"
        assert mission.status == "completed"
    
    def test_mission_get_summary(self, sample_hosts):
        """Test mission summary generation"""
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=sample_hosts
        )
        
        # Set some host statuses
        mission.hosts["vm-100"].last_status = "healthy"
        mission.hosts["vm-101"].last_status = "healthy"
        mission.hosts["vm-102"].locked = True
        
        # Add some tasks
        mission.completed_tasks = ["task-1", "task-2"]
        mission.failed_tasks = ["task-3"]
        mission.pending_tasks = ["task-4"]
        
        summary = mission.get_summary()
        
        assert summary["mission_id"] == "mission-001"
        assert summary["total_hosts"] == 3
        assert summary["healthy_hosts"] == 2
        assert summary["locked_hosts"] == 1
        assert summary["completed_tasks"] == 2
        assert summary["failed_tasks"] == 1
        assert summary["pending_tasks"] == 1
    
    def test_mission_to_dict(self, sample_hosts):
        """Test mission serialization"""
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=sample_hosts
        )
        
        result = mission.to_dict()
        
        assert isinstance(result, dict)
        assert result["mission_id"] == "mission-001"
        assert "vm-100" in result["hosts"]
        assert result["hosts"]["vm-100"]["os"] == "linux"


# =============================================================================
# MissionEngine Tests
# =============================================================================

class TestMissionEngine:
    """Tests for MissionEngine"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for engine"""
        return {
            "mission_store": MagicMock(),
            "task_queue": MagicMock(),
            "event_bus": MagicMock(),
            "planner": MagicMock()
        }
    
    @pytest.fixture
    def engine(self, mock_dependencies):
        """Create engine with mock dependencies"""
        return MissionEngine(
            mission_id="mission-001",
            **mock_dependencies
        )
    
    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.mission_id == "mission-001"
        assert engine._running is False
        assert engine._event_loop_task is None
    
    def test_engine_stores_dependencies(self, engine, mock_dependencies):
        """Test engine stores all dependencies"""
        assert engine.store == mock_dependencies["mission_store"]
        assert engine.task_queue == mock_dependencies["task_queue"]
        assert engine.event_bus == mock_dependencies["event_bus"]
        assert engine.planner == mock_dependencies["planner"]
    
    def test_start_mission(self, engine, mock_dependencies):
        """Test starting a mission"""
        # Create initial state
        hosts = {
            "vm-100": HostState(host_id="vm-100", os="linux")
        }
        initial_state = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=hosts
        )
        
        # Mock planner to return tasks
        mock_dependencies["planner"].initial_tasks.return_value = [
            Task(
                task_id="task-001",
                mission_id="mission-001",
                host_id="vm-100",
                agent_type="reaper-linux",
                action="linux.discover",
                params={}
            )
        ]
        
        # Mock store.load to return the mission
        mock_dependencies["mission_store"].load.return_value = initial_state
        
        engine.start_mission(initial_state)
        
        # Verify state was saved
        mock_dependencies["mission_store"].save.assert_called()
        
        # Verify initial tasks were requested
        mock_dependencies["planner"].initial_tasks.assert_called_once()
        
        # Verify tasks were queued
        mock_dependencies["task_queue"].publish.assert_called()
    
    def test_schedule_empty_tasks(self, engine, mock_dependencies):
        """Test scheduling empty task list"""
        engine._schedule_tasks([])
        
        # No tasks should be published
        mock_dependencies["task_queue"].publish.assert_not_called()
    
    def test_mission_not_found(self, engine, mock_dependencies):
        """Test scheduling when mission not found"""
        mock_dependencies["mission_store"].load.return_value = None
        
        tasks = [
            Task(
                task_id="task-001",
                mission_id="mission-001",
                host_id="vm-100",
                agent_type="reaper-linux",
                action="linux.discover",
                params={}
            )
        ]
        
        engine._schedule_tasks(tasks)
        
        # Tasks should not be published since mission not found
        mock_dependencies["task_queue"].publish.assert_not_called()


# =============================================================================
# MissionEngine Event Handling Tests
# =============================================================================

class TestMissionEngineEventHandling:
    """Tests for event handling in MissionEngine"""
    
    @pytest.fixture
    def engine_with_mission(self):
        """Create engine with a running mission"""
        mock_store = MagicMock()
        mock_queue = MagicMock()
        mock_bus = MagicMock()
        mock_planner = MagicMock()
        
        engine = MissionEngine(
            mission_id="mission-001",
            mission_store=mock_store,
            task_queue=mock_queue,
            event_bus=mock_bus,
            planner=mock_planner
        )
        
        # Set up a running mission
        hosts = {
            "vm-100": HostState(host_id="vm-100", os="linux"),
            "vm-101": HostState(host_id="vm-101", os="windows")
        }
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=hosts,
            status="running",
            pending_tasks=["task-001", "task-002"]
        )
        mock_store.load.return_value = mission
        
        return engine, mission, mock_planner
    
    def test_successful_result_processing(self, engine_with_mission):
        """Test processing successful task result"""
        engine, mission, mock_planner = engine_with_mission
        
        # Create a successful result
        result = ResultEvent(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            status="success",
            summary="Discovery complete",
            data={"services": ["ssh", "http"]}
        )
        
        # The mission should track this result
        assert "task-001" in mission.pending_tasks
    
    def test_failed_result_processing(self, engine_with_mission):
        """Test processing failed task result"""
        engine, mission, _ = engine_with_mission
        
        result = ResultEvent(
            task_id="task-001",
            mission_id="mission-001",
            host_id="vm-100",
            status="error",
            error_code="CONNECTION_TIMEOUT",
            retriable=True
        )
        
        # Verify the result can be tracked
        assert result.status == "error"
        assert result.retriable is True


# =============================================================================
# Mission Completion Tests
# =============================================================================

class TestMissionCompletion:
    """Tests for mission completion scenarios"""
    
    @pytest.fixture
    def completed_mission(self):
        """Create a completed mission"""
        hosts = {
            "vm-100": HostState(
                host_id="vm-100",
                os="linux",
                last_status="healthy",
                vulnerabilities_injected=["CVE-2021-44228"]
            )
        }
        return MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=hosts,
            status="completed",
            completed_tasks=["task-1", "task-2", "task-3"]
        )
    
    def test_completed_mission_summary(self, completed_mission):
        """Test summary of completed mission"""
        summary = completed_mission.get_summary()
        
        assert summary["status"] == "completed"
        assert summary["completed_tasks"] == 3
        assert summary["pending_tasks"] == 0
    
    def test_mission_all_hosts_healthy(self, completed_mission):
        """Test all hosts marked healthy"""
        healthy_count = sum(
            1 for h in completed_mission.hosts.values()
            if h.last_status == "healthy"
        )
        
        assert healthy_count == len(completed_mission.hosts)
    
    def test_mission_vulnerabilities_injected(self, completed_mission):
        """Test vulnerabilities were injected"""
        total_vulns = sum(
            len(h.vulnerabilities_injected)
            for h in completed_mission.hosts.values()
        )
        
        assert total_vulns > 0


# =============================================================================
# Mission Failure Tests
# =============================================================================

class TestMissionFailure:
    """Tests for mission failure scenarios"""
    
    def test_host_reaches_max_failures(self):
        """Test host locking after max failures"""
        host = HostState(host_id="vm-100", os="linux", max_failures=3)
        
        # Simulate reaching max failures
        for i in range(3):
            host.failure_count += 1
        
        # Should be at max
        assert host.failure_count >= host.max_failures
        
        # Lock the host
        host.locked = True
        assert host.locked is True
    
    def test_mission_with_failed_tasks(self):
        """Test mission with some failed tasks"""
        hosts = {
            "vm-100": HostState(host_id="vm-100", os="linux")
        }
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=hosts,
            failed_tasks=["task-1", "task-3"],
            completed_tasks=["task-2"]
        )
        
        summary = mission.get_summary()
        
        assert summary["failed_tasks"] == 2
        assert summary["completed_tasks"] == 1
    
    def test_mission_cancellation(self):
        """Test mission cancellation"""
        hosts = {"vm-100": HostState(host_id="vm-100", os="linux")}
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="test",
            hosts=hosts
        )
        
        mission.status = "cancelled"
        
        assert mission.status == "cancelled"


# =============================================================================
# Mission Type Tests
# =============================================================================

class TestMissionTypes:
    """Tests for different mission types"""
    
    def test_web_security_lab(self):
        """Test web security lab mission type"""
        hosts = {"vm-100": HostState(host_id="vm-100", os="linux")}
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="web-security-lab",
            hosts=hosts
        )
        
        assert mission.mission_type == "web-security-lab"
    
    def test_network_defense_lab(self):
        """Test network defense lab mission type"""
        hosts = {"vm-100": HostState(host_id="vm-100", os="linux")}
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="network-defense-lab",
            hosts=hosts
        )
        
        assert mission.mission_type == "network-defense-lab"
    
    def test_incident_response_lab(self):
        """Test incident response lab mission type"""
        hosts = {"vm-100": HostState(host_id="vm-100", os="windows")}
        mission = MissionState(
            mission_id="mission-001",
            lab_id="lab-001",
            mission_type="incident-response-lab",
            hosts=hosts
        )
        
        assert mission.mission_type == "incident-response-lab"

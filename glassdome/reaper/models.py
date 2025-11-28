"""
Models module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class Task:
    """
    Represents work to be done by a Reaper agent
    
    A task is a single unit of work targeting one VM,
    such as discovering services or injecting a vulnerability.
    """
    task_id: str
    mission_id: str
    host_id: str
    agent_type: str      # "reaper-windows" | "reaper-linux" | "reaper-macos"
    action: str          # e.g. "linux.discover", "windows.inject_vuln"
    params: Dict[str, Any]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "host_id": self.host_id,
            "agent_type": self.agent_type,
            "action": self.action,
            "params": self.params
        }


@dataclass
class ResultEvent:
    """
    Result of a task execution by a Reaper agent
    
    Published to the event bus after a task completes,
    allowing the MissionEngine to react and plan next steps.
    """
    event_type: str = "task.result"
    task_id: str = ""
    mission_id: str = ""
    host_id: str = ""
    agent_type: str = ""
    action: str = ""
    status: str = "unknown"  # "success" | "error" | "partial"
    summary: str = ""
    stdout_tail: str = ""
    stderr_tail: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    logs_ref: Optional[str] = None
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    retriable: bool = False
    error_code: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "host_id": self.host_id,
            "agent_type": self.agent_type,
            "action": self.action,
            "status": self.status,
            "summary": self.summary,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "data": self.data,
            "logs_ref": self.logs_ref,
            "ts": self.ts,
            "retriable": self.retriable,
            "error_code": self.error_code
        }


@dataclass
class HostState:
    """
    State of a single VM in a Reaper mission
    
    Tracks health, failures, and discovered facts about the VM.
    """
    host_id: str
    os: str  # "windows" | "linux" | "macos"
    ip_address: Optional[str] = None
    last_status: str = "unknown"  # "unknown" | "healthy" | "degraded" | "error"
    last_tasks: List[str] = field(default_factory=list)
    failure_count: int = 0
    max_failures: int = 3
    locked: bool = False
    facts: Dict[str, Any] = field(default_factory=dict)
    vulnerabilities_injected: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "host_id": self.host_id,
            "os": self.os,
            "ip_address": self.ip_address,
            "last_status": self.last_status,
            "last_tasks": self.last_tasks,
            "failure_count": self.failure_count,
            "max_failures": self.max_failures,
            "locked": self.locked,
            "facts": self.facts,
            "vulnerabilities_injected": self.vulnerabilities_injected
        }


@dataclass
class MissionState:
    """
    Complete state of a vulnerability injection mission
    
    Manages all VMs in the mission, tracks progress,
    and persists state for recovery after restarts.
    """
    mission_id: str
    lab_id: str  # Link to LabOrchestrator deployment
    mission_type: str  # e.g. "web-security-lab", "network-defense-lab"
    hosts: Dict[str, HostState]
    pending_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "pending"  # "pending" | "running" | "completed" | "failed" | "cancelled"
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "mission_id": self.mission_id,
            "lab_id": self.lab_id,
            "mission_type": self.mission_type,
            "hosts": {hid: h.to_dict() for hid, h in self.hosts.items()},
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get high-level mission summary"""
        healthy_hosts = sum(1 for h in self.hosts.values() if h.last_status == "healthy")
        locked_hosts = sum(1 for h in self.hosts.values() if h.locked)
        
        return {
            "mission_id": self.mission_id,
            "status": self.status,
            "total_hosts": len(self.hosts),
            "healthy_hosts": healthy_hosts,
            "locked_hosts": locked_hosts,
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


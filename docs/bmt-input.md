# Reaper System - Step-by-Step Implementation Guide

## Overview
Build an event-driven, swarm-based orchestration system where:
- **Overseer** creates and monitors lab deployments
- **Reaper (MissionEngine)** manages individual lab missions without blocking
- **Agents** (win/linux/mac) execute OS-specific tasks in parallel
- Everything communicates via async events and shared state

## Phase 1: Project Structure & Core Models

### Step 1.1: Create directory structure
```
reaper_system/
├── overseer/
│   ├── __init__.py
│   ├── service.py
│   └── planner.py
├── reaper/
│   ├── __init__.py
│   ├── engine.py
│   ├── planner.py
│   └── models.py
├── agents/
│   ├── __init__.py
│   ├── base.py
│   ├── win_agent.py
│   ├── linux_agent.py
│   └── mac_agent.py
├── infra/
│   ├── __init__.py
│   ├── task_queue.py
│   ├── event_bus.py
│   ├── mission_store.py
│   └── logging.py
├── llm/
│   ├── __init__.py
│   ├── client.py
│   └── prompts.py
├── tests/
│   └── __init__.py
├── requirements.txt
└── main.py
```

### Step 1.2: Create `reaper/models.py`
Implement all dataclasses:

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class Task:
    """Represents work to be done by an agent"""
    task_id: str
    mission_id: str
    host_id: str
    agent_type: str      # "reaper-win" | "reaper-linux" | "reaper-mac"
    action: str          # e.g. "windows.file_write", "linux.run_shell"
    params: Dict[str, Any]
    
    def to_dict(self) -> dict:
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
    """Result of a task execution"""
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
    """State of a single host in a mission"""
    host_id: str
    os: str  # "windows" | "linux" | "macos"
    last_status: str = "unknown"  # "unknown" | "healthy" | "degraded" | "error"
    last_tasks: list[str] = field(default_factory=list)
    failure_count: int = 0
    max_failures: int = 3
    locked: bool = False
    facts: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "host_id": self.host_id,
            "os": self.os,
            "last_status": self.last_status,
            "last_tasks": self.last_tasks,
            "failure_count": self.failure_count,
            "max_failures": self.max_failures,
            "locked": self.locked,
            "facts": self.facts
        }

@dataclass
class MissionState:
    """Complete state of a lab mission"""
    mission_id: str
    lab_type: str  # e.g. "windows-baseline-lab"
    hosts: Dict[str, HostState]
    pending_tasks: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "lab_type": self.lab_type,
            "hosts": {hid: h.to_dict() for hid, h in self.hosts.items()},
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
```

## Phase 2: Infrastructure Layer (In-Memory Implementations)

### Step 2.1: Create `infra/task_queue.py`

```python
from abc import ABC, abstractmethod
from typing import Iterator
from collections import deque
from threading import Lock
import time
from reaper.models import Task

class TaskQueue(ABC):
    @abstractmethod
    def publish(self, task: Task) -> None:
        """Publish a task for agents to consume"""
        pass
    
    @abstractmethod
    def consume(self, agent_type: str) -> Iterator[Task]:
        """Yield tasks for this agent type (blocking/polling)"""
        pass

class InMemoryTaskQueue(TaskQueue):
    """Simple in-memory queue for testing"""
    def __init__(self):
        self._queues: dict[str, deque] = {}
        self._lock = Lock()
    
    def publish(self, task: Task) -> None:
        with self._lock:
            if task.agent_type not in self._queues:
                self._queues[task.agent_type] = deque()
            self._queues[task.agent_type].append(task)
            print(f"[TaskQueue] Published {task.task_id} for {task.agent_type}")
    
    def consume(self, agent_type: str) -> Iterator[Task]:
        """Poll for tasks every 0.1s"""
        while True:
            with self._lock:
                if agent_type in self._queues and self._queues[agent_type]:
                    task = self._queues[agent_type].popleft()
                    print(f"[TaskQueue] {agent_type} consumed {task.task_id}")
                    yield task
            time.sleep(0.1)  # polling interval
```

### Step 2.2: Create `infra/event_bus.py`

```python
from abc import ABC, abstractmethod
from typing import Iterator
from collections import deque
from threading import Lock
import time
from reaper.models import ResultEvent

class EventBus(ABC):
    @abstractmethod
    def publish_result(self, event: ResultEvent) -> None:
        """Publish a result event"""
        pass
    
    @abstractmethod
    def subscribe_results(self, mission_id: str) -> Iterator[ResultEvent]:
        """Yield result events for this mission (blocking/polling)"""
        pass

class InMemoryEventBus(EventBus):
    """Simple in-memory event bus for testing"""
    def __init__(self):
        self._events: dict[str, deque] = {}
        self._lock = Lock()
    
    def publish_result(self, event: ResultEvent) -> None:
        with self._lock:
            if event.mission_id not in self._events:
                self._events[event.mission_id] = deque()
            self._events[event.mission_id].append(event)
            print(f"[EventBus] Published result for {event.task_id} (status: {event.status})")
    
    def subscribe_results(self, mission_id: str) -> Iterator[ResultEvent]:
        """Poll for events every 0.1s"""
        while True:
            with self._lock:
                if mission_id in self._events and self._events[mission_id]:
                    event = self._events[mission_id].popleft()
                    print(f"[EventBus] Mission {mission_id} received result for {event.task_id}")
                    yield event
            time.sleep(0.1)
```

### Step 2.3: Create `infra/mission_store.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from threading import Lock
from reaper.models import MissionState

class MissionStore(ABC):
    @abstractmethod
    def load(self, mission_id: str) -> Optional[MissionState]:
        """Load mission state"""
        pass
    
    @abstractmethod
    def save(self, mission: MissionState) -> None:
        """Save mission state"""
        pass

class InMemoryMissionStore(MissionStore):
    """Simple in-memory store for testing"""
    def __init__(self):
        self._store: dict[str, MissionState] = {}
        self._lock = Lock()
    
    def load(self, mission_id: str) -> Optional[MissionState]:
        with self._lock:
            return self._store.get(mission_id)
    
    def save(self, mission: MissionState) -> None:
        with self._lock:
            self._store[mission.mission_id] = mission
            print(f"[MissionStore] Saved state for {mission.mission_id}")
```

## Phase 3: Reaper (MissionEngine)

### Step 3.1: Create `reaper/planner.py` (simple rule-based version)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from reaper.models import MissionState, Task, ResultEvent
import uuid

class MissionPlanner(ABC):
    @abstractmethod
    def initial_tasks(self, state: MissionState) -> List[Task]:
        """Return initial tasks for mission start"""
        pass
    
    @abstractmethod
    def next_tasks(
        self, 
        state: MissionState, 
        last_result: Optional[ResultEvent] = None
    ) -> List[Task]:
        """Decide next tasks based on current state and last result"""
        pass

class SimpleRuleBasedPlanner(MissionPlanner):
    """Basic planner: discover hosts, then baseline them"""
    
    def initial_tasks(self, state: MissionState) -> List[Task]:
        """Create discovery tasks for all hosts"""
        tasks = []
        for host_id, host in state.hosts.items():
            agent_type = self._os_to_agent_type(host.os)
            task = Task(
                task_id=f"t-{uuid.uuid4().hex[:8]}",
                mission_id=state.mission_id,
                host_id=host_id,
                agent_type=agent_type,
                action=f"{host.os}.discover",
                params={}
            )
            tasks.append(task)
        return tasks
    
    def next_tasks(
        self, 
        state: MissionState, 
        last_result: Optional[ResultEvent] = None
    ) -> List[Task]:
        """
        Simple rules:
        - If discovery succeeded and facts are empty, baseline host
        - If host is locked, skip it
        """
        if not last_result:
            return []
        
        host = state.hosts.get(last_result.host_id)
        if not host or host.locked:
            return []
        
        tasks = []
        
        # After successful discovery, schedule baseline
        if last_result.action.endswith(".discover") and last_result.status == "success":
            agent_type = self._os_to_agent_type(host.os)
            task = Task(
                task_id=f"t-{uuid.uuid4().hex[:8]}",
                mission_id=state.mission_id,
                host_id=host.host_id,
                agent_type=agent_type,
                action=f"{host.os}.baseline",
                params={}
            )
            tasks.append(task)
        
        return tasks
    
    def _os_to_agent_type(self, os: str) -> str:
        return f"reaper-{os}"
```

### Step 3.2: Create `reaper/engine.py`

```python
from infra.task_queue import TaskQueue
from infra.event_bus import EventBus
from infra.mission_store import MissionStore
from reaper.planner import MissionPlanner
from reaper.models import MissionState, Task, ResultEvent
from typing import List
from datetime import datetime

class MissionEngine:
    """Event-driven mission controller (one per lab deployment)"""
    
    def __init__(
        self,
        mission_id: str,
        mission_store: MissionStore,
        task_queue: TaskQueue,
        event_bus: EventBus,
        planner: MissionPlanner
    ):
        self.mission_id = mission_id
        self.store = mission_store
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.planner = planner
    
    def start_mission(self, initial_state: MissionState) -> None:
        """Initialize and kick off the mission"""
        print(f"\n[MissionEngine] Starting mission {self.mission_id}")
        self.store.save(initial_state)
        
        initial_tasks = self.planner.initial_tasks(initial_state)
        print(f"[MissionEngine] Generated {len(initial_tasks)} initial tasks")
        self._schedule_tasks(initial_tasks)
    
    def _schedule_tasks(self, tasks: List[Task]) -> None:
        """Fire-and-forget: enqueue tasks without blocking"""
        mission = self.store.load(self.mission_id)
        if not mission:
            return
        
        for task in tasks:
            mission.pending_tasks.append(task.task_id)
            self.task_queue.publish(task)
        
        mission.updated_at = datetime.utcnow().isoformat() + "Z"
        self.store.save(mission)
    
    def process_result(self, event: ResultEvent) -> None:
        """
        React to a single result event:
        1. Update mission state
        2. Ask planner for next steps
        3. Schedule new tasks
        """
        mission = self.store.load(self.mission_id)
        if not mission:
            return
        
        print(f"\n[MissionEngine] Processing result for {event.task_id}")
        
        # Update host state
        host = mission.hosts.get(event.host_id)
        if host:
            host.last_tasks.append(event.task_id)
            host.last_status = "healthy" if event.status == "success" else "degraded"
            
            if event.status == "error":
                host.failure_count += 1
                if host.failure_count >= host.max_failures:
                    host.locked = True
                    print(f"[MissionEngine] Host {event.host_id} locked due to failures")
            
            # Store discovery facts
            if event.action.endswith(".discover") and event.data:
                host.facts.update(event.data)
        
        # Update task tracking
        if event.task_id in mission.pending_tasks:
            mission.pending_tasks.remove(event.task_id)
        mission.completed_tasks.append(event.task_id)
        
        mission.updated_at = event.ts
        self.store.save(mission)
        
        # Decide next steps
        next_tasks = self.planner.next_tasks(mission, last_result=event)
        if next_tasks:
            print(f"[MissionEngine] Scheduling {len(next_tasks)} new tasks")
            self._schedule_tasks(next_tasks)
        else:
            print(f"[MissionEngine] No new tasks to schedule")
    
    def run_event_loop(self) -> None:
        """
        Blocking loop: listen for results and process them.
        This should run in a background thread/process.
        """
        print(f"[MissionEngine] Starting event loop for {self.mission_id}")
        for event in self.event_bus.subscribe_results(self.mission_id):
            self.process_result(event)
```

## Phase 4: Agents (Workers)

### Step 4.1: Create `agents/base.py`

```python
from abc import ABC, abstractmethod
from infra.task_queue import TaskQueue
from infra.event_bus import EventBus
from reaper.models import Task, ResultEvent

class BaseAgent(ABC):
    """Base class for all OS-specific agents"""
    
    def __init__(self, agent_type: str, task_queue: TaskQueue, event_bus: EventBus):
        self.agent_type = agent_type
        self.task_queue = task_queue
        self.event_bus = event_bus
    
    def run_forever(self) -> None:
        """Main worker loop: consume tasks, execute, emit results"""
        print(f"[{self.agent_type}] Starting worker loop")
        for task in self.task_queue.consume(self.agent_type):
            print(f"[{self.agent_type}] Handling {task.task_id}: {task.action}")
            event = self.handle_task(task)
            self.event_bus.publish_result(event)
    
    @abstractmethod
    def handle_task(self, task: Task) -> ResultEvent:
        """Execute a task and return a result event"""
        pass
```

### Step 4.2: Create `agents/win_agent.py` (stub for now)

```python
from agents.base import BaseAgent
from reaper.models import Task, ResultEvent
from datetime import datetime
import time

class WindowsAgent(BaseAgent):
    """Windows executor (WinRM/PowerShell) - stub version"""
    
    def __init__(self, task_queue, event_bus):
        super().__init__("reaper-windows", task_queue, event_bus)
    
    def handle_task(self, task: Task) -> ResultEvent:
        # Simulate work
        time.sleep(0.5)
        
        if task.action == "windows.discover":
            return self._discover(task)
        elif task.action == "windows.baseline":
            return self._baseline(task)
        else:
            return ResultEvent(
                task_id=task.task_id,
                mission_id=task.mission_id,
                host_id=task.host_id,
                agent_type=self.agent_type,
                action=task.action,
                status="error",
                summary=f"Unknown action: {task.action}",
                error_code="UNKNOWN_ACTION"
            )
    
    def _discover(self, task: Task) -> ResultEvent:
        return ResultEvent(
            task_id=task.task_id,
            mission_id=task.mission_id,
            host_id=task.host_id,
            agent_type=self.agent_type,
            action=task.action,
            status="success",
            summary=f"Discovered Windows host {task.host_id}",
            data={
                "os_version": "Windows Server 2022",
                "hostname": task.host_id,
                "ip": "10.0.0.1"
            }
        )
    
    def _baseline(self, task: Task) -> ResultEvent:
        return ResultEvent(
            task_id=task.task_id,
            mission_id=task.mission_id,
            host_id=task.host_id,
            agent_type=self.agent_type,
            action=task.action,
            status="success",
            summary=f"Baselined Windows host {task.host_id}",
            data={"firewall": "enabled", "rdp": "enabled"}
        )
```

### Step 4.3: Create `agents/linux_agent.py` and `agents/mac_agent.py`

Copy the pattern from `win_agent.py`, change agent_type to `"reaper-linux"` and `"reaper-macos"`.

## Phase 5: Overseer

### Step 5.1: Create `overseer/service.py`

```python
from reaper.engine import MissionEngine
from reaper.planner import MissionPlanner
from infra.mission_store import MissionStore
from infra.task_queue import TaskQueue
from infra.event_bus import EventBus
from reaper.models import MissionState, HostState
from typing import Callable
from datetime import datetime

class OverseerService:
    """High-level orchestrator: creates and monitors missions"""
    
    def __init__(
        self,
        mission_store: MissionStore,
        task_queue: TaskQueue,
        event_bus: EventBus,
        planner_factory: Callable[[str], MissionPlanner]
    ):
        self.store = mission_store
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.planner_factory = planner_factory
        self.engines = {}  # mission_id -> MissionEngine
    
    def create_mission(
        self, 
        mission_id: str, 
        lab_type: str, 
        hosts: list[dict]
    ) -> MissionEngine:
        """
        Create and start a new mission.
        hosts: list of {"host_id": str, "os": str}
        """
        print(f"\n[Overseer] Creating mission {mission_id}")
        
        ts = datetime.utcnow().isoformat() + "Z"
        host_map = {
            h["host_id"]: HostState(
                host_id=h["host_id"],
                os=h["os"]
            )
            for h in hosts
        }
        
        state = MissionState(
            mission_id=mission_id,
            lab_type=lab_type,
            hosts=host_map,
            created_at=ts,
            updated_at=ts
        )
        
        planner = self.planner_factory(lab_type)
        engine = MissionEngine(
            mission_id,
            self.store,
            self.task_queue,
            self.event_bus,
            planner
        )
        
        engine.start_mission(state)
        self.engines[mission_id] = engine
        
        return engine
    
    def get_mission_status(self, mission_id: str) -> dict:
        """Get summary of mission state"""
        state = self.store.load(mission_id)
        if not state:
            return {"error": "Mission not found"}
        
        return {
            "mission_id": state.mission_id,
            "lab_type": state.lab_type,
            "total_hosts": len(state.hosts),
            "pending_tasks": len(state.pending_tasks),
            "completed_tasks": len(state.completed_tasks),
            "hosts": {
                hid: {
                    "status": h.last_status,
                    "failure_count": h.failure_count,
                    "locked": h.locked
                }
                for hid, h in state.hosts.items()
            }
        }
```

## Phase 6: Main Demo Script

### Step 6.1: Create `main.py`

```python
#!/usr/bin/env python3
"""
Demo: Launch a mission with 2 Windows hosts and 1 Linux host.
Watch as Reaper coordinates discovery and baseline tasks.
"""

import threading
import time
from infra.task_queue import InMemoryTaskQueue
from infra.event_bus import InMemoryEventBus
from infra.mission_store import InMemoryMissionStore
from overseer.service import OverseerService
from reaper.planner import SimpleRuleBasedPlanner
from agents.win_agent import WindowsAgent
from agents.linux_agent import LinuxAgent

def main():
    print("=" * 60)
    print("REAPER SYSTEM DEMO")
    print("=" * 60)
    
    # Infrastructure
    task_queue = InMemoryTaskQueue()
    event_bus = InMemoryEventBus()
    mission_store = InMemoryMissionStore()
    
    # Overseer
    def planner_factory(lab_type: str):
        return SimpleRuleBasedPlanner()
    
    overseer = OverseerService(
        mission_store,
        task_queue,
        event_bus,
        planner_factory
    )
    
    # Create mission
    mission_id = "lab-demo-001"
    hosts = [
        {"host_id": "win-01", "os": "windows"},
        {"host_id": "win-02", "os": "windows"},
        {"host_id": "lnx-01", "os": "linux"}
    ]
    
    engine = overseer.create_mission(mission_id, "baseline-lab", hosts)
    
    # Start agents in background threads
    win_agent = WindowsAgent(task_queue, event_bus)
    linux_agent = LinuxAgent(task_queue, event_bus)
    
    agent_threads = [
        threading.Thread(target=win_agent.run_forever, daemon=True),
        threading.Thread(target=linux_agent.run_forever, daemon=True),
    ]
    
    for t in agent_threads:
        t.start()
    
    # Start mission engine event loop in background
    engine_thread = threading.Thread(
        target=engine.run_event_loop, 
        daemon=True
    )
    engine_thread.start()
    
    # Monitor for 10 seconds
    for i in range(10):
        time.sleep(1)
        status = overseer.get_mission_status(mission_id)
        print(f"\n--- Status at t+{i+1}s ---")
        print(f"Pending: {status['pending_tasks']}, Completed: {status['completed_tasks']}")
        for hid, hstate in status['hosts'].items():
            print(f"  {hid}: {hstate['status']} (failures: {hstate['failure_count']})")
    
    print("\n" + "=" * 60)
    print("Demo complete. In production, this would run indefinitely.")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

## Phase 7: What to Ask Your Coding Agent

Give your LLM coding agent (Cursor, etc.) this prompt:

```
Create a Python project implementing the Reaper System architecture:

1. Set up the directory structure exactly as shown in Phase 1.1
2. Implement all dataclasses in reaper/models.py (Phase 1.2)
3. Implement InMemoryTaskQueue, InMemoryEventBus, InMemoryMissionStore (Phase 2)
4. Implement SimpleRuleBasedPlanner (Phase 3.1)
5. Implement MissionEngine with start_mission, process_result, run_event_loop (Phase 3.2)
6. Implement BaseAgent and WindowsAgent stub (Phase 4)
7. Create LinuxAgent following the same pattern as WindowsAgent
8. Implement OverseerService (Phase 5)
9. Create main.py demo script (Phase 6)
10. Add requirements.txt with: python-dateutil

Run the demo and verify:
- Overseer creates mission
- Agents consume tasks in parallel
- MissionEngine processes results and schedules follow-up tasks
- All hosts move from "unknown" → "healthy" status
```

## Next Steps After Basic Implementation

Once the skeleton works:

### 7.1 Add Real WinRM/SSH Execution
Replace stub agents with actual remote execution:
- Install `pywinrm` for Windows
- Install `paramiko` for Linux/Mac SSH
- Implement real PowerShell/shell command execution

### 7.2 Add LLM-Based Planning
Replace `SimpleRuleBasedPlanner` with `LLMPlanner` that:
- Calls Claude/GPT to analyze host facts
- Generates next tasks based on desired state
- Handles errors by asking LLM for recovery steps

### 7.3 Add Persistence
Replace in-memory implementations with:
- Redis/RabbitMQ for task queue
- Kafka/Redis Streams for event bus
- PostgreSQL for mission store

### 7.4 Add Monitoring
- Real logging with structured logs
- Metrics/dashboards for mission progress
- Alerts when hosts are locked or missions stall

### 7.5 Scale Horizontally
- Run multiple agent workers (N × reaper-win, etc.)
- Deploy mission engines as separate services
- Add load balancing and retry logic
"""
Engine module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
from typing import List, Optional
from datetime import datetime, timezone
import logging

from glassdome.reaper.task_queue import TaskQueue
from glassdome.reaper.event_bus import EventBus
from glassdome.reaper.mission_store import MissionStore
from glassdome.reaper.planner import MissionPlanner
from glassdome.reaper.models import MissionState, Task, ResultEvent

logger = logging.getLogger(__name__)


class MissionEngine:
    """
    Event-driven mission controller (one instance per lab deployment)
    
    Responsibilities:
    - Initialize mission and schedule initial tasks
    - Listen for task result events
    - Update mission state based on results
    - Ask planner for next steps
    - Schedule new tasks without blocking
    - Handle failures and host locking
    """
    
    def __init__(
        self,
        mission_id: str,
        mission_store: MissionStore,
        task_queue: TaskQueue,
        event_bus: EventBus,
        planner: MissionPlanner
    ):
        """
        Initialize mission engine
        
        Args:
            mission_id: Unique mission identifier
            mission_store: State persistence layer
            task_queue: Task distribution queue
            event_bus: Result event distribution bus
            planner: Mission planning strategy
        """
        self.mission_id = mission_id
        self.store = mission_store
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.planner = planner
        self._running = False
        self._event_loop_task = None
        
        logger.info(f"MissionEngine initialized for {mission_id}")
    
    def start_mission(self, initial_state: MissionState) -> None:
        """
        Initialize and kick off the mission
        
        Args:
            initial_state: Initial mission state with hosts to target
        """
        logger.info(f"\n[MissionEngine] Starting mission {self.mission_id}")
        logger.info(f"  Lab ID: {initial_state.lab_id}")
        logger.info(f"  Type: {initial_state.mission_type}")
        logger.info(f"  Hosts: {len(initial_state.hosts)}")
        
        # Update status
        initial_state.status = "running"
        initial_state.updated_at = datetime.now(timezone.utc).isoformat() + "Z"
        
        # Save initial state
        self.store.save(initial_state)
        
        # Generate initial tasks
        initial_tasks = self.planner.initial_tasks(initial_state)
        logger.info(f"[MissionEngine] Generated {len(initial_tasks)} initial tasks")
        
        # Schedule tasks
        self._schedule_tasks(initial_tasks)
        
        logger.info(f"[MissionEngine] Mission {self.mission_id} started successfully")
    
    def _schedule_tasks(self, tasks: List[Task]) -> None:
        """
        Fire-and-forget: enqueue tasks without blocking
        
        Args:
            tasks: Tasks to schedule
        """
        if not tasks:
            return
        
        mission = self.store.load(self.mission_id)
        if not mission:
            logger.error(f"Cannot schedule tasks: mission {self.mission_id} not found")
            return
        
        for task in tasks:
            # Add to pending list
            mission.pending_tasks.append(task.task_id)
            
            # Publish to task queue
            self.task_queue.publish(task)
            
            logger.info(
                f"[MissionEngine] Scheduled task {task.task_id} "
                f"for {task.host_id} (action: {task.action})"
            )
        
        # Update mission timestamp
        mission.updated_at = datetime.now(timezone.utc).isoformat() + "Z"
        self.store.save(mission)
    
    def process_result(self, event: ResultEvent) -> None:
        """
        React to a single result event:
        1. Update mission state
        2. Update host state
        3. Ask planner for next steps
        4. Schedule new tasks
        
        Args:
            event: Task result event
        """
        mission = self.store.load(self.mission_id)
        if not mission:
            logger.error(f"Cannot process result: mission {self.mission_id} not found")
            return
        
        logger.info(f"\n[MissionEngine] Processing result for {event.task_id}")
        logger.info(f"  Host: {event.host_id}")
        logger.info(f"  Action: {event.action}")
        logger.info(f"  Status: {event.status}")
        logger.info(f"  Summary: {event.summary}")
        
        # Update host state
        host = mission.hosts.get(event.host_id)
        if host:
            # Track task
            host.last_tasks.append(event.task_id)
            
            # Update status
            if event.status == "success":
                host.last_status = "healthy"
                host.failure_count = 0  # Reset on success
                
                # Store discovered facts
                if event.data:
                    host.facts.update(event.data)
                
                # Track injected vulnerabilities
                if event.action.endswith(".inject_vuln") or event.action.endswith(".baseline"):
                    vuln_names = event.data.get("vulnerabilities_injected", [])
                    host.vulnerabilities_injected.extend(vuln_names)
                    logger.info(f"  Vulnerabilities injected: {vuln_names}")
            
            elif event.status == "error":
                host.last_status = "degraded"
                host.failure_count += 1
                
                # Lock host if too many failures
                if host.failure_count >= host.max_failures:
                    host.locked = True
                    logger.warning(
                        f"[MissionEngine] Host {event.host_id} locked due to "
                        f"{host.failure_count} failures"
                    )
            
            elif event.status == "partial":
                host.last_status = "degraded"
        
        # Update task tracking
        if event.task_id in mission.pending_tasks:
            mission.pending_tasks.remove(event.task_id)
        
        if event.status == "success":
            mission.completed_tasks.append(event.task_id)
        elif event.status == "error":
            mission.failed_tasks.append(event.task_id)
        
        # Update timestamp
        mission.updated_at = event.ts
        
        # Save updated state
        self.store.save(mission)
        
        # Check if mission is complete
        if self._is_mission_complete(mission):
            logger.info(f"[MissionEngine] Mission {self.mission_id} completed!")
            mission.status = "completed"
            self.store.save(mission)
            self.stop()
            return
        
        # Decide next steps
        next_tasks = self.planner.next_tasks(mission, last_result=event)
        
        if next_tasks:
            logger.info(f"[MissionEngine] Scheduling {len(next_tasks)} new tasks")
            self._schedule_tasks(next_tasks)
        else:
            logger.info(f"[MissionEngine] No new tasks to schedule")
    
    def _is_mission_complete(self, mission: MissionState) -> bool:
        """
        Check if mission is complete
        
        A mission is complete when:
        - No pending tasks
        - All healthy hosts have vulnerabilities injected
        - All other hosts are locked
        
        Args:
            mission: Mission state
            
        Returns:
            True if mission is complete
        """
        # Still have pending tasks
        if mission.pending_tasks:
            return False
        
        # Check each host
        for host in mission.hosts.values():
            # If host is locked, skip it
            if host.locked:
                continue
            
            # If host is healthy but has no vulnerabilities injected, mission not complete
            if host.last_status == "healthy" and not host.vulnerabilities_injected:
                return False
        
        return True
    
    async     def run_event_loop_sync(self) -> None:
        """
        Blocking loop: listen for results and process them.
        This should run in a background thread (not asyncio task).
        """
        logger.info(f"[MissionEngine] Starting event loop for {self.mission_id}")
        self._running = True
        
        try:
            for event in self.event_bus.subscribe_results(self.mission_id):
                if not self._running:
                    logger.info(f"[MissionEngine] Event loop stopped for {self.mission_id}")
                    break
                
                self.process_result(event)
        except Exception as e:
            logger.error(f"[MissionEngine] Event loop error: {e}", exc_info=True)
            self._running = False
    
    async def run_event_loop(self) -> None:
        """
        Async version for compatibility with asyncio-based code
        """
        import threading
        thread = threading.Thread(target=self.run_event_loop_sync, daemon=True)
        thread.start()
        
        # Wait for thread to finish or until stopped
        while self._running and thread.is_alive():
            await asyncio.sleep(0.1)
    
    def start_event_loop_background(self) -> None:
        """Start event loop in background thread"""
        if self._event_loop_task:
            logger.warning(f"Event loop already running for {self.mission_id}")
            return
        
        import threading
        self._event_loop_task = threading.Thread(
            target=self.run_event_loop_sync,
            daemon=True,
            name=f"MissionEngine-{self.mission_id}"
        )
        self._event_loop_task.start()
        logger.info(f"[MissionEngine] Event loop started in background for {self.mission_id}")
    
    def stop(self) -> None:
        """Stop the mission engine"""
        logger.info(f"[MissionEngine] Stopping mission {self.mission_id}")
        self._running = False
        
        if self._event_loop_task and not self._event_loop_task.done():
            self._event_loop_task.cancel()
    
    def get_status(self) -> dict:
        """
        Get current mission status
        
        Returns:
            Mission status dictionary
        """
        mission = self.store.load(self.mission_id)
        if not mission:
            return {"error": "Mission not found"}
        
        return mission.get_summary()
    
    def get_detailed_status(self) -> dict:
        """
        Get detailed mission status including host states
        
        Returns:
            Detailed mission status dictionary
        """
        mission = self.store.load(self.mission_id)
        if not mission:
            return {"error": "Mission not found"}
        
        return mission.to_dict()


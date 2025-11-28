"""
Task Queue module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Iterator
from collections import deque
from threading import Lock
import time
import logging

from glassdome.reaper.models import Task

logger = logging.getLogger(__name__)


class TaskQueue(ABC):
    """Abstract base class for task queue implementations"""
    
    @abstractmethod
    def publish(self, task: Task) -> None:
        """
        Publish a task for agents to consume
        
        Args:
            task: Task to publish
        """
        pass
    
    @abstractmethod
    def consume(self, agent_type: str) -> Iterator[Task]:
        """
        Yield tasks for this agent type (blocking/polling)
        
        Args:
            agent_type: Agent type to consume tasks for (e.g., "reaper-linux")
            
        Yields:
            Tasks for the agent to execute
        """
        pass
    
    @abstractmethod
    def get_queue_depth(self, agent_type: str) -> int:
        """
        Get number of pending tasks for an agent type
        
        Args:
            agent_type: Agent type to check
            
        Returns:
            Number of pending tasks
        """
        pass


class InMemoryTaskQueue(TaskQueue):
    """
    Simple in-memory queue for testing and single-process deployments
    
    Uses thread-safe deques to distribute tasks to agents.
    Agents poll the queue every 0.1s for new work.
    """
    
    def __init__(self):
        """Initialize in-memory task queue"""
        self._queues: dict[str, deque] = {}
        self._lock = Lock()
        logger.info("InMemoryTaskQueue initialized")
    
    def publish(self, task: Task) -> None:
        """
        Publish a task to the appropriate agent queue
        
        Args:
            task: Task to publish
        """
        with self._lock:
            if task.agent_type not in self._queues:
                self._queues[task.agent_type] = deque()
            self._queues[task.agent_type].append(task)
            logger.info(f"[TaskQueue] Published {task.task_id} for {task.agent_type} (action: {task.action})")
    
    def consume(self, agent_type: str) -> Iterator[Task]:
        """
        Poll for tasks every 0.1s
        
        This is a blocking generator that yields tasks as they become available.
        
        Args:
            agent_type: Agent type to consume tasks for
            
        Yields:
            Tasks for the agent to execute
        """
        logger.info(f"[TaskQueue] {agent_type} consumer started")
        
        while True:
            with self._lock:
                if agent_type in self._queues and self._queues[agent_type]:
                    task = self._queues[agent_type].popleft()
                    logger.info(f"[TaskQueue] {agent_type} consumed {task.task_id}")
                    yield task
            
            time.sleep(0.1)  # polling interval
    
    def get_queue_depth(self, agent_type: str) -> int:
        """
        Get number of pending tasks for an agent type
        
        Args:
            agent_type: Agent type to check
            
        Returns:
            Number of pending tasks
        """
        with self._lock:
            if agent_type not in self._queues:
                return 0
            return len(self._queues[agent_type])
    
    def get_all_queue_depths(self) -> dict[str, int]:
        """
        Get pending task counts for all agent types
        
        Returns:
            Dictionary mapping agent_type to queue depth
        """
        with self._lock:
            return {agent_type: len(queue) for agent_type, queue in self._queues.items()}


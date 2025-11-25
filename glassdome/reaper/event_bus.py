"""
Reaper Event Bus

Distributes task result events to MissionEngines for processing.
In-memory implementation for Phase 1 (can be replaced with Kafka/Redis Streams later).
"""

from abc import ABC, abstractmethod
from typing import Iterator
from collections import deque
from threading import Lock
import time
import logging

from glassdome.reaper.models import ResultEvent

logger = logging.getLogger(__name__)


class EventBus(ABC):
    """Abstract base class for event bus implementations"""
    
    @abstractmethod
    def publish_result(self, event: ResultEvent) -> None:
        """
        Publish a result event
        
        Args:
            event: Result event to publish
        """
        pass
    
    @abstractmethod
    def subscribe_results(self, mission_id: str) -> Iterator[ResultEvent]:
        """
        Yield result events for this mission (blocking/polling)
        
        Args:
            mission_id: Mission ID to subscribe to
            
        Yields:
            Result events for the mission
        """
        pass
    
    @abstractmethod
    def get_pending_count(self, mission_id: str) -> int:
        """
        Get number of pending events for a mission
        
        Args:
            mission_id: Mission ID to check
            
        Returns:
            Number of pending events
        """
        pass


class InMemoryEventBus(EventBus):
    """
    Simple in-memory event bus for testing and single-process deployments
    
    Uses thread-safe deques to route events to mission engines.
    Mission engines poll the bus every 0.1s for new events.
    """
    
    def __init__(self):
        """Initialize in-memory event bus"""
        self._events: dict[str, deque] = {}
        self._lock = Lock()
        logger.info("InMemoryEventBus initialized")
    
    def publish_result(self, event: ResultEvent) -> None:
        """
        Publish a result event to the appropriate mission queue
        
        Args:
            event: Result event to publish
        """
        with self._lock:
            if event.mission_id not in self._events:
                self._events[event.mission_id] = deque()
            self._events[event.mission_id].append(event)
            logger.info(
                f"[EventBus] Published result for {event.task_id} "
                f"(mission: {event.mission_id}, status: {event.status})"
            )
    
    def subscribe_results(self, mission_id: str) -> Iterator[ResultEvent]:
        """
        Poll for events every 0.1s
        
        This is a blocking generator that yields events as they become available.
        
        Args:
            mission_id: Mission ID to subscribe to
            
        Yields:
            Result events for the mission
        """
        logger.info(f"[EventBus] Mission {mission_id} subscribed to result events")
        
        while True:
            with self._lock:
                if mission_id in self._events and self._events[mission_id]:
                    event = self._events[mission_id].popleft()
                    logger.info(f"[EventBus] Mission {mission_id} received result for {event.task_id}")
                    yield event
            
            time.sleep(0.1)  # polling interval
    
    def get_pending_count(self, mission_id: str) -> int:
        """
        Get number of pending events for a mission
        
        Args:
            mission_id: Mission ID to check
            
        Returns:
            Number of pending events
        """
        with self._lock:
            if mission_id not in self._events:
                return 0
            return len(self._events[mission_id])
    
    def get_all_pending_counts(self) -> dict[str, int]:
        """
        Get pending event counts for all missions
        
        Returns:
            Dictionary mapping mission_id to pending event count
        """
        with self._lock:
            return {mission_id: len(events) for mission_id, events in self._events.items()}


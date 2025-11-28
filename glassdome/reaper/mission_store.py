"""
Mission Store module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Optional
from threading import Lock
import logging

from glassdome.reaper.models import MissionState

logger = logging.getLogger(__name__)


class MissionStore(ABC):
    """Abstract base class for mission store implementations"""
    
    @abstractmethod
    def load(self, mission_id: str) -> Optional[MissionState]:
        """
        Load mission state
        
        Args:
            mission_id: Mission ID to load
            
        Returns:
            Mission state, or None if not found
        """
        pass
    
    @abstractmethod
    def save(self, mission: MissionState) -> None:
        """
        Save mission state
        
        Args:
            mission: Mission state to save
        """
        pass
    
    @abstractmethod
    def delete(self, mission_id: str) -> bool:
        """
        Delete mission state
        
        Args:
            mission_id: Mission ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def list_missions(self) -> list[str]:
        """
        List all mission IDs
        
        Returns:
            List of mission IDs
        """
        pass


class InMemoryMissionStore(MissionStore):
    """
    Simple in-memory store for testing and single-process deployments
    
    Stores mission state in memory with thread-safe access.
    State is lost on restart (will add JSON file persistence later).
    """
    
    def __init__(self):
        """Initialize in-memory mission store"""
        self._store: dict[str, MissionState] = {}
        self._lock = Lock()
        logger.info("InMemoryMissionStore initialized")
    
    def load(self, mission_id: str) -> Optional[MissionState]:
        """
        Load mission state from memory
        
        Args:
            mission_id: Mission ID to load
            
        Returns:
            Mission state, or None if not found
        """
        with self._lock:
            mission = self._store.get(mission_id)
            if mission:
                logger.debug(f"[MissionStore] Loaded state for {mission_id}")
            else:
                logger.warning(f"[MissionStore] Mission {mission_id} not found")
            return mission
    
    def save(self, mission: MissionState) -> None:
        """
        Save mission state to memory
        
        Args:
            mission: Mission state to save
        """
        with self._lock:
            self._store[mission.mission_id] = mission
            logger.info(
                f"[MissionStore] Saved state for {mission.mission_id} "
                f"(status: {mission.status}, pending: {len(mission.pending_tasks)}, "
                f"completed: {len(mission.completed_tasks)})"
            )
    
    def delete(self, mission_id: str) -> bool:
        """
        Delete mission state from memory
        
        Args:
            mission_id: Mission ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if mission_id in self._store:
                del self._store[mission_id]
                logger.info(f"[MissionStore] Deleted state for {mission_id}")
                return True
            else:
                logger.warning(f"[MissionStore] Cannot delete {mission_id}, not found")
                return False
    
    def list_missions(self) -> list[str]:
        """
        List all mission IDs in store
        
        Returns:
            List of mission IDs
        """
        with self._lock:
            return list(self._store.keys())
    
    def get_all_summaries(self) -> dict[str, dict]:
        """
        Get summaries for all missions
        
        Returns:
            Dictionary mapping mission_id to summary
        """
        with self._lock:
            return {mission_id: mission.get_summary() for mission_id, mission in self._store.items()}


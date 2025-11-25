"""
Base Reaper Agent

Abstract base class for all OS-specific Reaper agents.
"""

from abc import ABC, abstractmethod
import logging

from glassdome.reaper.task_queue import TaskQueue
from glassdome.reaper.event_bus import EventBus
from glassdome.reaper.models import Task, ResultEvent

logger = logging.getLogger(__name__)


class BaseReaperAgent(ABC):
    """
    Base class for all OS-specific Reaper agents
    
    Responsibilities:
    - Consume tasks from queue
    - Execute tasks on target VMs
    - Publish result events
    - Handle errors gracefully
    """
    
    def __init__(self, agent_type: str, task_queue: TaskQueue, event_bus: EventBus):
        """
        Initialize Reaper agent
        
        Args:
            agent_type: Agent type identifier (e.g., "reaper-linux")
            task_queue: Task queue to consume from
            event_bus: Event bus to publish results to
        """
        self.agent_type = agent_type
        self.task_queue = task_queue
        self.event_bus = event_bus
        
        logger.info(f"{agent_type} initialized")
    
    def run_forever(self) -> None:
        """
        Main worker loop: consume tasks, execute, emit results
        
        This is a blocking loop that runs indefinitely.
        Typically run in a background thread.
        """
        logger.info(f"[{self.agent_type}] Starting worker loop")
        
        try:
            for task in self.task_queue.consume(self.agent_type):
                logger.info(f"[{self.agent_type}] Handling {task.task_id}: {task.action}")
                
                try:
                    event = self.handle_task(task)
                    self.event_bus.publish_result(event)
                except Exception as e:
                    logger.error(
                        f"[{self.agent_type}] Failed to handle task {task.task_id}: {e}",
                        exc_info=True
                    )
                    # Publish error event
                    error_event = ResultEvent(
                        task_id=task.task_id,
                        mission_id=task.mission_id,
                        host_id=task.host_id,
                        agent_type=self.agent_type,
                        action=task.action,
                        status="error",
                        summary=f"Agent exception: {str(e)}",
                        error_code="AGENT_EXCEPTION",
                        retriable=True
                    )
                    self.event_bus.publish_result(error_event)
        except KeyboardInterrupt:
            logger.info(f"[{self.agent_type}] Worker loop interrupted")
        except Exception as e:
            logger.error(f"[{self.agent_type}] Worker loop error: {e}", exc_info=True)
    
    @abstractmethod
    def handle_task(self, task: Task) -> ResultEvent:
        """
        Execute a task and return a result event
        
        This method must be implemented by OS-specific agents.
        
        Args:
            task: Task to execute
            
        Returns:
            Result event with execution details
        """
        pass
    
    def _create_success_event(
        self, 
        task: Task, 
        summary: str, 
        data: dict = None,
        stdout: str = "",
        stderr: str = ""
    ) -> ResultEvent:
        """
        Helper to create a success result event
        
        Args:
            task: Originating task
            summary: Human-readable summary
            data: Optional data dictionary
            stdout: Optional stdout
            stderr: Optional stderr
            
        Returns:
            Success result event
        """
        return ResultEvent(
            task_id=task.task_id,
            mission_id=task.mission_id,
            host_id=task.host_id,
            agent_type=self.agent_type,
            action=task.action,
            status="success",
            summary=summary,
            data=data or {},
            stdout_tail=stdout[-500:] if stdout else "",
            stderr_tail=stderr[-500:] if stderr else ""
        )
    
    def _create_error_event(
        self, 
        task: Task, 
        summary: str, 
        error_code: str = None,
        retriable: bool = False,
        stdout: str = "",
        stderr: str = ""
    ) -> ResultEvent:
        """
        Helper to create an error result event
        
        Args:
            task: Originating task
            summary: Human-readable error description
            error_code: Optional error code
            retriable: Whether the task can be retried
            stdout: Optional stdout
            stderr: Optional stderr
            
        Returns:
            Error result event
        """
        return ResultEvent(
            task_id=task.task_id,
            mission_id=task.mission_id,
            host_id=task.host_id,
            agent_type=self.agent_type,
            action=task.action,
            status="error",
            summary=summary,
            error_code=error_code,
            retriable=retriable,
            stdout_tail=stdout[-500:] if stdout else "",
            stderr_tail=stderr[-500:] if stderr else ""
        )


"""
Engine module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import asyncio
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OrchestrationTask:
    """Represents a single task in the orchestration"""
    
    def __init__(self, task_id: str, task_def: Dict[str, Any],
                 dependencies: Optional[List[str]] = None):
        self.task_id = task_id
        self.task_def = task_def
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None


class OrchestrationEngine:
    """
    Orchestration engine for managing complex deployments
    
    Features:
    - Dependency resolution
    - Parallel execution
    - Failure handling and rollback
    - Progress tracking
    """
    
    def __init__(self):
        self.tasks: Dict[str, OrchestrationTask] = {}
        self.task_graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()
    
    def add_task(self, task_id: str, task_def: Dict[str, Any],
                 dependencies: Optional[List[str]] = None) -> None:
        """
        Add a task to the orchestration
        
        Args:
            task_id: Unique task identifier
            task_def: Task definition
            dependencies: List of task IDs this task depends on
        """
        task = OrchestrationTask(task_id, task_def, dependencies)
        self.tasks[task_id] = task
        
        # Build dependency graph
        if dependencies:
            for dep_id in dependencies:
                self.task_graph[dep_id].append(task_id)
                self.reverse_graph[task_id].append(dep_id)
        
        logger.info(f"Task {task_id} added with {len(dependencies or [])} dependencies")
    
    def get_ready_tasks(self) -> List[str]:
        """
        Get tasks that are ready to execute
        (all dependencies completed, not yet started)
        """
        ready = []
        
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_completed = all(
                dep_id in self.completed_tasks
                for dep_id in task.dependencies
            )
            
            if deps_completed:
                ready.append(task_id)
                task.status = TaskStatus.READY
        
        return ready
    
    async def execute_task(self, task_id: str,
                          executor_func: callable) -> Dict[str, Any]:
        """
        Execute a single task
        
        Args:
            task_id: Task ID to execute
            executor_func: Async function to execute the task
            
        Returns:
            Task result
        """
        task = self.tasks[task_id]
        
        try:
            task.status = TaskStatus.RUNNING
            self.running_tasks.add(task_id)
            
            logger.info(f"Executing task {task_id}")
            result = await executor_func(task.task_def)
            
            task.result = result
            
            if result.get("success"):
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.add(task_id)
                logger.info(f"Task {task_id} completed successfully")
            else:
                task.status = TaskStatus.FAILED
                task.error = result.get("error")
                self.failed_tasks.add(task_id)
                logger.error(f"Task {task_id} failed: {task.error}")
            
            self.running_tasks.remove(task_id)
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} failed with exception: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.failed_tasks.add(task_id)
            self.running_tasks.remove(task_id)
            
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }
    
    async def run(self, executor_func: callable,
                  max_parallel: int = 5,
                  fail_fast: bool = False) -> Dict[str, Any]:
        """
        Run the orchestration
        
        Args:
            executor_func: Async function to execute tasks
            max_parallel: Maximum number of parallel tasks
            fail_fast: Stop on first failure
            
        Returns:
            Orchestration results
        """
        logger.info(f"Starting orchestration with {len(self.tasks)} tasks")
        start_time = asyncio.get_event_loop().time()
        
        # Validate no circular dependencies
        if not self._validate_dag():
            return {
                "success": False,
                "error": "Circular dependencies detected"
            }
        
        # Execute tasks
        active_tasks = []
        
        while len(self.completed_tasks) + len(self.failed_tasks) < len(self.tasks):
            # Get ready tasks
            ready_tasks = self.get_ready_tasks()
            
            # Launch tasks up to max_parallel
            while ready_tasks and len(active_tasks) < max_parallel:
                task_id = ready_tasks.pop(0)
                task_coro = self.execute_task(task_id, executor_func)
                active_tasks.append(asyncio.create_task(task_coro))
            
            # Wait for at least one task to complete
            if active_tasks:
                done, pending = await asyncio.wait(
                    active_tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Check for failures
                if fail_fast and self.failed_tasks:
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                    break
                
                # Update active tasks
                active_tasks = list(pending)
            else:
                # No active or ready tasks - check if we're stuck
                if not self.completed_tasks and not self.failed_tasks:
                    logger.error("No tasks can be executed - dependency issue")
                    break
                await asyncio.sleep(0.1)
        
        # Cancel any remaining tasks if fail_fast
        for task in active_tasks:
            if not task.done():
                task.cancel()
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Generate results
        results = {
            "success": len(self.failed_tasks) == 0,
            "total_tasks": len(self.tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "duration_seconds": duration,
            "tasks": {
                task_id: {
                    "status": task.status.value,
                    "result": task.result,
                    "error": task.error
                }
                for task_id, task in self.tasks.items()
            }
        }
        
        logger.info(
            f"Orchestration completed: {results['completed']}/{results['total_tasks']} "
            f"tasks successful in {duration:.2f}s"
        )
        
        return results
    
    def _validate_dag(self) -> bool:
        """Validate that the task graph is a directed acyclic graph (no cycles)"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            for neighbor in self.task_graph.get(task_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    logger.error(f"Circular dependency detected involving task {task_id}")
                    return False
        
        return True
    
    def get_execution_plan(self) -> List[List[str]]:
        """
        Get the execution plan as layers of tasks
        Each layer can be executed in parallel
        """
        if not self._validate_dag():
            return []
        
        # Topological sort to get execution order
        in_degree = {task_id: len(self.reverse_graph.get(task_id, []))
                    for task_id in self.tasks}
        
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        layers = []
        
        while queue:
            layer = list(queue)
            layers.append(layer)
            
            next_queue = deque()
            for task_id in layer:
                for dependent in self.task_graph.get(task_id, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            
            queue = next_queue
        
        return layers
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current orchestration progress"""
        total = len(self.tasks)
        completed = len(self.completed_tasks)
        failed = len(self.failed_tasks)
        running = len(self.running_tasks)
        pending = total - completed - failed - running
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "percentage": int((completed + failed) / total * 100) if total > 0 else 0
        }


"""
Agent Manager - Coordinates all agents
"""
from typing import Dict, List, Any, Optional
from glassdome.agents.base import BaseAgent, AgentType, AgentStatus
import logging
import asyncio

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Central manager for all autonomous agents
    Handles agent lifecycle, task distribution, and coordination
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent"""
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.agent_type})")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """Get all agents of a specific type"""
        return [
            agent for agent in self.agents.values()
            if agent.agent_type == agent_type
        ]
    
    async def submit_task(self, task: Dict[str, Any]) -> str:
        """
        Submit a task for agent execution
        
        Args:
            task: Task definition
            
        Returns:
            Task ID
        """
        task_id = f"task_{len(self.task_queue.qsize())}"
        task["task_id"] = task_id
        await self.task_queue.put(task)
        logger.info(f"Task {task_id} submitted to queue")
        return task_id
    
    async def assign_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Assign task to appropriate agent and execute
        
        Args:
            task: Task definition
            
        Returns:
            Execution result
        """
        agent_type = task.get("agent_type", AgentType.DEPLOYMENT)
        
        # Find available agent of the requested type
        available_agents = [
            agent for agent in self.get_agents_by_type(agent_type)
            if agent.status in [AgentStatus.IDLE, AgentStatus.COMPLETED]
        ]
        
        if not available_agents:
            logger.warning(f"No available agents for type {agent_type}")
            return None
        
        # Select first available agent (could implement load balancing here)
        agent = available_agents[0]
        
        logger.info(f"Assigning task {task.get('task_id')} to agent {agent.agent_id}")
        result = await agent.run(task)
        
        return result
    
    async def start(self) -> None:
        """Start the agent manager task processor"""
        self.running = True
        logger.info("Agent Manager started")
        
        while self.running:
            try:
                # Get task from queue (with timeout to allow checking running flag)
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Assign and execute task
                result = await self.assign_task(task)
                
                if result:
                    logger.info(f"Task {task.get('task_id')} completed: {result.get('success')}")
                else:
                    logger.error(f"Task {task.get('task_id')} could not be assigned")
                
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
    
    async def stop(self) -> None:
        """Stop the agent manager"""
        self.running = False
        logger.info("Agent Manager stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "total_agents": len(self.agents),
            "agents": {
                agent_id: {
                    "type": agent.agent_type.value,
                    "status": agent.status.value,
                    "error": agent.error
                }
                for agent_id, agent in self.agents.items()
            },
            "queue_size": self.task_queue.qsize(),
            "running": self.running
        }


# Global agent manager instance
agent_manager = AgentManager()


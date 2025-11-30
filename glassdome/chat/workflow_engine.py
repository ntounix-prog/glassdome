"""
Workflow Engine module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    COLLECTING_DATA = "collecting_data"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Individual step status"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    step_id: str
    name: str
    description: str
    required_data: List[str]  # Data fields needed for this step
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Workflow:
    """
    Represents a multi-step operation workflow
    
    Used for complex operations like:
    - Lab deployment (collect specs → confirm → deploy VMs → inject vulns)
    - Reaper mission (select targets → configure → execute → report)
    """
    workflow_id: str
    workflow_type: str  # "deploy_lab", "create_mission", etc.
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    collected_data: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current active step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def get_missing_required_fields(self) -> List[str]:
        """Get list of required fields not yet collected"""
        return [f for f in self.required_fields if f not in self.collected_data]
    
    def is_data_complete(self) -> bool:
        """Check if all required data has been collected"""
        return len(self.get_missing_required_fields()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "status": s.status.value,
                }
                for s in self.steps
            ],
            "collected_data": self.collected_data,
            "missing_fields": self.get_missing_required_fields(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class WorkflowEngine:
    """
    Engine for managing workflow execution
    
    Responsibilities:
    - Create workflows from templates
    - Track data collection progress
    - Execute workflow steps
    - Handle errors and rollbacks
    """
    
    def __init__(self):
        """Initialize workflow engine"""
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_handlers: Dict[str, Callable[..., Awaitable[Dict[str, Any]]]] = {}
        logger.info("WorkflowEngine initialized")
    
    def register_handler(
        self,
        workflow_type: str,
        handler: Callable[..., Awaitable[Dict[str, Any]]]
    ):
        """
        Register a handler for a workflow type
        
        Args:
            workflow_type: Type of workflow (e.g., "deploy_lab")
            handler: Async function to execute the workflow
        """
        self.workflow_handlers[workflow_type] = handler
        logger.info(f"Registered handler for workflow type: {workflow_type}")
    
    def create_workflow(
        self,
        workflow_type: str,
        name: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Create a new workflow from a template
        
        Args:
            workflow_type: Type of workflow to create
            name: Human-readable name
            initial_data: Initial data to seed the workflow
            
        Returns:
            New Workflow instance
        """
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        
        # Get workflow template
        template = self._get_workflow_template(workflow_type)
        
        workflow = Workflow(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            name=name,
            description=template["description"],
            steps=[
                WorkflowStep(
                    step_id=f"step-{i}",
                    name=step["name"],
                    description=step["description"],
                    required_data=step.get("required_data", [])
                )
                for i, step in enumerate(template["steps"])
            ],
            required_fields=template["required_fields"],
            optional_fields=template.get("optional_fields", []),
            status=WorkflowStatus.COLLECTING_DATA
        )
        
        # Seed with initial data
        if initial_data:
            workflow.collected_data.update(initial_data)
        
        # Store workflow
        self.active_workflows[workflow_id] = workflow
        
        logger.info(f"Created workflow {workflow_id} of type {workflow_type}")
        return workflow
    
    def _get_workflow_template(self, workflow_type: str) -> Dict[str, Any]:
        """Get workflow template by type"""
        templates = {
            "deploy_lab": {
                "description": "Deploy a new lab environment with VMs and vulnerabilities",
                "required_fields": ["lab_name", "platform", "lab_type"],
                "optional_fields": ["vm_count", "vulnerabilities", "auto_inject_vulnerabilities"],
                "steps": [
                    {
                        "name": "Collect Requirements",
                        "description": "Gather lab specifications from operator",
                        "required_data": ["lab_name", "platform", "lab_type"]
                    },
                    {
                        "name": "Validate Configuration",
                        "description": "Validate lab configuration and resource availability",
                        "required_data": []
                    },
                    {
                        "name": "Confirm Deployment",
                        "description": "Present deployment plan and get operator confirmation",
                        "required_data": []
                    },
                    {
                        "name": "Deploy Infrastructure",
                        "description": "Create networks and deploy VMs",
                        "required_data": []
                    },
                    {
                        "name": "Inject Vulnerabilities",
                        "description": "Run Reaper mission to inject vulnerabilities",
                        "required_data": []
                    },
                    {
                        "name": "Finalize",
                        "description": "Verify deployment and provide access details",
                        "required_data": []
                    }
                ]
            },
            "create_mission": {
                "description": "Create a Reaper vulnerability injection mission",
                "required_fields": ["mission_name", "lab_id", "mission_type"],
                "optional_fields": ["target_hosts", "vulnerability_categories"],
                "steps": [
                    {
                        "name": "Collect Requirements",
                        "description": "Gather mission specifications",
                        "required_data": ["mission_name", "lab_id", "mission_type"]
                    },
                    {
                        "name": "Identify Targets",
                        "description": "Identify and validate target hosts",
                        "required_data": []
                    },
                    {
                        "name": "Confirm Mission",
                        "description": "Present mission plan and get confirmation",
                        "required_data": []
                    },
                    {
                        "name": "Execute Mission",
                        "description": "Start Reaper mission",
                        "required_data": []
                    },
                    {
                        "name": "Monitor Progress",
                        "description": "Monitor vulnerability injection progress",
                        "required_data": []
                    }
                ]
            },
            "query_status": {
                "description": "Query system or resource status",
                "required_fields": ["resource_type"],
                "optional_fields": ["resource_id", "include_details"],
                "steps": [
                    {
                        "name": "Execute Query",
                        "description": "Query the requested resource status",
                        "required_data": ["resource_type"]
                    }
                ]
            }
        }
        
        if workflow_type not in templates:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        return templates[workflow_type]
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get an active workflow by ID"""
        return self.active_workflows.get(workflow_id)
    
    def update_workflow_data(
        self,
        workflow_id: str,
        data: Dict[str, Any]
    ) -> Workflow:
        """
        Update collected data for a workflow
        
        Args:
            workflow_id: Workflow ID
            data: New data to merge
            
        Returns:
            Updated Workflow
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow.collected_data.update(data)
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Check if data collection is complete
        if workflow.is_data_complete() and workflow.status == WorkflowStatus.COLLECTING_DATA:
            workflow.status = WorkflowStatus.AWAITING_CONFIRMATION
        
        logger.info(f"Updated workflow {workflow_id} data: {list(data.keys())}")
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a workflow that has all required data
        
        Args:
            workflow_id: Workflow ID to execute
            
        Returns:
            Execution result
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if not workflow.is_data_complete():
            missing = workflow.get_missing_required_fields()
            raise ValueError(f"Workflow missing required data: {missing}")
        
        workflow.status = WorkflowStatus.EXECUTING
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Executing workflow {workflow_id}")
        
        try:
            # Get handler for this workflow type
            handler = self.workflow_handlers.get(workflow.workflow_type)
            
            if handler:
                result = await handler(workflow)
            else:
                # Default execution: step through each step
                result = await self._default_execute(workflow)
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.result = result
            workflow.updated_at = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            return result
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
            workflow.updated_at = datetime.now(timezone.utc).isoformat()
            
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise
    
    async def _default_execute(self, workflow: Workflow) -> Dict[str, Any]:
        """Default workflow execution - step through each step"""
        results = []
        
        for i, step in enumerate(workflow.steps):
            workflow.current_step_index = i
            step.status = StepStatus.ACTIVE
            step.started_at = datetime.now(timezone.utc).isoformat()
            
            try:
                # Mark step as completed (actual execution would happen here)
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now(timezone.utc).isoformat()
                step.result = {"success": True}
                results.append({"step": step.name, "status": "completed"})
                
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                step.completed_at = datetime.now(timezone.utc).isoformat()
                raise
        
        return {
            "workflow_id": workflow.workflow_id,
            "status": "completed",
            "steps": results,
            "data": workflow.collected_data
        }
    
    def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Cancel an active workflow
        
        Args:
            workflow_id: Workflow ID to cancel
            
        Returns:
            Cancellation result
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return {"success": False, "error": f"Workflow {workflow_id} not found"}
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Remove from active workflows
        del self.active_workflows[workflow_id]
        
        logger.info(f"Cancelled workflow {workflow_id}")
        return {"success": True, "workflow_id": workflow_id}
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return [wf.to_dict() for wf in self.active_workflows.values()]
    
    def get_data_collection_prompt(self, workflow: Workflow) -> str:
        """
        Generate a prompt for collecting missing data
        
        Args:
            workflow: Workflow needing data
            
        Returns:
            Prompt string for the operator
        """
        missing = workflow.get_missing_required_fields()
        
        if not missing:
            return "All required information has been collected."
        
        prompts = {
            "lab_name": "What would you like to name this lab?",
            "platform": "Which platform should I deploy to? (proxmox, aws, azure, esxi)",
            "lab_type": "What type of lab? (web-security, network-defense, active-directory, custom)",
            "vm_count": "How many VMs do you need?",
            "mission_name": "What would you like to name this mission?",
            "lab_id": "Which lab deployment should I target?",
            "mission_type": "What type of mission? (web-security-lab, network-defense-lab)",
            "resource_type": "What type of resource? (system, labs, deployments, missions, vms, hosts)"
        }
        
        questions = []
        for field in missing:
            if field in prompts:
                questions.append(f"- {prompts[field]}")
            else:
                questions.append(f"- Please provide: {field}")
        
        return "I need a bit more information:\n" + "\n".join(questions)


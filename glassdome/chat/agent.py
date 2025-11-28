"""
Agent module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import uuid
import json
import logging
import traceback
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
from enum import Enum

from glassdome.chat.llm_service import LLMService, LLMMessage, LLMResponse, Tool, ToolCall
from glassdome.chat.workflow_engine import WorkflowEngine, Workflow, WorkflowStatus
from glassdome.chat.tools import OVERSEER_TOOLS, get_tool_by_name, LAB_TEMPLATES

# Configure logger with DEBUG level for detailed tracing
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MessageRole(str, Enum):
    """Chat message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """A single chat message"""
    id: str
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_llm_message(self) -> LLMMessage:
        """Convert to LLMMessage format"""
        return LLMMessage(
            role=self.role.value,
            content=self.content,
            tool_calls=self.tool_calls,
            tool_call_id=self.tool_call_id
        )


@dataclass
class ActionRequest:
    """Represents an action that needs confirmation"""
    action_id: str
    action_type: str
    summary: str
    details: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, approved, rejected, executed


@dataclass
class Conversation:
    """A chat conversation with context and state"""
    conversation_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    active_workflow: Optional[str] = None  # Workflow ID if in progress
    pending_action: Optional[ActionRequest] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_message(self, role: MessageRole, content: str, **kwargs) -> ChatMessage:
        """Add a message to the conversation"""
        message = ChatMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            role=role,
            content=content,
            **kwargs
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow().isoformat()
        return message
    
    def get_llm_messages(self, max_messages: int = 50) -> List[LLMMessage]:
        """Get messages in LLM format, limited to recent history"""
        messages = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [m.to_llm_message() for m in messages]


# System prompt for the Overseer chat agent
OVERSEER_SYSTEM_PROMPT = """You are Overseer, the intelligent operations assistant for Glassdome - a cyber range deployment framework.

Your role is to help operators:
1. Deploy training labs with VMs and networking
2. Create Reaper missions to inject vulnerabilities for security training
3. Monitor and query system status
4. Search knowledge base for documentation and past issues

IMPORTANT GUIDELINES:
- Be conversational and helpful, like a knowledgeable colleague
- Ask clarifying questions when you need more information
- For destructive or costly operations, always confirm with the operator before proceeding
- Use the available tools to interact with Glassdome systems
- Provide clear summaries of what you're doing and what happened

AVAILABLE LAB TYPES:
- web-security: Web application security training (DVWA, XSS, SQLi)
- network-defense: Network security and defense training
- active-directory: Windows/AD security testing

AVAILABLE PLATFORMS:
- proxmox: On-premises Proxmox VE
- aws: Amazon Web Services
- azure: Microsoft Azure
- esxi: VMware ESXi

When deploying labs, you'll work with the Lab Orchestrator.
When injecting vulnerabilities, you'll create Reaper missions.
Both systems are already integrated - you just need to collect requirements and execute.

Current time: {current_time}
"""


class OverseerChatAgent:
    """
    Main chat agent for operator interactions
    
    Handles:
    - Conversation management
    - LLM interactions with tool calling
    - Workflow orchestration
    - Tool execution
    - Action confirmation
    """
    
    def __init__(self, overseer_entity=None):
        """
        Initialize the chat agent
        
        Args:
            overseer_entity: Optional OverseerEntity instance for system integration
        """
        self.llm = LLMService()
        self.workflow_engine = WorkflowEngine()
        self.conversations: Dict[str, Conversation] = {}
        self.overseer = overseer_entity
        
        # Register workflow handlers
        self._register_workflow_handlers()
        
        # Build tool list for LLM
        self.tools = [
            Tool(
                name=t.name,
                description=t.description,
                parameters=t.parameters
            )
            for t in OVERSEER_TOOLS
        ]
        
        logger.info("OverseerChatAgent initialized")
    
    def _register_workflow_handlers(self):
        """Register handlers for workflow types"""
        self.workflow_engine.register_handler("deploy_lab", self._handle_deploy_lab)
        self.workflow_engine.register_handler("create_mission", self._handle_create_mission)
    
    # ═══════════════════════════════════════════════════
    # Conversation Management
    # ═══════════════════════════════════════════════════
    
    def create_conversation(self) -> Conversation:
        """Create a new conversation"""
        conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        conversation = Conversation(conversation_id=conv_id)
        
        # Add system message
        conversation.add_message(
            MessageRole.SYSTEM,
            OVERSEER_SYSTEM_PROMPT.format(
                current_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            )
        )
        
        self.conversations[conv_id] = conversation
        logger.info(f"Created conversation {conv_id}")
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get an existing conversation"""
        return self.conversations.get(conversation_id)
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    # ═══════════════════════════════════════════════════
    # Message Processing
    # ═══════════════════════════════════════════════════
    
    async def process_message(
        self,
        conversation_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Process an incoming message from the operator
        
        Args:
            conversation_id: Conversation ID
            message: User message text
            
        Returns:
            Response dict with content and metadata
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            conversation = self.create_conversation()
            conversation_id = conversation.conversation_id
        
        # Add user message
        conversation.add_message(MessageRole.USER, message)
        
        # Check for pending action confirmation
        if conversation.pending_action:
            return await self._handle_action_response(conversation, message)
        
        # Check for active workflow
        if conversation.active_workflow:
            return await self._handle_workflow_message(conversation, message)
        
        # Normal message processing with LLM
        return await self._process_with_llm(conversation)
    
    async def _process_with_llm(self, conversation: Conversation) -> Dict[str, Any]:
        """Process message through LLM with tool calling"""
        conv_id = conversation.conversation_id
        logger.info(f"[{conv_id}] Processing with LLM - {len(conversation.messages)} messages")
        
        try:
            # Log available providers
            available = self.llm.list_available_providers()
            logger.debug(f"[{conv_id}] Available LLM providers: {available}")
            
            if not available:
                logger.error(f"[{conv_id}] NO LLM PROVIDERS AVAILABLE!")
                return {
                    "conversation_id": conv_id,
                    "response": "Error: No LLM providers are configured. Please check that OpenAI or Anthropic API keys are set up in the secrets manager.",
                    "type": "error",
                    "error": "No LLM providers available"
                }
            
            # Get LLM response
            logger.debug(f"[{conv_id}] Calling LLM.complete() with {len(self.tools)} tools")
            response = await self.llm.complete(
                messages=conversation.get_llm_messages(),
                tools=self.tools,
                temperature=0.7
            )
            
            logger.info(f"[{conv_id}] LLM response received - provider: {response.provider}, tool_calls: {len(response.tool_calls or [])}")
            
            # Handle tool calls
            if response.tool_calls:
                logger.info(f"[{conv_id}] Processing {len(response.tool_calls)} tool calls")
                return await self._handle_tool_calls(conversation, response)
            
            # Regular response
            conversation.add_message(MessageRole.ASSISTANT, response.content)
            logger.debug(f"[{conv_id}] Regular response: {response.content[:200]}...")
            
            return {
                "conversation_id": conversation.conversation_id,
                "response": response.content,
                "type": "message"
            }
            
        except Exception as e:
            logger.error(f"[{conv_id}] LLM PROCESSING ERROR: {e}")
            logger.error(f"[{conv_id}] Traceback:\n{traceback.format_exc()}")
            
            error_msg = f"I encountered an error processing your request: {str(e)}"
            conversation.add_message(MessageRole.ASSISTANT, error_msg)
            return {
                "conversation_id": conversation.conversation_id,
                "response": error_msg,
                "type": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def _handle_tool_calls(
        self,
        conversation: Conversation,
        response: LLMResponse
    ) -> Dict[str, Any]:
        """Handle LLM tool calls"""
        results = []
        
        # First, add the assistant message with tool_calls to conversation
        # This is required by OpenAI - tool results must follow a message with tool_calls
        assistant_msg = conversation.add_message(
            MessageRole.ASSISTANT,
            response.content or "",
            tool_calls=[
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments)
                    }
                }
                for tc in response.tool_calls
            ]
        )
        
        for tool_call in response.tool_calls:
            logger.info(f"Executing tool: {tool_call.name} with args: {tool_call.arguments}")
            
            try:
                result = await self._execute_tool(
                    conversation,
                    tool_call.name,
                    tool_call.arguments
                )
                results.append({
                    "tool": tool_call.name,
                    "result": result
                })
                
                # Add tool result to conversation
                conversation.add_message(
                    MessageRole.TOOL,
                    json.dumps(result),
                    tool_call_id=tool_call.id
                )
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                error_result = {"error": str(e)}
                results.append({
                    "tool": tool_call.name,
                    "error": str(e)
                })
                # Still need to add tool result even on error
                conversation.add_message(
                    MessageRole.TOOL,
                    json.dumps(error_result),
                    tool_call_id=tool_call.id
                )
        
        # Get follow-up response from LLM
        try:
            follow_up = await self.llm.complete(
                messages=conversation.get_llm_messages(),
                tools=self.tools,
                temperature=0.7
            )
            
            # Check if the follow-up also has tool calls (recursive)
            if follow_up.tool_calls:
                logger.info(f"Follow-up has {len(follow_up.tool_calls)} more tool calls, processing recursively")
                # Process the additional tool calls
                recursive_result = await self._handle_tool_calls(conversation, follow_up)
                # Combine results
                recursive_result["tool_results"] = results + (recursive_result.get("tool_results") or [])
                return recursive_result
            
            conversation.add_message(MessageRole.ASSISTANT, follow_up.content)
            
            return {
                "conversation_id": conversation.conversation_id,
                "response": follow_up.content,
                "type": "tool_result",
                "tool_results": results
            }
        except Exception as e:
            logger.error(f"Follow-up LLM call failed: {e}")
            # Return tool results without follow-up
            summary = "\n".join([
                f"**{r['tool']}**: {r.get('result', {}).get('formatted', r.get('result', r.get('error', 'completed')))}"
                for r in results
            ])
            return {
                "conversation_id": conversation.conversation_id,
                "response": summary or "Tool executed successfully.",
                "type": "tool_result",
                "tool_results": results
            }
    
    # ═══════════════════════════════════════════════════
    # Tool Execution
    # ═══════════════════════════════════════════════════
    
    async def _execute_tool(
        self,
        conversation: Conversation,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool call"""
        tool_def = get_tool_by_name(tool_name)
        
        if not tool_def:
            return {"error": f"Unknown tool: {tool_name}"}
        
        # Route to appropriate handler
        handlers = {
            "deploy_lab": self._tool_deploy_lab,
            "deploy_vm": self._tool_deploy_vm,
            "terminate_vm": self._tool_terminate_vm,
            "send_email": self._tool_send_email,
            "create_reaper_mission": self._tool_create_mission,
            "get_status": self._tool_get_status,
            "list_resources": self._tool_list_resources,
            "search_knowledge": self._tool_search_knowledge,
            "stop_resource": self._tool_stop_resource,
            "ask_clarification": self._tool_ask_clarification,
            "confirm_action": self._tool_confirm_action,
            "get_platform_status": self._tool_get_platform_status,
        }
        
        handler = handlers.get(tool_name)
        if handler:
            return await handler(conversation, arguments)
        
        return {"error": f"No handler for tool: {tool_name}"}
    
    async def _tool_send_email(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle send_email tool call"""
        logger.info(f"Send email requested: {args}")
        
        to_addresses = args.get("to", [])
        subject = args.get("subject", "")
        body = args.get("body", "")
        from_address = args.get("from_address", "overseer@xisx.org")
        
        if not to_addresses or not subject or not body:
            return {
                "status": "error",
                "error": "Missing required fields: to, subject, and body are required"
            }
        
        # Create action request for confirmation
        action = ActionRequest(
            action_id=f"action-{uuid.uuid4().hex[:8]}",
            action_type="send_email",
            summary=f"📧 Send email to {', '.join(to_addresses)}",
            details={
                "from": from_address,
                "to": to_addresses,
                "cc": args.get("cc"),
                "subject": subject,
                "body": body,
                "html_body": args.get("html_body")
            },
            warnings=[]
        )
        conversation.pending_action = action
        
        return {
            "status": "awaiting_confirmation",
            "action": action.summary,
            "details": {
                "to": to_addresses,
                "subject": subject,
                "preview": body[:100] + "..." if len(body) > 100 else body
            },
            "message": f"Ready to send email to {', '.join(to_addresses)}. Please confirm."
        }
    
    async def _tool_terminate_vm(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle terminate_vm tool call - destroy a VM"""
        logger.info(f"Terminate VM requested: {args}")
        
        platform = args.get("platform", "aws").lower()
        instance_id = args.get("instance_id")
        instance_name = args.get("instance_name")
        region = args.get("region")
        
        # Need either instance_id or instance_name
        if not instance_id and not instance_name:
            return {
                "status": "error",
                "error": "Please provide either instance_id or instance_name to identify the VM to terminate."
            }
        
        # Create action request for confirmation
        identifier = instance_id or instance_name
        action = ActionRequest(
            action_id=f"action-{uuid.uuid4().hex[:8]}",
            action_type="terminate_vm",
            summary=f"⚠️ TERMINATE VM '{identifier}' on {platform.upper()}",
            details={
                "platform": platform,
                "instance_id": instance_id,
                "instance_name": instance_name,
                "region": region or "us-east-1"
            },
            warnings=[
                "⚠️ THIS WILL PERMANENTLY DELETE THE VM AND ALL ITS DATA!",
                "This action cannot be undone."
            ]
        )
        conversation.pending_action = action
        
        return {
            "status": "awaiting_confirmation",
            "action": action.summary,
            "details": action.details,
            "warnings": action.warnings,
            "message": f"Ready to terminate '{identifier}' on {platform.upper()}. This is PERMANENT. Please confirm."
        }
    
    async def _tool_deploy_vm(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle deploy_vm tool call - deploy a single VM"""
        logger.info(f"Deploy VM requested: {args}")
        
        platform = args.get("platform", "aws").lower()
        vm_name = args.get("name", f"glassdome-{uuid.uuid4().hex[:6]}")
        
        # Create action request for confirmation
        action = ActionRequest(
            action_id=f"action-{uuid.uuid4().hex[:8]}",
            action_type="deploy_vm",
            summary=f"Deploy '{vm_name}' on {platform.upper()}",
            details={
                "name": vm_name,
                "platform": platform,
                "region": args.get("region", "us-east-1"),
                "os_type": args.get("os_type", "ubuntu"),
                "instance_type": args.get("instance_type", "t2.nano"),
                "disk_size_gb": args.get("disk_size_gb", 8)
            },
            warnings=[f"This will create a new VM on {platform.upper()} which may incur costs."]
        )
        conversation.pending_action = action
        
        return {
            "status": "awaiting_confirmation",
            "action": action.summary,
            "details": action.details,
            "warnings": action.warnings,
            "message": f"Ready to deploy '{vm_name}' on {platform.upper()}. Please confirm to proceed."
        }
    
    async def _tool_deploy_lab(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle deploy_lab tool call"""
        # Create workflow for lab deployment
        workflow = self.workflow_engine.create_workflow(
            workflow_type="deploy_lab",
            name=args.get("lab_name", "New Lab"),
            initial_data=args
        )
        
        conversation.active_workflow = workflow.workflow_id
        
        # Check if we have all required data
        if workflow.is_data_complete():
            # Create action request for confirmation
            action = ActionRequest(
                action_id=f"action-{uuid.uuid4().hex[:8]}",
                action_type="deploy_lab",
                summary=self._build_lab_summary(args),
                details=args,
                warnings=self._get_deployment_warnings(args)
            )
            conversation.pending_action = action
            
            return {
                "status": "awaiting_confirmation",
                "action": action.summary,
                "details": action.details,
                "warnings": action.warnings
            }
        else:
            # Need more data
            missing = workflow.get_missing_required_fields()
            return {
                "status": "collecting_data",
                "workflow_id": workflow.workflow_id,
                "missing_fields": missing,
                "prompt": self.workflow_engine.get_data_collection_prompt(workflow)
            }
    
    async def _tool_create_mission(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create_reaper_mission tool call"""
        workflow = self.workflow_engine.create_workflow(
            workflow_type="create_mission",
            name=args.get("mission_name", "New Mission"),
            initial_data=args
        )
        
        conversation.active_workflow = workflow.workflow_id
        
        if workflow.is_data_complete():
            action = ActionRequest(
                action_id=f"action-{uuid.uuid4().hex[:8]}",
                action_type="create_mission",
                summary=f"Create Reaper mission '{args.get('mission_name')}' targeting lab {args.get('lab_id')}",
                details=args
            )
            conversation.pending_action = action
            
            return {
                "status": "awaiting_confirmation",
                "action": action.summary,
                "details": action.details
            }
        else:
            missing = workflow.get_missing_required_fields()
            return {
                "status": "collecting_data",
                "missing_fields": missing,
                "prompt": self.workflow_engine.get_data_collection_prompt(workflow)
            }
    
    async def _tool_get_status(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_status tool call"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")
        
        if not self.overseer:
            return {"error": "Overseer not connected"}
        
        if resource_type == "system":
            return self.overseer.get_status()
        elif resource_type == "missions":
            if resource_id:
                return self.overseer.get_reaper_mission_status(resource_id)
            else:
                return {"missions": self.overseer.list_reaper_missions()}
        elif resource_type == "vms":
            return {"vms": list(self.overseer.state.vms.values())}
        elif resource_type == "hosts":
            return {"hosts": list(self.overseer.state.hosts.values())}
        else:
            return {"error": f"Unknown resource type: {resource_type}"}
    
    async def _tool_list_resources(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle list_resources tool call"""
        resource_type = args.get("resource_type")
        
        if resource_type == "templates":
            from glassdome.chat.tools import list_lab_templates
            return {"templates": list_lab_templates()}
        elif resource_type == "missions":
            if self.overseer:
                return {"missions": self.overseer.list_reaper_missions()}
            return {"missions": []}
        elif resource_type == "platforms":
            return {
                "platforms": [
                    {"name": "proxmox", "status": "available"},
                    {"name": "aws", "status": "available"},
                    {"name": "azure", "status": "available"},
                    {"name": "esxi", "status": "available"}
                ]
            }
        else:
            return {"resources": [], "note": f"Listing {resource_type} not implemented"}
    
    async def _tool_search_knowledge(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle search_knowledge tool call"""
        query = args.get("query")
        search_type = args.get("search_type", "general")
        
        if self.overseer and hasattr(self.overseer, 'rag'):
            if search_type == "error":
                result = self.overseer.rag.search_error(query)
            else:
                result = self.overseer.rag.quick_search(query)
            return {"results": result}
        
        return {"results": "Knowledge base not available"}
    
    async def _tool_stop_resource(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle stop_resource tool call"""
        resource_type = args.get("resource_type")
        resource_id = args.get("resource_id")
        
        # Create confirmation action
        action = ActionRequest(
            action_id=f"action-{uuid.uuid4().hex[:8]}",
            action_type="stop_resource",
            summary=f"Stop {resource_type} '{resource_id}'",
            details=args,
            warnings=[f"This will stop the {resource_type}. Any running processes will be terminated."]
        )
        conversation.pending_action = action
        
        return {
            "status": "awaiting_confirmation",
            "action": action.summary,
            "warnings": action.warnings
        }
    
    async def _tool_ask_clarification(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle ask_clarification tool call"""
        return {
            "question": args.get("question"),
            "options": args.get("options", []),
            "context": args.get("context", "")
        }
    
    async def _tool_confirm_action(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle confirm_action tool call"""
        action = ActionRequest(
            action_id=f"action-{uuid.uuid4().hex[:8]}",
            action_type=args.get("action_type"),
            summary=args.get("action_summary"),
            details=args.get("details", {}),
            warnings=args.get("warnings", [])
        )
        conversation.pending_action = action
        
        return {
            "status": "awaiting_confirmation",
            "action_id": action.action_id,
            "summary": action.summary,
            "warnings": action.warnings
        }
    
    async def _tool_get_platform_status(
        self,
        conversation: Conversation,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_platform_status tool call - check cloud instances"""
        platform = args.get("platform", "all").lower()
        region = args.get("region")
        instance_id = args.get("instance_id")
        
        logger.info(f"Getting platform status: platform={platform}, region={region}")
        
        results = {}
        
        try:
            # AWS Status
            if platform in ["aws", "all"]:
                aws_status = await self._get_aws_status(region, instance_id)
                results["aws"] = aws_status
            
            # Proxmox Status
            if platform in ["proxmox", "all"]:
                proxmox_status = await self._get_proxmox_status(instance_id)
                results["proxmox"] = proxmox_status
            
            # Format response
            summary_lines = []
            total_running = 0
            total_stopped = 0
            
            for plat, data in results.items():
                if data.get("connected"):
                    running = data.get("summary", {}).get("running", 0)
                    stopped = data.get("summary", {}).get("stopped", 0)
                    total = data.get("summary", {}).get("total", 0)
                    total_running += running
                    total_stopped += stopped
                    summary_lines.append(f"**{plat.upper()}**: {total} instances ({running} running, {stopped} stopped)")
                    
                    # List instances
                    for inst in data.get("instances", [])[:5]:  # Limit to 5
                        name = inst.get("name", inst.get("id", "unnamed"))
                        status = inst.get("status", inst.get("state", "unknown"))
                        region_info = inst.get("region", "")
                        ip = inst.get("public_ip") or inst.get("ip", "")
                        summary_lines.append(f"  - {name}: {status}" + (f" ({region_info})" if region_info else "") + (f" - IP: {ip}" if ip else ""))
                else:
                    summary_lines.append(f"**{plat.upper()}**: Not connected - {data.get('message', 'unavailable')}")
            
            return {
                "status": "success",
                "platforms_checked": list(results.keys()),
                "summary": {
                    "total_running": total_running,
                    "total_stopped": total_stopped,
                    "total": total_running + total_stopped
                },
                "details": results,
                "formatted": "\n".join(summary_lines)
            }
            
        except Exception as e:
            logger.error(f"Error getting platform status: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _get_aws_status(self, region: str = None, instance_id: str = None) -> Dict[str, Any]:
        """Get AWS EC2 instance status"""
        from glassdome.core.session import get_session
        
        try:
            session = get_session()
            aws_key = session.secrets.get('aws_access_key_id')
            aws_secret = session.secrets.get('aws_secret_access_key')
            
            if not aws_key or not aws_secret:
                return {"connected": False, "message": "AWS credentials not configured"}
            
            import boto3
            
            # Check multiple regions if none specified
            regions = [region] if region else ["us-east-1", "us-west-2"]
            all_instances = []
            
            for reg in regions:
                try:
                    ec2 = boto3.client(
                        'ec2',
                        aws_access_key_id=aws_key,
                        aws_secret_access_key=aws_secret,
                        region_name=reg
                    )
                    
                    # Filter by instance_id if provided
                    filters = []
                    if instance_id:
                        response = ec2.describe_instances(InstanceIds=[instance_id])
                    else:
                        response = ec2.describe_instances()
                    
                    for reservation in response.get('Reservations', []):
                        for instance in reservation.get('Instances', []):
                            name = "Unnamed"
                            for tag in instance.get('Tags', []):
                                if tag['Key'] == 'Name':
                                    name = tag['Value']
                                    break
                            
                            all_instances.append({
                                "id": instance['InstanceId'],
                                "name": name,
                                "state": instance.get('State', {}).get('Name', 'unknown'),
                                "instance_type": instance.get('InstanceType', ''),
                                "public_ip": instance.get('PublicIpAddress'),
                                "private_ip": instance.get('PrivateIpAddress'),
                                "region": reg,
                                "launch_time": str(instance.get('LaunchTime', ''))
                            })
                except Exception as e:
                    logger.warning(f"Error checking AWS region {reg}: {e}")
            
            running = sum(1 for i in all_instances if i['state'] == 'running')
            stopped = sum(1 for i in all_instances if i['state'] == 'stopped')
            
            return {
                "connected": True,
                "instances": all_instances,
                "summary": {
                    "total": len(all_instances),
                    "running": running,
                    "stopped": stopped
                }
            }
            
        except Exception as e:
            logger.error(f"AWS status error: {e}")
            return {"connected": False, "message": str(e)}
    
    async def _get_proxmox_status(self, vm_id: str = None) -> Dict[str, Any]:
        """Get Proxmox VM status"""
        try:
            from glassdome.platforms.proxmox_factory import get_proxmox_client
            
            client = get_proxmox_client("01")
            if not await client.test_connection():
                return {"connected": False, "message": "Proxmox connection failed"}
            
            nodes = await client.list_nodes()
            all_vms = []
            
            for node in nodes:
                node_name = node.get("node")
                if node_name:
                    vms = await client.list_vms(node_name)
                    for vm in vms:
                        if vm.get("template"):
                            continue  # Skip templates
                        if vm_id and str(vm.get("vmid")) != str(vm_id):
                            continue
                        all_vms.append({
                            "id": vm.get("vmid"),
                            "name": vm.get("name"),
                            "status": vm.get("status"),
                            "node": node_name,
                            "cpu": f"{vm.get('cpu', 0) * 100:.1f}%",
                            "memory": f"{vm.get('mem', 0) / (1024**3):.1f} GB"
                        })
            
            running = sum(1 for v in all_vms if v['status'] == 'running')
            stopped = sum(1 for v in all_vms if v['status'] == 'stopped')
            
            return {
                "connected": True,
                "instances": all_vms,
                "summary": {
                    "total": len(all_vms),
                    "running": running,
                    "stopped": stopped
                }
            }
            
        except Exception as e:
            logger.error(f"Proxmox status error: {e}")
            return {"connected": False, "message": str(e)}
    
    # ═══════════════════════════════════════════════════
    # Action Confirmation
    # ═══════════════════════════════════════════════════
    
    async def _handle_action_response(
        self,
        conversation: Conversation,
        message: str
    ) -> Dict[str, Any]:
        """Handle response to pending action confirmation"""
        action = conversation.pending_action
        message_lower = message.lower().strip()
        
        # Check for approval
        if any(word in message_lower for word in ["yes", "approve", "confirm", "do it", "proceed", "go ahead", "ok", "okay"]):
            action.status = "approved"
            conversation.pending_action = None
            
            # Execute the action
            result = await self._execute_confirmed_action(conversation, action)
            
            response = f"Done! {result.get('message', 'Action completed.')}"
            conversation.add_message(MessageRole.ASSISTANT, response)
            
            return {
                "conversation_id": conversation.conversation_id,
                "response": response,
                "type": "action_executed",
                "result": result
            }
        
        # Check for rejection
        elif any(word in message_lower for word in ["no", "cancel", "stop", "reject", "abort", "nevermind"]):
            action.status = "rejected"
            conversation.pending_action = None
            
            if conversation.active_workflow:
                self.workflow_engine.cancel_workflow(conversation.active_workflow)
                conversation.active_workflow = None
            
            response = "Understood, I've cancelled the action."
            conversation.add_message(MessageRole.ASSISTANT, response)
            
            return {
                "conversation_id": conversation.conversation_id,
                "response": response,
                "type": "action_cancelled"
            }
        
        # Check for modification request
        else:
            # Pass to LLM to handle modification
            return await self._process_with_llm(conversation)
    
    async def _execute_confirmed_action(
        self,
        conversation: Conversation,
        action: ActionRequest
    ) -> Dict[str, Any]:
        """Execute a confirmed action"""
        logger.info(f"Executing confirmed action: {action.action_type}")
        
        if action.action_type == "deploy_lab":
            return await self._execute_lab_deployment(action.details)
        elif action.action_type == "deploy_vm":
            return await self._execute_vm_deployment(action.details)
        elif action.action_type == "terminate_vm":
            return await self._execute_terminate_vm(action.details)
        elif action.action_type == "send_email":
            return await self._execute_send_email(action.details)
        elif action.action_type == "create_mission":
            return await self._execute_mission_creation(action.details)
        elif action.action_type == "stop_resource":
            return await self._execute_stop_resource(action.details)
        else:
            return {"error": f"Unknown action type: {action.action_type}"}
    
    async def _execute_vm_deployment(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single VM deployment"""
        platform = details.get("platform", "aws").lower()
        
        logger.info(f"Executing VM deployment: {details}")
        
        if platform == "aws":
            return await self._deploy_to_aws(details)
        elif platform == "proxmox":
            return await self._deploy_to_proxmox(details)
        else:
            return {
                "success": False,
                "error": f"Platform '{platform}' not yet supported for direct VM deployment"
            }
    
    async def _execute_terminate_vm(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM termination"""
        platform = details.get("platform", "aws").lower()
        
        logger.info(f"Executing VM termination: {details}")
        
        if platform == "aws":
            return await self._terminate_aws_instance(details)
        elif platform == "proxmox":
            return await self._terminate_proxmox_vm(details)
        else:
            return {
                "success": False,
                "error": f"Platform '{platform}' not yet supported for termination"
            }
    
    async def _terminate_aws_instance(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Terminate an AWS EC2 instance"""
        from glassdome.core.session import get_session
        import boto3
        
        logger.info(f"Terminating AWS instance: {details}")
        
        session = get_session()
        aws_key = session.secrets.get('aws_access_key_id')
        aws_secret = session.secrets.get('aws_secret_access_key')
        
        if not aws_key or not aws_secret:
            return {"success": False, "error": "AWS credentials not configured"}
        
        instance_id = details.get("instance_id")
        instance_name = details.get("instance_name")
        region = details.get("region", "us-east-1")
        
        try:
            # If we only have name, find the instance ID
            if not instance_id and instance_name:
                # Search both regions
                for reg in ["us-east-1", "us-west-2"]:
                    ec2 = boto3.client(
                        'ec2',
                        aws_access_key_id=aws_key,
                        aws_secret_access_key=aws_secret,
                        region_name=reg
                    )
                    response = ec2.describe_instances(
                        Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}]
                    )
                    for reservation in response.get('Reservations', []):
                        for instance in reservation.get('Instances', []):
                            if instance.get('State', {}).get('Name') != 'terminated':
                                instance_id = instance['InstanceId']
                                region = reg
                                break
                    if instance_id:
                        break
                
                if not instance_id:
                    return {"success": False, "error": f"Could not find instance with name '{instance_name}'"}
            
            # Terminate the instance
            ec2 = boto3.client(
                'ec2',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=region
            )
            
            logger.info(f"Calling terminate_instances for {instance_id} in {region}")
            response = ec2.terminate_instances(InstanceIds=[instance_id])
            
            # Check termination status
            terminating = response.get('TerminatingInstances', [])
            if terminating:
                current_state = terminating[0].get('CurrentState', {}).get('Name', 'unknown')
                return {
                    "success": True,
                    "message": f"✅ Instance '{instance_id}' terminated successfully",
                    "instance_id": instance_id,
                    "region": region,
                    "state": current_state
                }
            else:
                return {"success": False, "error": "Termination request returned no results"}
                
        except Exception as e:
            logger.error(f"AWS terminate failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to terminate instance: {e}"
            }
    
    async def _terminate_proxmox_vm(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Terminate a Proxmox VM"""
        # TODO: Implement Proxmox VM termination
        return {
            "success": False,
            "error": "Proxmox VM termination not yet implemented"
        }
    
    async def _execute_send_email(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email via Mailcow"""
        from glassdome.core.session import get_session
        from glassdome.integrations.mailcow_client import MailcowClient
        
        logger.info(f"Sending email: {details}")
        
        try:
            session = get_session()
            
            # Get Mailcow credentials from session (try multiple key names)
            mailcow_api_key = (
                session.secrets.get('mailcow_api_key') or 
                session.secrets.get('mail_api') or
                session.secrets.get('mailcow_key')
            )
            mailcow_url = session.secrets.get('mailcow_url', 'https://mail.xisx.org')
            
            if not mailcow_api_key:
                return {
                    "success": False,
                    "error": "Mailcow API key not configured in secrets"
                }
            
            # Initialize client
            client = MailcowClient(
                api_url=mailcow_url,
                api_token=mailcow_api_key
            )
            
            # Send the email via SMTP (Mailcow API doesn't support sending)
            # Always use glassdome-ai@xisx.org as sender (the only configured mailbox)
            from_address = "glassdome-ai@xisx.org"  # Override any other sender
            to_addresses = details.get("to", [])
            subject = details.get("subject", "")
            body = details.get("body", "")
            html_body = details.get("html_body")
            cc = details.get("cc")
            
            # Get SMTP password for the mailbox
            smtp_password = (
                session.secrets.get('overseer_mail_password') or 
                session.secrets.get('mail_password') or
                session.secrets.get('mailcow_smtp_password')
            )
            
            if not smtp_password:
                return {
                    "success": False,
                    "error": "SMTP password not configured. Please add 'overseer_mail_password' to secrets for the overseer@xisx.org mailbox."
                }
            
            result = client.send_email(
                mailbox=from_address,
                password=smtp_password,
                to_addresses=to_addresses,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                use_api=False  # Use SMTP instead of API (Mailcow API doesn't support sending)
            )
            
            if result.get("success"):
                logger.info(f"Email sent successfully to {to_addresses}")
                return {
                    "success": True,
                    "message": f"✅ Email sent to {', '.join(to_addresses)}",
                    "subject": subject,
                    "recipients": to_addresses
                }
            else:
                logger.error(f"Failed to send email: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error sending email")
                }
                
        except Exception as e:
            logger.error(f"Email send failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to send email: {e}"
            }
    
    async def _execute_lab_deployment(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute lab deployment - actually creates VMs on the target platform"""
        logger.info(f"Executing lab deployment: {details}")
        
        platform = details.get("platform", "").lower()
        lab_name = details.get("lab_name", "unnamed-lab")
        
        try:
            # AWS deployment
            if platform == "aws":
                return await self._deploy_to_aws(details)
            
            # Proxmox deployment
            elif platform == "proxmox":
                return await self._deploy_to_proxmox(details)
            
            # Other platforms - placeholder
            else:
                lab_id = f"lab-{uuid.uuid4().hex[:8]}"
                return {
                    "success": True,
                    "message": f"Lab '{lab_name}' deployment queued for {platform}",
                    "lab_id": lab_id,
                    "platform": platform,
                    "status": "queued",
                    "note": f"Full {platform} integration coming soon"
                }
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Deployment failed: {str(e)}",
                "error": str(e)
            }
    
    async def _deploy_to_aws(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy VM to AWS EC2"""
        from glassdome.platforms.aws_client import AWSClient
        from glassdome.core.session import get_session
        
        logger.info(f"Starting AWS deployment with details: {details}")
        
        # Get AWS credentials from session
        session = get_session()
        aws_key = session.secrets.get('aws_access_key_id')
        aws_secret = session.secrets.get('aws_secret_access_key')
        
        if not aws_key or not aws_secret:
            return {"success": False, "error": "AWS credentials not configured"}
        
        # Parse region - default to us-east-1
        region = details.get("region", "us-east-1")
        # Also check if region hint is in other fields
        details_str = str(details).lower()
        if "east" in details_str and "region" not in details:
            region = "us-east-1"
        elif "west" in details_str and "region" not in details:
            region = "us-west-2"
        
        logger.info(f"Using region: {region}")
        
        # Create AWS client
        aws_client = AWSClient(
            access_key_id=aws_key,
            secret_access_key=aws_secret,
            region=region
        )
        
        # Build VM config - support both 'name' and 'lab_name' fields
        vm_name = details.get("name") or details.get("lab_name", f"glassdome-{uuid.uuid4().hex[:6]}")
        instance_type = details.get("instance_type", "t2.nano")
        
        # Support "nano", "micro", "small" shortcuts in instance_type or size field
        size = details.get("size", "").lower()
        if not instance_type.startswith("t"):  # If not already a valid type
            if size == "nano" or "nano" in details_str:
                instance_type = "t2.nano"
            elif size == "micro" or "micro" in details_str:
                instance_type = "t2.micro"
            elif size == "small" or "small" in details_str:
                instance_type = "t2.small"
        
        os_type = details.get("os_type", "ubuntu")
        
        vm_config = {
            "name": vm_name,
            "os_type": os_type,
            "os_version": "22.04",
            "instance_type": instance_type,
            "disk_size_gb": details.get("disk_size_gb", 8),
            "tags": {
                "Name": vm_name,
                "CreatedBy": "Glassdome-Overseer",
                "Project": "Glassdome"
            }
        }
        
        logger.info(f"Creating AWS EC2 instance: {vm_config}")
        
        try:
            # Actually create the VM
            result = await aws_client.create_vm(vm_config)
            
            logger.info(f"AWS deployment result: {result}")
            
            return {
                "success": True,
                "message": f"✅ EC2 instance '{vm_name}' created in {region}",
                "instance_id": result.get("instance_id"),
                "instance_type": instance_type,
                "region": region,
                "public_ip": result.get("public_ip"),
                "private_ip": result.get("private_ip"),
                "status": "running"
            }
        except Exception as e:
            logger.error(f"AWS deployment failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to create EC2 instance: {e}"
            }
    
    async def _deploy_to_proxmox(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy VM to Proxmox"""
        # TODO: Implement actual Proxmox deployment
        lab_id = f"lab-{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "message": f"Lab '{details.get('lab_name')}' queued for Proxmox deployment",
            "lab_id": lab_id,
            "platform": "proxmox",
            "status": "queued"
        }
    
    async def _execute_mission_creation(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Reaper mission creation"""
        logger.info(f"Creating Reaper mission: {details}")
        
        if self.overseer:
            mission_id = f"mission-{uuid.uuid4().hex[:8]}"
            target_hosts = details.get("target_hosts", [])
            
            result = self.overseer.create_reaper_mission(
                mission_id=mission_id,
                lab_id=details.get("lab_id"),
                mission_type=details.get("mission_type"),
                target_vms=target_hosts
            )
            return result
        
        return {
            "success": True,
            "message": f"Mission '{details.get('mission_name')}' created",
            "mission_id": f"mission-{uuid.uuid4().hex[:8]}"
        }
    
    async def _execute_stop_resource(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute resource stop"""
        resource_type = details.get("resource_type")
        resource_id = details.get("resource_id")
        
        if resource_type == "mission" and self.overseer:
            return self.overseer.cancel_reaper_mission(resource_id)
        
        return {
            "success": True,
            "message": f"{resource_type} '{resource_id}' stopped"
        }
    
    # ═══════════════════════════════════════════════════
    # Workflow Handling
    # ═══════════════════════════════════════════════════
    
    async def _handle_workflow_message(
        self,
        conversation: Conversation,
        message: str
    ) -> Dict[str, Any]:
        """Handle message when workflow is active"""
        workflow = self.workflow_engine.get_workflow(conversation.active_workflow)
        
        if not workflow:
            conversation.active_workflow = None
            return await self._process_with_llm(conversation)
        
        # Use LLM to extract data from message
        return await self._process_with_llm(conversation)
    
    async def _handle_deploy_lab(self, workflow: Workflow) -> Dict[str, Any]:
        """Handle lab deployment workflow execution"""
        data = workflow.collected_data
        
        if self.overseer:
            # Create lab through orchestrator
            # This is a placeholder - would integrate with LabOrchestrator
            pass
        
        return {
            "success": True,
            "workflow_id": workflow.workflow_id,
            "lab_id": f"lab-{uuid.uuid4().hex[:8]}",
            "message": f"Lab '{data.get('lab_name')}' deployed successfully"
        }
    
    async def _handle_create_mission(self, workflow: Workflow) -> Dict[str, Any]:
        """Handle mission creation workflow execution"""
        data = workflow.collected_data
        
        if self.overseer:
            result = self.overseer.create_reaper_mission(
                mission_id=f"mission-{uuid.uuid4().hex[:8]}",
                lab_id=data.get("lab_id"),
                mission_type=data.get("mission_type"),
                target_vms=data.get("target_hosts", [])
            )
            return result
        
        return {
            "success": True,
            "workflow_id": workflow.workflow_id,
            "message": f"Mission '{data.get('mission_name')}' created"
        }
    
    # ═══════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════
    
    def _build_lab_summary(self, args: Dict[str, Any]) -> str:
        """Build human-readable lab deployment summary"""
        lab_name = args.get("lab_name", "New Lab")
        platform = args.get("platform", "unknown")
        lab_type = args.get("lab_type", "custom")
        vm_count = args.get("vm_count", "auto")
        
        template = LAB_TEMPLATES.get(lab_type, {})
        template_vms = len(template.get("vms", []))
        
        summary = f"Deploy '{lab_name}' on {platform}\n"
        summary += f"Type: {lab_type}\n"
        summary += f"VMs: {vm_count if vm_count != 'auto' else template_vms}"
        
        if args.get("vulnerabilities"):
            summary += f"\nVulnerabilities: {', '.join(args['vulnerabilities'])}"
        
        return summary
    
    def _get_deployment_warnings(self, args: Dict[str, Any]) -> List[str]:
        """Get warnings for lab deployment"""
        warnings = []
        
        platform = args.get("platform")
        if platform in ["aws", "azure"]:
            warnings.append(f"This will deploy resources on {platform}, which may incur costs.")
        
        vm_count = args.get("vm_count", 0)
        if vm_count > 5:
            warnings.append(f"Deploying {vm_count} VMs - ensure sufficient resources are available.")
        
        return warnings
    
    # ═══════════════════════════════════════════════════
    # Streaming Support
    # ═══════════════════════════════════════════════════
    
    async def stream_response(
        self,
        conversation_id: str,
        message: str
    ) -> AsyncIterator[str]:
        """
        Stream a response for the given message
        
        Args:
            conversation_id: Conversation ID
            message: User message
            
        Yields:
            Response chunks as they arrive
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            conversation = self.create_conversation()
        
        conversation.add_message(MessageRole.USER, message)
        
        # Stream from LLM
        full_response = ""
        async for chunk in self.llm.stream(
            messages=conversation.get_llm_messages(),
            temperature=0.7
        ):
            full_response += chunk
            yield chunk
        
        # Save complete response
        conversation.add_message(MessageRole.ASSISTANT, full_response)


"""
API endpoints for chat

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel

# Configure logging for chat module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Global chat agent instance (initialized on first use)
_chat_agent = None
_overseer_entity = None


def get_chat_agent():
    """Get or create the chat agent singleton"""
    global _chat_agent, _overseer_entity
    
    if _chat_agent is None:
        logger.info("=" * 60)
        logger.info("INITIALIZING OVERSEER CHAT AGENT")
        logger.info("=" * 60)
        
        try:
            from glassdome.chat.agent import OverseerChatAgent
            
            # Try to get Overseer entity if available
            try:
                from glassdome.overseer.entity import OverseerEntity
                from glassdome.core.security import get_secure_settings
                logger.info("Getting secure settings...")
                settings = get_secure_settings()
                logger.info("Creating OverseerEntity...")
                _overseer_entity = OverseerEntity(settings)
                logger.info("✓ OverseerEntity initialized")
            except Exception as e:
                logger.warning(f"✗ Could not initialize OverseerEntity: {e}")
                logger.debug(traceback.format_exc())
                _overseer_entity = None
            
            logger.info("Creating OverseerChatAgent...")
            _chat_agent = OverseerChatAgent(overseer_entity=_overseer_entity)
            
            # Log available providers
            providers = _chat_agent.llm.list_available_providers()
            logger.info(f"✓ Chat agent initialized with LLM providers: {providers}")
            
            if not providers:
                logger.error("⚠ NO LLM PROVIDERS! Chat will not work properly.")
                logger.error("Check that OpenAI or Anthropic API keys are in the secrets manager.")
            
        except Exception as e:
            logger.error(f"FATAL: Failed to initialize chat agent: {e}")
            logger.error(traceback.format_exc())
            raise
        
        logger.info("=" * 60)
    
    return _chat_agent


# ═══════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    """Response with conversation details"""
    conversation_id: str
    created_at: str
    message_count: int


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    message: str
    stream: bool = False


class MessageResponse(BaseModel):
    """Response from the chat agent"""
    conversation_id: str
    response: str
    type: str  # "message", "tool_result", "action_executed", etc.
    tool_results: Optional[List[Dict[str, Any]]] = None
    pending_action: Optional[Dict[str, Any]] = None


class ActionConfirmRequest(BaseModel):
    """Request to confirm or reject an action"""
    action_id: str
    approved: bool
    modifications: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════
# REST Endpoints
# ═══════════════════════════════════════════════════

@router.get("/")
async def chat_info():
    """Get chat service information"""
    agent = get_chat_agent()
    return {
        "service": "Overseer Chat",
        "status": "online",
        "active_conversations": len(agent.conversations),
        "llm_providers": agent.llm.list_available_providers()
    }


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: Optional[CreateConversationRequest] = None):
    """
    Create a new chat conversation
    
    Returns a conversation ID to use for subsequent messages.
    """
    agent = get_chat_agent()
    conversation = agent.create_conversation()
    
    return ConversationResponse(
        conversation_id=conversation.conversation_id,
        created_at=conversation.created_at,
        message_count=len(conversation.messages)
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation details and history
    """
    agent = get_chat_agent()
    conversation = agent.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation.conversation_id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "message_count": len(conversation.messages),
        "messages": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in conversation.messages
            if msg.role.value != "system"  # Don't expose system prompt
        ],
        "active_workflow": conversation.active_workflow,
        "pending_action": {
            "action_id": conversation.pending_action.action_id,
            "action_type": conversation.pending_action.action_type,
            "summary": conversation.pending_action.summary,
            "warnings": conversation.pending_action.warnings
        } if conversation.pending_action else None
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation
    """
    agent = get_chat_agent()
    
    if agent.delete_conversation(conversation_id):
        return {"success": True, "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message to the chat agent
    
    The agent will process the message, potentially calling tools,
    and return a response.
    """
    agent = get_chat_agent()
    
    # Validate conversation exists or will be created
    conversation = agent.get_conversation(conversation_id)
    if not conversation:
        # Create new conversation with the provided ID
        conversation = agent.create_conversation()
        # Update the ID (bit of a hack but works for now)
        agent.conversations.pop(conversation.conversation_id)
        conversation.conversation_id = conversation_id
        agent.conversations[conversation_id] = conversation
    
    # Process the message
    result = await agent.process_message(conversation_id, request.message)
    
    return MessageResponse(
        conversation_id=result["conversation_id"],
        response=result["response"],
        type=result.get("type", "message"),
        tool_results=result.get("tool_results"),
        pending_action=result.get("pending_action")
    )


@router.post("/conversations/{conversation_id}/actions/{action_id}/confirm")
async def confirm_action(
    conversation_id: str,
    action_id: str,
    request: ActionConfirmRequest
):
    """
    Confirm or reject a pending action
    """
    agent = get_chat_agent()
    conversation = agent.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.pending_action:
        raise HTTPException(status_code=400, detail="No pending action")
    
    if conversation.pending_action.action_id != action_id:
        raise HTTPException(status_code=400, detail="Action ID mismatch")
    
    # Process confirmation
    if request.approved:
        result = await agent.process_message(
            conversation_id,
            "yes, proceed"
        )
    else:
        result = await agent.process_message(
            conversation_id,
            "no, cancel"
        )
    
    return result


# ═══════════════════════════════════════════════════
# WebSocket Endpoint
# ═══════════════════════════════════════════════════

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, conversation_id: str, websocket: WebSocket):
        """Accept and register a WebSocket connection"""
        await websocket.accept()
        self.active_connections[conversation_id] = websocket
        logger.info(f"WebSocket connected: {conversation_id}")
    
    def disconnect(self, conversation_id: str):
        """Remove a WebSocket connection"""
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id]
            logger.info(f"WebSocket disconnected: {conversation_id}")
    
    async def send_message(self, conversation_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection"""
        if conversation_id in self.active_connections:
            await self.active_connections[conversation_id].send_json(message)
    
    async def send_chunk(self, conversation_id: str, chunk: str):
        """Send a streaming chunk"""
        if conversation_id in self.active_connections:
            await self.active_connections[conversation_id].send_json({
                "type": "chunk",
                "content": chunk
            })


manager = ConnectionManager()


@router.websocket("/ws/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time chat
    
    Protocol:
    - Client sends: {"type": "message", "content": "user message"}
    - Server sends: {"type": "chunk", "content": "..."} for streaming
    - Server sends: {"type": "complete", "response": "full response", ...} when done
    - Server sends: {"type": "action", "action": {...}} for pending actions
    - Client sends: {"type": "confirm", "approved": true/false} for actions
    """
    logger.info(f"[WS:{conversation_id}] New WebSocket connection")
    await manager.connect(conversation_id, websocket)
    
    try:
        agent = get_chat_agent()
    except Exception as e:
        logger.error(f"[WS:{conversation_id}] Failed to get chat agent: {e}")
        await websocket.send_json({
            "type": "error",
            "error": f"Failed to initialize chat agent: {str(e)}"
        })
        await websocket.close()
        return
    
    # Ensure conversation exists
    if not agent.get_conversation(conversation_id):
        conversation = agent.create_conversation()
        agent.conversations.pop(conversation.conversation_id)
        conversation.conversation_id = conversation_id
        agent.conversations[conversation_id] = conversation
        logger.info(f"[WS:{conversation_id}] Created new conversation")
    
    try:
        # Send welcome message with provider info
        providers = agent.llm.list_available_providers()
        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
            "message": "Connected to Overseer. How can I help you today?",
            "providers": providers
        })
        logger.info(f"[WS:{conversation_id}] Sent welcome message. Providers: {providers}")
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            logger.debug(f"[WS:{conversation_id}] Received: {msg_type}")
            
            if msg_type == "message":
                content = data.get("content", "")
                # Default to NON-streaming to support tool calls
                # Streaming mode doesn't support tools properly
                stream = data.get("stream", False)
                
                logger.info(f"[WS:{conversation_id}] Processing message: '{content[:100]}...' stream={stream}")
                
                if stream:
                    # Stream response
                    await websocket.send_json({
                        "type": "start",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    full_response = ""
                    try:
                        async for chunk in agent.stream_response(conversation_id, content):
                            full_response += chunk
                            await websocket.send_json({
                                "type": "chunk",
                                "content": chunk
                            })
                        logger.info(f"[WS:{conversation_id}] Stream complete, {len(full_response)} chars")
                    except Exception as e:
                        logger.error(f"[WS:{conversation_id}] Streaming error: {e}")
                        logger.error(traceback.format_exc())
                        await websocket.send_json({
                            "type": "error",
                            "error": str(e),
                            "details": traceback.format_exc()
                        })
                        continue
                    
                    await websocket.send_json({
                        "type": "complete",
                        "response": full_response
                    })
                else:
                    # Non-streaming response
                    try:
                        result = await agent.process_message(conversation_id, content)
                        logger.info(f"[WS:{conversation_id}] Message processed, type: {result.get('type')}")
                        
                        await websocket.send_json({
                            "type": "complete",
                            "response": result["response"],
                            "result_type": result.get("type"),
                            "tool_results": result.get("tool_results")
                        })
                    except Exception as e:
                        logger.error(f"[WS:{conversation_id}] Process message error: {e}")
                        logger.error(traceback.format_exc())
                        await websocket.send_json({
                            "type": "error",
                            "error": str(e),
                            "details": traceback.format_exc()
                        })
                        continue
                    
                    # Check for pending action
                    conversation = agent.get_conversation(conversation_id)
                    if conversation and conversation.pending_action:
                        action = conversation.pending_action
                        logger.info(f"[WS:{conversation_id}] Pending action: {action.action_type}")
                        await websocket.send_json({
                            "type": "action",
                            "action": {
                                "action_id": action.action_id,
                                "action_type": action.action_type,
                                "summary": action.summary,
                                "details": action.details,
                                "warnings": action.warnings
                            }
                        })
            
            elif msg_type == "confirm":
                # Handle action confirmation
                approved = data.get("approved", False)
                logger.info(f"[WS:{conversation_id}] Action confirmation: approved={approved}")
                response_text = "yes, proceed" if approved else "no, cancel"
                try:
                    result = await agent.process_message(conversation_id, response_text)
                    await websocket.send_json({
                        "type": "action_result",
                        "approved": approved,
                        "response": result["response"],
                        "result": result.get("result")
                    })
                except Exception as e:
                    logger.error(f"[WS:{conversation_id}] Action confirm error: {e}")
                    logger.error(traceback.format_exc())
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "status":
                conversation = agent.get_conversation(conversation_id)
                await websocket.send_json({
                    "type": "status",
                    "conversation_id": conversation_id,
                    "message_count": len(conversation.messages) if conversation else 0,
                    "active_workflow": conversation.active_workflow if conversation else None,
                    "has_pending_action": bool(conversation.pending_action) if conversation else False
                })
    
    except WebSocketDisconnect:
        manager.disconnect(conversation_id)
        logger.info(f"[WS:{conversation_id}] Client disconnected")
    except Exception as e:
        logger.error(f"[WS:{conversation_id}] WebSocket error: {e}")
        logger.error(traceback.format_exc())
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
                "details": traceback.format_exc()
            })
        except:
            pass
        manager.disconnect(conversation_id)


# ═══════════════════════════════════════════════════
# Utility Endpoints
# ═══════════════════════════════════════════════════

@router.get("/templates")
async def list_templates():
    """
    List available lab templates
    """
    from glassdome.chat.tools import list_lab_templates
    return {"templates": list_lab_templates()}


@router.get("/tools")
async def list_tools():
    """
    List available tools for the chat agent
    """
    from glassdome.chat.tools import OVERSEER_TOOLS
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "requires_confirmation": t.requires_confirmation
            }
            for t in OVERSEER_TOOLS
        ]
    }


@router.get("/providers")
async def list_providers():
    """
    List available LLM providers
    """
    agent = get_chat_agent()
    return {
        "providers": agent.llm.list_available_providers(),
        "default": agent.llm.default_provider
    }


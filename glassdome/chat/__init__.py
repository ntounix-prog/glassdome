"""
  Init   module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from glassdome.chat.llm_service import (
    LLMService,
    LLMMessage,
    LLMResponse,
    LLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    Tool,
    ToolCall
)
from glassdome.chat.workflow_engine import (
    WorkflowEngine,
    Workflow,
    WorkflowStep,
    WorkflowStatus
)
from glassdome.chat.agent import (
    OverseerChatAgent,
    Conversation,
    ChatMessage,
    MessageRole
)
from glassdome.chat.tools import (
    OVERSEER_TOOLS,
    LAB_TEMPLATES,
    get_tool_by_name,
    get_tools_for_llm,
    list_lab_templates
)

__all__ = [
    # LLM Service
    "LLMService",
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "Tool",
    "ToolCall",
    # Workflow Engine
    "WorkflowEngine",
    "Workflow",
    "WorkflowStep",
    "WorkflowStatus",
    # Chat Agent
    "OverseerChatAgent",
    "Conversation",
    "ChatMessage",
    "MessageRole",
    # Tools
    "OVERSEER_TOOLS",
    "LAB_TEMPLATES",
    "get_tool_by_name",
    "get_tools_for_llm",
    "list_lab_templates",
]

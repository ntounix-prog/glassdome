"""
Llm Service module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import os
import json
import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, AsyncIterator, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_api_key(key_name: str) -> Optional[str]:
    """Get API key from session secrets or environment"""
    # Try session first
    try:
        from glassdome.core.session import get_session
        session = get_session()
        if session.authenticated and session.secrets:
            secret_key = key_name.lower()
            if secret_key in session.secrets:
                logger.debug(f"Got {key_name} from session secrets")
                return session.secrets[secret_key]
    except Exception as e:
        logger.debug(f"Could not get {key_name} from session: {e}")
    
    # Fall back to environment
    env_value = os.getenv(key_name)
    if env_value:
        logger.debug(f"Got {key_name} from environment")
    return env_value


class LLMProviderType(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMMessage:
    """Standard message format for LLM conversations"""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # For tool messages
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    """Represents an LLM tool/function call"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """Standard response format from LLM providers"""
    content: str
    role: str = "assistant"
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None
    provider: str = ""
    model: str = ""
    raw_response: Optional[Any] = None


@dataclass
class Tool:
    """Tool definition for LLM function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self._initialized = False
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Complete a conversation with the LLM
        
        Args:
            messages: Conversation history
            tools: Available tools for function calling
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            
        Returns:
            LLMResponse with content and optional tool calls
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """
        Stream a response from the LLM
        
        Args:
            messages: Conversation history
            tools: Available tools
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            
        Yields:
            Response chunks as they arrive
        """
        pass
    
    def is_available(self) -> bool:
        """Check if provider is configured and available"""
        return bool(self.api_key)


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider (GPT-4, GPT-4o, etc.)"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: Optional[str] = None
    ):
        resolved_key = api_key or _get_api_key("OPENAI_API_KEY") or _get_api_key("openai_api_key")
        super().__init__(
            api_key=resolved_key,
            model=model
        )
        self.base_url = base_url
        self._client = None
        if resolved_key:
            logger.info(f"OpenAI provider initialized with model: {model}")
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def _get_client(self):
        """Lazy-load OpenAI client"""
        if not self._client:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage to OpenAI format"""
        result = []
        for msg in messages:
            m = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            result.append(m)
        return result
    
    def _convert_tools(self, tools: List[Tool]) -> List[Dict[str, Any]]:
        """Convert Tool to OpenAI function format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in tools
        ]
    
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Complete using OpenAI API"""
        client = self._get_client()
        
        kwargs = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = "auto"
        
        response = await client.chat.completions.create(**kwargs)
        
        choice = response.choices[0]
        message = choice.message
        
        # Parse tool calls if present
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                )
                for tc in message.tool_calls
            ]
        
        return LLMResponse(
            content=message.content or "",
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None,
            provider=self.provider_name,
            model=self.model,
            raw_response=response
        )
    
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """Stream response from OpenAI"""
        client = self._get_client()
        
        kwargs = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        
        response = await client.chat.completions.create(**kwargs)
        
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        resolved_key = api_key or _get_api_key("ANTHROPIC_API_KEY") or _get_api_key("anthropic_api_key")
        super().__init__(
            api_key=resolved_key,
            model=model
        )
        self._client = None
        if resolved_key:
            logger.info(f"Anthropic provider initialized with model: {model}")
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    def _get_client(self):
        """Lazy-load Anthropic client"""
        if not self._client:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
        return self._client
    
    def _convert_messages(self, messages: List[LLMMessage]) -> tuple:
        """Convert LLMMessage to Anthropic format (separate system prompt)"""
        system_prompt = ""
        converted = []
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role == "tool":
                # Anthropic uses tool_result blocks
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    }]
                })
            else:
                converted.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return system_prompt, converted
    
    def _convert_tools(self, tools: List[Tool]) -> List[Dict[str, Any]]:
        """Convert Tool to Anthropic format"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters
            }
            for tool in tools
        ]
    
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Complete using Anthropic API"""
        client = self._get_client()
        
        system_prompt, converted_messages = self._convert_messages(messages)
        
        kwargs = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        
        response = await client.messages.create(**kwargs)
        
        # Parse response content
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))
        
        return LLMResponse(
            content=content,
            role="assistant",
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response.stop_reason or "stop",
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            provider=self.provider_name,
            model=self.model,
            raw_response=response
        )
    
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """Stream response from Anthropic"""
        client = self._get_client()
        
        system_prompt, converted_messages = self._convert_messages(messages)
        
        kwargs = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text


class LLMService:
    """
    Main LLM service with provider management and fallback
    
    Usage:
        service = LLMService()
        response = await service.complete(messages)
    """
    
    def __init__(
        self,
        default_provider: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None
    ):
        """
        Initialize LLM service
        
        Args:
            default_provider: Primary provider to use (openai, anthropic, local)
            fallback_providers: Ordered list of fallback providers
        """
        self.default_provider = default_provider or os.getenv("LLM_DEFAULT_PROVIDER", "openai")
        self.fallback_providers = fallback_providers or []
        
        # Initialize provider registry
        self._providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()
        
        logger.info(f"LLMService initialized with default provider: {self.default_provider}")
    
    def _initialize_providers(self):
        """Initialize available providers based on configuration"""
        logger.info("Initializing LLM providers...")
        
        # OpenAI - check session secrets and environment
        openai_key = _get_api_key("OPENAI_API_KEY") or _get_api_key("openai_api_key")
        if openai_key:
            try:
                self._providers["openai"] = OpenAIProvider(api_key=openai_key)
                logger.info("✓ OpenAI provider available")
            except Exception as e:
                logger.error(f"✗ Failed to initialize OpenAI provider: {e}")
        else:
            logger.warning("✗ OpenAI provider not available (no API key)")
        
        # Anthropic - check session secrets and environment
        anthropic_key = _get_api_key("ANTHROPIC_API_KEY") or _get_api_key("anthropic_api_key")
        if anthropic_key:
            try:
                self._providers["anthropic"] = AnthropicProvider(api_key=anthropic_key)
                logger.info("✓ Anthropic provider available")
            except Exception as e:
                logger.error(f"✗ Failed to initialize Anthropic provider: {e}")
        else:
            logger.warning("✗ Anthropic provider not available (no API key)")
        
        if not self._providers:
            logger.error("⚠ NO LLM PROVIDERS AVAILABLE - Chat will not work!")
        else:
            logger.info(f"Available providers: {list(self._providers.keys())}")
    
    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """
        Get a specific provider or the default
        
        Args:
            name: Provider name or None for default
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If provider not available
        """
        provider_name = name or self.default_provider
        
        if provider_name not in self._providers:
            available = list(self._providers.keys())
            if available:
                logger.warning(
                    f"Provider '{provider_name}' not available, using '{available[0]}'"
                )
                provider_name = available[0]
            else:
                raise ValueError(
                    "No LLM providers configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
                )
        
        return self._providers[provider_name]
    
    def list_available_providers(self) -> List[str]:
        """List available provider names"""
        return list(self._providers.keys())
    
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider: Optional[str] = None
    ) -> LLMResponse:
        """
        Complete a conversation with fallback support
        
        Args:
            messages: Conversation history
            tools: Available tools
            temperature: Sampling temperature
            max_tokens: Max response tokens
            provider: Specific provider to use
            
        Returns:
            LLMResponse
        """
        request_id = f"llm-{datetime.utcnow().strftime('%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"[{request_id}] LLM complete request - {len(messages)} messages, {len(tools or [])} tools")
        
        if not self._providers:
            logger.error(f"[{request_id}] NO PROVIDERS AVAILABLE! Reinitializing...")
            self._initialize_providers()
            if not self._providers:
                raise ValueError("No LLM providers configured. Check API keys in secrets or environment.")
        
        providers_to_try = [provider or self.default_provider] + self.fallback_providers
        logger.debug(f"[{request_id}] Providers to try: {providers_to_try}")
        
        last_error = None
        for provider_name in providers_to_try:
            if provider_name not in self._providers:
                logger.debug(f"[{request_id}] Provider '{provider_name}' not in available providers, skipping")
                continue
            
            try:
                logger.info(f"[{request_id}] Trying provider: {provider_name}")
                llm = self._providers[provider_name]
                response = await llm.complete(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"[{request_id}] SUCCESS via {provider_name} in {elapsed:.2f}s - "
                    f"usage: {response.usage}, tool_calls: {len(response.tool_calls or [])}"
                )
                return response
                
            except Exception as e:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"[{request_id}] Provider '{provider_name}' FAILED after {elapsed:.2f}s: {e}\n"
                    f"Traceback: {traceback.format_exc()}"
                )
                last_error = e
                continue
        
        logger.error(f"[{request_id}] ALL PROVIDERS FAILED. Last error: {last_error}")
        raise ValueError(f"All providers failed. Last error: {last_error}")
    
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream a response with fallback support
        
        Args:
            messages: Conversation history
            tools: Available tools
            temperature: Sampling temperature
            max_tokens: Max response tokens
            provider: Specific provider to use
            
        Yields:
            Response chunks
        """
        provider_name = provider or self.default_provider
        llm = self.get_provider(provider_name)
        
        async for chunk in llm.stream(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            yield chunk
    
    def register_provider(self, name: str, provider: LLMProvider):
        """
        Register a custom provider
        
        Args:
            name: Provider name
            provider: LLMProvider instance
        """
        self._providers[name] = provider
        logger.info(f"Registered custom provider: {name}")


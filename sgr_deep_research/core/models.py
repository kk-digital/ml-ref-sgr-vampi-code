import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

_token_usage_logger = logging.getLogger(__name__)


class SourceData(BaseModel):
    """Data about a research source."""

    number: int = Field(description="Citation number")
    title: str | None = Field(default="Untitled", description="Page title")
    url: str = Field(description="Source URL")
    snippet: str = Field(default="", description="Search snippet or summary")
    full_content: str = Field(default="", description="Full scraped content")
    char_count: int = Field(default=0, description="Character count of full content")

    def __str__(self):
        return f"[{self.number}] {self.title or 'Untitled'} - {self.url}"


class SearchResult(BaseModel):
    """Search result with query, answer, and sources."""

    query: str = Field(description="Search query")
    answer: str | None = Field(default=None, description="AI-generated answer from search")
    citations: list[SourceData] = Field(default_factory=list, description="List of source citations")
    timestamp: datetime = Field(default_factory=datetime.now, description="Search execution timestamp")

    def __str__(self):
        return f"Search: '{self.query}' ({len(self.citations)} sources)"


class AgentStatesEnum(str, Enum):
    INITED = "inited"
    RESEARCHING = "researching"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    COMPLETED = "completed"
    ERROR = "error"
    FAILED = "failed"

    FINISH_STATES = {COMPLETED, FAILED, ERROR}


class ResearchContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    current_step_reasoning: Any = None
    execution_result: str = None

    state: AgentStatesEnum = Field(default=AgentStatesEnum.INITED, description="Current research state")
    iteration: int = Field(default=0, description="Current iteration number")

    searches: list[SearchResult] = Field(default_factory=list, description="List of performed searches")
    sources: dict[str, SourceData] = Field(default_factory=dict, description="Dictionary of found sources")

    searches_used: int = Field(default=0, description="Number of searches performed")

    clarifications_used: int = Field(default=0, description="Number of clarifications requested")
    clarification_received: asyncio.Event = Field(
        default_factory=asyncio.Event, description="Event for clarification synchronization"
    )
    
    working_directory: str = Field(default=".", description="Working directory for file operations")

    # ToDO: rename, my creativity finished now
    def agent_state(self) -> dict:
        return self.model_dump(exclude={"searches", "sources", "clarification_received"})


class TokenUsage(BaseModel):
    """Token usage statistics for an agent."""
    
    prompt_tokens: int = Field(default=0, description="Total input/prompt tokens")
    completion_tokens: int = Field(default=0, description="Total output/completion tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")
    thinking_tokens: int = Field(default=0, description="Thinking/reasoning tokens (if available)")
    cached_tokens: int = Field(default=0, description="Cached prompt tokens (if available)")
    cost: float = Field(default=0.0, description="Total cost in USD from API")
    
    # Per-request detailed tracking for benchmarking
    request_details: list = Field(default_factory=list, description="Detailed per-request data including prompts and outputs")
    
    def add_usage(self, usage) -> None:
        """Add usage from an OpenAI response.
        
        Args:
            usage: OpenAI CompletionUsage object or dict with token counts and cost
        """
        if usage is None:
            return
        
        # Debug: Log raw usage object to understand what we're receiving
        _token_usage_logger.debug(f"Raw usage object type: {type(usage)}")
        _token_usage_logger.debug(f"Raw usage object: {usage}")
        if hasattr(usage, '__dict__'):
            _token_usage_logger.debug(f"Usage __dict__: {usage.__dict__}")
        if hasattr(usage, 'model_extra'):
            _token_usage_logger.debug(f"Usage model_extra: {usage.model_extra}")
        
        if hasattr(usage, 'prompt_tokens'):
            self.prompt_tokens += getattr(usage, 'prompt_tokens', 0) or 0
            self.completion_tokens += getattr(usage, 'completion_tokens', 0) or 0
            self.total_tokens += getattr(usage, 'total_tokens', 0) or 0
            
            # Extract thinking/reasoning tokens from completion_tokens_details
            if hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
                details = usage.completion_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    self.thinking_tokens += details.reasoning_tokens or 0
            
            # Extract cached tokens from prompt_tokens_details (OpenRouter format)
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                prompt_details = usage.prompt_tokens_details
                if hasattr(prompt_details, 'cached_tokens'):
                    self.cached_tokens += prompt_details.cached_tokens or 0
            
            # Extract cost from API response (OpenRouter provides this as extra field)
            # Try direct attribute first
            cost_val = getattr(usage, 'cost', None)
            # If not found, try model_extra (Pydantic models store extra fields here)
            if cost_val is None and hasattr(usage, 'model_extra'):
                cost_val = usage.model_extra.get('cost')
            # Also try __dict__ for non-Pydantic objects
            if cost_val is None and hasattr(usage, '__dict__'):
                cost_val = usage.__dict__.get('cost')
            
            _token_usage_logger.debug(f"Extracted cost_val: {cost_val}")
            if cost_val is not None:
                self.cost += float(cost_val)
                _token_usage_logger.info(f"API cost extracted: ${cost_val}")
            else:
                _token_usage_logger.warning("No cost found in API response - will use fallback calculation")
        elif isinstance(usage, dict):
            self.prompt_tokens += usage.get('prompt_tokens', 0) or 0
            self.completion_tokens += usage.get('completion_tokens', 0) or 0
            self.total_tokens += usage.get('total_tokens', 0) or 0
            self.thinking_tokens += usage.get('thinking_tokens', 0) or 0
            self.cached_tokens += usage.get('cached_tokens', 0) or 0
            # Also check nested details format
            completion_details = usage.get('completion_tokens_details', {})
            if completion_details:
                self.thinking_tokens += completion_details.get('reasoning_tokens', 0) or 0
            prompt_details = usage.get('prompt_tokens_details', {})
            if prompt_details:
                self.cached_tokens += prompt_details.get('cached_tokens', 0) or 0
            # Extract cost from dict (OpenRouter provides this)
            cost_val = usage.get('cost')
            _token_usage_logger.debug(f"Dict cost_val: {cost_val}")
            if cost_val is not None:
                self.cost += float(cost_val)
                _token_usage_logger.info(f"API cost extracted from dict: ${cost_val}")
    
    def add_request_detail(self, request_num: int, prompt_messages: list, response_content: str, usage: dict | None = None) -> None:
        """Add detailed request information for benchmark tracking.
        
        Args:
            request_num: The request number (1-indexed)
            prompt_messages: The messages sent to the LLM
            response_content: The LLM's response content
            usage: Token usage for this specific request
        """
        # Truncate prompt messages for storage (keep structure but limit content size)
        truncated_messages = []
        for msg in prompt_messages:
            truncated_msg = {"role": msg.get("role", "unknown")}
            content = msg.get("content", "")
            if content:
                truncated_msg["content"] = content[:2000] + "..." if len(content) > 2000 else content
            else:
                truncated_msg["content"] = None
            if "tool_calls" in msg:
                truncated_msg["tool_calls"] = msg["tool_calls"]
            truncated_messages.append(truncated_msg)
        
        self.request_details.append({
            "request_num": request_num,
            "prompt_messages": truncated_messages,
            "response_content": response_content[:5000] if len(response_content) > 5000 else response_content,
            "usage": usage or {},
        })
    
    def to_dict(self) -> dict:
        """Return usage as dictionary.
        
        Ensures total_tokens includes thinking_tokens if they're not already counted.
        Some providers include thinking tokens in total, others don't.
        """
        # Calculate what total should be: prompt + completion
        calculated_total = self.prompt_tokens + self.completion_tokens
        
        # If API total matches calculated, thinking tokens might not be included
        # If thinking tokens exist and total doesn't seem to include them, add them
        final_total = self.total_tokens
        if self.thinking_tokens > 0:
            # Check if thinking tokens are already included in total
            # If total equals prompt + completion, thinking is NOT included
            if self.total_tokens == calculated_total:
                final_total = self.total_tokens + self.thinking_tokens
            # If total is less than calculated + thinking, it's likely not included
            elif self.total_tokens < calculated_total + self.thinking_tokens:
                final_total = calculated_total + self.thinking_tokens
        
        result = {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": final_total,
            "thinking_tokens": self.thinking_tokens,
            "cached_tokens": self.cached_tokens,
            "cost": self.cost,
        }
        
        # Include request_details if available
        if self.request_details:
            result["request_details"] = self.request_details
        
        return result


class AgentStatistics(BaseModel):
    pass

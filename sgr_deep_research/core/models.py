import asyncio
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
    
    def add_usage(self, usage) -> None:
        """Add usage from an OpenAI response.
        
        Args:
            usage: OpenAI CompletionUsage object or dict with token counts
        """
        if usage is None:
            return
        
        if hasattr(usage, 'prompt_tokens'):
            self.prompt_tokens += getattr(usage, 'prompt_tokens', 0) or 0
            self.completion_tokens += getattr(usage, 'completion_tokens', 0) or 0
            self.total_tokens += getattr(usage, 'total_tokens', 0) or 0
            
            # Extract thinking/reasoning tokens from completion_tokens_details
            if hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
                details = usage.completion_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    self.thinking_tokens += details.reasoning_tokens or 0
        elif isinstance(usage, dict):
            self.prompt_tokens += usage.get('prompt_tokens', 0) or 0
            self.completion_tokens += usage.get('completion_tokens', 0) or 0
            self.total_tokens += usage.get('total_tokens', 0) or 0
            self.thinking_tokens += usage.get('thinking_tokens', 0) or 0
    
    def to_dict(self) -> dict:
        """Return usage as dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "thinking_tokens": self.thinking_tokens,
        }


class AgentStatistics(BaseModel):
    pass

"""Data models for model benchmark module."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported provider types."""
    OPENROUTER = "openrouter"
    CEREBRAS = "cerebras"


class ModelConfig(BaseModel):
    """Configuration for a single model."""
    
    name: str = Field(description="Model identifier (e.g., 'anthropic/claude-sonnet-4')")
    provider: ProviderType = Field(description="Provider type")
    display_name: Optional[str] = Field(default=None, description="Human-readable name")
    
    # Pricing per 1M tokens (for cost calculation)
    input_price_per_million: float = Field(default=0.0, description="Input token price per 1M tokens")
    output_price_per_million: float = Field(default=0.0, description="Output token price per 1M tokens")
    
    def get_display_name(self) -> str:
        return self.display_name or self.name


class TaskResult(BaseModel):
    """Result of a single task execution."""
    
    task_id: str = Field(description="Task identifier (filename)")
    task_content: str = Field(description="Task content/prompt")
    model_name: str = Field(description="Model used")
    
    # Timing
    start_time: datetime = Field(description="Execution start time")
    end_time: datetime = Field(description="Execution end time")
    duration_seconds: float = Field(description="Total execution time in seconds")
    
    # Token usage
    prompt_tokens: int = Field(default=0, description="Number of input/prompt tokens")
    completion_tokens: int = Field(default=0, description="Number of output/completion tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")
    thinking_tokens: int = Field(default=0, description="Thinking/reasoning tokens (if available)")
    
    # Cost
    cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    
    # Result
    success: bool = Field(default=True, description="Whether execution succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    response: Optional[str] = Field(default=None, description="Model response content")
    
    # Metadata
    iterations: int = Field(default=0, description="Number of agent iterations")
    request_count: int = Field(default=1, description="Number of API requests made for this task")
    
    # Per-request details for detailed logging
    request_details: list[dict] = Field(default_factory=list, description="Details of each API request (input/output tokens, cost)")


class ModelReport(BaseModel):
    """Aggregated report for a single model across all tasks."""
    
    model_name: str = Field(description="Model identifier")
    display_name: str = Field(description="Human-readable model name")
    provider: ProviderType = Field(description="Provider type")
    
    # Task counts
    total_tasks: int = Field(default=0, description="Total number of tasks")
    successful_tasks: int = Field(default=0, description="Number of successful tasks")
    failed_tasks: int = Field(default=0, description="Number of failed tasks")
    
    # Averages
    avg_duration_seconds: float = Field(default=0.0, description="Average execution time")
    avg_prompt_tokens: float = Field(default=0.0, description="Average prompt tokens per task")
    avg_completion_tokens: float = Field(default=0.0, description="Average completion tokens per task")
    avg_total_tokens: float = Field(default=0.0, description="Average total tokens per task")
    avg_thinking_tokens: float = Field(default=0.0, description="Average thinking tokens per task")
    avg_cost_usd: float = Field(default=0.0, description="Average cost per task in USD")
    avg_iterations: float = Field(default=0.0, description="Average iterations per task")
    
    # Totals
    total_duration_seconds: float = Field(default=0.0, description="Total execution time")
    total_prompt_tokens: int = Field(default=0, description="Total prompt tokens")
    total_completion_tokens: int = Field(default=0, description="Total completion tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_thinking_tokens: int = Field(default=0, description="Total thinking tokens")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    total_requests: int = Field(default=0, description="Total number of API requests")
    avg_requests_per_task: float = Field(default=0.0, description="Average requests per task")
    
    # Individual results
    task_results: list[TaskResult] = Field(default_factory=list, description="Individual task results")


class BenchmarkReport(BaseModel):
    """Complete benchmark report across all models."""
    
    benchmark_id: str = Field(description="Unique benchmark run identifier")
    start_time: datetime = Field(description="Benchmark start time")
    end_time: Optional[datetime] = Field(default=None, description="Benchmark end time")
    
    # Configuration
    tasks_directory: str = Field(description="Directory containing task files")
    total_tasks: int = Field(default=0, description="Total number of tasks")
    models_tested: list[str] = Field(default_factory=list, description="List of models tested")
    
    # Model reports
    model_reports: dict[str, ModelReport] = Field(default_factory=dict, description="Reports per model")
    
    # Summary
    total_duration_seconds: float = Field(default=0.0, description="Total benchmark duration")
    total_cost_usd: float = Field(default=0.0, description="Total cost across all models")


class BenchmarkConfig(BaseModel):
    """Configuration for benchmark execution."""
    
    tasks_directory: str = Field(description="Directory containing .txt task files")
    output_directory: str = Field(default="benchmark_results", description="Output directory for reports")
    
    # Execution settings
    max_iterations: int = Field(default=20, description="Maximum agent iterations per task")
    batch_size: int = Field(default=1, description="Number of tasks to run in parallel per model")
    timeout_seconds: int = Field(default=300, description="Timeout per task in seconds")
    
    # Models to benchmark
    models: list[ModelConfig] = Field(default_factory=list, description="Models to benchmark")

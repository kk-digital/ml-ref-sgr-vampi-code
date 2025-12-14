"""Benchmark runner for executing tasks across multiple models via sgr-vampi-code agent."""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from .models import (
    BenchmarkConfig,
    BenchmarkReport,
    ModelConfig,
    ModelReport,
    ProviderType,
    TaskResult,
)
from .providers import BaseProvider, get_provider

logger = logging.getLogger(__name__)

# SGR Vampi Code API configuration
SGR_API_BASE_URL = os.getenv("SGR_API_BASE_URL", "http://localhost:8010")


class BenchmarkRunner:
    """Runs benchmark tasks across multiple models."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.benchmark_id = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.report = BenchmarkReport(
            benchmark_id=self.benchmark_id,
            start_time=datetime.now(),
            tasks_directory=config.tasks_directory,
            models_tested=[m.name for m in config.models],
        )
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create a shared HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout_seconds))
        return self._http_client
    
    async def _close_http_client(self):
        """Close the shared HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
    
    def load_tasks(self) -> list[tuple[str, str]]:
        """Load tasks from .txt files in the tasks directory.
        
        Returns list of (task_id, task_content) tuples.
        """
        tasks_dir = Path(self.config.tasks_directory)
        if not tasks_dir.exists():
            raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")
        
        tasks = []
        for task_file in sorted(tasks_dir.glob("*.txt")):
            task_id = task_file.stem
            task_content = task_file.read_text(encoding="utf-8").strip()
            if task_content:
                tasks.append((task_id, task_content))
                logger.info(f"Loaded task: {task_id}")
        
        if not tasks:
            raise ValueError(f"No .txt task files found in {tasks_dir}")
        
        self.report.total_tasks = len(tasks)
        logger.info(f"Loaded {len(tasks)} tasks from {tasks_dir}")
        return tasks
    
    async def run_single_task(
        self,
        task_id: str,
        task_content: str,
        model_config: ModelConfig,
        provider: BaseProvider,
    ) -> TaskResult:
        """Execute a single task with a specific model via sgr-vampi-code agent."""
        start_time = datetime.now()
        start_ts = time.time()
        
        result = TaskResult(
            task_id=task_id,
            task_content=task_content,
            model_name=model_config.name,
            start_time=start_time,
            end_time=start_time,
            duration_seconds=0.0,
        )
        
        try:
            result = await self._run_with_sgr_agent(result, task_id, task_content, model_config, provider)
            
        except asyncio.TimeoutError:
            result.success = False
            result.error_message = f"Task timed out after {self.config.timeout_seconds}s"
            logger.error(f"Task '{task_id}' timed out")
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Task '{task_id}' failed: {e}")
        
        finally:
            end_time = datetime.now()
            result.end_time = end_time
            result.duration_seconds = time.time() - start_ts
        
        return result
    
    async def _run_with_sgr_agent(
        self,
        result: TaskResult,
        task_id: str,
        task_content: str,
        model_config: ModelConfig,
        provider: BaseProvider,
    ) -> TaskResult:
        """Execute task using sgr-vampi-code agent API."""
        logger.info(f"Running task '{task_id}' with model '{model_config.get_display_name()}' via sgr-vampi-code agent")
        
        response_content = ""
        iterations = 0
        request_count = 0
        request_details = []  # Track per-request input/output/cost details
        detailed_requests = []  # Track per-request prompts and outputs
        usage_data = None  # Will store actual token usage from final chunk
        seen_tool_call_ids = set()  # Track unique tool call IDs to count actual iterations
        
        # Get provider-specific base URL and API key
        llm_base_url = None
        llm_api_key = None
        if model_config.provider == ProviderType.OPENROUTER:
            llm_base_url = "https://openrouter.ai/api/v1"
            llm_api_key = os.getenv("OPENROUTER_API_KEY")
        elif model_config.provider == ProviderType.CEREBRAS:
            llm_base_url = "https://api.cerebras.ai/v1"
            llm_api_key = os.getenv("CEREBRAS_API_KEY")
        
        http_client = await self._get_http_client()
        async with http_client.stream(
                "POST",
                f"{SGR_API_BASE_URL}/v1/chat/completions",
                json={
                    "model": "sgr_vampi_code",  # Use the coding agent
                    "messages": [{"role": "user", "content": task_content}],
                    "stream": True,
                    "max_tokens": self.config.max_iterations * 500,
                    "temperature": 0.3,
                    # Dynamic LLM configuration
                    "llm_model": model_config.name,
                    "llm_base_url": llm_base_url,
                    "llm_api_key": llm_api_key,
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            # Check for request_details in usage (sent with final chunk)
                            if "usage" in chunk and chunk["usage"]:
                                if "request_details" in chunk["usage"]:
                                    for req in chunk["usage"]["request_details"]:
                                        detailed_requests.append(req)
                                    logger.debug(f"Task '{task_id}': Found {len(chunk['usage']['request_details'])} request_details in final usage")
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    response_content += delta["content"]
                                # Count unique tool calls by ID (not streaming chunks)
                                if "tool_calls" in delta and delta["tool_calls"]:
                                    for tc in delta["tool_calls"]:
                                        tc_id = tc.get("id")
                                        if tc_id and tc_id not in seen_tool_call_ids:
                                            seen_tool_call_ids.add(tc_id)
                                            iterations += 1
                                            logger.debug(f"Task '{task_id}': New tool call detected: {tc_id} (iteration {iterations})")
                            # Capture usage data from chunks
                            
                            if "usage" in chunk and chunk["usage"]:
                                current_usage = chunk["usage"]
                                # Track each request's usage when we see finish_reason
                                finish_reason = chunk["choices"][0].get("finish_reason") if chunk.get("choices") else None
                                if finish_reason or current_usage.get("prompt_tokens", 0) > 0:
                                    request_count += 1
                                    request_detail = {
                                        "request_num": request_count,
                                        "prompt_tokens": current_usage.get("prompt_tokens", 0) or 0,
                                        "completion_tokens": current_usage.get("completion_tokens", 0) or 0,
                                        "thinking_tokens": current_usage.get("thinking_tokens", 0) or 0,
                                        "total_tokens": current_usage.get("total_tokens", 0) or 0,
                                        "cost": current_usage.get("cost"),
                                    }
                                    # Check for reasoning tokens in details
                                    details = current_usage.get("completion_tokens_details", {})
                                    if details and details.get("reasoning_tokens"):
                                        request_detail["thinking_tokens"] = details.get("reasoning_tokens", 0)
                                    request_details.append(request_detail)
                                    logger.debug(f"Task '{task_id}': Request #{request_count} usage: {request_detail}")
                                usage_data = current_usage
                                logger.debug(f"Task '{task_id}': Captured usage from chunk: {usage_data}")
                        except json.JSONDecodeError:
                            pass
        
        result.response = response_content
        result.success = True
        result.iterations = max(1, iterations)
        result.request_count = max(1, request_count)
        
        # Merge detailed_requests (with prompt/response text) into request_details
        # This ensures each request entry has both token counts AND text content
        if detailed_requests:
            # Use detailed_requests as the primary source since it has text content
            merged_details = []
            for detail in detailed_requests:
                req_num = detail.get('request_num', 0)
                # Find matching token counts from request_details
                matching_counts = next(
                    (rd for rd in request_details if rd.get('request_num') == req_num),
                    {}
                )
                merged_entry = {
                    "request_num": req_num,
                    "prompt_tokens": matching_counts.get('prompt_tokens', detail.get('usage', {}).get('prompt_tokens', 0)),
                    "completion_tokens": matching_counts.get('completion_tokens', detail.get('usage', {}).get('completion_tokens', 0)),
                    "thinking_tokens": matching_counts.get('thinking_tokens', detail.get('usage', {}).get('thinking_tokens', 0)),
                    "total_tokens": matching_counts.get('total_tokens', detail.get('usage', {}).get('total_tokens', 0)),
                    "cost": matching_counts.get('cost', detail.get('usage', {}).get('cost')),
                    # Add text content
                    "prompt_messages": detail.get('prompt_messages', []),
                    "response_content": detail.get('response_content', ''),
                }
                merged_details.append(merged_entry)
            result.request_details = merged_details
        else:
            result.request_details = request_details
        result.detailed_requests = detailed_requests  # Keep for backward compatibility
        
        logger.debug(
            f"Task '{task_id}': Streaming complete - "
            f"iterations={iterations} (unique tool calls: {len(seen_tool_call_ids)}), "
            f"requests={request_count}"
        )
        
        # Extract actual token usage and cost from API response
        logger.debug(f"Task '{task_id}': Raw usage_data from API: {usage_data}")
        if usage_data:
            result.prompt_tokens = usage_data.get("prompt_tokens", 0) or 0
            result.completion_tokens = usage_data.get("completion_tokens", 0) or 0
            
            # Extract thinking/reasoning tokens - check multiple locations
            # 1. Direct field (from our agent's TokenUsage.to_dict())
            thinking = usage_data.get("thinking_tokens", 0) or 0
            # 2. OpenRouter/OpenAI format: completion_tokens_details.reasoning_tokens
            if thinking == 0:
                details = usage_data.get("completion_tokens_details", {})
                if details:
                    thinking = details.get("reasoning_tokens", 0) or 0
            result.thinking_tokens = thinking
            
            # Calculate total tokens: prompt + completion + thinking
            # Note: Some APIs include thinking in completion_tokens, others don't
            # We ensure total includes all token types
            api_total = usage_data.get("total_tokens", 0) or 0
            calculated_total = result.prompt_tokens + result.completion_tokens
            # If API total doesn't include thinking tokens, add them
            if api_total > 0 and result.thinking_tokens > 0:
                # Check if thinking tokens are already included in total
                if api_total < calculated_total + result.thinking_tokens:
                    result.total_tokens = api_total + result.thinking_tokens
                else:
                    result.total_tokens = api_total
            elif api_total > 0:
                result.total_tokens = api_total
            else:
                result.total_tokens = calculated_total + result.thinking_tokens
            
            # Use cost from API if available (OpenRouter provides this)
            api_cost = usage_data.get("cost")
            if api_cost is not None:
                result.cost_usd = float(api_cost)
                logger.info(f"Task '{task_id}': Using API-provided cost: ${api_cost}")
            else:
                # Fallback to calculated cost if API doesn't provide it
                result.cost_usd = provider.calculate_cost(
                    result.prompt_tokens,
                    result.completion_tokens + result.thinking_tokens  # Include thinking in cost calc
                )
                logger.warning(f"Task '{task_id}': No cost in API response, using calculated: ${result.cost_usd:.6f}")
            
            # Extract cached tokens if available
            cached = usage_data.get("cached_tokens", 0) or 0
            if cached == 0:
                prompt_details = usage_data.get("prompt_tokens_details", {})
                if prompt_details:
                    cached = prompt_details.get("cached_tokens", 0) or 0
            
            logger.info(
                f"Task '{task_id}': Token usage - prompt={result.prompt_tokens}, "
                f"completion={result.completion_tokens}, thinking={result.thinking_tokens}, "
                f"cached={cached}, total={result.total_tokens}, cost=${result.cost_usd:.6f}"
            )
        else:
            # Fallback to estimation if no usage data available
            # Use tiktoken-style estimation: ~4 chars per token for English text
            result.prompt_tokens = max(1, len(task_content) // 4)
            result.completion_tokens = max(1, len(response_content) // 4)
            result.total_tokens = result.prompt_tokens + result.completion_tokens
            result.thinking_tokens = 0
            result.cost_usd = provider.calculate_cost(
                result.prompt_tokens,
                result.completion_tokens
            )
            logger.warning(
                f"Task '{task_id}': No usage data received from API, using estimates. "
                f"Provider: {model_config.provider.value}, Model: {model_config.name}. "
                f"Estimated tokens: prompt={result.prompt_tokens}, completion={result.completion_tokens}"
            )
        
        logger.info(
            f"Task '{task_id}' completed via agent: "
            f"iterations={result.iterations}, "
            f"tokens={result.total_tokens}, "
            f"thinking_tokens={result.thinking_tokens}"
        )
        
        return result
    
    async def run_model_benchmark(
        self,
        model_config: ModelConfig,
        tasks: list[tuple[str, str]],
    ) -> ModelReport:
        """Run all tasks for a single model in parallel."""
        logger.info(f"Starting benchmark for model: {model_config.get_display_name()}")
        
        report = ModelReport(
            model_name=model_config.name,
            display_name=model_config.get_display_name(),
            provider=model_config.provider,
            total_tasks=len(tasks),
        )
        
        try:
            provider = get_provider(model_config)
        except ValueError as e:
            logger.error(f"Failed to initialize provider for {model_config.name}: {e}")
            report.failed_tasks = len(tasks)
            return report
        
        # Run ALL tasks in parallel for this model
        all_results = await asyncio.gather(*[
            self.run_single_task(task_id, task_content, model_config, provider)
            for task_id, task_content in tasks
        ], return_exceptions=True)
        
        for result in all_results:
            if isinstance(result, Exception):
                report.failed_tasks += 1
                logger.error(f"Unexpected error: {result}")
            else:
                report.task_results.append(result)
                if result.success:
                    report.successful_tasks += 1
                else:
                    report.failed_tasks += 1
        
        successful_results = [r for r in report.task_results if r.success]
        if successful_results:
            report.total_duration_seconds = sum(r.duration_seconds for r in successful_results)
            report.total_prompt_tokens = sum(r.prompt_tokens for r in successful_results)
            report.total_completion_tokens = sum(r.completion_tokens for r in successful_results)
            report.total_tokens = sum(r.total_tokens for r in successful_results)
            report.total_thinking_tokens = sum(r.thinking_tokens for r in successful_results)
            report.total_cost_usd = sum(r.cost_usd for r in successful_results)
            report.total_requests = sum(r.request_count for r in successful_results)
            
            n = len(successful_results)
            report.avg_duration_seconds = report.total_duration_seconds / n
            report.avg_prompt_tokens = report.total_prompt_tokens / n
            report.avg_completion_tokens = report.total_completion_tokens / n
            report.avg_total_tokens = report.total_tokens / n
            report.avg_thinking_tokens = report.total_thinking_tokens / n
            report.avg_cost_usd = report.total_cost_usd / n
            report.avg_iterations = sum(r.iterations for r in successful_results) / n
            report.avg_requests_per_task = report.total_requests / n
        
        logger.info(
            f"Model '{model_config.get_display_name()}' completed: "
            f"{report.successful_tasks}/{report.total_tasks} successful, "
            f"avg_tokens={report.avg_total_tokens:.0f}, "
            f"avg_time={report.avg_duration_seconds:.2f}s, "
            f"total_cost=${report.total_cost_usd:.4f}"
        )
        
        return report
    
    async def run(self) -> BenchmarkReport:
        """Run the complete benchmark across all models."""
        logger.info(f"Starting benchmark {self.benchmark_id}")
        logger.info(f"Models to test: {[m.get_display_name() for m in self.config.models]}")
        
        tasks = self.load_tasks()
        
        # Run all models concurrently
        model_reports = await asyncio.gather(*[
            self.run_model_benchmark(model_config, tasks)
            for model_config in self.config.models
        ])
        
        for model_report in model_reports:
            self.report.model_reports[model_report.model_name] = model_report
        
        self.report.end_time = datetime.now()
        self.report.total_duration_seconds = (
            self.report.end_time - self.report.start_time
        ).total_seconds()
        self.report.total_cost_usd = sum(
            r.total_cost_usd for r in self.report.model_reports.values()
        )
        
        # Clean up HTTP client
        await self._close_http_client()
        
        logger.info(
            f"Benchmark completed in {self.report.total_duration_seconds:.2f}s, "
            f"total cost: ${self.report.total_cost_usd:.4f}"
        )
        
        return self.report

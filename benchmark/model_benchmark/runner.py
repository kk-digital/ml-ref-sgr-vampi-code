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
        
        # Get provider-specific base URL and API key
        llm_base_url = None
        llm_api_key = None
        if model_config.provider == ProviderType.OPENROUTER:
            llm_base_url = "https://openrouter.ai/api/v1"
            llm_api_key = os.getenv("OPENROUTER_API_KEY")
        elif model_config.provider == ProviderType.CEREBRAS:
            llm_base_url = "https://api.cerebras.ai/v1"
            llm_api_key = os.getenv("CEREBRAS_API_KEY")
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout_seconds)) as http_client:
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
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    response_content += delta["content"]
                                if "tool_calls" in delta:
                                    iterations += 1
                        except json.JSONDecodeError:
                            pass
        
        result.response = response_content
        result.success = True
        result.iterations = max(1, iterations)
        
        # Estimate tokens (rough estimate for agent mode)
        result.prompt_tokens = len(task_content.split()) * 2
        result.completion_tokens = len(response_content.split()) * 2
        result.total_tokens = result.prompt_tokens + result.completion_tokens
        
        result.cost_usd = provider.calculate_cost(
            result.prompt_tokens,
            result.completion_tokens
        )
        
        logger.info(
            f"Task '{task_id}' completed via agent: "
            f"iterations={result.iterations}, "
            f"tokens~={result.total_tokens}"
        )
        
        return result
    
    async def run_model_benchmark(
        self,
        model_config: ModelConfig,
        tasks: list[tuple[str, str]],
    ) -> ModelReport:
        """Run all tasks for a single model."""
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
        
        for i in range(0, len(tasks), self.config.batch_size):
            batch = tasks[i:i + self.config.batch_size]
            
            batch_results = await asyncio.gather(*[
                self.run_single_task(task_id, task_content, model_config, provider)
                for task_id, task_content in batch
            ], return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    report.failed_tasks += 1
                    logger.error(f"Unexpected error in batch: {result}")
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
            
            n = len(successful_results)
            report.avg_duration_seconds = report.total_duration_seconds / n
            report.avg_prompt_tokens = report.total_prompt_tokens / n
            report.avg_completion_tokens = report.total_completion_tokens / n
            report.avg_total_tokens = report.total_tokens / n
            report.avg_thinking_tokens = report.total_thinking_tokens / n
            report.avg_cost_usd = report.total_cost_usd / n
            report.avg_iterations = sum(r.iterations for r in successful_results) / n
        
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
        
        logger.info(
            f"Benchmark completed in {self.report.total_duration_seconds:.2f}s, "
            f"total cost: ${self.report.total_cost_usd:.4f}"
        )
        
        return self.report

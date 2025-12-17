#!/usr/bin/env python3
"""
Model Benchmark Runner - Execute tasks across multiple LLM models and generate reports.

Usage:
    python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir ./tasks --output-dir ./results
    
    # With specific models
    python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir ./tasks --models claude-sonnet gpt-4

See README.md for full documentation.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .models import BenchmarkConfig, ModelConfig, ProviderType
from .providers import DEFAULT_MODELS
from .runner import BenchmarkRunner
from .reports import ReportGenerator

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(project_root / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Predefined model configurations with real model names
AVAILABLE_MODELS = {
    # OpenRouter models - Latest models (December 2024)
    "claude-opus-4.5": ModelConfig(
        name="anthropic/claude-opus-4.5",
        provider=ProviderType.OPENROUTER,
        display_name="Claude Opus 4.5",
        input_price_per_million=15.0,
        output_price_per_million=75.0,
    ),
    "claude-sonnet-4.5": ModelConfig(
        name="anthropic/claude-sonnet-4.5",
        provider=ProviderType.OPENROUTER,
        display_name="Claude Sonnet 4.5",
        input_price_per_million=3.0,
        output_price_per_million=15.0,
    ),
    "glm-4.6": ModelConfig(
        name="z-ai/glm-4.6",
        provider=ProviderType.OPENROUTER,
        display_name="GLM 4.6",
        input_price_per_million=0.30,
        output_price_per_million=0.90,
    ),
    "gpt-5.1": ModelConfig(
        name="openai/gpt-5.1",
        provider=ProviderType.OPENROUTER,
        display_name="GPT-5.1",
        input_price_per_million=2.50,
        output_price_per_million=10.0,
    ),
    "grok-4.1-fast": ModelConfig(
        name="x-ai/grok-4.1-fast",
        provider=ProviderType.OPENROUTER,
        display_name="Grok 4.1 Fast",
        input_price_per_million=0.20,
        output_price_per_million=0.50,
    ),
    "gemini-3-pro": ModelConfig(
        name="google/gemini-3-pro-preview",
        provider=ProviderType.OPENROUTER,
        display_name="Gemini 3 Pro",
        input_price_per_million=1.25,
        output_price_per_million=10.0,
    ),
    # Cerebras models
    "cerebras-glm-4.6": ModelConfig(
        name="zai-glm-4.6",
        provider=ProviderType.CEREBRAS,
        display_name="GLM 4.6 (Cerebras)",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    ),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run benchmark tasks across multiple LLM models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with all default models
    python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir ./tasks
    
    # Run with specific models
    python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir ./tasks --models claude-sonnet-4.5 gpt-5.1
    
    # Run with custom settings
    python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir ./tasks --batch-size 3 --timeout 600
    
Available models:
    OpenRouter: claude-opus-4.5, claude-sonnet-4.5, glm-4.6, gpt-5.1, grok-4.1-fast, gemini-3n
    Cerebras: cerebras-glm-4.6
        """
    )
    
    parser.add_argument(
        "--tasks-dir",
        type=str,
        required=False,
        default=None,
        help="Directory containing .txt task files"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Output directory for reports (default: benchmark_results)"
    )
    
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=None,
        help="Specific models to test (default: all available models)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of tasks to run in parallel per model (default: 1)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per task in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        help="Maximum agent iterations per task (default: 20)"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )
    
    return parser.parse_args()


def print_summary(report, report_paths: dict):
    """Print detailed summary with per-model metrics and success/failure counts."""
    print("\n" + "=" * 120)
    print("BENCHMARK COMPLETE")
    print("=" * 120)
    print(f"Total Duration: {report.total_duration_seconds:.2f}s")
    print(f"Total Cost: ${report.total_cost_usd:.6f}")
    print(f"Total Tasks: {report.total_tasks}")
    print(f"Models Tested: {len(report.model_reports)}")
    
    # Per-model summary table
    print("\n## Per-Model Summary\n")
    
    # Header - widths: #=4, Model=27, Success=10, Requests=10, AvgTime=12, AvgThink=14, AvgTokens=14, TokSec=12, AvgCost=14, TotalThink=16, TotalTokens=16, TotalCost=14
    header = (
        f"| {'#':>2} "
        f"| {'Model':<25} "
        f"| {'Success':<8} "
        f"| {'Requests':>8} "
        f"| {'Avg Time':>10} "
        f"| {'Avg Think':>12} "
        f"| {'Avg Tokens':>12} "
        f"| {'Tok/Sec':>10} "
        f"| {'Avg Cost':>12} "
        f"| {'Total Think':>14} "
        f"| {'Total Tokens':>14} "
        f"| {'Total Cost':>12} |"
    )
    separator = (
        f"|{'-'*4}"
        f"|{'-'*27}"
        f"|{'-'*10}"
        f"|{'-'*10}"
        f"|{'-'*12}"
        f"|{'-'*14}"
        f"|{'-'*14}"
        f"|{'-'*12}"
        f"|{'-'*14}"
        f"|{'-'*16}"
        f"|{'-'*16}"
        f"|{'-'*14}|"
    )
    
    print(header)
    print(separator)
    
    # Sort models by total tokens (ascending)
    sorted_models = sorted(report.model_reports.values(), key=lambda m: m.total_tokens)
    
    # Per-model rows
    for rank, model_report in enumerate(sorted_models, 1):
        success = model_report.successful_tasks
        total = model_report.total_tasks
        
        # Format success
        status = f"{success}/{total}"
        
        # Calculate tokens per second
        tok_per_sec = model_report.avg_total_tokens / model_report.avg_duration_seconds if model_report.avg_duration_seconds > 0 else 0
        
        row = (
            f"| {rank:>2} "
            f"| {model_report.display_name:<25} "
            f"| {status:<8} "
            f"| {model_report.total_requests:>8} "
            f"| {model_report.avg_duration_seconds:>9.2f}s "
            f"| {model_report.avg_thinking_tokens:>12,.0f} "
            f"| {model_report.avg_total_tokens:>12,.0f} "
            f"| {tok_per_sec:>10,.0f} "
            f"| ${model_report.avg_cost_usd:>11.4f} "
            f"| {model_report.total_thinking_tokens:>14,} "
            f"| {model_report.total_tokens:>14,} "
            f"| ${model_report.total_cost_usd:>11.4f} |"
        )
        print(row)
    
    print("\n" + "=" * 120)
    
    # Per-task summary
    print("\n## Per-Task Summary\n")
    
    # Collect all unique task IDs
    task_ids = set()
    for model_report in report.model_reports.values():
        for task_result in model_report.task_results:
            task_ids.add(task_result.task_id)
    task_ids = sorted(task_ids)
    
    if task_ids:
        # Get sorted models for consistent column order
        sorted_model_names = sorted([m.display_name for m in report.model_reports.values()])
        
        # Print header
        task_header = f"| {'Task':<30} |"
        for model_name in sorted_model_names:
            # Truncate model name if too long
            short_name = model_name[:15] if len(model_name) > 15 else model_name
            task_header += f" {short_name:<15} |"
        print(task_header)
        
        task_sep = f"|{'-'*32}|"
        for _ in sorted_model_names:
            task_sep += f"{'-'*17}|"
        print(task_sep)
        
        # Print each task row
        for task_id in task_ids:
            row = f"| {task_id:<30} |"
            for model_name in sorted_model_names:
                model_report = next((m for m in report.model_reports.values() if m.display_name == model_name), None)
                if model_report:
                    task_result = next((r for r in model_report.task_results if r.task_id == task_id), None)
                    if task_result:
                        status = "✓" if task_result.success else "✗"
                        cell = f"{status} {task_result.total_tokens:,} tok"
                        row += f" {cell:<15} |"
                    else:
                        row += f" {'-':<15} |"
                else:
                    row += f" {'-':<15} |"
            print(row)
        
        print()
    
    # Detailed per-task results with responses
    print("\n" + "=" * 120)
    print("DETAILED TASK RESULTS")
    print("=" * 120)
    
    for task_id in task_ids:
        # Get task content from first available result
        task_content = ""
        for model_report in report.model_reports.values():
            task_result = next((r for r in model_report.task_results if r.task_id == task_id), None)
            if task_result and task_result.task_content:
                task_content = task_result.task_content
                break
        
        print(f"\n{'─' * 120}")
        print(f"TASK: {task_id}")
        print(f"{'─' * 120}")
        if task_content:
            # Truncate long task descriptions
            display_content = task_content[:300] + "..." if len(task_content) > 300 else task_content
            print(f"Description: {display_content}")
        print()
        
        # Show each model's result for this task
        for model_report in sorted(report.model_reports.values(), key=lambda m: m.display_name):
            task_result = next((r for r in model_report.task_results if r.task_id == task_id), None)
            if task_result:
                status = "✓ SUCCESS" if task_result.success else "✗ FAILED"
                print(f"  [{model_report.display_name}] {status}")
                print(f"    Time: {task_result.duration_seconds:.2f}s | Tokens: {task_result.total_tokens:,} | Think: {task_result.thinking_tokens:,} | Cost: ${task_result.cost_usd:.4f}")
                
                if task_result.error_message:
                    print(f"    Error: {task_result.error_message}")
                
                if task_result.response:
                    # Show truncated response
                    response_preview = task_result.response[:500].replace('\n', ' ')
                    if len(task_result.response) > 500:
                        response_preview += "..."
                    print(f"    Response: {response_preview}")
                print()
    
    # Show failed models details if any
    failed_models = [m for m in report.model_reports.values() if m.failed_tasks > 0]
    if failed_models:
        print("\n" + "-" * 100)
        print("FAILED REQUESTS DETAILS")
        print("-" * 100)
        for model_report in failed_models:
            print(f"\n{model_report.display_name}:")
            for task_result in model_report.task_results:
                if not task_result.success:
                    print(f"  - Task '{task_result.task_id}': {task_result.error_message}")
    
    # Reports generated
    print("\n" + "-" * 100)
    print("REPORTS GENERATED")
    print("-" * 100)
    for report_type, path in report_paths.items():
        print(f"  {report_type:<10}: {path}")
    
    print("=" * 100 + "\n")


def list_available_models():
    """Print available models and their configurations."""
    print("\nAvailable Models:")
    print("=" * 80)
    print(f"{'Alias':<20} {'Model ID':<40} {'Provider':<12}")
    print("-" * 80)
    
    for alias, config in AVAILABLE_MODELS.items():
        print(f"{alias:<20} {config.name:<40} {config.provider.value:<12}")
    
    print("\nUsage: --models claude-sonnet-4.5 gpt-5.1 gemini-2.5-pro")
    print()


def get_selected_models(model_aliases: list[str] | None) -> list[ModelConfig]:
    """Get model configurations from aliases."""
    if model_aliases is None:
        return list(AVAILABLE_MODELS.values())
    
    models = []
    for alias in model_aliases:
        if alias in AVAILABLE_MODELS:
            models.append(AVAILABLE_MODELS[alias])
        else:
            logger.warning(f"Unknown model alias: {alias}. Skipping.")
            print(f"Warning: Unknown model '{alias}'. Available: {list(AVAILABLE_MODELS.keys())}")
    
    if not models:
        raise ValueError("No valid models selected")
    
    return models


async def main():
    args = parse_args()
    
    if args.list_models:
        list_available_models()
        return
    
    # Validate tasks-dir is provided when not listing models
    if not args.tasks_dir:
        print("Error: --tasks-dir is required")
        print("Use --list-models to see available models")
        sys.exit(1)
    
    # Validate environment
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    
    if not openrouter_key and not cerebras_key:
        print("Error: No API keys found. Set OPENROUTER_API_KEY and/or CEREBRAS_API_KEY")
        print("Copy .env.example to .env and add your keys")
        sys.exit(1)
    
    # Get selected models
    try:
        models = get_selected_models(args.models)
    except ValueError as e:
        print(f"Error: {e}")
        list_available_models()
        sys.exit(1)
    
    # Filter models based on available API keys
    available_models = []
    for model in models:
        if model.provider == ProviderType.OPENROUTER and not openrouter_key:
            logger.warning(f"Skipping {model.name}: OPENROUTER_API_KEY not set")
            continue
        if model.provider == ProviderType.CEREBRAS and not cerebras_key:
            logger.warning(f"Skipping {model.name}: CEREBRAS_API_KEY not set")
            continue
        available_models.append(model)
    
    if not available_models:
        print("Error: No models available with current API keys")
        sys.exit(1)
    
    # Create benchmark config
    config = BenchmarkConfig(
        tasks_directory=args.tasks_dir,
        output_directory=args.output_dir,
        max_iterations=args.max_iterations,
        batch_size=args.batch_size,
        timeout_seconds=args.timeout,
        models=available_models,
    )
    
    print("\n" + "=" * 80)
    print("MODEL BENCHMARK")
    print("=" * 80)
    print(f"Tasks Directory: {config.tasks_directory}")
    print(f"Output Directory: {config.output_directory}")
    print(f"Models: {[m.get_display_name() for m in config.models]}")
    print(f"Batch Size: {config.batch_size}")
    print(f"Timeout: {config.timeout_seconds}s")
    print("=" * 80 + "\n")
    
    # Run benchmark
    runner = BenchmarkRunner(config)
    report = await runner.run()
    
    # Generate reports
    report_generator = ReportGenerator(report, config.output_directory)
    report_paths = report_generator.generate_all()
    
    # Print summary
    print_summary(report, report_paths)


if __name__ == "__main__":
    asyncio.run(main())

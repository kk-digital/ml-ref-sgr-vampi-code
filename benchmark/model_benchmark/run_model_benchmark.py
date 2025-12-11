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
    "gemini-3n": ModelConfig(
        name="google/gemini-3n",
        provider=ProviderType.OPENROUTER,
        display_name="Gemini 3n",
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
    print("\n" + "=" * 100)
    print("BENCHMARK COMPLETE")
    print("=" * 100)
    print(f"Total Duration: {report.total_duration_seconds:.2f}s")
    print(f"Total Cost: ${report.total_cost_usd:.6f}")
    print(f"Total Tasks: {report.total_tasks}")
    print(f"Models Tested: {len(report.model_reports)}")
    
    # Per-model summary table
    print("\n" + "-" * 115)
    print("PER-MODEL SUMMARY")
    print("-" * 115)
    
    # Header
    header = (
        f"{'Model':<25} "
        f"{'Success':>8} "
        f"{'Failed':>8} "
        f"{'Avg Time':>10} "
        f"{'Avg Tokens':>12} "
        f"{'Total Tokens':>13} "
        f"{'Avg Think':>10} "
        f"{'Avg Cost':>12} "
        f"{'Total Cost':>12}"
    )
    print(header)
    print("-" * 115)
    
    # Per-model rows
    for model_report in report.model_reports.values():
        success = model_report.successful_tasks
        failed = model_report.failed_tasks
        total = model_report.total_tasks
        
        # Format success/failed with color indicators
        if failed > 0:
            status = f"{success}/{total}"
            failed_str = f"{failed}"
        else:
            status = f"{success}/{total}"
            failed_str = "0"
        
        row = (
            f"{model_report.display_name:<25} "
            f"{status:>8} "
            f"{failed_str:>8} "
            f"{model_report.avg_duration_seconds:>9.2f}s "
            f"{model_report.avg_total_tokens:>12.0f} "
            f"{model_report.total_tokens:>13} "
            f"{model_report.avg_thinking_tokens:>10.0f} "
            f"${model_report.avg_cost_usd:>11.6f} "
            f"${model_report.total_cost_usd:>11.6f}"
        )
        print(row)
    
    print("-" * 115)
    
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

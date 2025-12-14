"""Report generation for benchmark results."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import BenchmarkReport, ModelReport

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates various report formats from benchmark results."""
    
    def __init__(self, report: BenchmarkReport, output_dir: str = "benchmark_results"):
        self.report = report
        # Create benchmark-specific subdirectory
        self.base_output_dir = Path(output_dir)
        self.output_dir = self.base_output_dir / report.benchmark_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize model/task name for use as directory name."""
        # Replace problematic characters with underscores
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
            name = name.replace(char, '_')
        return name
    
    def generate_all(self) -> dict[str, Path]:
        """Generate all report formats and return paths."""
        paths = {}
        # Save individual task results per model/task
        self.save_per_task_results()
        paths["json"] = self.generate_json_report()
        paths["summary"] = self.generate_summary_report()
        paths["csv"] = self.generate_csv_report()
        paths["markdown"] = self.generate_markdown_report()
        return paths
    
    def save_per_task_results(self) -> None:
        """Save individual task results in benchmark_results/<benchmark_id>/<model_name>/<task_name>/ structure."""
        for model_name, model_report in self.report.model_reports.items():
            model_dir_name = self._sanitize_name(model_report.display_name)
            model_dir = self.output_dir / "models" / model_dir_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            for task_result in model_report.task_results:
                task_dir_name = self._sanitize_name(task_result.task_id)
                task_dir = model_dir / task_dir_name
                task_dir.mkdir(parents=True, exist_ok=True)
                
                # Save task result as JSON
                result_file = task_dir / "result.json"
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(task_result.model_dump(mode="json"), f, indent=2, default=str)
                
                # Save response content separately if available
                if task_result.response:
                    response_file = task_dir / "response.txt"
                    with open(response_file, "w", encoding="utf-8") as f:
                        f.write(task_result.response)
                
                logger.debug(f"Saved task result: {task_dir}")
            
            logger.info(f"Saved {len(model_report.task_results)} task results for model: {model_report.display_name}")
    
    def generate_json_report(self) -> Path:
        """Generate detailed JSON report."""
        filename = f"{self.report.benchmark_id}_full.json"
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.report.model_dump(mode="json"), f, indent=2, default=str)
        
        logger.info(f"JSON report saved: {filepath}")
        return filepath
    
    def generate_summary_report(self) -> Path:
        """Generate human-readable summary report."""
        filename = f"{self.report.benchmark_id}_summary.txt"
        filepath = self.output_dir / filename
        
        lines = []
        lines.append("=" * 80)
        lines.append("MODEL BENCHMARK SUMMARY REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Benchmark ID: {self.report.benchmark_id}")
        lines.append(f"Start Time: {self.report.start_time}")
        lines.append(f"End Time: {self.report.end_time}")
        lines.append(f"Total Duration: {self.report.total_duration_seconds:.2f} seconds")
        lines.append(f"Tasks Directory: {self.report.tasks_directory}")
        lines.append(f"Total Tasks: {self.report.total_tasks}")
        lines.append(f"Models Tested: {len(self.report.models_tested)}")
        lines.append(f"Total Cost: ${self.report.total_cost_usd:.6f}")
        lines.append("")
        
        lines.append("-" * 80)
        lines.append("PER-MODEL RESULTS")
        lines.append("-" * 80)
        
        for model_name, model_report in self.report.model_reports.items():
            lines.append("")
            lines.append(f"Model: {model_report.display_name}")
            lines.append(f"  Provider: {model_report.provider.value}")
            lines.append(f"  Tasks: {model_report.successful_tasks}/{model_report.total_tasks} successful")
            lines.append("")
            lines.append("  AVERAGES (per task):")
            lines.append(f"    - Time: {model_report.avg_duration_seconds:.2f}s")
            lines.append(f"    - Prompt Tokens: {model_report.avg_prompt_tokens:.0f}")
            lines.append(f"    - Completion Tokens: {model_report.avg_completion_tokens:.0f}")
            lines.append(f"    - Total Tokens: {model_report.avg_total_tokens:.0f}")
            lines.append(f"    - Thinking Tokens: {model_report.avg_thinking_tokens:.0f}")
            lines.append(f"    - Cost: ${model_report.avg_cost_usd:.6f}")
            lines.append(f"    - Iterations: {model_report.avg_iterations:.1f}")
            lines.append("")
            lines.append("  TOTALS:")
            lines.append(f"    - Total Time: {model_report.total_duration_seconds:.2f}s")
            lines.append(f"    - Total Tokens: {model_report.total_tokens}")
            lines.append(f"    - Total Thinking Tokens: {model_report.total_thinking_tokens}")
            lines.append(f"    - Total Cost: ${model_report.total_cost_usd:.6f}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("COMPARISON TABLE")
        lines.append("=" * 80)
        lines.append("")
        
        header = (
            f"| {'#':>2} "
            f"| {'Model':<25} "
            f"| {'Success':<8} "
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
            f"|{'-'*12}"
            f"|{'-'*14}"
            f"|{'-'*14}"
            f"|{'-'*12}"
            f"|{'-'*14}"
            f"|{'-'*16}"
            f"|{'-'*16}"
            f"|{'-'*14}|"
        )
        lines.append(header)
        lines.append(separator)
        
        # Sort models by total tokens (ascending)
        sorted_models = sorted(self.report.model_reports.values(), key=lambda m: m.total_tokens)
        
        for rank, model_report in enumerate(sorted_models, 1):
            success_rate = f"{model_report.successful_tasks}/{model_report.total_tasks}"
            tok_per_sec = model_report.avg_total_tokens / model_report.avg_duration_seconds if model_report.avg_duration_seconds > 0 else 0
            row = (
                f"| {rank:>2} "
                f"| {model_report.display_name:<25} "
                f"| {success_rate:<8} "
                f"| {model_report.avg_duration_seconds:>9.2f}s "
                f"| {model_report.avg_thinking_tokens:>12,.0f} "
                f"| {model_report.avg_total_tokens:>12,.0f} "
                f"| {tok_per_sec:>10,.0f} "
                f"| ${model_report.avg_cost_usd:>11.4f} "
                f"| {model_report.total_thinking_tokens:>14,} "
                f"| {model_report.total_tokens:>14,} "
                f"| ${model_report.total_cost_usd:>11.4f} |"
            )
            lines.append(row)
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("PER-TASK SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        
        # Collect all unique task IDs
        task_ids = set()
        for model_report in self.report.model_reports.values():
            for task_result in model_report.task_results:
                task_ids.add(task_result.task_id)
        task_ids = sorted(task_ids)
        
        if task_ids:
            # Get sorted models for consistent column order
            sorted_model_names = sorted([m.display_name for m in self.report.model_reports.values()])
            
            # Print header
            task_header = f"| {'Task':<30} |"
            for model_name in sorted_model_names:
                short_name = model_name[:15] if len(model_name) > 15 else model_name
                task_header += f" {short_name:<15} |"
            lines.append(task_header)
            
            task_sep = f"|{'-'*32}|"
            for _ in sorted_model_names:
                task_sep += f"{'-'*17}|"
            lines.append(task_sep)
            
            # Print each task row
            for task_id in task_ids:
                row = f"| {task_id:<30} |"
                for model_name in sorted_model_names:
                    model_report = next((m for m in self.report.model_reports.values() if m.display_name == model_name), None)
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
                lines.append(row)
        
        lines.append("")
        lines.append("=" * 80)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Summary report saved: {filepath}")
        return filepath
    
    def generate_csv_report(self) -> Path:
        """Generate CSV report for spreadsheet analysis."""
        filename = f"{self.report.benchmark_id}_results.csv"
        filepath = self.output_dir / filename
        
        headers = [
            "model_name",
            "display_name",
            "provider",
            "task_id",
            "success",
            "duration_seconds",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "thinking_tokens",
            "cost_usd",
            "iterations",
            "error_message",
        ]
        
        rows = []
        for model_report in self.report.model_reports.values():
            for task_result in model_report.task_results:
                row = [
                    model_report.model_name,
                    model_report.display_name,
                    model_report.provider.value,
                    task_result.task_id,
                    str(task_result.success),
                    f"{task_result.duration_seconds:.4f}",
                    str(task_result.prompt_tokens),
                    str(task_result.completion_tokens),
                    str(task_result.total_tokens),
                    str(task_result.thinking_tokens),
                    f"{task_result.cost_usd:.8f}",
                    str(task_result.iterations),
                    task_result.error_message or "",
                ]
                rows.append(",".join(row))
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            f.write("\n".join(rows))
        
        logger.info(f"CSV report saved: {filepath}")
        return filepath
    
    def generate_markdown_report(self) -> Path:
        """Generate Markdown report for documentation."""
        filename = f"{self.report.benchmark_id}_report.md"
        filepath = self.output_dir / filename
        
        lines = []
        lines.append("# Model Benchmark Report")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- **Benchmark ID**: `{self.report.benchmark_id}`")
        lines.append(f"- **Start Time**: {self.report.start_time}")
        lines.append(f"- **End Time**: {self.report.end_time}")
        lines.append(f"- **Total Duration**: {self.report.total_duration_seconds:.2f} seconds")
        lines.append(f"- **Tasks Directory**: `{self.report.tasks_directory}`")
        lines.append(f"- **Total Tasks**: {self.report.total_tasks}")
        lines.append(f"- **Models Tested**: {len(self.report.models_tested)}")
        lines.append(f"- **Total Cost**: ${self.report.total_cost_usd:.6f}")
        lines.append("")
        
        lines.append("## Summary Comparison")
        lines.append("")
        lines.append("| # | Model | Success | Avg Time | Avg Think | Avg Tokens | Tok/Sec | Avg Cost | Total Think | Total Tokens | Total Cost |")
        lines.append("|---|-------|---------|----------|-----------|------------|---------|----------|-------------|--------------|------------|")
        
        # Sort models by total tokens (ascending)
        sorted_models = sorted(self.report.model_reports.values(), key=lambda m: m.total_tokens)
        
        for rank, model_report in enumerate(sorted_models, 1):
            success_rate = f"{model_report.successful_tasks}/{model_report.total_tasks}"
            tok_per_sec = model_report.avg_total_tokens / model_report.avg_duration_seconds if model_report.avg_duration_seconds > 0 else 0
            lines.append(
                f"| {rank} | {model_report.display_name} | "
                f"{success_rate} | "
                f"{model_report.avg_duration_seconds:.2f}s | "
                f"{model_report.avg_thinking_tokens:,.0f} | "
                f"{model_report.avg_total_tokens:,.0f} | "
                f"{tok_per_sec:,.0f} | "
                f"${model_report.avg_cost_usd:.4f} | "
                f"{model_report.total_thinking_tokens:,} | "
                f"{model_report.total_tokens:,} | "
                f"${model_report.total_cost_usd:.4f} |"
            )
        
        lines.append("")
        lines.append("## Per-Task Summary")
        lines.append("")
        lines.append(self._generate_per_task_summary_markdown())
        lines.append("")
        
        lines.append("## Detailed Results by Model")
        lines.append("")
        
        for model_report in self.report.model_reports.values():
            lines.append(f"### {model_report.display_name}")
            lines.append("")
            lines.append(f"- **Provider**: {model_report.provider.value}")
            lines.append(f"- **Model ID**: `{model_report.model_name}`")
            lines.append("")
            lines.append("#### Averages (per task)")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Time | {model_report.avg_duration_seconds:.2f}s |")
            lines.append(f"| Prompt Tokens | {model_report.avg_prompt_tokens:.0f} |")
            lines.append(f"| Completion Tokens | {model_report.avg_completion_tokens:.0f} |")
            lines.append(f"| Total Tokens | {model_report.avg_total_tokens:.0f} |")
            lines.append(f"| Thinking Tokens | {model_report.avg_thinking_tokens:.0f} |")
            lines.append(f"| Cost | ${model_report.avg_cost_usd:.6f} |")
            lines.append("")
            lines.append("#### Totals")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Total Time | {model_report.total_duration_seconds:.2f}s |")
            lines.append(f"| Total Tokens | {model_report.total_tokens} |")
            lines.append(f"| Total Thinking Tokens | {model_report.total_thinking_tokens} |")
            lines.append(f"| Total Cost | ${model_report.total_cost_usd:.6f} |")
            lines.append(f"| Successful Tasks | {model_report.successful_tasks}/{model_report.total_tasks} |")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*Generated at {datetime.now().isoformat()}*")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Markdown report saved: {filepath}")
        return filepath
    
    def _generate_per_task_summary_markdown(self) -> str:
        """Generate per-task summary table in markdown format."""
        # Collect all unique task IDs
        task_ids = set()
        for model_report in self.report.model_reports.values():
            for task_result in model_report.task_results:
                task_ids.add(task_result.task_id)
        task_ids = sorted(task_ids)
        
        if not task_ids:
            return "No tasks found."
        
        lines = []
        
        # For each task, show results across all models
        for task_id in task_ids:
            # Get task content from first available result
            task_content = ""
            for model_report in self.report.model_reports.values():
                task_result = next((r for r in model_report.task_results if r.task_id == task_id), None)
                if task_result and task_result.task_content:
                    task_content = task_result.task_content
                    break
            
            lines.append(f"### Task: {task_id}")
            lines.append("")
            if task_content:
                lines.append("**Task Description:**")
                lines.append("")
                lines.append(f"> {task_content[:500]}{'...' if len(task_content) > 500 else ''}")
                lines.append("")
            
            lines.append("**Results:**")
            lines.append("")
            lines.append("| Model | Success | Time | Tokens | Think | Cost |")
            lines.append("|-------|---------|------|--------|-------|------|")
            
            for model_report in sorted(self.report.model_reports.values(), key=lambda m: m.display_name):
                task_result = next((r for r in model_report.task_results if r.task_id == task_id), None)
                if task_result:
                    success = "✓" if task_result.success else "✗"
                    lines.append(
                        f"| {model_report.display_name} | "
                        f"{success} | "
                        f"{task_result.duration_seconds:.2f}s | "
                        f"{task_result.total_tokens:,} | "
                        f"{task_result.thinking_tokens:,} | "
                        f"${task_result.cost_usd:.4f} |"
                    )
                else:
                    lines.append(f"| {model_report.display_name} | - | - | - | - | - |")
            
            lines.append("")
            
            # Add response content for each model
            lines.append("**Model Responses:**")
            lines.append("")
            for model_report in sorted(self.report.model_reports.values(), key=lambda m: m.display_name):
                task_result = next((r for r in model_report.task_results if r.task_id == task_id), None)
                if task_result:
                    lines.append(f"<details>")
                    lines.append(f"<summary><strong>{model_report.display_name}</strong> {'✓' if task_result.success else '✗'}</summary>")
                    lines.append("")
                    if task_result.error_message:
                        lines.append(f"**Error:** {task_result.error_message}")
                        lines.append("")
                    if task_result.response:
                        lines.append("```")
                        # Truncate very long responses
                        response_text = task_result.response
                        if len(response_text) > 5000:
                            response_text = response_text[:5000] + "\n\n... [truncated, see full response in models/<model>/<task>/response.txt]"
                        lines.append(response_text)
                        lines.append("```")
                    else:
                        lines.append("*No response content available*")
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_per_task_summary(self) -> dict[str, dict[str, dict]]:
        """Get per-task summary data structure.
        
        Returns:
            dict mapping task_id -> model_name -> result summary
        """
        task_summary = {}
        
        for model_report in self.report.model_reports.values():
            for task_result in model_report.task_results:
                if task_result.task_id not in task_summary:
                    task_summary[task_result.task_id] = {}
                
                task_summary[task_result.task_id][model_report.display_name] = {
                    "success": task_result.success,
                    "duration_seconds": task_result.duration_seconds,
                    "total_tokens": task_result.total_tokens,
                    "thinking_tokens": task_result.thinking_tokens,
                    "cost_usd": task_result.cost_usd,
                    "error_message": task_result.error_message,
                }
        
        return task_summary

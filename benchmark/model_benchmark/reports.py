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
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all(self) -> dict[str, Path]:
        """Generate all report formats and return paths."""
        paths = {}
        paths["json"] = self.generate_json_report()
        paths["summary"] = self.generate_summary_report()
        paths["csv"] = self.generate_csv_report()
        paths["markdown"] = self.generate_markdown_report()
        return paths
    
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

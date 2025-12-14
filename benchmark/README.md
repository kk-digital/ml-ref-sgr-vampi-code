# Model Benchmark Module

Benchmark multiple LLM models through the **sgr-vampi-code agent** and generate comprehensive comparison reports.

## Overview

This benchmark runs coding tasks through the sgr-vampi-code agent API, testing different LLM backends (via OpenRouter and Cerebras) to compare their performance on real-world coding tasks.

## Requirements

### 1. System Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Network access to API endpoints

### 2. API Keys

| Provider | Environment Variable | Get Key From |
|----------|---------------------|---------------|
| OpenRouter | `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| Cerebras | `CEREBRAS_API_KEY` | https://cloud.cerebras.ai/ |

### 3. sgr-vampi-code Agent API

The benchmark requires the sgr-vampi-code agent API to be running. This is the core component that executes tasks using the specified LLM models.

---

## End-to-End Setup Guide

### Step 1: Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/vamplabAI/sgr-vampi-code.git
cd sgr-vampi-code

# Install dependencies with uv
uv sync
```

### Step 2: Configure Environment Variables

```bash
# Create .env file in project root
cp config.yaml.example config.yaml

# Add your API keys to .env file
echo "OPENROUTER_API_KEY=your-openrouter-key-here" >> .env
echo "CEREBRAS_API_KEY=your-cerebras-key-here" >> .env
```

Or set them directly in your shell:

```bash
export OPENROUTER_API_KEY="your-openrouter-key-here"
export CEREBRAS_API_KEY="your-cerebras-key-here"
```

### Step 3: Start the sgr-vampi-code Agent API

```bash
# Start the API server (default port: 8010)
uv run python -m sgr_deep_research
```

Keep this terminal running. The API should be available at `http://localhost:8010`.

### Step 4: Run the Benchmark

Open a **new terminal** and run:

```bash
# Run benchmark with ALL models (default)
uv run python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir benchmark/model_benchmark/tasks

# Or run with specific models
uv run python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir benchmark/model_benchmark/tasks --models claude-sonnet-4.5 gpt-5.1 gemini-2.5-pro

uv run python -m benchmark.model_benchmark.run_model_benchmark --tasks-dir benchmark/model_benchmark/tasks --models grok-4.1-fast
```

### Step 5: View Results

Reports are generated in `benchmark_results/` directory:

```
benchmark_results/
├── benchmark_YYYYMMDD_HHMMSS_xxxxx_full.json      # Complete raw data
├── benchmark_YYYYMMDD_HHMMSS_xxxxx_summary.txt    # Human-readable summary
├── benchmark_YYYYMMDD_HHMMSS_xxxxx_results.csv    # Spreadsheet format
└── benchmark_YYYYMMDD_HHMMSS_xxxxx_report.md      # Markdown report
```

---

## Available Models

### OpenRouter Models (requires `OPENROUTER_API_KEY`)

| Alias | Model ID | Description |
|-------|----------|-------------|
| `claude-opus-4.5` | anthropic/claude-opus-4.5 | Claude Opus 4.5 - Frontier reasoning model |
| `claude-sonnet-4.5` | anthropic/claude-sonnet-4.5 | Claude Sonnet 4.5 - Best for coding |
| `glm-4.6` | z-ai/glm-4.6 | GLM 4.6 - 200K context |
| `gpt-5.1` | openai/gpt-5.1 | GPT-5.1 - Latest OpenAI model |
| `grok-4.1-fast` | x-ai/grok-4.1-fast | Grok 4.1 Fast - 2M context |
| `gemini-2.5-pro` | google/gemini-2.5-pro | Gemini 2.5 Pro - Google's best |

### Cerebras Models (requires `CEREBRAS_API_KEY`)

| Alias | Model ID | Description |
|-------|----------|-------------|
| `cerebras-glm-4.6` | zai-glm-4.6 | GLM 4.6 on Cerebras (ultra-fast inference) |

### List All Models

```bash
uv run python -m benchmark.model_benchmark.run_model_benchmark --list-models
```

---

## CLI Reference

```bash
uv run python -m benchmark.model_benchmark.run_model_benchmark [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--tasks-dir` | (required) | Directory containing `.txt` task files |
| `--output-dir` | `benchmark_results` | Output directory for reports |
| `--models` | all models | Space-separated list of model aliases |
| `--batch-size` | `1` | Tasks to run in parallel per model |
| `--timeout` | `300` | Timeout per task in seconds |
| `--max-iterations` | `20` | Maximum agent iterations per task |
| `--list-models` | - | List available models and exit |

---

## Creating Custom Tasks

Tasks are `.txt` files in the tasks directory. Each file contains one coding task:

```bash
# Example: Create a new task
echo "Write a Python function that implements binary search on a sorted list." \
    > benchmark/model_benchmark/tasks/task_007_binary_search.txt
```

### Task File Naming Convention

```
task_NNN_description.txt
```

- `NNN` - Sequential number (001, 002, etc.)
- `description` - Brief task description (snake_case)

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | OpenRouter API key (required for OpenRouter models) |
| `CEREBRAS_API_KEY` | - | Cerebras API key (required for Cerebras models) |
| `SGR_API_BASE_URL` | `http://localhost:8010` | sgr-vampi-code agent API URL |

---

## Troubleshooting

### "All connection attempts failed"

The sgr-vampi-code agent API is not running. Start it with:

```bash
uv run python -m sgr_deep_research
```

### "OPENROUTER_API_KEY environment variable not set"

Set your API key:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

### "No .txt task files found"

Ensure your tasks directory contains `.txt` files:

```bash
ls benchmark/model_benchmark/tasks/
```

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Benchmark CLI  │────▶│  sgr-vampi-code API  │────▶│  LLM Providers  │
│                 │     │  (localhost:8010)    │     │  - OpenRouter   │
│  run_model_     │     │                      │     │  - Cerebras     │
│  benchmark.py   │     │  Agent orchestration │     │                 │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
        │                                                    │
        │                                                    │
        ▼                                                    ▼
┌─────────────────┐                              ┌─────────────────┐
│  Reports        │                              │  Models         │
│  - JSON         │                              │  - Claude 4.5   │
│  - CSV          │                              │  - GPT-5.1      │
│  - Markdown     │                              │  - Gemini 2.5   │
│  - Summary      │                              │  - Grok 4.1     │
└─────────────────┘                              │  - GLM 4.6      │
                                                 └─────────────────┘
```

---

## License

MIT License - See main project LICENSE file.

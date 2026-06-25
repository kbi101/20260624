# Morphos

An autonomous AI agent system built on the ReAct pattern — everything runs locally. No cloud APIs, no external services.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) running locally with `gemma4:12b` pulled

```bash
ollama pull gemma4:12b
```

## Setup

```bash
pip install ollama httpx beautifulsoup4 readability-lxml rich
```

## Usage

### Interactive mode

```bash
python -m morphos.cli
```

Type your query at the `>` prompt. Type `quit` or press Ctrl+C to exit.

### Single query

```bash
python -m morphos.cli --query "What is 247 * 38 plus 15 squared?"
```

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `--query`, `-q` | — | A single query to run and exit |
| `--model` | `gemma4:12b` | Ollama model name |
| `--max-iters` | `10` | Maximum ReAct loop iterations |

## How It Works

Morphos uses a **ReAct** (Reason + Act) loop:

1. You type a query
2. The agent thinks, decides which tool to use, and executes it
3. Tool output is fed back as an observation
4. The cycle repeats until the agent produces a final answer or hits the iteration limit

### Available Tools

- **python_exec** — Runs Python code in a sandboxed subprocess (no network, timed out at 30s)
- **web_fetch** — Fetches a URL and extracts readable text using readability

## Project Structure

```
morphos/
├── agent.py         # ReAct loop (Thought → Action → Observation)
├── cli.py           # Terminal chat with rich output
├── config.py        # Model, iterations, timeouts
├── llm.py           # Ollama client wrapper
└── tools/
    ├── registry.py  # Pluggable tool system
    ├── python_exec.py   # Sandboxed Python execution
    └── web_fetch.py     # URL fetch + content extraction
```

## Roadmap

| Phase | Status | Description |
| --- | --- | --- |
| **001 — ReAct MVP** | Done | Core agent loop, tools, CLI |
| 002 — Memory & RAG | Planned | Vector DB, persistent memory |
| 003 — Dynamic Tooling | Planned | Self-written tools, reflection |
| 004 — Autonomous Growth | Planned | Self-improvement feedback loop |

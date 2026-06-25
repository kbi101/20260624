# Morphos — Local Autonomous Agent Specification

## Overview

Morphos is a locally-run autonomous agent system. An LLM acts as the reasoning engine inside a cyclic agentic loop with persistent memory, built-in tools, and reflection capabilities. **All components run on the user's machine.**

---

## Design Principles

1. 100% local — no cloud APIs, no external services
2. Modular — each component (brain, planner, executor, memory, tools) is replaceable
3. Iterative — ship a working MVP first, add complexity per phase
4. Safety-first — sandboxed code execution, iteration limits, cost controls

---

## Local-First Constraints

| Component | Cloud Alternative (morphos.md) | Local Replacement |
|-----------|-------------------------------|-------------------|
| LLM | GPT-4o, Claude 3.5 | **Ollama** (already on machine) |
| Vector DB | Pinecone, Weaviate | **ChromaDB** (local SQLite-backed) |
| Web Search | Tavily, Serper | Local HTTP fetch + HTML-to-text parser |
| Code Sandbox | E2B cloud sandbox | **Docker container** or subprocess with resource limits |
| Orchestration | LangGraph, CrewAI | Custom asyncio loop (lightweight, no framework dependency) |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│                  User CLI                      │
└────────────────────┬──────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│              Orchestrator (ReAct Loop)          │
│                                                │
│   Planner  →  decides next step                │
│   Executor →  runs tool                        │
│   Critic   →  validates output                 │
│   Reflector→  saves lessons to memory           │
└───────┬──────────┬──────────┬──────────────────┘
        │          │          │
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │ Tools  │ │Memory  │ │ LLM    │
   │Library │ │Store   │ │(Ollama)│
   └────────┘ └────────┘ └────────┘
```

### The ReAct Loop

Each iteration:
1. **Planner** receives current state + goal, outputs an action (think / use_tool / answer)
2. **Executor** runs the selected tool with arguments
3. **Critic** checks if the result is acceptable or needs another attempt
4. If not done → loop again. If too many iterations → exit with summary

Default max iterations per task: **10** (configurable).

---

## Core Components

### 1. LLM Interface (`brain`)

- Abstract interface that wraps any model provider
- Default implementation: **Ollama** (local)
- Supports multiple model slots: a fast small model for tool selection, a larger model for reasoning tasks
- Configurable via `config.yaml` — swap models without code changes

### 2. Tool Library (`tools`)

Built-in tools shipped with Morphos:

| Tool | Description |
|------|-------------|
| `python_repl` | Execute Python code in a sandboxed subprocess with timeout + output capture |
| `file_read` | Read a file from disk (whitelisted paths only) |
| `file_write` | Write content to a file |
| `web_fetch` | Fetch a URL, return clean markdown text |
| `directory_search` | Glob/grep-style file and content search |
| `calculator` | Direct eval of math expressions |

Tool creation: the agent can write new Python scripts that get registered as tools at runtime.

### 3. Memory Store (`memory`)

- **ChromaDB** for vector embeddings — stores facts, instructions, conversation history
- Two tiers:
  - *Working memory*: current session context (in-memory)
  - *Long-term memory*: persisted vector store + SQLite log of past interactions
- On each session end, a reflection pass summarizes key learnings and indexes them

### 4. Orchestrator (`orchestrator`)

- Async loop built on Python `asyncio`
- Manages the ReAct cycle: plan → execute → critique → reflect
- Enforces iteration limits and timeout per task
- Logs every step for debugging and post-hoc analysis

### 5. Critic / Reflector (`critic`)

- Second LLM call that reviews tool output before accepting it
- If output fails validation, feeds error back to Planner for retry
- End-of-session: analyzes all steps, extracts reusable patterns, updates long-term memory

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | **Python 3.11+** |
| LLM | **Ollama** (models: `llama3` fast + `qwen2.5:7b` or larger for reasoning) |
| Vector DB | **ChromaDB** (local, zero-config) |
| Embeddings | Ollama embedding API or sentence-transformers (local) |
| Web fetch | `httpx` + `trafilatura` (HTML → clean text, local) |
| Sandboxing | subprocess with `resource` limits + Docker (optional hardening) |
| Config | **YAML** — single `config.yaml` at project root |
| CLI | Click or argparse for terminal interface |

---

## Project Structure

```
morphos/
├── config.yaml                  # models, limits, paths
├── main.py                      # entry point
├── morphos/
│   ├── __init__.py
│   ├── brain/                   # LLM abstraction + Ollama adapter
│   │   ├── base.py
│   │   └── ollama_adapter.py
│   ├── tools/                   # tool registry + built-in tools
│   │   ├── registry.py
│   │   ├── python_repl.py
│   │   ├── file_ops.py
│   │   ├── web_fetcher.py
│   │   ├── search.py
│   │   └── calculator.py
│   ├── memory/                  # vector store + working context
│   │   ├── chroma_store.py
│   │   ├── working_memory.py
│   │   └── reflector.py
│   ├── orchestrator/            # ReAct loop engine
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── critic.py
│   │   └── loop.py
│   └── cli/                     # terminal interface
│       └── app.py
├── data/                        # ChromaDB storage, logs
│   ├── vector_store/
│   └── logs/
├── tests/
└── requirements.txt
```

---

## Implementation Phases

### Phase 1 — ReAct MVP (Target: working agent that can reason and use tools)
- Brain with Ollama adapter (chat + embeddings)
- Tool registry with 4 built-in tools: python_repl, file_read, calculator, directory_search
- Minimal orchestrator loop: planner → executor → answer (no critic yet)
- CLI: enter a task, see the reasoning trace and final answer
- Config: model selection, max iterations

### Phase 2 — Memory + RAG
- ChromaDB integration for persistent fact storage
- Working memory with context window management
- Session reflection on completion — save key learnings
- New tool: web_fetch (URL → text)
- Prompt injection of relevant memories from vector store each turn

### Phase 3 — Critic + Dynamic Tools
- Critic module for output validation and retry loops
- Agent can write and register new Python tools at runtime
- Docker-based sandboxing for untrusted code execution
- Log analysis: track which tools fail most, surface patterns

### Phase 4 — Autonomous Growth
- Background process that reviews past sessions and updates system instructions
- Tool library auto-curation: promote frequently-used agent scripts to permanent tools
- Multi-agent support: specialized sub-agents for distinct domains

---

## Open Questions (TBD)

1. Which Ollama models to default to? (speed vs quality trade-off)
2. Docker sandbox required for Phase 1, or acceptable without at first?
3. Embedding model: Ollama's built-in embed API, or a dedicated local sentence-transformers model?
4. Should the CLI support multi-turn conversation mode or single-task mode? (Both eventually. Start with multi-turn.)
5. Prompt templates: hand-crafted, or should we experiment with minimalistic prompts?

---

## Success Criteria Per Phase

| Phase | Definition of Done |
|-------|--------------------|
| 1 | Ask the agent a question requiring tool use → get correct answer with full trace visible |
| 2 | Second session remembers a fact learned in first session |
| 3 | Agent critiques its own bad output and retries successfully |
| 4 | System prompt or tool library improved without human intervention after multiple sessions |

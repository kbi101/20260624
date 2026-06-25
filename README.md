# Morphos — Autonomous AI Agent System

A fully autonomous, locally-run AI agent capable of web research, code execution, financial analysis, self-criticism, and continuous self-improvement through learned heuristics. No cloud APIs. No external services. Everything runs on your machine.

```
┌─────────── 1. Query ─────────────▶ Multi-Agent Router (optional)
│                                      ├─ FINANCE agent
│                                      ├─ RESEARCH agent  ◀── default
│                                      └─ CODING agent
│
▼        ▼ 2. ReAct Loop             ▼ 3. Tools executed
┌──── User     │  Thought → Action → Observe    │ web_search / web_fetch (Playwright Chrome)
│ │ Query      │  up to max-iters cycles        │ finance (yfinance) / python_exec
│ └────────────┼───────────────────────────────▶ │ calculator / memory_search
│              │                                └──────────────┬───────────────▼
│              │  4. Critic validates → accept/retry           ▼
│              │  5. Final Answer rendered to terminal    Working Memory (6k tokens)
│              │                                          ↓
│              └──────────────── on quit: Reflector ◀──▶ ChromaDB   (facts + lessons)
```

## Live Workflow Diagram

See [spec/diagram1.md](spec/diagram1.md) for the full mermaid flowchart with all components and data flows.

## Quick Start

### 1. Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com)** running locally with both models pulled:

```bash
ollama pull gemma4:12b
ollama pull nomic-embed-text
```

- **Google Chrome** installed (used by Playwright for authentic web browsing)

### 2. Install

```bash
pip install ollama httpx beautifulsoup4 readability-lxml rich playwright chromadb yfinance
playwright install   # downloads browser binaries if needed
```

### 3. Run

| Mode | Command | Description |
|------|---------|-------------|
| Interactive REPL | `python -m morphos.cli` | Full session with persistent memory, reflection on exit |
| Single query | `python -m morphos.cli --query "..."` | One-shot answer, exits immediately |
| Multi-agent routing | `python -m morphos.cli --multi-agent --query "..."` | Classifies query into FINANCE/RESEARCH/CODING before execution |
| Growth cycle | `python -m morphos.cli --grow` | Self-improvement: analyze past sessions, evolve prompts |
| Auto-evolve | `python -m morphos.cli --grow --auto-evolve` | Apply learned prompt patches automatically |

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--query`, `-q` | — | Single query to run and exit |
| `--model` | `gemma4:12b` | Ollama model name |
| `--max-iters` | `10` | Maximum ReAct loop iterations per query |
| `--no-critic` | off | Disable critic validation layer |
| `--critic-strictness` | `moderate` | Critic level: `loose`, `moderate`, or `strict` |
| `--multi-agent` | off | Enable routing to specialized sub-agents |
| `--grow` | off | Run one autonomous growth cycle |
| `--auto-evolve` | off | Auto-apply prompt patches from growth cycle |

## Architecture Overview

```mermaid
flowchart TB
    CLI[Terminal<br/>CLI + REPL] --> Router{-multi-agent?}
    Router -- yes --> Classify[LLM classify →<br/>FINANCE / RESEARCH<br/>/ CODING]
    Router -- no --> Agent
    Classify --> SubAgent{Specialized Agent}

    Agent[ReAct Loop] --> BuildPrompt[System Prompt Builder<br/>tools + RAG memory<br/>+ heuristic hints]
    SubAgent --> BuildPrompt

    BuildPrompt --> LLM[gemma4:12b via Ollama]
    LLM --> Parse{Parse response}
    Parse -- Final Answer --> Render[Rich CLI rendering]
    Parse -- Action --> ToolExec[Execute tool]
    ToolExec --> Critic[LLM quality<br/>validation]
    Critic -- reject --> LLM
    Critic -- accept --> Record[Analyzer records<br/>duration + status]
    Record --> MemoryStore[(Working Memory<br/>6000 token window)]
    MemoryStore --> LLM

    CLI -. quit .-> Reflector[Session Reflection<br/>extract facts, lessons,<br/>source heuristics]
    Reflector --> FactStore[(ChromaDB<br/>facts collection)]
    Reflector --> LessonStore[(ChromaDB<br/>lessons collection)]
    Reflector --> HeuristicFile[search_heuristics.json]

    ToolExec -->|web_search<br/>(duckduckgo.com)| Chrome[Playwright +<br/>real Chrome browser]
    ToolExec -->|finance| yf[yfinance library]
    ToolExec -->|memory_search| FactStore
```

## Features

### 🔍 Autonomous Web Research
Uses real Google Chrome via Playwright to browse the web genuinely. DuckDuckGo search integration — types queries like a human, avoids bot detection and CAPTCHAs. Pages are extracted with Mozilla's Readability algorithm + BeautifulSoup fallback for JavaScript-heavy SPAs.

### 📊 Real-Time Financial Data
Direct stock/ETF/cryptocurrency pricing via yfinance — bypasses Yahoo Finance web scraping issues entirely. Tested working from IP ranges that block Google Search and DDGS library.

### 🧠 Persistent Cross-Session Memory
ChromaDB-backed vector store with `nomic-embed-text` embeddings (served locally by Ollama). Two collections:
- **Facts** — discrete verifiable statements extracted during session reflection
- **Lessons** — tool usage patterns, what worked and what didn't

Memory is retrieved via semantic similarity search each turn and injected into the system prompt.

### ✋ Self-Criticism & Quality Gates
A separate LLM pass validates every tool result before it reaches the agent. Three strictness levels (`loose` / `moderate` / `strict`). Rejected outputs trigger automatic retry with different parameters or tools.

### 🌱 Autonomous Growth Cycle
Run `--grow` to analyze accumulated session logs and improve the system:
- **Prompt Evolution** — scans failure patterns, proposes targeted system prompt patches
- **Tool Curation** — promotes high-success dynamic tools, demotes chronic failures
- Reports saved as JSON with diffs for review

### 🤖 Multi-Agent Routing
Optional intelligent query classification dispatches to specialized sub-agents:

| Domain | Agent Name | Specialized Tools |
|--------|-----------|-------------------|
| FINANCE | `finance_agent` | finance, web_fetch, web_search, calculator |
| RESEARCH | `research_agent` | web_search, web_fetch, memory_search, python_exec |
| CODING | `coding_agent` | python_exec, file_read, directory_search, calculator |

Each sub-agent receives a narrowed tool set and domain-specific system prompt addon.

### 📝 Source Heuristics Engine
Learns which websites work for which query patterns. After successful sessions, the reflector extracts preferred source URLs and maps them to regex patterns. Future queries matching those patterns get direct URL hints injected into the system prompt — skipping expensive search steps entirely.

## Tool Reference

| Tool | Module | Description | Key Parameters |
|------|--------|-------------|---------------|
| `web_search` | `tools/web_search.py` | DuckDuckGo via real Chrome, heuristic-aware reranking | `query` |
| `web_fetch` | `tools/web_fetch.py` | Full page render + readability extraction (6000 char limit) | `url` |
| `finance` | `tools/finance.py` | yfinance: price, volume, market data | `symbol` or `text_query` |
| `python_exec` | `tools/python_exec.py` | Sandboxed Python with 30s timeout | `code` |
| `calculator` | `tools/calculator.py` | AST-safe arithmetic evaluation | `expression` |
| `memory_search` | `tools/memory_search.py` | Semantic query against ChromaDB facts/lessons | `query` |
| `file_read` | `tools/file_ops.py` | Path-whitelisted file reading | `filepath` |
| `file_write` | `tools/file_ops.py` | Path-whitelisted file writing | `filepath`, `content` |
| `directory_search` | `tools/directory_search.py` | Glob pattern file discovery | `pattern` |

## Project Structure

```
morphos/
├── agent.py              # ReAct loop (Thought → Action → Observation)
├── cli.py                # Rich terminal interface, event dispatcher
├── config.py             # Configuration dataclass
├── critic.py             # Output quality validation (3 strictness levels)
├── analyzer.py           # Performance metrics tracker per tool call
├── heuristics.py         # Learned source → URL pattern matching
├── multi_agent.py        # RouterAgent: classify + dispatch sub-agents
├── dynamic_tools.py      # Runtime-created tool persistence
├── llm.py                # Ollama chat client wrapper
├── docker_sandbox.py     # Container sandbox foundation (Phase 1)
│
├── tools/                # All agent capabilities
│   ├── browser.py        # Singleton Playwright manager, real Chrome
│   ├── web_search.py     # DuckDuckGo automation with reranking
│   ├── web_fetch.py      # Page rendering, readability extraction
│   ├── finance.py        # yfinance stock/crypto data
│   ├── python_exec.py    # Sandboxed code execution
│   ├── calculator.py     # Safe arithmetic expressions
│   ├── memory_search.py  # ChromaDB semantic search tool
│   ├── file_ops.py       # FileRead + FileWrite with path whitelist
│   ├── directory_search.py  # Glob pattern file finder
│   └── registry.py       # Pluggable tool registration system
│
├── memory/               # Persistent knowledge systems
│   ├── chroma_store.py   # ChromaDB vectors + Ollama embedder
│   ├── working_memory.py # Token-aware sliding window
│   └── reflector.py      # Post-session LLM fact/lesson/heuristic extraction
│
└── self_improve/         # Autonomous growth modules
    ├── prompt_evolver.py # Analyze failures → propose prompt patches
    ├── tool_curator.py   # Promote/demote tools by success rate
    └── growth_loop.py    # Orchestration + JSON report generation

data/
├── vector_store/         # ChromaDB persistent database
├── search_heuristics.json  # Learned source preferences
└── logs/                 # Analyzer session history
```

## Phase Rollout

| Phase | Spec File | Status | What's Included |
|-------|-----------|--------|-----------------|
| **001 — ReAct MVP** | [spec](spec/001-ReAct-MVP.md) | ✅ Complete | Core agent loop, python_exec, web_fetch, CLI |
| **002 — Memory + RAG** | [spec](spec/002-Memory-RAG.md) | ✅ Complete | ChromaDB vectors, session reflection, file ops, calculator |
| **003 — Critic & Dynamic Tools** | [spec](spec/003-Critic-DynamicTools.md) | ✅ Complete | Quality gates, runtime tool creation, analyzer logging |
| **004 — Autonomous Growth** | [spec](spec/004-AutonomousGrowth.md) | 🔄 In Progress | Self-improvement loops, multi-agent routing, source heuristics |

## Development

### Built With

This project was developed entirely with **[opencode](https://github.com/opencode-ai/opencode)** — the terminal-based AI coding agent. The development model was **[qwen3.6:27b](https://ollama.com/library/qwen3)**, running locally via Ollama. Every line of code, architecture decision, test run, and iteration flowed through this toolchain — making Morphos a real-world example of opencode-assisted agentic development.

### Stack

| Layer | Technology |
|-------|-----------|
| Local LLM inference | [Ollama](https://ollama.com) + `gemma4:12b` |
| Embeddings | Ollama + `nomic-embed-text` (768-dim vectors) |
| Web automation | [Playwright](https://playwright.dev) + real Google Chrome |
| Vector database | [ChromaDB](https://www.trychroma.com/) persistent client |
| Terminal UI | [Rich](https://rich.readthedocs.io/) — panels, syntax highlighting |
| Content extraction | [Readability.js](https://readability.net/) (Python port) + BeautifulSoup |
| Financial data | [yfinance](https://github.com/ranaroussi/yfinance) |

### Running Tests

```bash
# Single query test
python -m morphos.cli --query "What is AAPL stock price?"

# Multi-agent finance test
python -m morphos.cli --multi-agent --query "Compare S&P 500 vs NASDAQ"

# Growth cycle test
python -m morphos.cli --grow --auto-evolve
```

### Contributing

All contributions welcome. Please file issues for bugs and PRs for features. See [AGENTS.md](AGENTS.md) for project conventions.

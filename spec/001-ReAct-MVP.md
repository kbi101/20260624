# Phase 001 — ReAct MVP

## Goal
Build a minimal ReAct agent loop that can reason, use tools, and answer questions — everything runs locally.

## Scope

### Must Have
1. **Local LLM Interface**
   - Backend: Ollama (local inference)
   - Model: `gemma4:12b` (configurable via config file)
   - Abstraction layer to swap models without changing agent code

2. **ReAct Agent Loop**
   - Cyclic pattern: Thought → Action → Observation → repeat
   - Max iteration limit to prevent infinite loops (configurable, default 10)
   - Structured output parsing (Thought / Action / Action Input)

3. **Tool Registry**
   - Pluggable tool system with a shared interface
   - Initial tools:
     - `python_exec` — execute Python code in a restricted subprocess (no network access, timeout guard)
     - `web_fetch` — fetch a URL and extract readable text/markdown content (local HTTP, no cloud API)

4. **CLI Interface**
   - Terminal-based chat loop for user interaction
   - Displays agent thoughts, tool calls, and final answers

### Won't Do (Future Phases)
- Persistent memory / RAG (Phase 2)
- Dynamic tool creation and reflection (Phase 3)
- Autonomous growth and self-improvement (Phase 4)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI Chat   │ ◄──►│  ReAct Loop   │ ◄──►│ Local LLM   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  Tool Reg.   │
                    │             │
                    │ - py_exec   │
                    │ - web_fetch │
                    └─────────────┘
```

## Tech Stack (All Local)

| Layer | Technology |
| :--- | :--- |
| Language | Python 3.10+ |
| LLM Backend | Ollama |
| HTTP Client | `httpx` (async) |
| HTML Parsing | `beautifulsoup4` or `readability-lxml` |
| CLI | `rich` for terminal output |

## Success Criteria
- User asks a multi-step question requiring web lookup and calculation
- Agent reasons through steps, calls tools, and returns a correct final answer
- No external cloud APIs are called — everything runs on local machine

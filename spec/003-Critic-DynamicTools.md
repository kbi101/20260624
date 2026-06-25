# Phase 003 — Critic + Dynamic Tools

## Goal
Add self-validation via a critic module, allow the agent to write and register new tools at runtime, and harden code execution with Docker-based sandboxing.

## Scope

### Must Have

1. **Critic Module** (`morphos/critic.py`)
   - After each tool execution, a separate LLM call reviews the output for correctness, completeness, and safety
   - Decision: accept → proceed to next step or final answer; reject → feed error message back to planner for retry
   - Configurable critique prompts (e.g., "validate numerical results", "check for hallucination")

2. **Dynamic Tool Registration** (`morphos/tools/dynamic.py`)
   - Agent can write Python functions as new tools during a session
   - Functions are validated (AST check, no network/imports) then registered into the tool registry at runtime
   - Dynamic tools appear in the system prompt for subsequent turns
   - On session end, user is asked whether to persist dynamic tools permanently

3. **Docker Sandboxing** (`tools/python_exec.py` — modified)
   - Python code execution runs inside a Docker container with strict resource limits
   - No network access inside the sandbox
   - CPU/memory/time limits enforced at container level (e.g., 10s timeout, 256MB memory cap)

4. **Log Analysis** (`morphos/analyzer.py`)
   - Tracks tool execution history: success rate, failure patterns, latency per tool
   - End-of-session summary of which tools worked, which failed, and why
   - Outputs machine-readable JSON log + human-readable terminal report

### Won't Do (Future Phases)
- Background autonomous growth loop that rewrites prompts/tools on its own (Phase 4)
- Multi-agent coordination and sub-agent spawning (Phase 4)
- Tool library auto-curation based on usage frequency (Phase 4)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI Chat   │ ◄──►│  ReAct Loop   │ ◄──►│ Local LLM   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼───┐  ┌─────▼──┐   ┌────▼─────┐
         │ Tools   │  │ Critic │   │  Memory   │
         │Registry │  │(valida-│   │ (ChromaDB)│
         │        │  │ te/retr)│   │           │
         │Built-in│  └────────┘   └───────────┘
         │ + Dyn.│
         │Sandbox│
         └───────┘
```

## Components to Add

### `morphos/critic.py`
- Critic class: takes tool output + original intent, produces accept/reject verdict with reasoning
- Configurable thresholds: how strict should validation be? (default: moderate)
- Integration into agent loop after executor, before next iteration

### `morphos/tools/dynamic.py`
- DynamicToolRegistry class: validate function code, compile, register to main registry
- AST-based safety checks mirror python_exec blocklist (no network, no OS)
- Exposes `_register_tool` as an internal action the LLM can call by writing a script

### `morphos/analyzer.py`
- Analyzer class: collects metrics from each tool call (timestamp, tool name, status, duration)
- Session summary: success rate per tool, top failures, total tokens used
- Persists structured logs to `data/logs/` as JSON lines

### `tools/python_exec.py` — modified
- Instead of subprocess, launches a Docker container with Python pre-installed
- Injects code into container via stdin, captures stdout/stderr
- Applies resource limits: memory=256MB, cpus=1, timeout=10s

## Tech Stack Additions

| Component | Technology |
|-----------|------------|
| Sandboxing | Docker SDK for Python (`docker`) |
| Logging/Analysis | JSON lines + `rich` terminal tables |

## Success Criteria
- Agent calls a tool → critic reviews output → bad output is rejected and retried successfully
- Agent writes a new utility function during a session, registers it as a tool, then uses it in a later turn
- Code execution runs inside Docker with enforced resource limits
- End-of-session log shows which tools succeeded/failed and why

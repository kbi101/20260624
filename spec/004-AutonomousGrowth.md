# Phase 004 — Autonomous Growth

## Goal
Enable the system to self-improve over multiple sessions without human intervention: update its own prompts, auto-promote frequently-used dynamic tools to permanent ones, and spawn focused sub-agents for specialized domains.

## Scope

### Must Have

1. **Autonomous Prompt Evolution** (`morphos/self_improve/prompt_evolver.py`)
   - Background process (or end-of-session hook) that reviews past session logs + critic verdicts
   - Identifies recurring failures: parse errors, wrong tool choices, hallucinated answers
   - Proposes targeted system prompt patches (e.g., "add example for finance queries", "tweak format instructions")
   - Patches are diff-reviewed against the base prompt before application — user can enable/disable auto-apply

2. **Tool Library Auto-Curation** (`morphos/self_improve/tool_curator.py`)
   - Analyzes session logs to find high-frequency, high-success-rate dynamic tools
   - Tools that pass a frequency + success threshold are automatically promoted to permanent registration in `config.dynamic_tools_dir`
   - Low-performing tools (repeated critic rejections) get flagged for removal from prompts

3. **Background Growth Loop** (`morphos/self_improve/growth_loop.py`)
   - Async task that runs on a schedule (or manual trigger via CLI flag `--grow`)
   - Reads accumulated logs from `data/logs/`, computes improvement signals
   - Feeds signals into prompt_evolver and tool_curator
   - Outputs a human-readable "Growth Report" showing what changed and why

4. **Multi-Agent Support** (`morphos/multi_agent.py`)
   - Router agent that dispatches queries to domain-specialized sub-agents
   - Pre-defined specializations (configurable): `finance_agent`, `research_agent`, `coding_agent`
   - Each sub-agent gets a narrower, more focused system prompt and a curated tool subset
   - Router LLM call decides which sub-agent handles the query

### Won't Do (Future)
- Distributed agent orchestration (DAG-based multi-agent workflows)
- Real-time streaming of growth decisions back to active sessions
- Cross-machine learning / federated improvement

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI Chat   │ ◄──►│  ReAct Loop   │ ◄──►│ Local LLM   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
         ┌────▼───┐  ┌────▼────┐   ┌───────▼──────┐
         │ Tools   │  │ Critic  │   │ Multi-Agent   │
         │Registry │  │(valid-) │   │ Router        │
         │ + Dyn.  │  │ ation  │   │               │
         │Sandbox  │  └────────┘   ├─ Finance Agent │
         └────┬───┘              ├─ Research Agent  │
              │                  └─ Coding Agent    │
       ┌──────▼───────┐                    │
       │ Growth Loop   │◄───────────────────┘
       │(background)   │
       │              │
       │ - Prompt     │
       │   Evolver    │
       │ - Tool       │
       │   Curator    │
       └──────────────┘
```

## Components to Add

### `morphos/self_improve/prompt_evolver.py`
- PromptEvolver class: reads analyzer logs, identifies failure patterns
- Generates targeted patch suggestions for the system prompt
- Applies patches with optional user confirmation gate
- Persists evolved prompts to `config.yaml` or overlay file

### `morphos/self_improve/tool_curator.py`
- ToolCurator class: analyzes tool_usage.json logs for frequency and success metrics
- Promotes dynamic tools above threshold to permanent directory
- Demotes/removes chronic failures from available tool list

### `morphos/self_improve/growth_loop.py`
- GrowthLoop class: orchestrates prompt_evolver + tool_curator runs
- Triggers on CLI flag or scheduled interval
- Produces structured growth reports (what changed, expected impact)

### `morphos/multi_agent.py`
- RouterAgent: lightweight LLM call to classify query domain
- Sub-agent factory: creates specialized ReActAgent instances with tailored prompts and tool subsets
- Dispatch table: maps domains → agent configs

## Tech Stack Additions

| Component | Technology |
|-----------|------------|
| Growth scheduling | `asyncio` + cron-like interval or CLI trigger |
| Diff/patching | Python's `difflib` for prompt patches |
| Multi-agent routing | Same Ollama client, narrower system prompts |

## Success Criteria
- After 3+ sessions with recurring parse errors, the prompt evolver automatically adds a corrective format example
- A dynamic tool used successfully across 5+ sessions gets auto-promoted to permanent registration
- Routing agent correctly dispatches "get SPY price" to finance_agent and "what causes inflation" to research_agent
- Growth report shows measurable improvement (e.g., critic rejection rate dropped)

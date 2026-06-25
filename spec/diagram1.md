# Morphos Architecture & Workflow

```mermaid
flowchart TB
    subgraph CLI["cli.py — Entry Point"]
        ARG["Argument Parser<br/>--query / --multi-agent<br/>--grow / --auto-evolve"]
        INT["run_interactive<br/> REPL loop with readline history"]
        RAG["run_agent<br/> dispatches to agent or router"]
    end

    subgraph ROUTING["Multi-Agent Routing (Optional)"]
        RA["multi_agent.py<br/>RouterAgent"]
        CLASS["LLM classify query →<br/>FINANCE / RESEARCH / CODING"]
        SUBF["agent_factory → make_agent<br/>with narrowed tools + prompt addon"]
    end

    subgraph CORE["ReAct Agent Loop — agent.py"]
        SYS["_build_system_prompt<br/>tools list + heuristics hint + RAG memory"]
        WM["WorkingMemory<br/>sliding window, 6000 tokens"]
        REACT{for iter in max_iterations}
        LLM1["LLMClient.chat()<br/>→ gemma4:12b via Ollama"]
        PARSE["_parse_response"]
        PARSETYPE{parse result}
        EXEC["_execute_tool → tool.execute()"]
        CRIT["Critic.review<br/>loose / moderate / strict"]
        ANAL["Analyzer.record<br/>success / error / critic_rejected"]
        YIELD_EVENT["yield event (tool_result<br/>thought / critic / final_answer)"]
    end

    subgraph WEB_TOOLS["Web Tools — Playwright Chrome"]
        WS["web_search.py<br/>types into duckduckgo.com,<br/>scrapes results, heuristic rerank"]
        WF["web_fetch.py<br/>page.goto → networkidle →<br/>readability.Document →<br/>BeautifulSoup get_text → 6000 chars"]
        BM["browser.py<br/>singleton BrowserManager<br/>launch channel=chrome,<br/>shared BrowserContext"]
    end

    subgraph DATA_TOOLS["Data & Compute Tools"]
        FIN["finance.py<br/>yfinance — ticker price/volume<br/>IP-safe, no scraping needed"]
        PYE["python_exec.py<br/>sandboxed exec with timeout"]
        CALC["calculator.py<br/>AST-safe math eval"]
        FOP["file_ops.py<br/>FileRead + FileWrite path whitelist"]
        DIRS["directory_search.py<br/>glob pattern on local files"]
    end

    subgraph MEMORY["ChromaDB — data/vector_store/"]
        FC[facts collection]
        LC[lessons collection]
    end

    subgraph EMBED["Embedding Service"]
        OM["nomic-embed-text<br/>served by local Ollama"]
        CS["chroma_store.py<br/>add_fact / add_lesson / query"]
    end

    subgraph REFLECTION["Session Reflection — On Exit"]
        RF["reflector.py<br/>LLM extracts: facts, lessons,<br/>source heuristics from messages"]
        HEUR_J["data/search_heuristics.json<br/>pattern → preferred URL mapping"]
    end

    subgraph GROWTH["Growth Cycle — --grow Flag"]
        PE["prompt_evolver.py<br/>scans analyzer logs → prompt patches"]
        TC["tool_curator.py<br/>promote high-success / demote failures"]
        GL["growth_loop.py<br/>orchestrates, saves JSON report"]
    end

    subgraph HEURISTICS["Source Heuristics Runtime"]
        HENG["heuristics.py<br/>HeuristicEngine<br/>regex match query → URL template"]
    end

    ARG --> INT
    INT --> RAG
    ARG --> RAG

    RAG --> |multi-agent| RA
    RAG --> |single agent| SYS

    RA --> CLASS --> SUBF --> SYS
    SUBF --> FIN
    SUBF --> WS
    SUBF --> PYE

    SYS --> WM
    WM --> REACT --> LLM1 --> PARSE
    PARSE --> PARSETYPE
    
    PARSETYPE --> |"final answer OR (action + input)"| YIELD_EVENT
    PARSETYPE --> |action| EXEC

    EXEC --> WS
    EXEC --> WF
    EXEC --> FIN
    EXEC --> PYE
    EXEC --> CALC
    EXEC --> MS["memory_search.py<br/>query ChromaDB by embedding"]
    MS --> CS

    WS --> BM
    WF --> BM

    EXEC --> CRIT
    CRIT --> |reject| REACT
    CRIT --> |accept| ANAL --> YIELD_EVENT
    YIELD_EVENT --> WM --> REACT

    REACT --> |timeout| FALLBACK[LLM fallback answer]

    INT -.->|on quit| RF
    RF --> CS
    CS --> OM
    CS --> FC
    CS --> LC
    RF --> HEUR_J

    SYS -.-> HENG
    HENG -.-> HEUR_J

    GL --> PE
    GL --> TC
    PE -.-> SYS
```

## Component Details

| Component | File | Role |
|---|---|---|
| **LLM Inference** | `llm.py` | Wraps Ollama API, calls `gemma4:12b` for chat & classification |
| **Embedding** | `memory/chroma_store.py` | Calls `nomic-embed-text` via same local Ollama instance |
| **ReAct Loop** | `agent.py` | Thought → Action → Observation cycle, max 10 iterations |
| **Working Memory** | `memory/working_memory.py` | Token-aware sliding window (6000 tokens), keeps system prompt |
| **Persistent Memory** | `memory/chroma_store.py` | ChromaDB vector store with two collections: facts & lessons |
| **Critic** | `critic.py` | Post-tool LLM validation — loose/moderate/strict |
| **Analyzer** | `analyzer.py` | Records per-tool metrics (duration, status, critic verdict) |
| **Browser** | `tools/browser.py` | Singleton Playwright manager, real Chrome channel |
| **Web Search** | `tools/web_search.py` | Types into duckduckgo.com in real Chrome, heuristic rerank |
| **Web Fetch** | `tools/web_fetch.py` | Playwright page → readability extraction → 6000 chars text |
| **Finance** | `tools/finance.py` | yfinance library — bypasses IP-blocked Yahoo scraping |
| **Memory Search** | `tools/memory_search.py` | Embeds query, searches ChromaDB collections by similarity |
| **Heuristics** | `heuristics.py` | Runtime regex match of query → preferred URL templates |
| **Reflector** | `memory/reflector.py` | End-of-session LLM pass extracting facts, lessons, heuristics |
| **Router Agent** | `multi_agent.py` | LLM classifies queries into FINANCE/RESEARCH/CODING sub-agents |
| **Growth Loop** | `self_improve/growth_loop.py` | Orchestrates prompt evolution + tool curation on `--grow` |

## Workflow Summary

### Single Query
1. CLI parses args, calls `run_agent(query)`
2. If `--multi-agent`, RouterAgent classifies query with LLM, dispatches to narrow sub-agent
3. Agent builds system prompt: tool list + RAG memory recall + heuristic hints
4. ReAct loop fires: LLM generates Thought/Action → tool executes → Critic validates → result into Working Memory
5. On `Final Answer` or timeout (`--max-iters`), agent yields answer with fallback prompt
6. Events stream to Rich CLI as panels (thoughts, tool results, critic verdicts, final answer)

### Session Exit
1. All accumulated messages sent to Reflector LLM pass
2. Extracted facts stored as vectors in ChromaDB (via `nomic-embed-text` embedding)
3. Source heuristics learned → merged into `data/search_heuristics.json`
4. Analyzer session log saved, optional dynamic tool persistence prompt

### Growth Cycle (`--grow`)
1. Scans analyzer logs for failure patterns
2. Prompt Evolver proposes system prompt patches via LLM
3. Tool Curator promotes high-success dynamic tools, demotes chronic failures
4. Report saved to `data/growth_report_<timestamp>.json`

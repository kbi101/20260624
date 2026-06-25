# Phase 002 — Memory + RAG

## Goal
Add persistent memory so the agent remembers facts across sessions, retrieves relevant past knowledge during reasoning, and reflects on completed sessions to store key learnings.

## Scope

### Must Have

1. **ChromaDB Vector Store** (`morphos/memory/`)
   - Local ChromaDB instance backed by SQLite (zero external services)
   - Stores documents with metadata: session ID, timestamp, category (fact, lesson, conversation log)
   - Embedding via Ollama's built-in embed API (e.g., `nomic-embed-text` or `all-minilm`)
   - Collection-based separation: one collection for facts, one for reflection lessons

2. **Working Memory** (in-session context management)
   - Sliding window over conversation history to avoid blowing out the context window
   - Configurable max tokens per turn (default derived from model's context length)
   - Evicts oldest messages when approaching limit, preserves system prompt and recent exchanges
   - Exposed as a tool `memory_search` so the agent can query its own memory mid-conversation

3. **Session Reflection**
   - On session end (user types quit/exit), a reflection pass runs:
     - LLM summarizes what was learned in the session
     - Extracted facts and lessons are embedded and stored in ChromaDB
   - Stored reflections include source session ID, timestamp, and confidence score

4. **RAG Injection into Agent Loop**
   - Each turn, before sending to LLM, retrieve top-K relevant memories from vector store using the user's current query as the search vector
   - Inject retrieved context into the system prompt as a "Relevant Memory" section
   - Configurable retrieval count (default: 3) and similarity threshold

5. **New Tools** (missing from original spec)
   - `file_read` — read a file from disk with path whitelisting
   - `file_write` — write content to a file with path whitelisting
   - `directory_search` — glob-style file search within allowed paths
   - `calculator` — direct math expression evaluation (simpler alternative to python_exec for arithmetic)

### Won't Do (Future Phases)
- Critic module for output validation (Phase 3)
- Agent-written dynamic tool registration (Phase 3)
- Docker sandboxing (Phase 3)
- Background autonomous growth loop (Phase 4)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI Chat   │ ◄──►│  ReAct Loop   │ ◄──►│ Local LLM   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼───┐  ┌────▼───┐  ┌────▼──────────┐
         │ Tools   │  │Working │  │ Memory Store   │
         │ Registry│  │Memory  │  │ (ChromaDB)     │
         │        │  │(sliding │  │                 │
         │py_exec │  │ window)│  │ - Fact coll.    │
         │web_*   │  │        │  │ - Lesson coll.  │
         │finance │  └────────┘  │ - RAG retrieval │
         │file_*  │             │ - Reflection    │
         │calc    │             └─────────────────┘
```

## Components to Add

### `morphos/memory/chroma_store.py`
- ChromaDBManager class: init collection, add documents, query by similarity
- Uses Ollama embed API for embeddings (no separate embedding model needed)
- Persists to `data/vector_store/` on disk

### `morphos/memory/working_memory.py`
- WorkingMemory class: append messages, enforce sliding window by token count
- Token estimation via rough char-to-token ratio (or simple word count heuristic)
- Provides truncated context that fits within model's context window

### `morphos/memory/reflector.py`
- Reflector class: takes full conversation history, prompts LLM to extract facts and lessons
- Embeds and stores each extracted item into ChromaDB with metadata

### `morphos/agent.py` — modified
- Inject retrieved memories into system prompt each turn
- Pass working memory context instead of raw message list
- On session end, trigger reflection pass

### New tool files
- `tools/file_ops.py` — FileRead and FileWrite tools with path allowlist
- `tools/directory_search.py` — DirectorySearch tool with glob matching
- `tools/calculator.py` — Calculator tool for safe math evaluation (ast-based)

## Tech Stack Additions

| Component | Technology |
|-----------|------------|
| Vector DB | ChromaDB (`chromadb`) |
| Embeddings | Ollama embed API (`nomic-embed-text`) |

## Success Criteria
- In session 1, user tells the agent a personal fact (e.g., "my name is Alice")
- Session ends, reflection stores the fact
- In session 2, user asks "what's my name?" → agent retrieves from memory and answers correctly
- Working memory prevents context overflow on long conversations
- New tools are functional: read/write files, search directories, calculate expressions

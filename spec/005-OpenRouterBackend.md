# Phase 005 — OpenRouter Backend Support

## Goal
Allow Morphos to use OpenRouter's API as an alternative LLM backend, alongside the existing local Ollama backend. Users can switch per-session via CLI flags without any code changes to agents, tools, or critic.

## Motivation
- Local models may lack capability for complex reasoning tasks
- OpenRouter offers access to GPT-4, Claude, Gemini, and many more models
- Keeps cost control — users opt-in, fallback to local anytime
- Zero disruption to existing local-first workflow

## Scope

### Must Have

1. **Backend Abstraction** (`morphos/llm.py`)
   - `LLMClient` exposes a stable `.chat(messages: list[dict]) -> str` interface
   - Internal backend selection: `OllamaBackend` (existing) or `OpenRouterBackend` (new)
   - OpenRouterBackend uses raw `requests.post()` to `https://openrouter.ai/api/v1/chat/completions`

2. **Configuration** (`morphos/config.py`)
   - New fields: `backend`, `openrouter_model`, `openrouter_api_key`
   - API key defaults to `$OPENROUTER_API_KEY` environment variable

3. **CLI Flags** (`morphos/cli.py`)
   - `--backend ollama|openrouter` (default: `ollama`)
   - `--openrouter-model <slug>` — e.g. `google/gemini-2.0-flash`
   - Config object is threaded through to all LLMClient call sites

4. **Zero Call-Site Changes**
   - `agent.py`, `critic.py`, `reflector.py`, `multi_agent.py`, `self_improve/` — all pass `model=` and call `.chat()`, no changes needed

### Won't Do (Future)
- Automatic fallback from one backend to another on failure
- Per-tool backend routing (e.g., critic always local, main model always cloud)
- Streaming responses for OpenRouter
- Cost/budget tracking

## API Compatibility Notes

OpenRouter's `/api/v1/chat/completions` uses the same OpenAI-compatible message format:
```python
{"model": "...", "messages": [{"role": "user"|"assistant"|"system", "content": "..."}]}
```
This is identical to what Ollama expects, so the `messages` list flows through unchanged.

## Running It
```bash
# Local (default)
python -m morphos.cli --query "what is SPY price"

# Via OpenRouter
OPENROUTER_API_KEY=sk-or-xxx python -m morphos.cli --backend openrouter --openrouter-model "google/gemini-2.0-flash" --query "what is SPY price"
```

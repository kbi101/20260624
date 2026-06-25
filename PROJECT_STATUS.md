# Morphos — Project Status (Updated 2026-06-24)

## What Works ✅
| Tool | Backend | Notes |
|---|---|---|
| `python_exec` | Sandboxed subprocess + AST blocklist | Blocks network/OS imports, 30s timeout |
| `web_fetch` | Playwright + real Chrome (`channel="chrome"`) | Wait `domcontentloaded`, readability extraction |
| `web_search` | Types into duckduckgo.com via real Chrome | Works because DDG main site doesn't block regular Chrome |
| `finance` | yfinance library (no scraping) | Real-time ticker, range, volume, market cap |

## Architecture
```
morphos/
├── agent.py        # ReAct loop, system prompt, _parse_kwargs fallback per tool
├── cli.py          # Rich terminal UI, registers all 4 tools
├── config.py       # gemma4:12b, max_iterations defaults
├── llm.py          # Ollama client wrapper
└── tools/
    ├── browser.py     # BrowserManager singleton (real Chrome, not headless)
    ├── registry.py    # Tool ABC + ToolRegistry class
    ├── python_exec.py # Sandboxed code execution
    ├── web_fetch.py   # Playwright page load + readability
    ├── web_search.py  # DuckDuckGo type-and-search via Chrome
    └── finance.py     # yfinance stock/ETF data
```

## CRITICAL: Network Blockers 🚫
**This machine's IP (2600:6c40:...) is actively blocked by:**
- **Google Search** — returns captcha page even with real Chrome via Playwright (`channel="chrome"`, `headless=False`)
- **DDGS library** (`duckduckgo_search`) — consistently returns 0 results on this IP
- **Yahoo Finance, MarketWatch** — return 403/429 against all HTTP clients

**What DOES work from this IP:**
- DuckDuckGo main site (duckduckgo.com) via Playwright Chrome browser — no captcha
- Weather.gov direct URLs via Playwright — returns full page content
- yfinance library — completely unblocked, returns real-time data instantly
- Regular websites (example.com, Wikipedia, etc.) via Playwright — no issues

**Never do:**
- Use `duckduckgo_search` Python package → always returns empty
- Hit Google search via HTTP or Playwright → captcha wall
- Scrape Yahoo Finance/MarketWatch directly → 403 blocked
- Use headless Chromium for search engines → fingerprint bot detection

## Agent Behavior
- System prompt enforces JSON `Action Input:` with tool-specific parameter names
- `_parse_kwargs` has per-tool fallback: web_search→query, python_exec→code, others→url
- Max iterations exhausted → agent runs one more LLM turn to produce best available answer instead of hard fail
- Parse errors → format hint sent back to LLM for self-correction

## Running It
```bash
python -m morphos.cli                          # Interactive
python -m morphos.cli --query "what is SPY price"  # Single-shot
```

Make sure Ollama is running and `gemma4:12b` is pulled.

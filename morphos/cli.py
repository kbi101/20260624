"""CLI interface for Morphos agent."""

import re
import time
import uuid
import readline
import argparse
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from morphos.agent import ReActAgent
from morphos.config import Config
from morphos.tools.python_exec import PythonExec
from morphos.tools.web_fetch import WebFetch
from morphos.tools.web_search import WebSearch
from morphos.tools.finance import Finance
from morphos.tools.file_ops import FileRead, FileWrite
from morphos.tools.directory_search import DirectorySearch
from morphos.tools.calculator import Calculator
from morphos.tools.memory_search import MemorySearch
from morphos.memory.chroma_store import ChromaStore
from morphos.memory.reflector import Reflector
from morphos.dynamic_tools import save_dynamic_tools


console = Console()

THOUGHT_STYLE = "dim cyan"
TOOL_STYLE = "bold yellow"
RESULT_STYLE = "green"
ERROR_STYLE = "bold red"
FINAL_STYLE = "bold white on blue"
CRITIC_ACCEPT_STYLE = "dim green"
CRITIC_REJECT_STYLE = "bold magenta"

_session_id = str(uuid.uuid4())[:8]


def _register_tool(agent, tool):
    """Register a single tool on an agent."""
    agent.register_tool(tool)


ALL_TOOLS = {
    "python_exec": lambda cfg: PythonExec(timeout=cfg.python_timeout),
    "web_fetch": lambda cfg: WebFetch(timeout=cfg.web_timeout),
    "web_search": lambda _c: WebSearch(),
    "finance": lambda _c: Finance(),
    "file_read": lambda _c: FileRead(),
    "file_write": lambda _c: FileWrite(),
    "directory_search": lambda _c: DirectorySearch(),
    "calculator": lambda _c: Calculator(),
}


def _lazy_register_uct():
    """Lazy-add UCT tool so the import doesn't fire at module level."""
    try:
        def _uct_factory(cfg):
            from uct.toolkit import UCTGenerate as UCTGen
            return UCTGen(
                llm_client=__import__('morphos.llm', fromlist=['LLMClient']).LLMClient(model=cfg.model, config=cfg),
                depth=getattr(cfg, "uct_depth", 1),
                mode=getattr(cfg, "uct_mode", "understand"),
            )
        ALL_TOOLS["uct_generate"] = _uct_factory
    except ImportError:
        pass


_lazy_register_uct()


def make_agent(config=None, system_addon=None, allowed_tools=None):
    """Create a single agent, optionally with narrowed tool set and prompt addon."""
    from morphos.memory.chroma_store import ChromaStore
    from morphos.agent import ReActAgent
    if config is None:
        from morphos.config import Config
        config = Config()
    store = ChromaStore()
    agent = ReActAgent(
        model=config.model,
        max_iterations=config.max_iterations,
        config=config,
        store=store,
    )

    tools_to_register = set(allowed_tools) if allowed_tools else set(ALL_TOOLS.keys())
    for tname, factory in ALL_TOOLS.items():
        if tname in tools_to_register:
            _register_tool(agent, factory(config))
    if "memory_search" in tools_to_register:
        ms = MemorySearch(store=store)
        agent.register_tool(ms)

    if system_addon:
        agent._system_prompt_addon = system_addon

    return agent


def make_agents(config: Config):
    """Backward compat — creates full agent + store."""
    store = ChromaStore()
    agent = make_agent(config)
    ms = MemorySearch(store=store)
    agent.register_tool(ms)
    return agent, store


def _handle_event(event_type, payload):
    """Print a single event from the agent loop."""
    if event_type == "llm_response":
        thought_match = re.search(r"Thought:\s*(.+?)(?:\n|$)", payload, re.DOTALL)
        if thought_match:
            console.print(Panel(Text(thought_match.group(1).strip(), style=THOUGHT_STYLE), title="[dim]Thought"))
    elif event_type == "tool_result":
        tool_name, result = payload
        console.print(Panel(Text(result[:500], style=RESULT_STYLE), title=f"[bold yellow]{tool_name}"))
    elif event_type == "tool_error":
        console.print(Text(payload, style=ERROR_STYLE))
    elif event_type == "error":
        console.print(Text(payload, style=ERROR_STYLE))
    elif event_type == "final_answer":
        console.print(Panel(Markdown(payload), title="[green]Final Answer", border_style="green"))
    elif event_type == "critic":
        tool_name, verdict = payload
        if verdict == "accept":
            console.print(f"[dim green]✓ Critic accepted output from {tool_name}[/]")
        else:
            console.print(f"[bold magenta]✗ Critic rejected output from {tool_name} — retrying...[/]")
    elif event_type == "critic_reject":
        console.print(Text(payload, style=CRITIC_REJECT_STYLE))
    elif event_type == "timeout":
        console.print(Text(payload, style=ERROR_STYLE))
    elif event_type == "routed":
        console.print(f"[bold blue]🔀 Routed to {payload}[/]")


def run_agent(query: str, config: Config):
    from datetime import datetime
    console.print(f"[dim]⏱ {datetime.now().strftime('%H:%M:%S')} — Starting query…[/]")
    console.print(Panel(Text(query, style="bold"), title="[blue]User Query"))
    t_start = time.monotonic()

    if config.multi_agent:
        from morphos.multi_agent import RouterAgent
        from morphos.llm import LLMClient

        domain = RouterAgent(
            llm_client=LLMClient(model=config.model, config=config),
            agent_factory=make_agent,
        ).classify(query)

        console.print(f"[bold blue]🔀 Routed to {domain}[/]")

        if domain == "TEXTBOOK":
            _run_textbook(query, config)
            return None

        router = RouterAgent(
            llm_client=LLMClient(model=config.model, config=config),
            agent_factory=make_agent,
        )
        last_domain = None
        final_agent = None
        for event_type, payload in router.dispatch(query, config):
            if event_type == "routed":
                last_domain = payload
            _handle_event(event_type, payload)
        if last_domain:
            final_agent = router.get_agent(last_domain, config)
        return final_agent

    else:
        agent, store = make_agents(config)
        for event_type, payload in agent.run(query):
            _handle_event(event_type, payload)

    elapsed_s = time.monotonic() - t_start
    ts_end = datetime.now().strftime("%H:%M:%S")
    if elapsed_s < 60:
        label = int(elapsed_s * 1000), "ms"
    else:
        label = f"{elapsed_s:.1f}", "s"
    console.print(f"[dim]✓ {ts_end} — Query completed in {label[0]} {label[1]}[/]")
    return agent


def _run_textbook(query: str, config: Config):
    """Research topic online, invoke UCT engine for TEXTBOOK domain, display dashboard + references."""
    from morphos.llm import LLMClient
    from uct.engine import UCTEngine

    # ── Web research phase ────────────────────────────────────────
    search_tool = WebSearch()
    fetch_tool = WebFetch(timeout=config.web_timeout)
    
    console.print("[dim]🔍 Researching topic online...[/]")
    results_text = search_tool.execute(query, max_results=8)
    
    url_titles = []
    research_parts = []
    
    import re as _re
    link_matches = _re.findall(r'URL:\s*(https?://\S+)', results_text)
    
    for url in link_matches[:3]:
        console.print(f"[dim]  Fetching: {url}[/]")
        fetched = fetch_tool.execute(url)
        title_match = _re.search(r'\[(.+?)\]', fetched)
        t = title_match.group(1) if title_match else url[:80]
        content = fetched[len(title_match.group(0)):] if title_match else fetched
        url_titles.append((t, url))
        research_parts.append(content[:2000].strip())
    
    research_context = "\n\n".join(research_parts)
    
    # ── UCT generation with research context ──────────────────────
    llm = LLMClient(model=config.model, config=config)
    engine = UCTEngine(llm, depth=config.uct_depth, mode=config.uct_mode)
    rendered, model = engine.generate_dashboard(query, research_context=research_context)

    console.print(Panel(rendered, title=f"[green]📖 Cognitive Dashboard — {query}", border_style="green"))

    # ── References list ──────────────────────────────────────────
    if url_titles:
        ref_lines = []
        for i, (t, u) in enumerate(url_titles, 1):
            ref_lines.append(f"[{i}] [blue]{t}[/]")
            ref_lines.append(f"    {u}")
        console.print(Panel("\n".join(ref_lines), title="[yellow]References", border_style="yellow"))

    # Render knowledge graph if depth >= 2
    if config.uct_depth >= 2:
        graph = engine.build_graph(model)
        console.print(Panel(graph.terminal_render(), title="[yellow]Knowledge Graph", border_style="yellow"))


def run_interactive(config: Config):
    console.print(Panel("[bold blue]Morphos[/] — Type a query or 'quit' to exit.", border_style="blue"))
    store = ChromaStore()
    all_messages = []
    _last_agent = [None]

    history = []
    while True:
        try:
            console.print("[bold cyan]> [/]", end="")
            query = input().strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye!")
            break

        if query and query.lower() not in ("quit", "exit", "q"):
            history.append(query)
            readline.add_history(query)

        if not query or query.lower() in ("quit", "exit", "q"):
            _run_reflection(all_messages, store, config)
            if _last_agent[0]:
                _print_session_log(_last_agent[0])
                _handle_dynamic_tool_persistence(_last_agent[0], config)
            console.print("Bye!")
            break

        try:
            agent = run_agent(query, config)
            _last_agent[0] = agent
            if agent:
                all_messages.extend(agent.get_session_messages())
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")


def _run_reflection(messages: list[dict], store: ChromaStore, config=None):
    if not messages:
        return

    console.print("[dim]Running session reflection...[/dim]")
    try:
        from morphos.llm import LLMClient
        reflector = Reflector(chroma_store=store, llm_client=LLMClient(model="gemma4:12b", config=config))
        stats = reflector.reflect(messages, session_id=_session_id)
        parts = [f"{stats['facts_stored']} facts", f"{stats['lessons_stored']} lessons"]
        hl = stats.get('heuristics_learned', 0)
        if hl:
            parts.append(f"{hl} source heuristic(s)")
        console.print(f"[dim]Stored {', '.join(parts)}.[/dim]")
    except Exception as e:
        console.print(f"[dim red]Reflection skipped: {e}[/dim red]")


def _print_session_log(agent):
    try:
        report = agent.analyzer.terminal_report()
        if not report:
            return
        console.print(Panel(Text(report, style="dim"), title="[yellow]Session Log"))
        agent.analyzer.save(_session_id)
    except Exception as e:
        console.print(f"[dim red]Log save failed: {e}[/dim red]")


def _handle_dynamic_tool_persistence(agent, config):
    if not config.dynamic_tools_dir or not agent.dynamic_registry:
        return

    try:
        if not len(agent.dynamic_registry.tools):
            return

        console.print("[dim]New tools were created this session. Persist them for future sessions? (y/n)[/dim]")
        try:
            answer = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"

        if answer == "y":
            save_dynamic_tools(agent.dynamic_registry, config.dynamic_tools_dir)
            console.print("[dim green]Dynamic tools saved.[/dim]")
    except Exception as e:
        console.print(f"[dim red]Tool persistence failed: {e}[/dim red]")


def _run_growth_cycle(config):
    from morphos.llm import LLMClient
    from morphos.self_improve.growth_loop import GrowthLoop
    from morphos.dynamic_tools import DynamicToolRegistry

    console.print("[yellow]Running growth cycle...[/yellow]")
    llm = LLMClient(model=config.model, config=config)
    registry = DynamicToolRegistry() if config.dynamic_tools_dir else None
    if registry and config.dynamic_tools_dir:
        from morphos.dynamic_tools import load_persistent_dynamic_tools
        registry.persist_dir = config.dynamic_tools_dir
        load_persistent_dynamic_tools(registry, config.dynamic_tools_dir)

    from morphos.agent import SYSTEM_PROMPT
    analyzer_obj = type("AnalyzerProxy", (), {})()
    growth = GrowthLoop(llm, registry, analyzer_obj)
    report = growth.run_growth_cycle(SYSTEM_PROMPT, auto_apply=config.auto_evolve)
    console.print(Panel(Text(growth.terminal_report(report), style="dim"), title="[green]Growth Report"))
    saved_path = growth.save_report(report)
    console.print(f"[dim]Report saved to {saved_path}[/dim]")


def main():
    parser = argparse.ArgumentParser(description="Morphos — Local ReAct Agent")
    parser.add_argument("--query", "-q", help="Single query to run")
    parser.add_argument("--model", default="gemma4:12b", help="Ollama model name")
    parser.add_argument("--max-iters", type=int, default=10, help="Max ReAct iterations")
    parser.add_argument("--no-critic", action="store_true", help="Disable critic validation")
    parser.add_argument("--critic-strictness", default="moderate", choices=["loose", "moderate", "strict"])
    parser.add_argument("--critic-model", default="qwen2.5:3b", help="Smaller model for critic validation (default: qwen2.5:3b)")
    parser.add_argument("--dynamic-tools-dir", default=None, help="Directory for dynamic tools (e.g. data/dynamic_tools)")
    parser.add_argument("--grow", action="store_true", help="Run one growth cycle (prompt evolution + tool curation)")
    parser.add_argument("--auto-evolve", action="store_true", help="Auto-apply prompt patches from growth cycle")
    parser.add_argument("--multi-agent", action="store_true", help="Enable multi-agent routing (finance/research/coding)")
    parser.add_argument("--debug", action="store_true", help="Log every LLM call, tool invocation, and web request to debug.log")
    parser.add_argument("--backend", default="ollama", choices=["ollama", "openrouter"], help="LLM backend (default: ollama)")
    parser.add_argument("--openrouter-model", default=None, help="OpenRouter model slug (e.g. google/gemini-2.0-flash)")
    parser.add_argument("--openrouter-key", default=None, help="OpenRouter API key (or set OPENROUTER_API_KEY env var)")
    parser.add_argument("--uct-depth", type=int, default=1, help="UCT depth: 0=essence, 1=core, 2=full, 3=expert")
    parser.add_argument("--uct-mode", default="understand", choices=["understand", "exam", "practice", "research", "overview"], help="UCT rendering mode")
    parser.add_argument("--web", action="store_true", help="Launch web UI for Cognitive Dashboard instead of terminal")
    args = parser.parse_args()

    config = Config(
        model=args.model,
        max_iterations=args.max_iters,
        critic_enabled=not args.no_critic,
        critic_strictness=args.critic_strictness,
        dynamic_tools_dir=args.dynamic_tools_dir,
        auto_evolve=args.auto_evolve,
        multi_agent=args.multi_agent,
        debug=args.debug,
        backend=args.backend,
        openrouter_model=args.openrouter_model,
        openrouter_api_key=args.openrouter_key,
        uct_depth=args.uct_depth,
        uct_mode=args.uct_mode,
    )

    if args.web:
        _launch_web_server(args)
    elif args.grow:
        _run_growth_cycle(config)
    elif args.query:
        run_agent(args.query, config)
    else:
        run_interactive(config)


def _launch_web_server(args):
    """FastAPI server with web UI for UCT Cognitive Dashboard."""
    import subprocess as _sub
    import sys as _sys
    from pathlib import Path as _Path

    _server_dir = _Path(__file__).resolve().parent.parent
    console.print("[bold blue]Launching Morphos Web UI…[/]")
    port = getattr(args, 'port', 8000)
    console.print(f"[dim]Open http://localhost:{port}[/]")

    proc = _sub.Popen([
        _sys.executable, "-m", "uvicorn", "webui.server:app",
        "--host", "127.0.0.1", "--port", str(port),
    ], cwd=str(_server_dir))

    try:
        proc.wait()
    except KeyboardInterrupt:
        console.print("\n[dim]Shutting down server…[/]")
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
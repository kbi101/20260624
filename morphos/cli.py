"""CLI interface for Morphos agent."""

import re
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


def make_agents(config: Config) -> ReActAgent:
    store = ChromaStore()
    agent = ReActAgent(
        model=config.model,
        max_iterations=config.max_iterations,
        config=config,
        store=store,
    )
    agent.register_tool(PythonExec(timeout=config.python_timeout))
    agent.register_tool(WebFetch(timeout=config.web_timeout))
    agent.register_tool(WebSearch())
    agent.register_tool(Finance())
    agent.register_tool(FileRead())
    agent.register_tool(FileWrite())
    agent.register_tool(DirectorySearch())
    agent.register_tool(Calculator())
    ms = MemorySearch(store=store)
    agent.register_tool(ms)
    return agent, store


def run_agent(query: str, config: Config):
    agent, store = make_agents(config)

    console.print(Panel(Text(query, style="bold"), title="[blue]User Query"))

    for event_type, payload in agent.run(query):
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

    return agent


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
            _run_reflection(all_messages, store)
            if _last_agent[0]:
                _print_session_log(_last_agent[0])
                _handle_dynamic_tool_persistence(_last_agent[0], config)
            console.print("Bye!")
            break

        try:
            agent = run_agent(query, config)
            _last_agent[0] = agent
            all_messages.extend(agent.get_session_messages())
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")


def _run_reflection(messages: list[dict], store: ChromaStore):
    if not messages:
        return

    console.print("[dim]Running session reflection...[/dim]")
    try:
        from morphos.llm import LLMClient
        reflector = Reflector(chroma_store=store, llm_client=LLMClient(model="gemma4:12b"))
        stats = reflector.reflect(messages, session_id=_session_id)
        console.print(f"[dim]Stored {stats['facts_stored']} facts, {stats['lessons_stored']} lessons.[/dim]")
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
    llm = LLMClient(model=config.model)
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
    parser.add_argument("--dynamic-tools-dir", default=None, help="Directory for dynamic tools (e.g. data/dynamic_tools)")
    parser.add_argument("--grow", action="store_true", help="Run one growth cycle (prompt evolution + tool curation)")
    parser.add_argument("--auto-evolve", action="store_true", help="Auto-apply prompt patches from growth cycle")
    parser.add_argument("--multi-agent", action="store_true", help="Enable multi-agent routing (finance/research/coding)")
    args = parser.parse_args()

    config = Config(
        model=args.model,
        max_iterations=args.max_iters,
        critic_enabled=not args.no_critic,
        critic_strictness=args.critic_strictness,
        dynamic_tools_dir=args.dynamic_tools_dir,
        auto_evolve=args.auto_evolve,
        multi_agent=args.multi_agent,
    )

    if args.grow:
        _run_growth_cycle(config)
    elif args.query:
        run_agent(args.query, config)
    else:
        run_interactive(config)


if __name__ == "__main__":
    main()
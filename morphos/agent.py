"""ReAct agent with cyclic Thought → Action → Observation loop and RAG memory."""

import re
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from morphos.llm import LLMClient
from morphos.tools.registry import ToolRegistry
from morphos.memory.chroma_store import ChromaStore
from morphos.memory.working_memory import WorkingMemory
from morphos.config import Config
from morphos.critic import Critic
from morphos.analyzer import Analyzer
from morphos.debug_logger import DebugLogger
from morphos.dynamic_tools import DynamicToolRegistry
from morphos.heuristics import HeuristicEngine


SYSTEM_PROMPT = r"""You are an AI assistant. You must output exactly one of these two formats each turn:

To use a tool, output this EXACTLY:
Thought: <reason>
Action: <tool_name>
Action Input {{"arg": "value"}}

IMPORTANT: Only one tool call per turn. Wait for the Observation before calling another tool. Chain multiple steps by making one call at a time.

To finish, output this EXACTLY:
Final Answer: <answer>

CRITICAL RULES — DO NOT DEVIATE FROM THE FORMAT ABOVE:
1. Always start a line with "Thought:" before acting
2. Always write "Action: " followed by the exact tool name on its own line
3. Always write "Action Input: " followed by valid JSON on its own line
4. STOP GENERATING IMMEDIATELY after you write the closing brace "}}" of Action Input.  Do NOT write any Observation lines — the system will supply the real observation.
5. NEVER invent, guess, or hallucinate Observation content. Only work with data provided to you by the system.
6. Always end with "Final Answer: " when done — do not wrap it in Thought/Action blocks
7. Use only tools listed below

Available tools:
{tools_list}

Parameter names per tool:
- web_search → {{"query": "..."}}
- web_fetch → {{"url": "https://..."}} 
- python_exec → {{"code": "print(...)"}}
- finance → {{"symbol": "SPY"}} or {{"text_query": "..."}}
- file_read → {{"filepath": "/path/to/file"}} 
- file_write → {{"filepath": "/path", "content": "..."}}
- directory_search → {{"pattern": "*.py"}}
- calculator → {{"expression": "2+3*4"}}
- memory_search → {{"query": "..."}}

Examples:

User: What is 15 squared?
Thought: I need to compute the value.
Action: calculator
Action Input: {{"expression": "15*15"}}

Observation: = 225

Final Answer: 15 squared is 225.

User: What is the price of AAPL?
Thought: I need stock data first.
Action: finance
Action Input: {{"symbol": "AAPL"}}

Observation: AAPL latest close $198.50 + volume ...

Thought: Now let me search for recent news.
Action: web_search
Action Input: {{"query": "Apple Inc AAPL news today"}}

Observation: Search results for Apple news: ...

Citations and sources: When you rely on data from web_search or web_fetch tools, cite the source with a bracketed number like [1] next to the claim. The source list will be included at the end of your final answer by the system."""


SYSTEM_PROMPT_MEMORY = r"""
Relevant Memory from past sessions:
{memory_context}

Use this memory as additional knowledge when forming your responses. If memory contradicts real-time information, trust the tool results over memory."""


@dataclass
class ReActAgent:
    model: str = "gemma4:12b"
    max_iterations: int = 10
    config: Config | None = None
    rag_retrieval_count: int = 3
    memory: WorkingMemory = field(default=None)
    store: ChromaStore = field(default=None)

    def __post_init__(self):
        self.config = self.config or Config(model=self.model, max_iterations=self.max_iterations)
        self.debug = DebugLogger(enabled=self.config.debug)
        self.llm = LLMClient(
            model=self.model,
            debug_logger=self.debug,
            config=self.config,
        )
        self.registry = ToolRegistry()
        if self.memory is None:
            self.memory = WorkingMemory(max_tokens=6000)

        self.heuristics = HeuristicEngine()
        self.analyzer = Analyzer()
        self._source_urls: list[str] = []
        self.critic = None
        if self.config.critic_enabled:
            self.critic = Critic(
                critic_model=self.config.critic_model,
                strictness=self.config.critic_strictness,
                debug_logger=self.debug,
                config=self.config,
            )

        self.dynamic_registry = None
        if self.config.dynamic_tools_dir:
            from morphos.dynamic_tools import load_persistent_dynamic_tools
            self.dynamic_registry = DynamicToolRegistry(persist_dir=self.config.dynamic_tools_dir)
            load_persistent_dynamic_tools(self.dynamic_registry, self.config.dynamic_tools_dir)
            for dtool in self.dynamic_registry.tools.values():
                self.registry.register(dtool)

    def register_tool(self, tool):
        self.registry.register(tool)

    def _build_system_prompt(self, query_text: str = "") -> str:
        tools_info = "\n".join(f"- **{name}**: {desc}" for name, desc in self.registry.list_tools())
        prompt = SYSTEM_PROMPT.format(tools_list=tools_info)

        # Inject learned source heuristics into the prompt
        if query_text:
            hint = self.heuristics.build_prompt_hint(query_text)
            if hint:
                prompt += "\n" + hint

            # Financial query enrichment — always search for today's data & latest quote
            fin_hint = _build_financial_hint(query_text)
            if fin_hint:
                prompt += "\n" + fin_hint

        if self.store and query_text:
            memories = self.store.query(query_text, n_results=self.rag_retrieval_count)
            if memories:
                mem_lines = []
                for m in memories:
                    source = m.get("source", "unknown")
                    mem_lines.append(f"[{source}] {m['text']}")
                memory_block = SYSTEM_PROMPT_MEMORY.format(memory_context="\n".join(mem_lines))
                prompt += "\n" + memory_block

        return prompt

    def _extract_urls(self, observation: str) -> list[str]:
        import re as _re
        urls = _re.findall(r'https?://[^\s<>"\]]+', observation)
        return urls

    def run(self, query: str):
        LLMClient._has_fallen_back = False
        self.memory.clear()
        self._source_urls = []
        system_prompt = self._build_system_prompt(query)
        self.memory.append("system", system_prompt)
        today = datetime.now().strftime("%B %d, %Y")
        enriched_query = f"[Today is {today}]\n\n{query}"
        self.memory.append("user", enriched_query)
        self.debug.agent_step(0, "start", query)

        for iteration in range(1, self.max_iterations + 1):
            self.debug.agent_step(iteration, "llm_call")
            context = self.memory.get_context()
            llm_raw = self.llm.chat(context)
            yield "llm_response", llm_raw

            # Retry immediately on empty response — no point parsing nothing
            if not llm_raw.strip():
                self.memory.append("user", "Empty response. Please reply with a Thought, Action+Action Input, or Final Answer.")
                continue

            trimmed = _strip_hallucinated_observations(llm_raw)

            parsed = _parse_multi_response(trimmed, self.registry._tools.keys())
            if parsed is None:
                self.memory.append("assistant", llm_raw)
                correction = (
                    "PARSE ERROR - could not find valid format.\n"
                    "Output EXACTLY one of:\n"
                    'Action: <tool_name>\n'
                    'Action Input: {"key": "value"}\n\n'
                    "OR\n\n"
                    "Final Answer: <your answer>\n"
                    "No markdown wrapping. No extra text before or after."
                )
                yield "error", correction
                self.memory.append("user", correction)
                continue

            ptype, pdata = parsed

            if ptype == "final":
                source_block = ""
                if self._source_urls:
                    numbered = "\n".join(f"[{i}] {u}" for i, u in enumerate(self._source_urls[:10], 1))
                    source_block = "\n\n---\n**Sources:**\n" + numbered
                final_payload = pdata.strip()
                self.memory.append("assistant", llm_raw)
                yield "final_answer", final_payload + source_block
                self.debug.agent_step(iteration, "final_answer")
                return

            tool_name_str, kwargs = pdata[0]

            self.debug.tool_call(tool_name_str, kwargs)
            yield "llm_response", f"Action: {tool_name_str}({kwargs})"

            tool = self.registry.get(tool_name_str)
            if tool is None:
                observation = f"Unknown tool: {tool_name_str}"
                yield "tool_error", observation
                self.debug.tool_error(tool_name_str, observation, 0)
            else:
                start_time = time.time()
                exec_error = None
                try:
                    result = tool.execute(**kwargs)
                except TypeError as te:
                    clean_kwargs = _sanitize_kwargs(kwargs, tool_name_str)
                    if clean_kwargs != kwargs:
                        try:
                            result = tool.execute(**clean_kwargs)
                        except Exception as te2:
                            exec_error = f"Error: {te2}"
                            result = exec_error
                    else:
                        exec_error = f"Error: {te}"
                        result = exec_error
                except Exception as e:
                    exec_error = f"Error: {e}"
                    result = exec_error

                elapsed_ms = int((time.time() - start_time) * 1000)
                critic_verdict = None

                if self.critic and not exec_error:
                    accepted = self.critic.review(tool_name_str, result, query)
                    critic_verdict = "accept" if accepted else "reject"
                    yield "critic", (tool_name_str, critic_verdict)

                    if not accepted:
                        self.analyzer.record(
                            tool_name_str, elapsed_ms, "critic_rejected", iteration,
                            message=str(result)[:200], critic_verdict="reject",
                        )
                        observation = f"Critic rejected the output from {tool_name_str}. The result was deemed insufficient. Try again with different parameters or a different tool."
                        yield "critic_reject", observation
                    else:
                        self.analyzer.record(
                            tool_name_str, elapsed_ms, "success", iteration,
                            message=str(result)[:200], critic_verdict=critic_verdict,
                        )
                        observation = str(result)

                if exec_error:
                    self.analyzer.record(
                        tool_name_str, elapsed_ms, "error", iteration,
                        message=exec_error,
                    )
                    observation = str(result)

            self.memory.append("assistant", llm_raw)
            self.memory.maybe_compress()
            new_urls = self._extract_urls(observation)
            for u in new_urls:
                if u not in self._source_urls:
                    self._source_urls.append(u)
            self.memory.append("user", f"Observation: {observation}")

        # Timeout fallback — ask LLM for best answer with source citations
        if self._source_urls:
            numbered = "\n".join(f"[{i}] {u}" for i, u in enumerate(self._source_urls[:10], 1))
            source_prompt = (
                "\n\nSources you fetched this session:\n" + numbered +
                "\nInclude bracketed citations like [1] next to key claims."
            )
        else:
            source_prompt = ""

        fallback_result = self.llm.chat(
            self.memory.get_context()
            + [{"role": "user", "content": (
                f"Time is up. You've collected what information you can. Based on everything above, "
                f"give your best possible answer to the original question: {query}. "
                "If you lack real-time data, state that clearly and provide the closest information available."
                + source_prompt
            )}]
        )

        if self._source_urls:
            numbered = "\n".join(f"[{i}] {u}" for i, u in enumerate(self._source_urls[:10], 1))
            fallback_result += "\n\n---\n**Sources:**\n" + numbered

        self.memory.append("assistant", fallback_result.strip())
        yield "final_answer", fallback_result.strip()

    def get_session_messages(self) -> list[dict]:
        """Return all messages for reflection."""
        return self.memory.get_context()


def _parse_kwargs(text: str, tool_name: str = "") -> dict:
    """Try to parse JSON args; fall back based on the tool being called."""
    import json
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    # Not valid JSON — sensible defaults per tool
    if tool_name in ("web_search", "memory_search"):
        return {"query": text}
    if tool_name == "python_exec":
        return {"code": text}
    if tool_name == "calculator":
        return {"expression": text}
    if tool_name == "directory_search":
        return {"pattern": text}
    return {"url": text}


def _strip_hallucinated_observations(raw: str) -> str:
    """Remove fake Observation lines the model writes on its own.

    The agent loop supplies real observations. Any 'Observation:' line in the
    LLM output is fabricated data that will cause hallucinations in the final
    answer, so we strip everything from the first Action+Observation pair onward.
    """
    # Once we find a valid Action: ... Action Input: {...} block, cut
    # everything after it to remove hallucinated observations.
    lines = raw.split("\n")
    cutoff = len(lines)
    searching_for_action = False
    in_action_input = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"Action:\s*[\w_]+", stripped):
            searching_for_action = True
        elif searching_for_action and re.match(r"Action\s+Input:", stripped, re.I):
            in_action_input = True
        elif in_action_input:
            if "}" in stripped:
                cutoff = i + 1
                break
    else:
        # No action found — check for standalone Observation lines after any text
        first_obs = None
        for i, line in enumerate(lines):
            if re.match(r"Observation:", line.strip()):
                first_obs = i
                break
        if first_obs is not None:
            cutoff = first_obs

    return "\n".join(lines[:cutoff]).strip() + "\n"


def _parse_multi_response(raw: str, available_tools: set):
    """Extract Final Answer OR all Action blocks from one LLM turn.

    When the model outputs Actions AND hallucinated Observation lines,
    we extract only the valid Action/Action Input pairs and execute them for real.
    We skip any Final Answer that comes after a hallucinated chain.
    """
    import json

    # Line-by-line scanner — reliable across all action formats
    matches = _scan_actions(raw)

    if matches:
        pass  # go down to parse actions below
    elif re.search(r"Action:\s*[\w_]+", raw):
        # Actions exist but JSON couldn't be parsed — best-effort recovery
        matches = _recover_actions(raw, available_tools)
    else:
        # No actions → look for a clean Final Answer
        final = re.search(r"Final Answer:?\s*(.+)", raw, re.DOTALL)
        if final:
            return ("final", final.group(1).strip())
        return None

    actions = []
    for tname, json_blob in matches:
        tname = tname.strip()
        try:
            kwargs = json.loads(json_blob)
            if not isinstance(kwargs, dict):
                kwargs = {}
        except (json.JSONDecodeError, TypeError):
            fallback = json_blob.strip("{} ") if isinstance(json_blob, str) else ""
            kwargs = _parse_kwargs(fallback, tname) or {}
        actions.append((tname, kwargs))

    return ("actions", actions)


def _scan_actions(raw: str) -> list[tuple[str, str]]:
    """Scan raw text line-by-line for `Action:` + `Action Input:` pairs.

    Returns list of (tool_name, json_string) tuples.
    """
    results = []
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"Action:\s*([\w_]+)", line)
        if m:
            # Look for Action Input on the next non-empty line
            j = i + 1
            while j < len(lines) and not re.match(r"Action\s+Input:", lines[j]):
                j += 1
            if j < len(lines):
                input_line = lines[j].strip()
                # Strip "Action Input:" prefix
                json_text = re.sub(r"^Action\s+Input:\s*", "", input_line, flags=re.I)
                # If JSON spans multiple lines, keep merging until balanced braces
                brace_depth = 0
                completed = False
                for ch in json_text:
                    if ch == "{":
                        brace_depth += 1
                    elif ch == "}":
                        brace_depth -= 1
                    if brace_depth <= 0 and "{" in json_text:
                        completed = True
                        break

                while not completed and j + 1 < len(lines):
                    j += 1
                    extra = lines[j].strip()
                    # Stop if next line is a new section header (Observation, Action, etc.)
                    if re.match(r"(Action|Observation|Final Answer|Thought):\s*", extra):
                        break
                    json_text += " " + extra
                    for ch in lines[j].strip():
                        if ch == "{":
                            brace_depth += 1
                        elif ch == "}":
                            brace_depth -= 1
                        if brace_depth <= 0:
                            completed = True
                            break

                results.append((m.group(1), json_text))
        i += 1
    return results


def _recover_actions(raw: str, available_tools: set):
    """Best-effort recovery when Action Input JSON is missing or malformed."""
    action_lines = re.finditer(r"Action:\s*([\w_]+)\s*\n(.+?)(?=\n\s*Action:|\Z)", raw, re.DOTALL)
    results = []
    for m in action_lines:
        tname = m.group(1).strip()
        rest = m.group(2).strip()
        kw = _infer_kwargs(m.group(0), tname) or {"url": rest[:200]}
        results.append((tname, kw))
    return results


def _parse_response(raw: str, available_tools: set):
    """Legacy wrapper — backward compat for single-action path."""
    parsed = _parse_multi_response(raw, available_tools)
    if parsed is None:
        return None
    if parsed[0] == "final":
        return ("final", parsed[1])
    # "actions" → flatten to single action for legacy callers
    actions = parsed[1]
    if len(actions) == 1:
        tname, kwargs = actions[0]
        return ("action", {"tool": tname, "kwargs": kwargs})
    return parsed


def _infer_kwargs(raw: str, tool_name: str) -> dict | None:
    """Try to grok parameters from raw text when JSON is missing."""
    thought_end = re.search(r"Thought:", raw)
    snippet = "" if not thought_end else raw[thought_end.end():]

    # Strip markdown code fences that model sometimes adds
    snippet = re.sub(r"```[\w]*\n?", "", snippet).strip()
    line = snippet.split("\n")[0].strip().lstrip("-").strip()
    if not line:
        return None

    param_map = {
        "web_search": ("query",),
        "memory_search": ("query",),
        "python_exec": ("code",),
        "calculator": ("expression",),
        "directory_search": ("pattern",),
    }
    if tool_name in param_map:
        return {param_map[tool_name][0]: line}

    # web_fetch, finance fallback
    url_match = re.search(r"https?://\S+", raw)
    if url_match and tool_name == "web_fetch":
        return {"url": url_match.group(0)}

    symbol_match = re.search(r"Action:\s*finance", raw)
    if symbol_match:
        ticker = re.search(r"\b([A-Z]{1,5})\b", snippet)
        if ticker:
            return {"symbol": ticker.group(1).upper()}
    return None


def _sanitize_kwargs(kwargs: dict, tool_name: str) -> dict:
    """Merge positional-style args into canonical param names."""
    import json

    try:
        data = json.loads(str(kwargs)) if not isinstance(kwargs, dict) else kwargs
    except (json.JSONDecodeError, TypeError):
        return _infer_kwargs(str(kwargs), tool_name) or kwargs

    if not isinstance(data, dict):
        return data

    aliases = {
        "web_search": ["query"],
        "memory_search": ["query"],
        "python_exec": ["code", "expression"],
        "calculator": ["expression"],
        "directory_search": ["pattern"],
        "finance": ["symbol", "text_query"],
    }

    expected = aliases.get(tool_name, list(data.keys()))
    cleaned = {}
    for k, v in data.items():
        if k in expected:
            cleaned[k] = v
    return cleaned or data


def _build_financial_hint(query: str) -> str | None:
    """Detect financial queries and return a prompt hint to ask for today's data + latest quote."""
    q = query.lower()
    ticker_match = re.search(r"\b([A-Z]{3,5})\b", query)

    fin_keywords = [
        "price", "stock", "ticker", "quote", "share", "trading", "market",
        "earnings", "revenue", "performance", "etf", "funds", "ipo",
        "bullish", "bearish", "dividend", "yield", "pe ratio", "volume",
    ]

    has_fin_keyword = any(kw in q for kw in fin_keywords)

    # A 3-5 letter all-caps word is only treated as a ticker if it's short enough
    # to plausibly be one AND the query has financial context. Plain text with no
    # financial keywords and no obvious ticker gets ignored.
    known_non_tickers = {
        "WHAT", "THE", "WITH", "HAVE", "FROM", "THAT", "THIS", "THEY",
        "WHEN", "WHERE", "WHICH", "THERE", "AFTER", "BEFORE", "ABOUT",
        "YOUR", "MOST", "LONG", "NEAR", "LIKE", "SUCH", "MAKE", "VERY",
    }
    ticker = None
    if ticker_match:
        candidate = ticker_match.group(1).upper()
        if candidate not in known_non_tickers:
            ticker = candidate

    if has_fin_keyword or ticker:
        ticker_note = ""
        if ticker:
            ticker_note = f" The entity's ticker symbol is likely '{ticker}'."

        return (
            "FINANCIAL QUERY RULES:\n"
            f"{ticker_note}\n"
            "- When searching the web, always include 'today' or this date's year/month to ensure current data.\n"
            "- If a ticker symbol is present, first call the finance tool with that symbol to get the latest quote.\n"
            "- Report prices with today's context — do not give stale historical data without noting it."
        )

    return None
"""ReAct agent with cyclic Thought → Action → Observation loop and RAG memory."""

import re
import time
from dataclasses import dataclass, field
from typing import Optional

from morphos.llm import LLMClient
from morphos.tools.registry import ToolRegistry
from morphos.memory.chroma_store import ChromaStore
from morphos.memory.working_memory import WorkingMemory
from morphos.config import Config
from morphos.critic import Critic
from morphos.analyzer import Analyzer
from morphos.dynamic_tools import DynamicToolRegistry
from morphos.heuristics import HeuristicEngine


SYSTEM_PROMPT = r"""You are an AI assistant. You must output exactly one of these two formats each turn:

To use a tool, output this EXACTLY:
Thought: <reason>
Action: <tool_name>
Action Input: {{"arg": "value"}}

To finish, output this EXACTLY:
Final Answer: <answer>

CRITICAL RULES — DO NOT DEViate FROM THE FORMAT ABOVE:
1. Always start a line with "Thought:" before acting
2. Always write "Action: " followed by the exact tool name on its own line
3. Always write "Action Input: " followed by valid JSON on its own line
4. Always end with "Final Answer: " when done — do not wrap it in Thought/Action blocks
5. Use only tools listed below

Available tools:
{tools_list}

Parameter names per tool:
- web_search → {{\"query\": \"...\"}}
- web_fetch → {{\"url\": \"https://...\"}} 
- python_exec → {{\"code\": \"print(...)\"}}
- finance → {{\"symbol\": \"SPY\"}} or {{\"text_query\": \"...\"}}
- file_read → {{\"filepath\": \"/path/to/file\"}} 
- file_write → {{\"filepath\": \"/path\", \"content\": \"...\"}}
- directory_search → {{\"pattern\": \"*.py\"}}
- calculator → {{\"expression\": \"2+3*4\"}}
- memory_search → {{\"query\": \"...\"}}

Examples:

User: What is 15 squared?
Thought: I need to compute 15*15 so I will use the calculator tool.
Action: calculator
Action Input: {{"expression": "15*15"}}

Observation: = 225

Final Answer: 15 squared is 225.

User: What is the price of AAPL?
Thought: The user wants a stock price so I should use the finance tool.
Action: finance
Action Input: {{"symbol": "AAPL"}}

Observation: Latest price for AAPL: $198.50

Final Answer: Apple (AAPL) is currently trading at approximately $198.50."""


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
        self.llm = LLMClient(model=self.model)
        self.registry = ToolRegistry()
        if self.memory is None:
            self.memory = WorkingMemory(max_tokens=6000)

        self.heuristics = HeuristicEngine()
        self.analyzer = Analyzer()
        self.critic = None
        if self.config.critic_enabled:
            self.critic = Critic(llm_client=self.llm, strictness=self.config.critic_strictness)

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

    def run(self, query: str):
        self.memory.clear()
        system_prompt = self._build_system_prompt(query)
        self.memory.append("system", system_prompt)
        self.memory.append("user", query)

        for iteration in range(1, self.max_iterations + 1):
            context = self.memory.get_context()
            llm_raw = self.llm.chat(context)
            yield "llm_response", llm_raw

            parsed = _parse_response(llm_raw, self.registry._tools.keys())
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

            ptype, pdata = parsed  # ptype is "final" or "action"

            if ptype == "final":
                self.memory.append("assistant", llm_raw)
                yield "final_answer", pdata.strip()
                return

            tool_name_str, kwargs = pdata["tool"], pdata["kwargs"]
            tool = self.registry.get(tool_name_str)
            if tool is None:
                observation = f"Unknown tool: {tool_name_str}"
                yield "tool_error", observation
                self.memory.append("assistant", llm_raw)
                self.memory.append("user", f"Observation: {observation}")
                continue

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
                    observation = (
                        f"Critic rejected the output from {tool_name_str}. "
                        "The result was deemed insufficient. Try again with different parameters or a different tool."
                    )
                    yield "critic_reject", observation
                    self.memory.append("assistant", llm_raw)
                    self.memory.append("user", f"Observation: {observation}")
                    continue

            if exec_error:
                self.analyzer.record(
                    tool_name_str, elapsed_ms, "error", iteration,
                    message=exec_error, critic_verdict=critic_verdict,
                )
                yield "tool_error", result
            else:
                self.analyzer.record(
                    tool_name_str, elapsed_ms, "success", iteration,
                    message=str(result)[:200], critic_verdict=critic_verdict,
                )
                yield "tool_result", (tool_name_str, result)

            self.memory.append("assistant", llm_raw)
            self.memory.append("user", f"Observation: {result}")

        fallback_result = self.llm.chat(
            self.memory.get_context()
            + [{"role": "user", "content": (
                f"Time is up. You've collected what information you can. Based on everything above, "
                f"give your best possible answer to the original question: {query}. "
                "If you lack real-time data, state that clearly and provide the closest information available."
            )}]
        )
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


def _parse_response(raw: str, available_tools: set):
    """Extract intent from LLM output. Returns (type, data) or None."""
    import json

    final = re.search(r"Final Answer:?\s*(.+)", raw, re.DOTALL)
    if final:
        return ("final", final.group(1).strip())

    action_re = re.search(r"Action:\s*([\w_]+)", raw)
    input_re = re.search(r"Action Input:\s*\{(.+?)\}", raw, re.DOTALL)

    if action_re:
        tname = action_re.group(1).strip()

        if input_re:
            try:
                kwargs_str = f"{{{input_re.group(1)}}}"
                kwargs = json.loads(kwargs_str)
            except json.JSONDecodeError:
                kwargs = None
        else:
            kwargs = _infer_kwargs(raw, tname)

        return ("action", {"tool": tname, "kwargs": {} if kwargs is None else kwargs})

    # No recognized format at all
    return None


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
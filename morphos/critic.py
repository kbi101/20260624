"""Critic module that reviews tool outputs for correctness and completeness.

Uses a lightweight model (qwen2.5:3b) with a compressed prompt (~80 tokens) to
avoid latency spikes.  Deterministic tools (calculator, python_exec, file_read)
are auto-accepted without an LLM call.
"""

import json
import re
from morphos.llm import LLMClient
from morphos.debug_logger import DebugLogger


# The critic only checks if the TOOL RETURNED useful data for this query.
# It must NOT expect the tool to produce a final summary, article, or essay — that
# happens later in the agent's Final Answer step.
_CRITIC_SYSTEM = """You are a tool-output validator. Reply strictly as: {"v":"accept" or "reject", "r":"reason"}

RULES:
- The tool only needs to return useful RAW DATA (prices, links, snippets, numbers).
- DO NOT reject because the output is not a final summary, essay, report, or polished answer — that comes later.
- Accept if data is relevant and non-empty.
- Reject ONLY on: pure errors, empty output, completely irrelevant content, or clear failures (403/404)."""

_CRITIC_MESSAGE = """User goal: {query}
Tool used: {tool}
Tool returned:\n{output}\nReply:"""

# Strips summary/word-count instructions so the critic doesn't hold raw tool data
# against something it wasn't designed to produce.
_SUMMARY_PATTERNS = [
    re.compile(r"\b(?:write|provide|give)\s+(?:a\s+)?(?:(500|400|300)\s*)?words?.*summar\w*", re.I),
    re.compile(r"\bm(ake|e)\s+((?:an?\s+)?(?:full|detailed|comprehensive))?\s*(?:report|essay|summary|article|piece)", re.I),
    re.compile(r"\b(?:in|with)\s+\d+\s*words?", re.I),
]

_DETERMINISTIC_TOOLS = {"calculator", "python_exec", "file_read", "directory_search"}


def _sanitize_query_for_critic(query: str) -> str:
    """Remove word-count/summary directives — tools don't produce essays."""
    for pat in _SUMMARY_PATTERNS:
        query = pat.sub("", query)
    return re.sub(r"\s+and\s+$", "", re.sub(r"\s{2,}", " ", query), flags=re.I).strip()[:300]


class Critic:
    def __init__(
        self,
        llm_client=None,
        critic_model: str = "qwen2.5:3b",
        strictness: str = "moderate",
        debug_logger: DebugLogger | None = None,
        config=None,
    ):
        self.strictness = strictness
        self.debug = debug_logger or DebugLogger(enabled=False)

        if llm_client and not hasattr(llm_client, "model"):
            raise TypeError("llm_client must be an LLMClient instance")

        self.critic_llm = LLMClient(model=critic_model, debug_logger=self.debug, config=config)
        if llm_client and not critic_model:
            self.critic_llm = llm_client

    def _skip(self, tool_name: str) -> bool:
        return tool_name in _DETERMINISTIC_TOOLS

    def _build_message(self, query: str, tool: str, output: str) -> dict:
        clean_query = _sanitize_query_for_critic(query)
        return {
            "role": "user",
            "content": _CRITIC_MESSAGE.format(
                query=clean_query,
                tool=tool,
                output=output[:1500],
            ),
        }

    def evaluate(self, original_query: str, tool_name: str, tool_output: str) -> bool:
        self.debug.critic_call(tool_name, original_query)

        if self._skip(tool_name):
            self.debug.critic_verdict(tool_name, "accept", "deterministic — auto-accepted")
            return True

        # Heuristic fast-path: reject obvious errors immediately
        low = tool_output.lower().strip()
        if any(phrase in low for phrase in (
            "error:", "failed", "no data found", "empty",
            "403", "404", "unknown tool", "not found",
        )) and len(low) < 60:
            self.debug.critic_verdict(tool_name, "reject", "heuristic fast-reject")
            return False

        messages = [
            {"role": "system", "content": _CRITIC_SYSTEM},
            self._build_message(original_query, tool_name, tool_output),
        ]
        resp = self.critic_llm.chat(messages)

        # Primary: parse JSON
        try:
            data = json.loads(resp)
            v = data.get("v", data.get("verdict", "r"))
            r = data.get("r", data.get("reasoning", ""))
            accept = v in ("a", "accept")
            self.debug.critic_verdict(tool_name, "accept" if accept else "reject", r)
            return accept
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: lean toward accepting when JSON fails
        resp_low = resp.lower()
        if any(w in resp_low for w in ("reject", "error")):
            self.debug.critic_verdict(tool_name, "reject", resp[:500])
            return False
        self.debug.critic_verdict(tool_name, "accept", resp[:500])
        return True

    def review(self, tool_name: str, tool_output: str, original_query: str) -> bool:
        return self.evaluate(original_query, tool_name, tool_output)

"""Debug logger that records every LLM call, tool invocation, and web request."""

import json
import time
from datetime import datetime, timezone


class DebugLogger:
    """Thread-safe debug logger that appends structured entries to a log file."""

    def __init__(self, enabled: bool, log_path: str = "debug.log"):
        self.enabled = enabled
        self.log_path = log_path
        if self.enabled:
            # Truncate on first use so each run gets a fresh log
            with open(log_path, "w") as f:
                f.write(f"# Morphos debug log — started {datetime.now(timezone.utc).isoformat()}\n\n")

    def _write(self, category: str, label: str, data: dict):
        if not self.enabled:
            return
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": int(time.monotonic() * 1000),
            "category": category,
            "label": label,
            **data,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def llm_request(self, model: str, messages: list[dict]):
        self._write("llm", "request", {
            "model": model,
            "messages_count": len(messages),
            "messages": _truncate_messages(messages),
        })

    def llm_response(self, response: str, duration_ms: int):
        self._write("llm", "response", {
            "duration_ms": duration_ms,
            "response_length": len(response),
            "response": response,
        })

    def tool_call(self, tool_name: str, kwargs: dict):
        self._write("tool", "call", {
            "tool": tool_name,
            "kwargs": kwargs,
        })

    def tool_result(self, tool_name: str, result: str, duration_ms: int):
        self._write("tool", "result", {
            "tool": tool_name,
            "duration_ms": duration_ms,
            "result_length": len(result),
            "result": result,
        })

    def tool_error(self, tool_name: str, error: str, duration_ms: int):
        self._write("tool", "error", {
            "tool": tool_name,
            "duration_ms": duration_ms,
            "error": error,
        })

    def web_request(self, url: str, method: str = "GET"):
        self._write("web", "request", {
            "method": method,
            "url": url,
        })

    def web_response(self, url: str, status: str, duration_ms: int, body_preview: str = ""):
        self._write("web", "response", {
            "url": url,
            "status": status,
            "duration_ms": duration_ms,
            "body_length": len(body_preview),
            "body_preview": body_preview[:2000],
        })

    def critic_call(self, tool_name: str, query: str):
        self._write("critic", "call", {
            "tool": tool_name,
            "original_query": query,
        })

    def critic_verdict(self, tool_name: str, verdict: str, reasoning: str = ""):
        self._write("critic", "verdict", {
            "tool": tool_name,
            "verdict": verdict,
            "reasoning": reasoning,
        })

    def agent_step(self, iteration: int, phase: str, detail: str = ""):
        self._write("agent", "step", {
            "iteration": iteration,
            "phase": phase,
            "detail": detail,
        })


def _truncate_messages(messages: list[dict]) -> list[dict]:
    """Shrink long message content so the log stays usable."""
    truncated = []
    for m in messages:
        copy = dict(m)
        content = copy.get("content", "")
        if isinstance(content, str) and len(content) > 1200:
            copy["content"] = content[:600] + "\n...\n[truncated " + str(len(content)) + " chars total]\n" + content[-500:]
        elif isinstance(content, list):
            copy["content"] = [_truncate_block(b) for b in content]
        truncated.append(copy)
    return truncated


def _truncate_block(block: dict) -> dict:
    c = block.get("text", "")
    if len(c) > 800:
        return {**block, "text": c[:400] + "...(truncated)"}
    return block

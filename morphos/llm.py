"""Local LLM interface via Ollama."""

import re
import time
import ollama
from morphos.debug_logger import DebugLogger


# Patterns that leak control tokens from the tokenizer into generated text
_STOP_PATTERNS = [
    re.compile(r"<channel\|>"),
    re.compile(r"\s*<pad>"),
]


class LLMClient:
    def __init__(
        self,
        model: str = "gemma4:12b",
        debug_logger: DebugLogger = None,
        stop_tokens: list[str] | None = None,
    ):
        self.model = model
        self.debug = debug_logger or DebugLogger(enabled=False)

    def chat(self, messages: list[dict]) -> str:
        self.debug.llm_request(self.model, messages)
        t0 = time.monotonic()

        resp = ollama.chat(model=self.model, messages=messages)
        duration_ms = int((time.monotonic() - t0) * 1000)
        content = resp["message"]["content"]

        # Strip any leaked control tokens that slipped through
        for pat in _STOP_PATTERNS:
            content = pat.sub("", content)
        content = content.strip()

        self.debug.llm_response(content, duration_ms)
        return content


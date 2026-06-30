"""LLM interface supporting multiple backends (Ollama, OpenRouter)."""

import json
import os
import re
import time
import ollama
from morphos.debug_logger import DebugLogger


_STOP_PATTERNS = [
    re.compile(r"<channel\|>"),
    re.compile(r"\s*<pad>"),
]


class LLMBackend:
    """Abstract interface for an LLM backend."""

    def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError


class OllamaBackend(LLMBackend):
    def __init__(self, model: str):
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        resp = ollama.chat(model=self.model, messages=messages)
        content = resp["message"]["content"]
        for pat in _STOP_PATTERNS:
            content = pat.sub("", content)
        return content.strip()


class OpenRouterBackend(LLMBackend):
    """Lightweight OpenRouter backend using requests (no SDK dependency)."""

    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    def chat(self, messages: list[dict]) -> str:
        import requests

        resp = requests.post(
            self.ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "messages": messages},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class LLMClient:
    def __init__(
        self,
        model: str = "gemma4:12b",
        debug_logger: DebugLogger = None,
        config=None,
    ):
        self.model = model
        self.debug = debug_logger or DebugLogger(enabled=False)

        if config is not None and getattr(config, "backend", "ollama") == "openrouter":
            override_model = getattr(config, "openrouter_model", None) or model
            api_key = getattr(config, "openrouter_api_key", "")
            if not api_key:
                raise RuntimeError(
                    "OpenRouter backend selected but no API key found. "
                    'Set OPENROUTER_API_KEY env var or pass config.openrouter_api_key.'
                )
            self.backend: LLMBackend = OpenRouterBackend(override_model, api_key)
        else:
            self.backend = OllamaBackend(model)

    def chat(self, messages: list[dict]) -> str:
        self.debug.llm_request(self.model, messages)
        t0 = time.monotonic()

        content = self.backend.chat(messages)

        duration_ms = int((time.monotonic() - t0) * 1000)
        self.debug.llm_response(content, duration_ms)
        return content

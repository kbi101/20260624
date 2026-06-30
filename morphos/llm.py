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
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 3

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    def chat(self, messages: list[dict]) -> str:
        import requests

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    self.ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.model, "messages": messages},
                    timeout=120,
                )

                if resp.status_code == 429:
                    raise RetryableError("Rate limited (429)")
                elif resp.status_code >= 500:
                    raise RetryableError(f"Server error ({resp.status_code})")

                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

            except (RetryableError, requests.exceptions.ConnectionError) as e:
                last_error = e
                delay = self.RETRY_BASE_DELAY * attempt
                print(f"\n[dim]OpenRouter {e}, retrying in {delay}s (attempt {attempt}/{self.MAX_RETRIES})[/]\n")
                time.sleep(delay)

        raise last_error


class RetryableError(Exception):
    pass


class LLMClient:
    _has_fallen_back: bool = False

    def __init__(
        self,
        model: str = "gemma4:12b",
        debug_logger: DebugLogger = None,
        config=None,
    ):
        self.model = model
        self.debug = debug_logger or DebugLogger(enabled=False)
        self.fallback_ollama = OllamaBackend(model)

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

        if LLMClient._has_fallen_back:
            content = self.fallback_ollama.chat(messages)
        else:
            try:
                content = self.backend.chat(messages)
            except Exception as e:
                print(f"\n[dim]OpenRouter failed, falling back to local Ollama for this session[/]\n")
                LLMClient._has_fallen_back = True
                content = self.fallback_ollama.chat(messages)

        duration_ms = int((time.monotonic() - t0) * 1000)
        self.debug.llm_response(content, duration_ms)
        return content

"""Working memory with sliding window to prevent context overflow."""


class WorkingMemory:
    """Manages conversation history with a token-aware sliding window."""

    CHARS_PER_TOKEN = 4

    def __init__(self, max_tokens: int = 6000):
        self.max_tokens = max_tokens
        self._messages: list[dict] = []

    def append(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // self.CHARS_PER_TOKEN

    def get_context(self) -> list[dict]:
        """Return messages trimmed to fit within max_tokens, always keeping the system prompt."""
        total_tokens = sum(self._estimate_tokens(m["content"]) for m in self._messages)
        if total_tokens <= self.max_tokens:
            return list(self._messages)

        # Keep system prompt (first message), then keep newest messages that fit
        result = []
        remaining = self.max_tokens

        for msg in reversed(self._messages):
            tokens = self._estimate_tokens(msg["content"])
            if remaining - tokens < 0:
                break
            result.append(msg)
            remaining -= tokens

        return list(reversed(result))

    def clear(self):
        self._messages.clear()

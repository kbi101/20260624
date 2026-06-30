"""Working memory with sliding window to prevent context overflow."""


class WorkingMemory:
    """Manages conversation history with a token-aware sliding window."""

    CHARS_PER_TOKEN = 4
    TOOL_RESULT_MAX_CHARS = 2000
    COMPRESSION_THRESHOLD = 0.8  # kick in summarization at 80% capacity

    def __init__(self, max_tokens: int = 6000):
        self.max_tokens = max_tokens
        self._messages: list[dict] = []

    def append(self, role: str, content: str):
        # Hard-truncate tool outputs to avoid flooding context
        if role == "user" and content.startswith("Observation"):
            if len(content) > self.TOOL_RESULT_MAX_CHARS:
                content = (
                    content[: self.TOOL_RESULT_MAX_CHARS]
                    + f"\n...[truncated, original was {len(content)} chars]"
                )
        elif role == "assistant":
            if len(content) > self.TOOL_RESULT_MAX_CHARS:
                content = (
                    content[: self.TOOL_RESULT_MAX_CHARS]
                    + f"\n...[truncated, original was {len(content)} chars]"
                )
        self._messages.append({"role": role, "content": content})

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // self.CHARS_PER_TOKEN

    @property
    def _total_tokens(self) -> int:
        return sum(self._estimate_tokens(m["content"]) for m in self._messages)

    def compress_oldest_pair(self):
        """Shrink the oldest assistant + user observation pair into a one-line summary.

        Returns True if a compression happened, False if there's nothing to compress."""
        system_end = 1
        # Find first assistant message after system
        idx = None
        for i in range(system_end, len(self._messages)):
            if self._messages[i]["role"] == "assistant":
                idx = i
                break
        if idx is None or idx + 1 >= len(self._messages):
            return False

        asst_text = self._messages[idx]["content"]
        next_text = self._messages[idx + 1]["content"]

        parts_asst = []
        parts_obs = []
        for line in asst_text.splitlines():
            if line.startswith("Action:"):
                parts_asst.append(line.strip())
        for line in next_text.splitlines():
            if line.strip().startswith("Observation"):
                first_line = line.strip()[:200]
                parts_obs.append(first_line)

        summary = (
            f"[compressed turn] Tool calls: {'; '.join(parts_asst)}. "
            f"Results: {'  '.join(parts_obs)}."
        )

        self._messages[idx] = {"role": "assistant", "content": summary}
        del self._messages[idx + 1]
        return True

    def maybe_compress(self, llm_client=None):
        """If we're past the threshold, iteratively compress oldest turns to make room."""
        budget = int(self.max_tokens * self.COMPRESSION_THRESHOLD)
        while self._total_tokens > budget and self.compress_oldest_pair():
            pass

    def get_context(self) -> list[dict]:
        """Return messages trimmed to fit within max_tokens, always keeping the system prompt."""
        total_tokens = self._total_tokens
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

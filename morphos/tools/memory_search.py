"""Tool that lets the agent query its own persistent memory."""

from morphos.memory.chroma_store import ChromaStore
from morphos.tools.registry import Tool


class MemorySearch(Tool):
    """Searches the agent's stored facts and lessons via ChromaDB."""

    def __init__(self, store: ChromaStore | None = None):
        self.store = store

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return (
            "Search the agent's persistent memory for previously stored facts, lessons, and knowledge. "
            "Use this to recall information from past sessions."
        )

    def execute(self, query: str) -> str:
        if self.store is None:
            return "Memory store not initialized yet."

        results = self.store.query(query, n_results=5)
        if not results:
            return "No relevant memories found for that query."

        lines = []
        for r in results:
            source = r.get("source", "unknown")
            text = r["text"]
            meta = r.get("metadata", {}) or {}
            ts = meta.get("timestamp", "")
            line = f"[{source}] {text}"
            if ts:
                line += f" (stored: {ts[:10]})"
            lines.append(line)

        return "Relevant memories:\n" + "\n".join(lines)

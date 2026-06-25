"""Session reflection - extracts facts and lessons from conversation history."""

import json
from morphos.memory.chroma_store import ChromaStore


REFLECTION_PROMPT = """Analyze this completed agent session. Extract two categories of information:

1. KEY FACTS: Factual information, user preferences, personal details, or domain knowledge.
2. LESSONS: Patterns about tool behavior, what succeeded/failed, strategies that worked.

Only extract genuinely useful items. If nothing worth remembering, return empty lists.

Respond in THIS EXACT JSON format:
{{"facts": ["f1", "f2"], "lessons": ["l1"]}}

Session transcript:
{transcript}"""


class Reflector:
    def __init__(self, chroma_store: ChromaStore, llm_client=None):
        self.store = chroma_store
        self.llm = llm_client

    def reflect(self, messages: list[dict], session_id: str) -> dict:
        transcript = "\n".join(
            f"{m['role']}: {m['content'][:2000]}" for m in messages
        )
        resp = self.llm.chat([{"role": "user", "content": REFLECTION_PROMPT.format(transcript=transcript)}])

        facts: list[str] = []
        lessons: list[str] = []

        try:
            data = json.loads(resp)
            if isinstance(data, dict):
                facts = data.get("facts", []) or []
                lessons = data.get("lessons", []) or []
        except (json.JSONDecodeError, TypeError):
            lines = [l.strip().lstrip("-*• ").strip() for l in resp.strip().split("\n")]
            lessons = [l for l in lines if len(l) > 10]

        for f in facts:
            self.store.add_fact(f, session_id)
        for l in lessons:
            self.store.add_lesson(l, session_id)

        return {"facts_stored": len(facts), "lessons_stored": len(lessons)}

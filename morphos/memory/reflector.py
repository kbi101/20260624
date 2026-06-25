"""Session reflection - extracts facts, lessons, and source heuristics from conversation history."""

import json
import re
from morphos.memory.chroma_store import ChromaStore


REFLECTION_PROMPT = """Analyze this completed agent session. Extract three categories of information:

1. KEY FACTS: Factual information, user preferences, personal details, or domain knowledge.
2. LESSONS: Patterns about tool behavior, what succeeded/failed, strategies that worked.
3. SOURCE HEURISTICS: Specific webpage patterns that reliably provided correct data for certain query types.
   Format as: {"query_pattern": "...", "url": "...", "notes": "..."}
   - query_pattern: regex-like description of queries this source works for (e.g., "earnings date", "stock price")
   - url: the actual URL that worked (include template vars like {ticker} where applicable)
   - notes: why it worked or what to watch out for

Only extract genuinely useful items. If nothing worth remembering, return empty lists.

Respond in THIS EXACT JSON format:
{{"facts": ["f1", "f2"], "lessons": ["l1"], "source_heuristics": [{{"query_pattern": "...", "url": "...", "notes": "..."}}]}}

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
        source_heuristics: list[dict] = []

        try:
            data = json.loads(resp)
            if isinstance(data, dict):
                facts = data.get("facts", []) or []
                lessons = data.get("lessons", []) or []
                source_heuristics = data.get("source_heuristics", []) or []
        except (json.JSONDecodeError, TypeError):
            lines = [l.strip().lstrip("-*• ").strip() for l in resp.strip().split("\n")]
            lessons = [l for l in lines if len(l) > 10]

        for f in facts:
            self.store.add_fact(f, session_id)
        for l in lessons:
            self.store.add_lesson(l, session_id)

        # Store source heuristics to the heuristic engine
        if source_heuristics:
            try:
                from morphos.heuristics import HeuristicEngine
                engine = HeuristicEngine()
                for sh in source_heuristics:
                    qp = sh.get("query_pattern", "")
                    url = sh.get("url", "")
                    notes = sh.get("notes", "")
                    if qp and url:
                        engine.add_heuristic(pattern=qp, preferred_source=url, notes=notes)
                engine.save()
            except Exception:
                pass

        return {"facts_stored": len(facts), "lessons_stored": len(lessons), "heuristics_learned": len(source_heuristics)}

"""Multi-resolution compression pipeline — derives levels from generated concept data."""

from uct.models import CompressionLevels, Concept


class Compressor:
    """Derives 4 resolution levels from Concept fields (no extra LLM calls)."""

    def __init__(self, llm_client):
        self.llm = llm_client  # Reserved for future LLM-driven compression

    def compress_all(self, topic: str, concepts: list[Concept]) -> list[CompressionLevels]:
        topic_lower = topic.strip().lower()
        matched = [c for c in concepts if c.name.strip().lower() == topic_lower or topic_lower in c.name.strip().lower() or c.name.strip().lower() in topic_lower]
        unmatched = [c for c in concepts if c not in matched]
        ordered_concepts = matched + unmatched
        return [self._derive_levels(c) for c in ordered_concepts[:8] if c.definition]

    @staticmethod
    def _derive_levels(c: Concept) -> CompressionLevels:
        # Level 0 — Essence: just the definition (1 line)
        essence = c.definition.split('.')[0].strip() if c.definition else c.name

        # Level 1 — Functional: why it exists + constraints summary
        constraint_sum = " Constraints: " + ", ".join(c.constraints[:2]) if c.constraints else ""
        functional = f"{c.why_it_exists}{constraint_sum}" if c.why_it_exists else essence

        # Level 2 — Detailed: full definition + failure modes
        failure_sum = " Failure modes: " + ", ".join(c.failure_modes[:2]) if c.failure_modes else ""
        detailed = f"{c.definition}\n{c.why_it_exists}{failure_sum}"

        # Level 3 — Expert: re-derive from constraints as edge cases
        expert = (
            "Edge cases arise when constraints are violated: " +
            "; ".join(c.constraints) if c.constraints else "None documented."
        )

        return CompressionLevels(
            concept_name=c.name,
            level_0_essence=essence[:200],
            level_1_functional=functional[:400],
            level_2_detailed=detailed[:600],
            level_3_expert=expert[:500],
        )

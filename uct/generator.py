"""LLM orchestration pipeline: dimension analysis → object generation → compression → graph."""

import json
from typing import Optional

from uct.models import (
    Concept,
    SequenceBlock,
    CausalLoopBlock,
    PerspectiveMatrix,
    CompressionLevels,
    GraphEdge,
    ScaledConcept,
    DimensionProfile,
    TopicModel,
)


MEGA_PROMPT = r"""You are a Universal Cognitive Textbook engine. Given a topic, produce a complete structured knowledge dashboard in ONE JSON response.

TOPIC: {topic}
MODE: {mode}

Return STRICT JSON with this exact structure (no prose outside the JSON):

{{
  "dimensions": {{
    "structural": <float 0-1>,
    "sequential": <float 0-1>,
    "causal": <float 0-1>,
    "comparative": <float 0-1>,
    "spatial": <float 0-1>,
    "abstract": <float 0-1>,
    "dominant": ["dim1", "dim2"]
  }},

  "concepts": [
    {{
      "name": "<concept name>",
      "definition": "<one sentence>",
      "why_it_exists": "<what problem does it solve?>",
      "constraints": ["c1", "c2"],
      "failure_modes": ["f1", "f2"]
    }}
  ],

  "sequence_blocks": [
    {{
      "title": "<process name>",
      "steps": [{{"label":"..","transformation":"..","output":".."}}]
    }}
  ],

  "causal_loops": [
    {{
      "title": "<loop name>",
      "loops": [["A","B","C","A"]],
      "links": [{{"from_node":"A","to_node":"B","effect":"increases or decreases"}}],
      "loop_type": "reinforcing or balancing"
    }}
  ],

  "matrices": [
    {{
      "title": "<comparison title>",
      "attributes": ["attr1", "attr2"],
      "options": ["opt1", "opt2"],
      "cells": {{"attr1|opt1":"val","attr1|opt2":"val"}}
    }}
  ],

  "edges": [{{"from":"ConceptA","to":"ConceptB","edge_type":"prerequisite"}}],

  "scales": [{{"name":"ConceptA","scale":"component"}}]
}}

RULES:
- Generate 5-8 concepts
- At least 1 sequence block describing the main data flow or process
- At least 1 causal loop showing feedback dynamics
- At least 1 comparison matrix
- 6-12 edges between concepts (types: prerequisite, enables, contradicts, generalizes, specializes, analogous_to, historically_follows)
- Scale levels: physical, component, system, network, emergent
- Mode guidance:
  * understand: balanced conceptual overview
  * exam: emphasize hard constraints, edge cases, and failure modes
  * practice: emphasize detailed sequence steps, transformations, and failure conditions
  * research: emphasize causal loops, graph edge network, and comparative matrices
  * overview: concise definitions and clear taxonomy
- DO NOT include markdown or prose outside the JSON
"""


class UCTGenerator:
    """Orchestrates LLM calls to produce a full TopicModel."""

    def __init__(self, llm_client):
        self.llm = llm_client

    # ── Public API ─────────────────────────────────────────────────

    def generate(self, topic: str, research_context: str = "", mode: str = "understand") -> TopicModel:
        """Single-shot pipeline: one LLM call produces everything."""
        prompt = MEGA_PROMPT.format(topic=topic, mode=mode)
        if research_context:
            prompt += f"\n\nContext to ground your output:\n{research_context[:2000]}"

        resp = self.llm.chat([{"role": "user", "content": prompt}])
        data = _parse_json(resp)
        if not data:
            return TopicModel(topic=topic, dimension_profile=DimensionProfile(
                dominant=["structural"], primary_concepts=[topic],
            ))

        model = TopicModel(topic=topic)

        # Dimensions
        dim_data = data.get("dimensions", {})
        model.dimension_profile = DimensionProfile(
            structural=float(dim_data.get("structural", 0.5)),
            sequential=float(dim_data.get("sequential", 0.3)),
            causal=float(dim_data.get("causal", 0.4)),
            comparative=float(dim_data.get("comparative", 0.3)),
            spatial=float(dim_data.get("spatial", 0.2)),
            abstract=float(dim_data.get("abstract", 0.3)),
            dominant=dim_data.get("dominant", []),
            primary_concepts=[],
        )

        # Concepts
        for cd in data.get("concepts", []):
            try:
                c = Concept(
                    name=str(cd.get("name", "")),
                    definition=str(cd.get("definition", ""))[:300],
                    why_it_exists=str(cd.get("why_it_exists", ""))[:500],
                    constraints=cd.get("constraints", []),
                    failure_modes=cd.get("failure_modes", []),
                )
                if c.name:
                    model.concepts.append(c)
            except Exception:
                continue
        model.dimension_profile.primary_concepts = [c.name for c in model.concepts]

        # Sequence blocks
        from uct.models import Step as S
        for sb in data.get("sequence_blocks", []):
            try:
                steps = [
                    S(
                        label=s.get("label", f"Step {i}"),
                        input=s.get("input", ""),
                        transformation=s.get("transformation", ""),
                        validation=s.get("validation", ""),
                        output=s.get("output", ""),
                        failure_condition=s.get("failure_condition", ""),
                        prerequisites=s.get("prerequisites", []),
                    )
                    for i, s in enumerate(sb.get("steps", []))
                ]
                model.sequence_blocks.append(SequenceBlock(title=sb.get("title", ""), steps=steps))
            except Exception:
                continue

        # Causal loops
        from uct.models import Link as L
        for cl in data.get("causal_loops", []):
            try:
                links = [
                    L(
                        from_node=l.get("from_node", ""),
                        to_node=l.get("to_node", ""),
                        effect=l.get("effect", ""),
                        delay=l.get("delay", ""),
                    )
                    for l in cl.get("links", [])
                ]
                model.causal_loops.append(CausalLoopBlock(
                    title=cl.get("title", ""),
                    loops=cl.get("loops", []),
                    links=links,
                    loop_type=cl.get("loop_type", "balancing"),
                ))
            except Exception:
                continue

        # Matrices
        for mx in data.get("matrices", []):
            try:
                cells: dict[tuple[str, str], str] = {}
                raw_cells = mx.get("cells", {})
                for k, v in raw_cells.items():
                    if "|" in str(k):
                        parts = str(k).split("|", 1)
                        cells[(parts[0].strip(), parts[1].strip())] = str(v)
                model.matrices.append(PerspectiveMatrix(
                    title=mx.get("title", ""),
                    attributes=mx.get("attributes", []),
                    options=mx.get("options", []),
                    cells=cells,
                ))
            except Exception:
                continue

        # Edges
        for ed in data.get("edges", []):
            try:
                model.edges.append(GraphEdge(
                    from_node=str(ed.get("from", "")),
                    to_node=str(ed.get("to", "")),
                    edge_type=str(ed.get("edge_type", "prerequisite")),
                ))
            except Exception:
                continue

        # Scales
        for sc in data.get("scales", []):
            try:
                cname = str(sc.get("name", ""))
                matched = next((c for c in model.concepts if c.name == cname), None)
                concept_to_wrap = matched or Concept(name=cname, definition="", why_it_exists="")
                scaler = ScaledConcept(concept=concept_to_wrap, scale=str(sc.get("scale", "system")))
                model.scaled_concepts.append(scaler)
            except Exception:
                continue

        return model


# ── Helpers ────────────────────────────────────────────────────────

def _parse_json(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return d
    except (json.JSONDecodeError, TypeError):
        pass
    import re
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            d = json.loads(m.group())
            if isinstance(d, dict):
                return d
        except (json.JSONDecodeError, TypeError):
            pass
    return None

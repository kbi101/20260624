"""LLM prompt templates for every UCT generation phase."""

DIMENSION_ANALYSIS_PROMPT = r"""You are a cognitive dimension analyzer. Given a topic, decompose it into 6 cognitive dimensions.

Topic: {topic}

Each dimension is weighted 0.0 to 1.0 based on how central that lens is for understanding this topic.

Dimensions:
- structural: What exists? Types, hierarchies, components, taxonomy.
- sequential: Processes, pipelines, algorithms, timelines, workflows.
- causal: Why things happen, feedback loops, dependencies, systems behavior.
- comparative: Competitive options, tradeoff matrices, architectural alternatives.
- spatial: Physical arrangement, data flow topology, component placement.
- abstract: First principles, axioms, symbolic laws, governing theory.

Return STRICT JSON only (no prose, no markdown):
{{
  "structural": <float>,
  "sequential": <float>,
  "causal": <float>,
  "comparative": <float>,
  "spatial": <float>,
  "abstract": <float>,
  "dominant": ["dim1", "dim2"],
  "primary_concepts": ["concept1", "concept2", ...]
}}

Rules:
- dominant = top 2-3 dimensions by weight
- primary_concepts = 5-8 irreducible concepts that define the topic
- weights should sum roughly to 3.0-4.5 (not all dimensions are equal)"""


CONCEPT_GENERATION_PROMPT = r"""Generate a Core Concept Object for "{concept_name}" in context of topic: "{topic}".

Context from research:\n{research_context}

Return STRICT JSON only (no prose, no markdown wrapping):
{{
  "name": "<exact concept name>",
  "definition": "<one sentence max>",
  "why_it_exists": "<what problem does it solve?>",
  "constraints": ["constraint 1", "constraint 2"],
  "failure_modes": ["mode 1", "mode 2"]
}}

Rules:
- Be dense and precise
- definition must be exactly one sentence
- constraints are hard boundaries, not preferences
- failure_modes describe what breaks when the concept fails"""


SEQUENCE_GENERATION_PROMPT = r"""Generate a Sequence Block for "{sequence_title}" in context of topic: "{topic}".

Context from research:\n{research_context}

Return STRICT JSON only (no prose, no markdown wrapping):
{{
  "title": "<sequence title>",
  "steps": [
    {{
      "label": "Step name",
      "input": "what enters this step",
      "transformation": "what changes",
      "validation": "how correctness is checked",
      "output": "what leaves this step",
      "failure_condition": "what goes wrong here",
      "prerequisites": ["dep1"]
    }}
  ]
}}

Rules:
- 3-7 steps per sequence
- Each step must declare input → transformation → output explicitly"""


CAUSAL_LOOP_GENERATION_PROMPT = r"""Generate a Causal Loop Block for "{loop_title}" in context of topic: "{topic}".

Context from research:\n{research_context}

Return STRICT JSON only (no prose, no markdown wrapping):
{{
  "title": "<loop title>",
  "loops": [["A", "B", "C", "A"]],
  "links": [
    {{
      "from_node": "A",
      "to_node": "B",
      "effect": "increases or decreases",
      "delay": "temporal lag if any"
    }}
  ],
  "loop_type": "reinforcing or balancing"
}}

Rules:
- Each loop is a list of node names forming a cycle (first == last)
- Links describe the directional causality between consecutive nodes
- loop_type: reinforcing = amplifies; balancing = self-correcting"""


MATRIX_GENERATION_PROMPT = r"""Generate a Perspective Matrix comparing {options_list} in context of topic: "{topic}".

Context from research:\n{research_context}

Return STRICT JSON only (no prose, no markdown wrapping):
{{
  "title": "<comparison title>",
  "attributes": ["attr1", "attr2", ...],
  "options": ["opt1", "opt2", ...],
  "cells": {{
    "attr1|opt1": "value",
    "attr1|opt2": "value",
    ...
  }}
}}

Rules:
- attributes are the comparison dimensions (rows)
- options are what is being compared (columns)
- cells use "attribute|option" as key
- Be concise in cell values"""


COMPRESSION_PROMPT = r"""Compress this concept to 4 resolution levels. Return STRICT JSON only:

Topic: {topic}
Concept: {concept_name}
Definition: {definition}

Return JSON:
{{
  "concept_name": "...",
  "level_0_essence": "<one line: what is it>",
  "level_1_functional": "<2-3 lines: core mechanics>",
  "level_2_detailed": "<5-7 lines: implementation specifics>",
  "level_3_expert": "<edge cases, debates, unresolved questions>"
}}

Rules:
- Level 0: single sentence a beginner can retain
- Level 1: working mental model
- Level 2: enough to implement or teach
- Level 3: what experts debate"""


GRAPH_EDGE_GENERATION_PROMPT = r"""Generate typed edges between concepts for topic: "{topic}".

Concepts: {concept_names}

Edge types:
- prerequisite: A must be understood before B
- enables: A enables capability B
- contradicts: A and B conflict or compete
- generalizes: A is a broader version of B
- specializes: A is a narrower version of B
- analogous_to: A structurally resembles B
- historically_follows: A came after B in practice

Return STRICT JSON array (no prose, no markdown):
[
  {{"from": "A", "to": "B", "edge_type": "prerequisite"}},
  ...
]

Rules:
- Generate 5-15 edges
- Only connect concepts that genuinely relate
- Prefer prerequisite and enables edges (they are most useful)"""


SCALE_GENERATION_PROMPT = r"""Assign scale levels to concepts for topic: "{topic}".

Scale levels:
- physical: Hardware, signals, bits on wire
- component: Libraries, modules, individual services
- system: Full deployed systems, platforms
- network: Distributed systems, multi-tenant, ecosystems
- emergent: Systemic behaviors, market effects, social dynamics

Concepts to tag: {concept_names}

Return STRICT JSON array (no prose, no markdown):
[
  {{"name": "ConceptA", "scale": "system"}},
  ...
]

Assign each concept its most representative scale level."""


RESEARCH_CONTEXT_PROMPT = r"""You are building structured knowledge about: {topic}

Use the following research context to ground your output in real, current information:

{research_text}

If a specific detail is not covered by the research, use your best domain knowledge."""

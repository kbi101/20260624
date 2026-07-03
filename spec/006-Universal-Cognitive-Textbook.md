# Phase 6 — Universal Cognitive Textbook (UCT) Agent

## Status: Planned

## Overview

Build a specialized sub-agent that generates **cognitive dashboards** instead of prose. Given any topic, it decomposes knowledge into six cognitive dimensions, emits structured Knowledge Objects, and renders a terminal layout optimized for model construction rather than passive reading.

First demo topic: **Observability in Cloud and AI Applications**.

## Architecture

```
20260624/
├── morphos/              # Existing agent framework (unchanged)
├── uct/                  # NEW — UCT engine package
│   ├── __init__.py
│   ├── models.py         # Knowledge Object dataclasses
│   ├── dimensions.py     # 6-dimension taxonomy + weightings
│   ├── prompts.py        # LLM prompt templates per dimension/block type
│   ├── generator.py      # LLM orchestrator — produces Knowledge Objects
│   ├── renderer.py       # Rich terminal rendering engine
│   ├── graph.py          # Knowledge graph (nodes + typed edges)
│   ├── compressor.py     # Multi-resolution compression pipeline
│   └── toolkit.py        # UCTTool wrapper for ReAct integration
└── spec/
    └── 006-Universal-Cognitive-Textbook.md  ← this file
```

## Integration Points

### Router Registration

Add `TEXTBOOK` as a new domain in `morphos/multi_agent.py`:

```python
"TEXTBOOK": SubAgentConfig(
    name="textbook_agent",
    system_prompt_addon=(
        "You are a Universal Cognitive Textbook engine. Your job is NOT to write "
        "prose explanations. Given a topic, decompose it into cognitive dimensions, "
        "generate structured Knowledge Objects, and render them as a terminal dashboard."
    ),
    allowed_tools=["web_search", "web_fetch", "python_exec", "uct_generate"],
)
```

Router prompt gains a fourth classification:

```
- TEXTBOOK: deep explanations of technical/academic topics, "explain X", "teach me Y",
            textbook-style requests, systematic understanding of complex subjects
```

### UCTTool

`uct/toolkit.py` exposes a `UCTGenerate` tool conforming to the `ToolRegistry` ABC:

```python
class UCTGenerate(Tool):
    name = "uct_generate"
    description = "Generate a cognitive dashboard for a topic"
    
    def execute(self, topic: str, depth: int = 1, mode: str = "understand") -> str:
        """Orchestrates dimension analysis → object generation → terminal rendering."""
```

The tool returns a fully-rendered string that the agent appends as an observation.

## Core Design

### 1. Six Cognitive Dimensions (`dimensions.py`)

Every topic decomposes into these dimensions with LLM-assigned weightings:

```python
DIMENSIONS = {
    "structural":    {"question": "What exists?",          "blocks": ["Concept", "Hierarchy"]},
    "sequential":    {"question": "What happens in order?", "blocks": ["Sequence"]},
    "causal":        {"question": "Why does it happen?",    "blocks": ["CausalLoop", "DependencyGraph"]},
    "comparative":   {"question": "How is X different from Y?", "blocks": ["PerspectiveMatrix"]},
    "spatial":       {"question": "Where/how arranged?",   "blocks": ["ArchitectureDiagram"]},
    "abstract":      {"question": "What governs this?",     "blocks": ["Axioms", "Principles"]},
}
```

Dimension weightings per topic are computed by the LLM in a dedicated analysis pass before generating content. Example for observability:

```json
{
  "structural": 0.9,    // metrics/logs/traces framework
  "sequential": 0.7,    // data pipeline flow
  "causal": 0.8,        // why signals correlate, alerting loops
  "comparative": 0.6,   // OpenTelemetry vs Datadog vs Prometheus
  "spatial": 0.5,       // where components sit in stack
  "abstract": 0.4       // first principles of measurement
}
```

High-weight dimensions get more Knowledge Objects and screen real estate. Weight < 0.3 is sketched briefly or omitted.

### 2. Knowledge Object Models (`models.py`)

Strict dataclasses, no freeform prose:

#### Core Concept Object

```python
@dataclass
class Concept:
    name: str
    definition: str          # Max 1 sentence
    why_it_exists: str       # Problem statement
    constraints: list[str]   # Hard boundaries
    failure_modes: list[str] # What breaks and how
```

#### Sequence Block

```python
@dataclass
class Step:
    label: str
    input: str
    transformation: str
    validation: str
    output: str
    failure_condition: str
    prerequisites: list[str]

@dataclass 
class SequenceBlock:
    title: str
    steps: list[Step]
```

#### Causal Loop Block

```python
@dataclass
class Link:
    from_node: str
    to_node: str
    effect: str              # "increases", "decreases", "delays"
    delay: str = ""          // Temporal lag annotation

@dataclass
class CausalLoopBlock:
    title: str
    loops: list[list[str]]   # Cycle descriptions
    links: list[Link]
    loop_type: str           # "reinforcing" | "balancing"
```

#### Perspective Matrix

```python
@dataclass
class PerspectiveMatrix:
    title: str
    attributes: list[str]    # Row headers
    options: list[str]       # Column headers
    cells: dict[tuple[str, str], str]  # (attr, option) → value
```

#### Scale Layer Tag

```python
SCALE_LEVELS = ["physical", "component", "system", "network", "emergent"]

@dataclass
class ScaledConcept:
    concept: Concept
    scale: str               # One of SCALE_LEVELS
```

### 3. Generation Pipeline (`generator.py`)

Three-phase LLM orchestration:

**Phase A — Dimension Analysis**

Single LLM call that returns the 6-dimension weightings + dominant dimensions for the topic. Prompt template in `prompts.py`.

**Phase B — Knowledge Object Generation**

For each dominant dimension (weight ≥ 0.4), issue a targeted LLM call to generate structured objects. Each call outputs strict JSON matching one of the model types above. Few-shot examples provided per block type.

Key constraint: **no prose allowed**. The LLM must output YAML-like structured data. Post-processing validates against dataclass schemas. Failed validation triggers retry with format correction.

**Phase C — Compression Levels**

For each generated concept, the compressor produces 4 resolution variants:

```
Level 0 (Essence):    "Distributed tracing: tracking a request across microservices"
Level 1 (Functional): "Each request gets a trace ID child spans per service, parent-child hierarchy reconstructs the full path"
Level 2 (Detailed):   Propagation headers (W3C traceparent), span attributes, sampling strategies, OTLP export protocol
Level 3 (Expert):     Probabilistic vs dynamic sampling tradeoffs, tail-based sampling at collector, eBPF-based auto-instrumentation limitations
```

**Phase D — Graph Construction**

All concepts become graph nodes. The LLM generates typed edges:

```python
EDGE_TYPES = [
    "prerequisite",      # A must be understood before B
    "enables",          # A enables B
    "contradicts",      # A and B conflict
    "generalizes",      # A is a broader version of B
    "specializes",      # A is a narrower version of B  
    "analogous_to",     # A is like B in structure
    "historically_follows",  # A came after B
]
```

### 4. Terminal Renderer (`renderer.py`)

Uses Rich to render the **cognitive dashboard layout**:

```
┌─────────────────────────────────────────────────────────────┐
│  ▓ TOP: Core Concept Object (title + 1-sentence definition) │
├─────────────────────────────────────────────────────────────┤
│                     ▓ Essence (Level 0)                     │
├──────────────────┬──────────────────────┬──────────────────┤
│  ▓ LEFT:          │   ▓ CENTER:          │   ▓ RIGHT:       │
│  Prerequisites    │   Primary blocks     │   Comparison     │
│  graph / related  │   for dominant dim.  │   matrix (if      │
│  concepts         │                      │   comparative>0.4)│
├──────────────────┼──────────────────────┼──────────────────┤
│ ▓ BOTTOM: Failure modes, real-world applications, scale     │
│   layer tags, expert notes (collapsed at low depth)         │
└─────────────────────────────────────────────────────────────├
```

#### Rendering Rules

**Rule 1 — One Cognitive Function Per Region**: No mixing explanations with exceptions or comparisons within the same Rich Panel.

**Rule 2 — Color-Coded Dimensions**: Each dimension gets a consistent border color:
- Structural: blue
- Sequential: cyan
- Causal: magenta
- Comparative: yellow
- Spatial: green
- Abstract: white

**Rule 3 — Prose Length Limit**: Any text block exceeding 7 lines triggers a post-processing pass that splits or compresses it.

**Rule 4 — Depth Controls Visibility**:
- `depth=0`: Only TOP + Essence bar
- `depth=1`: TOP + Essence + CENTER (dominant dimension)
- `depth=2`: Full dashboard including LEFT/RIGHT/BOTTOM
- `depth=3`: Everything plus Level 3 expert notes, edge cases, unresolved debates

#### Adaptive Modes

`--uct-mode` select:
| Mode | Rendering Emphasis |
|------|-------------------|
| `understand` (default) | Causal emphasis, full explanation |
| `exam` | Compression-heavy, Level 2-3, dense notation |
| `practice` | Sequence blocks, procedures, failure modes |
| `research` | Edge cases, debates, unresolved questions |
| `overview` | Comparative matrix + Essence only |

### 5. Router Detection Heuristic

The router prompt for TEXTBOOK classification:

```
TEXTBOOK detection signals:
- "explain [complex topic]" 
- "teach me about X"
- "how does X work systematically"
- topic names: frameworks, architectures, paradigms, theories
- requests for "thorough", "comprehensive", "structured" explanations
- questions spanning multiple concepts in one domain
```

## Prompt Templates (`prompts.py`)

### Dimension Analysis Prompt

```
Given the topic: "{topic}"

Decompose it into 6 cognitive dimensions. Return JSON:
{{
  "structural": <0-1 weight>,
  "sequential": <0-1>,
  "causal": <0-1>,
  "comparative": <0-1>,
  "spatial": <0-1>,
  "abstract": <0-1>,
  "dominant": ["dim1", "dim2"],   // Top 2-3 dimensions
  "primary_concepts": ["concept1", ...]  // 5-8 core concepts to cover
}}
```

### Concept Generation Prompt (per dimension)

```
Generate a Core Concept Object for "{concept_name}" in the context of {topic}.
Strict JSON output matching this schema:
{{
  "name": "...",
  "definition": "One sentence max.",
  "why_it_exists": "What problem does it solve?",
  "constraints": ["c1", "c2"],
  "failure_modes": ["f1", "f2"]
}}

Rules: NO prose. NO explanation outside JSON. Be precise and dense.
```

Similar strict templates for each block type (Sequence, CausalLoop, PerspectiveMatrix).

### Compression Prompt

```
Compress this concept to 4 resolution levels. Return JSON:
{{
  "level_0_essence": "<one line: what is it>",
  "level_1_functional": "<2-3 lines: how it works>",
  "level_2_detailed": "<5-7 lines: implementation specifics>", 
  "level_3_expert": "<edge cases, debates, exceptions>"
}}

Concept: {concept_json}
```

### Graph Edge Generation Prompt

```
Here are concepts from the topic "{topic}":
{concept_names}

Generate typed edges between them. Return JSON array:
[{{"from": "A", "to": "B", "type": "prerequisite"}}, ...]

Edge types: prerequisite, enables, contradicts, generalizes, 
             specializes, analogous_to, historically_follows
```

## Tool Integration

### UCTGenerate Tool Parameters

```python
execute(
    topic: str,           # "observability in cloud and AI applications"
    depth: int = 1,       # 0-3 resolution level  
    mode: str = "understand",  # understand/exam/practice/research/overview
) -> str                  # Rich-rendered dashboard string
```

### Search Augmentation

Before generating, the tool uses `web_search` and `web_fetch` to gather current information about the topic. Web observations are injected into the generation prompts as context so the LLM grounds structured output in real data rather than training memory alone.

Flow:
1. Tool receives topic
2. Spawns internal web search for recent authoritative sources
3. Fetches top 2-3 results
4. Feeds fetched content into dimension analysis + object generation prompts
5. Returns rendered dashboard

## Demo Topic: Observability in Cloud and AI Applications

Expected output structure at `depth=2`, mode=`understand`:

### Dominant Dimensions (predicted)
- Structural (0.9): Metrics, Logs, Traces — the three pillars framework
- Causal (0.8): Alerting loops, SLO→SLI→error budget cascade
- Sequential (0.7): Data pipeline: instrumentation → collection → transport → storage → visualization
- Comparative (0.6): OpenTelemetry vs Prometheus/Datadog/New Relic

### Expected Knowledge Objects

**Concepts**: Distributed Tracing, Metrics Cardinality, SLIs/SLOs/SLAs, Log Aggregation, Observability Pipeline, eBPF Instrumentation, AI Model Observability (prompt drift, token latency)

**Sequence Block**: Request tracing pipeline (span creation → context propagation → export → ingestion → query)

**Causal Loop**: Alert fatigue loop (more alerts → noise → alert threshold increase → missed incidents → more alerts)

**Perspective Matrix**: OpenTelemetry vs Prometheus vs Datadog vs New Relic (data model, export protocol, scaling cost, AI-native features)

**Graph Edges**: "Distributed Tracing" prerequisite→"Context Propagation", "SLIs" enables→"SLOs", "eBPF" specializes→"Instrumentation"

## Success Criteria

1. Query "explain observability in cloud and AI apps" with `--multi-agent` → routes to TEXTBOOK domain
2. Output is a structured dashboard, not prose paragraphs
3. All 6 dimensions analyzed with weightings visible
4. At least 5 Core Concept Objects generated
5. At least 1 CausalLoop and 1 PerspectiveMatrix rendered
6. Knowledge graph shows typed edges between concepts
7. Depth 0 collapses to single-screen essence; depth 2 shows full dashboard
8. No prose block exceeds 7 lines

## Implementation Order

1. `models.py` — Dataclass definitions (no LLM, pure Python)
2. `dimensions.py` — Dimension taxonomy + weighting schema
3. `prompts.py` — All prompt templates with few-shot examples
4. `generator.py` — LLM orchestration pipeline (4 phases)
5. `renderer.py` — Rich terminal dashboard renderer
6. `compressor.py` — Multi-resolution compression
7. `graph.py` — Knowledge graph construction + edge types
8. `toolkit.py` — UCTGenerate tool wrapper
9. Router registration in `multi_agent.py` 
10. CLI flags: `--uct-depth`, `--uct-mode`

## Testing

```bash
# Basic generation test
python -m morphos.cli --multi-agent --query "explain observability in cloud and AI applications"

# Depth control test  
python -m morphos.cli --multi-agent --uct-depth 0 --query "explain distributed tracing"

# Mode comparison
python -m morphos.cli --multi-agent --uct-mode exam --query "explain service level objectives"
```

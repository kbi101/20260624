from dataclasses import dataclass, field
from typing import Optional


# ── Scale tagging ──────────────────────────────────────────────────────
SCALE_LEVELS = ["physical", "component", "system", "network", "emergent"]

EDGE_TYPES = [
    "prerequisite",
    "enables",
    "contradicts",
    "generalizes",
    "specializes",
    "analogous_to",
    "historically_follows",
]


@dataclass
class Concept:
    name: str
    definition: str
    why_it_exists: str
    constraints: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)


@dataclass
class ScaledConcept:
    concept: Concept
    scale: str

    def __post_init__(self):
        if self.scale not in SCALE_LEVELS:
            raise ValueError(f"scale must be one of {SCALE_LEVELS}")


@dataclass
class Step:
    label: str
    input: str
    transformation: str
    validation: str
    output: str
    failure_condition: str
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class SequenceBlock:
    title: str
    steps: list[Step]


@dataclass
class Link:
    from_node: str
    to_node: str
    effect: str
    delay: str = ""


@dataclass
class CausalLoopBlock:
    title: str
    loops: list[list[str]]
    links: list[Link]
    loop_type: str  # "reinforcing" | "balancing"


@dataclass
class PerspectiveMatrix:
    title: str
    attributes: list[str]
    options: list[str]
    cells: dict[tuple[str, str], str] = field(default_factory=dict)


@dataclass
class CompressionLevels:
    concept_name: str
    level_0_essence: str
    level_1_functional: str
    level_2_detailed: str
    level_3_expert: str


@dataclass
class GraphEdge:
    from_node: str
    to_node: str
    edge_type: str

    def __post_init__(self):
        if self.edge_type not in EDGE_TYPES:
            raise ValueError(f"edge_type must be one of {EDGE_TYPES}")


# ── Dimension analysis result ─────────────────────────────────────────
@dataclass
class DimensionProfile:
    structural: float = 0.0
    sequential: float = 0.0
    causal: float = 0.0
    comparative: float = 0.0
    spatial: float = 0.0
    abstract: float = 0.0
    dominant: list[str] = field(default_factory=list)
    primary_concepts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, float]:
        return {
            "structural": self.structural,
            "sequential": self.sequential,
            "causal": self.causal,
            "comparative": self.comparative,
            "spatial": self.spatial,
            "abstract": self.abstract,
        }

    def top_dimensions(self, min_weight=0.4) -> list[tuple[str, float]]:
        """Return dimensions above threshold, sorted descending."""
        pairs = [(k, v) for k, v in self.as_dict().items() if v >= min_weight]
        return sorted(pairs, key=lambda x: -x[1])


# ── Full UCT result container ────────────────────────────────────────
@dataclass
class TopicModel:
    topic: str
    dimension_profile: Optional[DimensionProfile] = None
    concepts: list[Concept] = field(default_factory=list)
    scaled_concepts: list[ScaledConcept] = field(default_factory=list)
    sequence_blocks: list[SequenceBlock] = field(default_factory=list)
    causal_loops: list[CausalLoopBlock] = field(default_factory=list)
    matrices: list[PerspectiveMatrix] = field(default_factory=list)
    compressions: list[CompressionLevels] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

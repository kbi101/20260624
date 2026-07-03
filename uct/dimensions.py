"""Six universal knowledge dimensions and their block-type mappings."""

DIMENSION_INFO: dict[str, dict] = {
    "structural": {
        "question": "What exists?",
        "best_repr": "Trees, graphs, hierarchies",
        "blocks": ["Concept", "ScaledConcept"],
        "color": "blue",
    },
    "sequential": {
        "question": "What happens in order?",
        "best_repr": "Pipelines, timelines, workflows",
        "blocks": ["SequenceBlock"],
        "color": "cyan",
    },
    "causal": {
        "question": "Why does it happen?",
        "best_repr": "Dependency graphs, feedback loops",
        "blocks": ["CausalLoopBlock"],
        "color": "magenta",
    },
    "comparative": {
        "question": "How is it different?",
        "best_repr": "Matrices, contrast tables",
        "blocks": ["PerspectiveMatrix"],
        "color": "yellow",
    },
    "spatial": {
        "question": "Where / how arranged?",
        "best_repr": "Maps, diagrams, coordinate systems",
        "blocks": ["Concept", "ScaledConcept"],
        "color": "green",
    },
    "abstract": {
        "question": "What are the governing principles?",
        "best_repr": "Axioms, symbolic compression",
        "blocks": ["Concept"],
        "color": "white",
    },
}


DIMENSION_NAMES = list(DIMENSION_INFO.keys())

DOMINANT_THRESHOLD = 0.4


def get_block_types_for_dimensions(dimension_weights: dict[str, float]) -> list[str]:
    """Return the set of Knowledge Object block types needed given dimension weightings."""
    seen: set[str] = set()
    for dim_name, weight in sorted(dimension_weights.items(), key=lambda x: -x[1]):
        if weight < DOMINANT_THRESHOLD:
            continue
        for btype in DIMENSION_INFO[dim_name].get("blocks", []):
            seen.add(btype)
    return list(seen)


def dimension_color(dim: str) -> str:
    return DIMENSION_INFO.get(dim, {}).get("color", "white")

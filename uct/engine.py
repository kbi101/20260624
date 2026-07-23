"""Main UCT orchestration module — ties generator, compressor, renderer together."""

from uct.models import TopicModel
from uct.generator import UCTGenerator
from uct.compressor import Compressor
from uct.renderer import UCTRenderer
from uct.graph import KnowledgeGraph


class UCTEngine:
    """Top-level orchestrator: generate → compress → render a cognitive dashboard."""

    def __init__(self, llm_client, depth: int = 1, mode: str = "understand"):
        self.generator = UCTGenerator(llm_client)
        self.compressor = Compressor(llm_client)
        self.renderer = UCTRenderer(depth=depth, mode=mode)

    def generate_dashboard(self, topic: str, research_context: str = "") -> tuple[str, TopicModel]:
        """Full pipeline. Returns (rendered_text, topic_model)."""

        # Phase 1: Generate structured objects (single-shot mega-prompt)
        model = self.generator.generate(topic, research_context)

        # Phase 2: Compress concepts into resolution levels
        if model.concepts:
            compressions = self.compressor.compress_all(topic, model.concepts)
            model.compressions = compressions

            # Re-wrap ScaledConcept with real Concept references
            name_map = {c.name: c for c in model.concepts}
            from uct.models import ScaledConcept as SC
            for sc in model.scaled_concepts:
                matched = name_map.get(sc.concept.name)
                if matched:
                    sc.concept = matched

        return self.renderer.render(model), model

    def build_graph(self, model: TopicModel) -> KnowledgeGraph:
        """Build traversable graph from a generated TopicModel."""
        g = KnowledgeGraph()
        for c in model.concepts:
            g.add_node(c.name)
        if model.edges:
            g.add_edges(model.edges)
        return g

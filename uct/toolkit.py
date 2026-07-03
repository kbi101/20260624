"""UCTTool — wraps UCTEngine as a Morphos ToolRegistry-compatible tool."""

from morphos.tools.registry import Tool


class UCTGenerate(Tool):
    """Morphos tool that generates a cognitive dashboard for any topic.
    
    Parameters:
        topic: str   – The subject to generate a textbook page for
        depth: int  – Resolution level (0=essence only, 1=core, 2=full, 3=expert)
        mode:  str  – Rendering mode (understand/exam/practice/research/overview)
    """

    def __init__(self, llm_client, depth: int = 1, mode: str = "understand"):
        from uct.engine import UCTEngine
        self.engine = UCTEngine(llm_client, depth=depth, mode=mode)
        self._default_depth = depth
        self._default_mode = mode

    @property
    def name(self) -> str:
        return "uct_generate"

    @property
    def description(self) -> str:
        return (
            "Generate a structured cognitive dashboard for a topic. "
            "Parameters: topic (str), depth (int 0-3), mode (understand/exam/practice/research/overview)."
        )

    def execute(self, topic: str, depth: int = None, mode: str = None, **kwargs) -> str:
        effective_depth = depth if depth is not None else self._default_depth
        effective_mode = mode if mode is not None else self._default_mode

        # Re-init renderer with requested depth/mode
        from uct.renderer import UCTRenderer
        self.engine.renderer = UCTRenderer(depth=effective_depth, mode=effective_mode)

        rendered_text, model = self.engine.generate_dashboard(topic)

        # Append a compact summary header for the agent to include
        dims = model.dimension_profile
        dominant_str = ", ".join(dims.dominant[:3]) if dims.dominant else "structural"
        concept_count = len(model.concepts)

        header = (
            f"\n=== COGNITIVE DASHBOARD: {topic} ===\n"
            f"Dominant dimensions: {dominant_str}\n"
            f"Concepts generated: {concept_count}\n"
            f"Depth: {effective_depth} | Mode: {effective_mode}\n"
        )

        return header + rendered_text

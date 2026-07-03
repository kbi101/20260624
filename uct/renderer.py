"""Rich terminal renderer for cognitive dashboard layout."""

from typing import Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from uct.models import (
    TopicModel,
    Concept,
    SequenceBlock,
    CausalLoopBlock,
    PerspectiveMatrix,
    CompressionLevels,
    GraphEdge,
    ScaledConcept,
)
from uct.dimensions import DIMENSION_INFO, dimension_color


class UCTRenderer:
    """Renders a TopicModel as a Rich terminal dashboard."""

    def __init__(self, depth: int = 1, mode: str = "understand"):
        self.depth = max(0, min(3, depth))
        self.mode = mode

    def render(self, model: TopicModel) -> str:
        """Return a printable string dashboard."""
        from rich.console import Console
        buf = Console(force_terminal=True, width=120)
        elements = []

        # ── TOP: Core topic title + Level 0 essence ────────────────
        self._render_top(buf, model, elements)

        if self.depth == 0:
            return self._join(elements, buf)

        # ── Dimension weightings bar ───────────────────────────────
        self._render_dimension_bar(buf, model, elements)

        # ── CENTER: Dominant dimension blocks ──────────────────────
        self._render_center(buf, model, elements)

        if self.depth >= 2:
            # LEFT: Prerequisite graph / related concepts
            self._render_left(buf, model, elements)

            # RIGHT: Comparative matrix (if applicable)
            self._render_right(buf, model, elements)

            # BOTTOM: Failure modes + scale layers + applications
            self._render_bottom(buf, model, elements)

        if self.depth >= 3:
            # Expert layer
            self._render_expert(buf, model, elements)

        return self._join(elements, buf)

    def _render_top(self, buf, model: TopicModel, elements: list):
        title = f"📖 {model.topic}"
        
        # Find Level 0 essence from compressions
        essence = ""
        for comp in model.compressions:
            if comp.level_0_essence:
                essence = comp.level_0_essence
                break
        
        # Fallback: use first concept definition
        if not essence and model.concepts:
            c = model.concepts[0]
            essence = f"{c.name}: {c.definition}"
        
        content_parts = []
        if model.dimension_profile.primary_concepts:
            concepts_str = ", ".join(model.dimension_profile.primary_concepts[:6])
            content_parts.append(f"[dim]Primary concepts:[/] {concepts_str}")
        
        content_text = "\n".join(p for p in [essence] + content_parts if p)
        elements.append(Panel(
            Text(content_text or model.topic),
            title=title,
            border_style="bold blue",
        ))

    def _render_dimension_bar(self, buf, model: TopicModel, elements: list):
        profile = model.dimension_profile
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("dim", style="bold")
        table.add_column("bar", style="white", justify="left")

        for dim_name in ["structural", "sequential", "causal", "comparative", "spatial", "abstract"]:
            weight = getattr(profile, dim_name, 0.0)
            bar_len = max(0, int(weight * 20))
            color = dimension_color(dim_name)
            bar_str = f"[{color}]" + "█" * bar_len + "[/]" + "░" * max(0, 20 - bar_len) + f" {weight:.1f}"
            table.add_row(f"{dim_name:>12}", bar_str)

        elements.append(Panel(table, title="[dim]Cognitive Dimensions", border_style="dim"))

    def _render_center(self, buf, model: TopicModel, elements: list):
        """Render dominant dimension blocks in center region."""
        top_dims = model.dimension_profile.top_dimensions(min_weight=0.4)
        if not top_dims and model.concepts:
            top_dims = [("structural", 0.5)]

        for dim_name, weight in top_dims:
            # Render concepts (always useful as structural anchors)
            if model.concepts and dim_name in ("structural", "abstract"):
                elements.append(self._render_concept_panel(model.concepts, dim_name))

            # Render sequence blocks
            if dim_name == "sequential" and model.sequence_blocks:
                for seq in model.sequence_blocks:
                    elements.append(self._render_sequence_panel(seq))

            # Render causal loops
            if dim_name == "causal" and model.causal_loops:
                for loop in model.causal_loops:
                    elements.append(self._render_causal_panel(loop))

    def _render_concept_panel(self, concepts: list[Concept], dim: str) -> Panel:
        table = Table(box=None, show_header=True, header_style="bold")
        table.add_column("Concept", style="bold blue", width=20)
        table.add_column("Definition", width=45)
        table.add_column("Why It Exists", width=30)

        for c in concepts[:8]:  # Cap to avoid overflow
            table.add_row(
                c.name[:19],
                c.definition[:44] if c.definition else "",
                c.why_it_exists[:29] if c.why_it_exists else "",
            )

        color = dimension_color(dim)
        return Panel(table, title=f"[{color}]Concepts [{color}]", border_style=color)

    def _render_sequence_panel(self, seq: SequenceBlock) -> Panel:
        lines = []
        for step in seq.steps:
            prereq_tag = f" (needs: {', '.join(step.prerequisites[:2])})" if step.prerequisites else ""
            lines.append(
                f"[bold cyan]{step.label}[/][dim]{prereq_tag}[/]\n"
                f"  Input: {step.input}\n"
                f"  → {step.transformation}\n"
                f"  ✓ Check: {step.validation}\n"
                f"  Output: {step.output}"
            )
            if step.failure_condition:
                lines.append(f"  [red]⚠ Failure: {step.failure_condition}[/]")
            lines.append("")

        return Panel(
            "\n".join(lines),
            title=f"Sequential: {seq.title}",
            border_style="cyan",
        )

    def _render_causal_panel(self, loop: CausalLoopBlock) -> Panel:
        lines = []
        lines.append(f"[bold]Type: {loop.loop_type}[/]\n")

        for cycle in loop.loops[:3]:
            arrow_chain = " → ".join(cycle)
            lines.append(f"  Cycle: {arrow_chain}\n")

        if loop.links:
            lines.append("[dim]Link details:[/]")
            for lnk in loop.links[:8]:
                delay_tag = f" (delay: {lnk.delay})" if lnk.delay else ""
                eff_marker = "↑" if "increas" in lnk.effect.lower() else "↓"
                lines.append(
                    f"  {eff_marker} {lnk.from_node} ──[{lnk.effect}]──> {lnk.to_node}{delay_tag}"
                )

        return Panel(
            "\n".join(lines),
            title=f"Causal Loop: {loop.title}",
            border_style="magenta",
        )

    def _render_left(self, buf, model: TopicModel, elements: list):
        """LEFT region: Prerequisite graph / related connections."""
        if not model.edges:
            return

        lines = []
        for edge in model.edges[:15]:
            type_icon = {
                "prerequisite": "⟵requires",
                "enables": "→enables",
                "contradicts": "⊗",
                "generalizes": "⊃",
                "specializes": "⊂",
                "analogous_to": "~",
                "historically_follows": "→after",
            }.get(edge.edge_type, edge.edge_type)

            lines.append(
                f"[bold]{edge.from_node}[/] [dim]{type_icon}[/] [bold]{edge.to_node}[/]"
            )

        elements.append(Panel(
            "\n".join(lines),
            title="Knowledge Graph",
            border_style="dim blue",
        ))

    def _render_right(self, buf, model: TopicModel, elements: list):
        """RIGHT region: Comparative matrix."""
        if not model.matrices:
            return

        for mx in model.matrices:
            table = Table(show_header=True, header_style="bold yellow")
            table.add_column("Attribute", style="bold")
            for opt in mx.options:
                table.add_column(opt)

            for attr in mx.attributes:
                row_vals = [str(mx.cells.get((attr, opt), "")) for opt in mx.options]
                table.add_row(attr, *row_vals)

            elements.append(Panel(
                table,
                title=f"Comparison: {mx.title}",
                border_style="yellow",
            ))

    def _render_bottom(self, buf, model: TopicModel, elements: list):
        """BOTTOM region: Failure modes + scale layers."""
        lines = []

        # Failure modes from all concepts
        all_failures = {}
        for c in model.concepts:
            if c.failure_modes:
                all_failures[c.name] = c.failure_modes

        if all_failures:
            lines.append("[bold red]Failure Modes[/]")
            for name, modes in list(all_failures.items())[:5]:
                for m in modes[:2]:
                    lines.append(f"  [red]⚠[/] {name}: {m}")

        # Constraints summary
        all_constraints = {}
        for c in model.concepts:
            if c.constraints:
                all_constraints[c.name] = c.constraints

        if all_constraints:
            lines.append("")
            lines.append("[bold]Hard Constraints[/]")
            for name, constrs in list(all_constraints.items())[:5]:
                for cl in constrs[:2]:
                    lines.append(f"  [yellow]└─[/] {name}: {cl}")

        # Scale layer tags
        if model.scaled_concepts:
            lines.append("")
            lines.append("[bold]Scale Layers[/]")
            levels_order = ["physical", "component", "system", "network", "emergent"]
            for lvl in levels_order:
                at_lvl = [sc.concept.name for sc in model.scaled_concepts if sc.scale == lvl]
                if at_lvl:
                    lines.append(f"  [{lvl.upper()}]: {', '.join(at_lvl)}")

        if lines:
            elements.append(Panel(
                "\n".join(lines),
                title="Failure Modes & Constraints",
                border_style="dim red",
            ))

    def _render_expert(self, buf, model: TopicModel, elements: list):
        """Level 3 expert notes."""
        lines = ["[bold]Expert Layer — Edge Cases & Debates[/]\n"]
        for comp in model.compressions:
            if comp.level_3_expert:
                lines.append(f"[bold]{comp.concept_name}[/]")
                # Truncate long prose into 7-line chunks
                expert = comp.level_3_expert[:500]
                words = expert.split()
                chunk = []
                for w in words:
                    chunk.append(w)
                    if len(chunk) > 120:
                        lines.append("  " + " ".join(chunk))
                        chunk = []
                if chunk:
                    lines.append("  " + " ".join(chunk))
                lines.append("")

        elements.append(Panel(
            "\n".join(lines),
            title="[bold]Expert Layer",
            border_style="bright_black on white",
        ))

    @staticmethod
    def _join(elements: list, buf):
        """Render all Rich elements to a string."""
        output = Console(force_terminal=True, width=120, record=True)
        for el in elements:
            output.print(el)
        return output.export_text()

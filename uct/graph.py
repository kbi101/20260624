"""Knowledge graph construction and traversal."""

from collections import defaultdict
from uct.models import GraphEdge, EDGE_TYPES


class KnowledgeGraph:
    """In-memory knowledge graph over UCT concept nodes."""

    def __init__(self):
        self.nodes: list[str] = []
        self.edges: dict[str, list[GraphEdge]] = defaultdict(list)

    def add_node(self, name: str):
        if name not in self.nodes:
            self.nodes.append(name)

    def add_edges(self, edges: list[GraphEdge]):
        for e in edges:
            self.add_node(e.from_node)
            self.add_node(e.to_node)
            self.edges[e.edge_type].append(e)

    def prerequisites_for(self, node: str) -> list[str]:
        return [e.from_node for e in self.edges.get("prerequisite", []) if e.to_node == node]

    def enables(self, node: str) -> list[str]:
        return [e.to_node for e in self.edges.get("enables", []) if e.from_node == node]

    def all_connections(self, node: str) -> list[tuple[str, str, str]]:
        """Returns (connected_node, edge_type, direction) for a given node."""
        conns = []
        for etype in EDGE_TYPES:
            for e in self.edges.get(etype, []):
                if e.from_node == node:
                    conns.append((e.to_node, etype, "->"))
                elif e.to_node == node:
                    conns.append((e.from_node, etype, "<-"))
        return conns

    def terminal_render(self) -> str:
        """ASCII-friendly graph summary for terminal display."""
        if not self.nodes:
            return "(no graph data)"

        lines = [f"[bold]Concept Nodes ({len(self.nodes)}):[/] " + ", ".join(self.nodes[:12])]
        if len(self.nodes) > 12:
            lines[-1] += f" ... and {len(self.nodes)-12} more"

        for etype in EDGE_TYPES:
            edges = self.edges.get(etype, [])
            if not edges:
                continue
            lines.append(f"\n[dim]── {etype.upper()} ({len(edges)} links) ──[/dim]")
            for e in edges[:10]:
                lines.append(f"  {e.from_node} → {e.to_node}")

        return "\n".join(lines)

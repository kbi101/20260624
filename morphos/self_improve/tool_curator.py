"""ToolCurator — promotes high-performing dynamic tools, demotes chronic failures.

Analyzes session logs to find:
- Dynamic tools used successfully across many sessions → promote to permanent
- Dynamic tools with repeated critic rejections → flag for removal
"""

import json
import os
from dataclasses import dataclass

from morphos.analyzer import LOGS_DIR
from morphos.dynamic_tools import DynamicToolRegistry


PROMOTE_THRESHOLD = 5
REJECT_PENALTY = 3


@dataclass
class ToolMetric:
    name: str
    total_calls: int
    successes: int
    failures: int
    critic_rejections: int
    avg_duration_ms: float
    should_promote: bool = False
    should_demote: bool = False


class ToolCurator:
    """Analyzes tool usage logs and curates the dynamic tool library."""

    def __init__(self, registry: DynamicToolRegistry, log_dir=None):
        self.registry = registry
        self.log_dir = log_dir or LOGS_DIR

    def analyze(self) -> list[ToolMetric]:
        """Compute per-tool metrics across all sessions."""
        metrics: dict[str, ToolMetric] = {}

        if not os.path.isdir(self.log_dir):
            return []

        for fname in os.listdir(self.log_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.log_dir, fname)) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue

            for rec in data.get("records", []):
                tool = rec.get("tool", "unknown")
                if tool not in metrics:
                    metrics[tool] = ToolMetric(
                        name=tool,
                        total_calls=0,
                        successes=0,
                        failures=0,
                        critic_rejections=0,
                        avg_duration_ms=0,
                    )
                m = metrics[tool]
                m.total_calls += 1
                if rec.get("status") == "success":
                    m.successes += 1
                else:
                    m.failures += 1
                if rec.get("critic_verdict") == "reject":
                    m.critic_rejections += 1

        for m in metrics.values():
            total = m.successes + m.failures
            if total > 0:
                m.avg_duration_ms = round(
                    sum(r.get("duration_ms", 0)
                        for _ in [1]) / max(m.total_calls, 1), 1
                )

            promote_rate = m.successes / max(m.total_calls, 1)
            m.should_promote = (
                m.total_calls >= PROMOTE_THRESHOLD and promote_rate >= 0.7
            )
            m.should_demote = (
                m.critic_rejections >= REJECT_PENALTY
                and m.critic_rejections / max(m.total_calls, 1) > 0.5
            )

        return list(metrics.values())

    def promote_dynamic_tools(self):
        """Persist dynamic tools that meet the promotion threshold."""
        metrics = self.analyze()
        promoted: list[str] = []
        for m in metrics:
            if m.should_promote and m.name in self.registry.tools:
                promoted.append(m.name)

        if promoted and self.registry.persist_dir:
            os.makedirs(self.registry.persist_dir, exist_ok=True)
            self.registry.save_to_file(
                os.path.join(self.registry.persist_dir, "tools.json")
            )

        return promoted

    def demote_dynamic_tools(self):
        """Remove dynamic tools that consistently fail."""
        metrics = self.analyze()
        removed: list[str] = []
        for m in metrics:
            if m.should_demote and m.name in self.registry.tools:
                del self.registry.tools[m.name]
                removed.append(m.name)
        return removed

    def curate(self) -> dict:
        """Run both promotion and demotion. Returns a report."""
        promoted = self.promote_dynamic_tools()
        removed = self.demote_dynamic_tools()
        all_metrics = self.analyze()
        return {
            "promoted": promoted,
            "removed": removed,
            "metrics": [
                {
                    "name": m.name,
                    "calls": m.total_calls,
                    "successes": m.successes,
                    "failures": m.failures,
                    "rejections": m.critic_rejections,
                    "promote": m.should_promote,
                    "demote": m.should_demote,
                }
                for m in all_metrics
            ],
        }
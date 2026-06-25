"""GrowthLoop — orchestrates prompt evolution and tool curation as a periodic task.

Runs on CLI flag `--grow` or scheduled interval. Produces a human-readable
Growth Report showing what changed and why.
"""

import json
import os
from datetime import datetime, timezone

from morphos.self_improve.prompt_evolver import PromptEvolver
from morphos.self_improve.tool_curator import ToolCurator


class GrowthLoop:
    """Background growth loop that iteratively improves the system."""

    def __init__(self, llm_client, registry, analyzer, log_dir=None):
        self.llm = llm_client
        self.registry = registry
        self.analyzer = analyzer
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "logs")
        self.evolver = PromptEvolver(self.llm, self.log_dir)
        if registry:
            self.curator = ToolCurator(registry, self.log_dir)
        else:
            self.curator = None

    def run_growth_cycle(self, current_prompt: str, auto_apply: bool = False) -> dict:
        """Execute one full growth cycle and return the report."""
        timestamp = datetime.now(timezone.utc).isoformat()
        report = {
            "timestamp": timestamp,
            "prompt_evolution": {},
            "tool_curation": {},
        }

        # --- Prompt evolution ---
        evol_report = self.evolver.evolve(current_prompt)
        report["prompt_evolution"] = {
            "analysis": evol_report["analysis"],
            "patches_applied": evol_report["patches_applied"],
            "diff": evol_report["diff"],
        }

        if auto_apply and evol_report["patches_applied"] > 0:
            report["prompt_evolution"]["new_prompt_saved"] = True
        else:
            report["prompt_evolution"]["new_prompt_saved"] = False

        # --- Tool curation ---
        if self.curator:
            curate_report = self.curator.curate()
            report["tool_curation"] = {
                "promoted": curate_report["promoted"],
                "removed": curate_report["removed"],
                "metrics_summary": curate_report["metrics"],
            }

        return report

    def terminal_report(self, cycle_report: dict) -> str:
        """Human-readable growth summary for the terminal."""
        lines = ["Growth Report:", f"  Timestamp: {cycle_report['timestamp']}"]

        pe = cycle_report.get("prompt_evolution", {})
        patches = pe.get("patches_applied", 0)
        saved = pe.get("new_prompt_saved", False)
        lines.append(f"  Prompt Evolution — {patches} patch(es) proposed, saved: {saved}")

        tc = cycle_report.get("tool_curation", {})
        if tc:
            promoted = tc.get("promoted", [])
            removed = tc.get("removed", [])
            lines.append(f"  Tool Curation — promoted: {promoted}, removed: {removed}")

        return "\n".join(lines)

    def save_report(self, cycle_report: dict) -> str:
        """Persist the growth report to a JSON file. Returns path."""
        import glob as globmod
        data_dir = os.path.dirname(self.log_dir)
        if not os.path.isdir(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = os.path.join(data_dir, f"growth_report_{ts}.json")
        with open(path, "w") as f:
            json.dump(cycle_report, f, indent=2)
        return path
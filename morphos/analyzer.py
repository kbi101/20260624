"""Log analysis tool — tracks tool execution metrics and produces session reports."""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional


LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "logs")


@dataclass
class ToolCallRecord:
    tool_name: str
    timestamp: float
    duration_ms: int
    status: str  # "success" | "error"
    message: str = ""  # error details or brief summary
    iteration: int = 0
    critic_verdict: Optional[str] = None


class Analyzer:
    """Collects metrics from each tool call and produces session summaries."""

    def __init__(self):
        os.makedirs(LOGS_DIR, exist_ok=True)
        self.records: list[ToolCallRecord] = []

    def record(self, tool_name: str, duration_ms: int, status: str, iteration: int,
               message: str = "", critic_verdict: Optional[str] = None):
        self.records.append(ToolCallRecord(
            tool_name=tool_name,
            timestamp=time.time(),
            duration_ms=duration_ms,
            status=status,
            message=message[:300],
            iteration=iteration,
            critic_verdict=critic_verdict,
        ))

    def summary(self) -> dict:
        """Return aggregated statistics about the session."""
        if not self.records:
            return {"total_calls": 0}

        tool_stats: dict[str, dict] = {}
        for r in self.records:
            if r.tool_name not in tool_stats:
                tool_stats[r.tool_name] = {"successes": 0, "failures": 0, "total_ms": 0, "critic_rejects": 0}
            s = tool_stats[r.tool_name]
            s["total_ms"] += r.duration_ms
            if r.status == "success":
                s["successes"] += 1
            else:
                s["failures"] += 1
            if r.critic_verdict == "reject":
                s["critic_rejects"] += 1

        for tool_name, s in tool_stats.items():
            total = s["successes"] + s["failures"]
            s["total_calls"] = total
            s["success_rate"] = round(s["successes"] / total * 100, 1) if total else 0

        return {
            "total_calls": len(self.records),
            "tool_stats": tool_stats,
        }

    def save(self, session_id: str):
        """Persist all records as a JSON log file."""
        path = os.path.join(LOGS_DIR, f"{session_id}.json")
        entries = [
            {
                "tool": r.tool_name,
                "iteration": r.iteration,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "message": r.message,
                "critic_verdict": r.critic_verdict,
            }
            for r in self.records
        ]
        with open(path, "w") as f:
            json.dump({"session_id": session_id, "records": entries}, f, indent=2)

    def terminal_report(self) -> str:
        """Human-readable summary for the terminal."""
        s = self.summary()
        if not s["total_calls"]:
            return ""

        lines = ["Session log:", f"  Total tool calls: {s['total_calls']}"]
        for tool_name, stats in s["tool_stats"].items():
            rate = stats.get("success_rate", 0)
            rejects = stats.get("critic_rejects", 0)
            lines.append(f"  {tool_name}: {stats['total_calls']} calls, "
                         f"{rate}% success, {rejects} critic rejections")

        return "\n".join(lines)

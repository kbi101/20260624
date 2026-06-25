"""PromptEvolver — reads analyzer logs, finds failure patterns, proposes system prompt patches.

The evolver looks at aggregated session data and produces targeted improvements:
- Format examples added for tools with high parse-error rates
- Parameter hints inserted for tools with frequent TypeError failures
- Critic-rejection hot-spots get extra guidance in the prompt
"""

import json
import os
import difflib

from morphos.analyzer import LOGS_DIR


EVOLVE_SYSTEM_INSTRUCTIONS = """You are a prompt engineering assistant.
Review this analysis of agent session logs and propose concrete patches to the system prompt.

Analysis:
{analysis}

Current system prompt:
---
{current_prompt}
---

Output JSON with up to 3 targeted patches. Each patch has:
- "reason": why this change is needed
- "insert_after": a snippet indicating where in the prompt to insert
- "patch_text": the exact text to add (can be empty for deletions)

Format:
{{"patches": [{{"reason": "...", "insert_after": "...", "patch_text": "..."}}]}}"""


class PromptEvolver:
    """Reviews past session logs + critic verdicts and proposes prompt patches."""

    def __init__(self, llm_client, log_dir=None):
        self.llm = llm_client
        self.log_dir = log_dir or LOGS_DIR

    def analyze_logs(self) -> dict:
        """Read all log files, compute failure patterns per tool."""
        pattern_stats: dict[str, dict] = {}

        if not os.path.isdir(self.log_dir):
            return {"total_sessions": 0, "tools": {}}

        log_files = [f for f in os.listdir(self.log_dir) if f.endswith(".json")]
        total_parse_errors = 0
        per_tool_failures: dict[str, int] = {}
        per_tool_rejections: dict[str, int] = {}
        per_tool_successes: dict[str, int] = {}

        for lf in log_files:
            try:
                with open(os.path.join(self.log_dir, lf)) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue

            for rec in data.get("records", []):
                tool = rec.get("tool", "unknown")
                status = rec.get("status", "")
                verdict = rec.get("critic_verdict", None)

                if tool not in per_tool_successes:
                    per_tool_successes[tool] = 0
                    per_tool_failures[tool] = 0
                    per_tool_rejections[tool] = 0

                if status == "success":
                    per_tool_successes[tool] += 1
                else:
                    per_tool_failures[tool] += 1

                if verdict == "reject":
                    per_tool_rejections[tool] += 1

            session_parse_errors = sum(
                1 for r in data.get("records", [])
                if r.get("status") == "error" and "parse" in r.get("message", "").lower()
            )
            total_parse_errors += session_parse_errors

        analysis: dict[str, object] = {
            "total_sessions": len(log_files),
            "total_parse_errors": total_parse_errors,
            "tools": {},
        }

        all_tools = set(per_tool_successes.keys())
        for tool in all_tools:
            s = per_tool_successes.get(tool, 0)
            f = per_tool_failures.get(tool, 0)
            rj = per_tool_rejections.get(tool, 0)
            total = s + f
            analysis["tools"][tool] = {
                "successes": s,
                "failures": f,
                "critic_rejections": rj,
                "success_rate": round(s / total * 100, 1) if total else 0,
            }

        return analysis

    def propose_patches(self, current_prompt: str) -> list[dict]:
        """Call the LLM with log analysis to get suggested prompt patches."""
        analysis = self.analyze_logs()
        analysis_text = json.dumps(analysis, indent=2)

        resp = self.llm.chat([{
            "role": "user",
            "content": EVOLVE_SYSTEM_INSTRUCTIONS.format(
                analysis=analysis_text,
                current_prompt=current_prompt[:6000],
            ),
        }])

        patches = []
        try:
            data = json.loads(resp)
            patches = data.get("patches", [])
        except (json.JSONDecodeError, TypeError):
            pass

        return patches

    def apply_patches(self, current_prompt: str, patches: list[dict]) -> str:
        """Apply a list of diff-like patches to the prompt text."""
        result = current_prompt
        for patch in patches:
            marker = patch.get("insert_after", "")
            text = patch.get("patch_text", "")
            if marker and text and marker in result:
                idx = result.index(marker) + len(marker)
                result = result[:idx] + "\n" + text + result[idx:]
        return result

    def evolve(self, current_prompt: str) -> dict:
        """Full cycle: analyze → propose → apply. Returns report."""
        analysis = self.analyze_logs()
        patches = self.propose_patches(current_prompt)
        new_prompt = self.apply_patches(current_prompt, patches)
        return {
            "analysis": analysis,
            "patches_applied": len(patches),
            "old_prompt": current_prompt,
            "new_prompt": new_prompt,
            "diff": "\n".join(difflib.unified_diff(
                current_prompt.splitlines(),
                new_prompt.splitlines(),
                fromfile="before", tofile="after", lineterm="",
            )),
        }
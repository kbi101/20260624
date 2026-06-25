"""Critic module that reviews tool outputs for correctness and completeness.

The critic intercepts between executor (tool) and planner (next step). It asks 
the LLM to evaluate whether a tool's output is good enough, or if it should be 
rejected so the agent can re-try with better parameters.
"""

import json

CRITIC_PROMPT_LOOSE = """You are a quality validator for an AI agent's tool calls.

Original user intent: {original_query}
Tool used: {tool_name}
Tool output:
---
{tool_output}
---

Is this output sufficient to answer the user's question, or does it need to be re-done?
Criteria:
1. Does it actually contain the information needed? (not an error, not empty, not irrelevant)
2. Is it complete, or clearly truncated / incomplete?
3. Did the tool parameters make sense for the task?

Be lenient — only reject if the output is clearly bad.

Respond in JSON format:
{{"verdict": "accept" or "reject", "reasoning": "<brief explanation>"}}"""

CRITIC_PROMPT_MODERATE = """You are a quality validator for an AI agent's tool calls.

Original user intent: {original_query}
Tool used: {tool_name}
Tool output:
---
{tool_output}
---

Is this output sufficient to answer the user's question, or does it need to be re-done?
Criteria:
1. Does it actually contain the information needed? (not an error, not empty, not irrelevant)
2. Is it complete, or clearly truncated / incomplete?
3. Did the tool parameters make sense for the task?

Use balanced judgment — reject if there are notable gaps.

Respond in JSON format:
{{"verdict": "accept" or "reject", "reasoning": "<brief explanation>"}}"""

CRITIC_PROMPT_STRICT = """You are a quality validator for an AI agent's tool calls.

Original user intent: {original_query}
Tool used: {tool_name}
Tool output:
---
{tool_output}
---

Is this output sufficient to answer the user's question, or does it need to be re-done?
Criteria:
1. Does it actually contain the information needed? (not an error, not empty, not irrelevant)
2. Is it complete, or clearly truncated / incomplete?
3. Did the tool parameters make sense for the task?

Be strict — reject any output with minor shortcomings, partial data, or weak results.

Respond in JSON format:
{{"verdict": "accept" or "reject", "reasoning": "<brief explanation>"}}"""

STRICTNESS_PROMPTS = {
    "loose": CRITIC_PROMPT_LOOSE,
    "moderate": CRITIC_PROMPT_MODERATE,
    "strict": CRITIC_PROMPT_STRICT,
}


class Critic:
    """Separate LLM call that validates tool output before passing to planner."""

    def __init__(self, llm_client, strictness="moderate"):
        self.llm = llm_client
        self.strictness = strictness

    def _pick_prompt(self):
        return STRICTNESS_PROMPTS.get(self.strictness, CRITIC_PROMPT_MODERATE)

    def evaluate(self, original_query: str, tool_name: str, tool_output: str) -> bool:
        """Return True if output is acceptable, False if it should be rejected/retried."""
        prompt = self._pick_prompt().format(
            original_query=original_query,
            tool_name=tool_name,
            tool_output=tool_output[:2000],
        )
        resp = self.llm.chat([{"role": "user", "content": prompt}])

        try:
            data = json.loads(resp)
            return data.get("verdict") == "accept"
        except (json.JSONDecodeError, TypeError):
            pass

        response_lower = resp.lower()
        if "reject" in response_lower:
            return False
        if "not sufficient" in response_lower or "incomplete" in response_lower:
            return False
        return True

    def review(self, tool_name: str, tool_output: str, original_query: str) -> bool:
        """Alias used by agent loop — matches the signature call site expects."""
        return self.evaluate(original_query, tool_name, tool_output)

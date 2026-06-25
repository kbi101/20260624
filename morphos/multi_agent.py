"""Multi-Agent support — router dispatches queries to domain-specialized sub-agents."""

from dataclasses import dataclass, field
from typing import Optional


ROUTER_PROMPT = r"""You are a query router. Classify this user query into one of these domains:

- FINANCE: stock prices, ETFs, market data, currency, cryptocurrency, financial instruments
- RESEARCH: general knowledge, facts, explanations, comparisons, definitions, historical events, science
- CODING: programming questions, code reviews, debugging, algorithms, scripts, code generation

Query: {query}

Respond in JSON: {{"domain": "<DOMAIN_NAME>", "reasoning": "<brief>"}}"""


@dataclass
class SubAgentConfig:
    """Configuration for a domain-specialized sub-agent."""
    name: str
    system_prompt_addon: str
    allowed_tools: Optional[list[str]] = None


# Default sub-agent specializations
DEFAULT_AGENTS = {
    "FINANCE": SubAgentConfig(
        name="finance_agent",
        system_prompt_addon=(
            "You are a finance specialist. Focus on providing accurate financial data. "
            "Use the finance tool for stock/ETF prices, currency conversions, and market analysis. "
            "Always cite specific numbers with timestamps when available."
        ),
        allowed_tools=["finance", "web_fetch", "web_search", "calculator"],
    ),
    "RESEARCH": SubAgentConfig(
        name="research_agent",
        system_prompt_addon=(
            "You are a research specialist. Focus on thorough, well-sourced answers. "
            "Use web_search and web_fetch to verify facts. Cross-reference multiple sources. "
            "Prefer recent, authoritative information over model knowledge."
        ),
        allowed_tools=["web_fetch", "web_search", "calculator", "python_exec"],
    ),
    "CODING": SubAgentConfig(
        name="coding_agent",
        system_prompt_addon=(
            "You are a coding specialist. Focus on clean, correct, well-explained code. "
            "Use python_exec to validate code before presenting it. Test edge cases. "
            "Explain your reasoning for design choices."
        ),
        allowed_tools=["python_exec", "calculator", "file_read", "directory_search"],
    ),
}


class RouterAgent:
    """Lightweight LLM call to classify query domain, dispatches to sub-agent."""

    def __init__(self, llm_client, agent_factory, sub_agents: Optional[dict[str, SubAgentConfig]] = None):
        self.llm = llm_client
        self.agent_factory = agent_factory
        self.sub_agents = sub_agents or DEFAULT_AGENTS
        self._instances: dict[str, object] = {}

    def classify(self, query: str) -> str:
        """Return domain name (FINANCE / RESEARCH / CODING)."""
        prompt = ROUTER_PROMPT.format(query=query[:1000])
        resp = self.llm.chat([{"role": "user", "content": prompt}])

        try:
            data = resp.strip()
            import json
            parsed = json.loads(data)
            return parsed.get("domain", "RESEARCH")
        except (json.JSONDecodeError, TypeError):
            pass

        response_upper = resp.upper()
        for domain in self.sub_agents.keys():
            if domain in response_upper:
                return domain
        return "RESEARCH"

    def get_agent(self, domain: str, config=None):
        """Get or create a sub-agent instance for the given domain."""
        if domain not in self._instances:
            sconfig = self.sub_agents.get(domain)
            agent = self.agent_factory(
                config=config,
                system_addon=sconfig.system_prompt_addon,
                allowed_tools=sconfig.allowed_tools or None,
            )
            self._instances[domain] = agent
        return self._instances[domain]

    def dispatch(self, query: str, config=None):
        """Classify and run. Yields same events as ReActAgent.run()."""
        domain = self.classify(query)
        agent = self.get_agent(domain, config)
        yield "routed", domain
        yield from agent.run(query)

    def list_agents(self) -> list[str]:
        return list(self.sub_agents.keys())
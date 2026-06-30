"""Configuration for Morphos."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    model: str = "gemma4:12b"
    max_iterations: int = 10
    python_timeout: int = 30
    web_timeout: int = 15
    critic_enabled: bool = True
    critic_strictness: str = "moderate"
    critic_model: str = "qwen2.5:3b"
    dynamic_tools_dir: str = None

    # Phase 4 - Autonomous Growth
    auto_evolve: bool = False
    auto_growth: bool = False
    multi_agent: bool = False
    debug: bool = False

    # Phase 5 — LLM backend selection
    backend: str = "ollama"
    openrouter_model: str = None
    openrouter_api_key: str = None

    def __post_init__(self):
        if self.openrouter_api_key is None:
            self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")

    # Post-processing strips leaked control symbols. Avoid sending stop tokens
    # to Ollama — even harmless-looking ones can break Gemma's output.

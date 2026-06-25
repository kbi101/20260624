"""Configuration for Morphos."""

from dataclasses import dataclass


@dataclass
class Config:
    model: str = "gemma4:12b"
    max_iterations: int = 10
    python_timeout: int = 30
    web_timeout: int = 15
    critic_enabled: bool = True
    critic_strictness: str = "moderate"
    dynamic_tools_dir: str = None

    # Phase 4 — Autonomous Growth
    auto_evolve: bool = False
    auto_growth: bool = False
    multi_agent: bool = False

"""Configuration for Hist Neo4j connection."""

import os
from pathlib import Path

# Automatically load .env if present at project root
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    try:
        for line in _env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

HIST_NEO4J_URI = os.getenv("HIST_NEO4J_URI", "bolt://localhost:7689")
HIST_NEO4J_USER = os.getenv("HIST_NEO4J_USER", os.getenv("NEO4J_USER", "neo4j"))
HIST_NEO4J_PASSWORD = os.getenv("HIST_NEO4J_PASSWORD", os.getenv("NEO4J_PASSWORD", "morphos_hist"))
HIST_DB_NAME = os.getenv("HIST_DB_NAME", os.getenv("NEO4J_DATABASE", "hist"))

"""Glob-style directory search with path whitelisting."""

import os
from dataclasses import dataclass
from glob import glob as _glob
from morphos.tools.registry import Tool


ALLOWED_PATHS = [os.getcwd()]


def _is_allowed(path: str) -> bool:
    real = os.path.realpath(path)
    return any(real.startswith(p) for p in ALLOWED_PATHS)


@dataclass
class DirectorySearch(Tool):
    @property
    def name(self) -> str:
        return "directory_search"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern within allowed directories."

    def execute(self, pattern: str) -> str:
        for base in ALLOWED_PATHS:
            full = os.path.join(base, pattern)
            matches = _glob(full, recursive=True)
            allowed = [m for m in matches if _is_allowed(m)]
            if allowed:
                lines = "\n".join(str(m) for m in sorted(allowed)[:50])
                return f"Found {len(allowed)} match(es):\n{lines}"
        return f"No matches for pattern '{pattern}' within allowed paths."

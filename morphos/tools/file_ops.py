"""Read files from disk with path whitelisting."""

import os
from dataclasses import dataclass
from morphos.tools.registry import Tool


ALLOWED_PATHS = [os.getcwd()]


def _is_allowed(filepath: str) -> bool:
    real = os.path.realpath(filepath)
    return any(real.startswith(p) for p in ALLOWED_PATHS)


@dataclass
class FileRead(Tool):
    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "Read the contents of a file from disk. Provide a file path."

    def execute(self, filepath: str) -> str:
        if not _is_allowed(filepath):
            return f"Access denied: path outside allowed directories: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()[:8000]
        except FileNotFoundError:
            return f"File not found: {filepath}"
        except Exception as e:
            return f"Error reading file: {e}"


@dataclass
class FileWrite(Tool):
    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "Write content to a file on disk. Provide filepath and content."

    def execute(self, filepath: str, content: str) -> str:
        if not _is_allowed(filepath):
            return f"Access denied: path outside allowed directories: {filepath}"
        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} chars to {filepath}"
        except Exception as e:
            return f"Error writing file: {e}"

"""Dynamic tool registration at runtime — agent writes functions that become real tools."""

import ast
from dataclasses import dataclass

from morphos.tools.registry import Tool

ALLOWED_IMPORTS = {"math", "json", "re", "datetime", "collections", "itertools", "functools", "statistics"}

# Tools the agent cannot override — built-in safety net
RESERVED_NAMES = {
    "python_exec", "web_fetch", "web_search", "finance",
    "file_read", "file_write", "directory_search", "calculator", "memory_search",
}


class DynamicTool(Tool):
    """A tool whose source code is written at runtime and compiled safely."""

    def __init__(self, name: str, description: str, source: str):
        if name in RESERVED_NAMES:
            raise ValueError(f"Tool name '{name}' is reserved")

        self._name = name
        self._description = description
        self._source = source

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in ALLOWED_IMPORTS:
                        raise ValueError(f"Disallowed import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] not in ALLOWED_IMPORTS:
                    raise ValueError(f"Disallowed import from: {node.module}")

        ns = {}
        exec(compile(tree, "<dynamic_tool>", "exec"), ns)
        fn = ns.get(name)
        if not callable(fn):
            raise ValueError(f"No callable '{name}' found in source code")
        self._fn = fn

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, **kwargs) -> str:
        try:
            result = self._fn(**kwargs)
            return str(result) if result is not None else "(no output)"
        except Exception as e:
            return f"Execution error: {type(e).__name__}: {e}"


class DynamicToolRegistry:
    """Manages runtime-created tools. Persists to JSON when told to."""

    def __init__(self, persist_dir=None):
        self._tools: dict[str, DynamicTool] = {}
        self.created: list[str] = []
        self.persist_dir = persist_dir

    @property
    def tools(self):
        return self._tools

    def create(self, name: str, description: str, source: str) -> DynamicTool:
        tool = DynamicTool(name=name, description=description, source=source)
        self._tools[name] = tool
        self.created.append(name)
        return tool

    def list(self):
        return [(t.name, t.description) for t in self._tools.values()]

    def get_all(self):
        return dict(self._tools)

    def save_to_file(self, path: str):
        import json
        entries = [
            {"name": t._name, "description": t._description, "source": t._source}
            for t in self._tools.values()
        ]
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)

    def load_from_file_into(self, path: str):
        """Load tools from a file into this existing registry."""
        import json
        try:
            with open(path) as f:
                entries = json.load(f)
            for entry in entries:
                try:
                    self.create(
                        name=entry["name"],
                        description=entry["description"],
                        source=entry["source"],
                    )
                except Exception:
                    pass  # skip bad entries
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    @classmethod
    def load_from_file(cls, path: str) -> "DynamicToolRegistry":
        import json
        registry = cls()
        try:
            with open(path) as f:
                entries = json.load(f)
            for entry in entries:
                try:
                    registry.create(
                        name=entry["name"],
                        description=entry["description"],
                        source=entry["source"],
                    )
                except Exception:
                    pass  # skip bad entries
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return registry


def load_persistent_dynamic_tools(registry: DynamicToolRegistry, persist_dir: str):
    """Load dynamic tools from the persistence directory."""
    import os
    import glob as globmod
    for filepath in globmod.glob(os.path.join(persist_dir, "*.json")):
        registry.load_from_file_into(filepath)


def save_dynamic_tools(registry: DynamicToolRegistry, persist_dir: str):
    """Save dynamic tools to the persistence directory."""
    import os
    os.makedirs(persist_dir, exist_ok=True)
    filepath = os.path.join(persist_dir, "tools.json")
    registry.save_to_file(filepath)

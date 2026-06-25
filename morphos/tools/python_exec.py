"""Sandboxed Python execution tool with optional Docker sandboxing."""

import ast
from dataclasses import dataclass

from morphos.tools.registry import Tool


@dataclass
class PythonExec(Tool):
    timeout: int = 30
    use_docker: bool = True

    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return "Execute Python code in a sandboxed subprocess and return stdout."

    def execute(self, code: str) -> str:
        _validate_code(code)

        if self.use_docker:
            from morphos.docker_sandbox import try_docker_exec, fallback_subprocess_exec
            result = try_docker_exec(code, timeout=self.timeout)
            if result is not None:
                return result

        return _subprocess_exec(code, self.timeout)


def _validate_code(code: str):
    """Basic safety: parse AST and reject dangerous imports."""
    tree = ast.parse(code)
    dangerous_modules = {"subprocess", "socket", "http", "urllib", "os", "sys"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in dangerous_modules:
                    raise ValueError(f"Import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in dangerous_modules:
                raise ValueError(f"Import from '{node.module}' is not allowed")


def _subprocess_exec(code: str, timeout: int) -> str:
    """Subprocess-based execution as the default fallback."""
    import subprocess
    import sys
    import textwrap

    wrapper = textwrap.dedent(f"""
    __code__ = {repr(code)}
    import sys
    sys.path.insert(0, "/tmp")
    exec_result = None
    try:
        exec_result = exec(compile(__code__, "<exec>", "exec"))
        if exec_result is not None:
            print(exec_result)
        else:
            print("__VOID__")
    except Exception as e:
        print(f"ERROR: {{type(e).__name__}}: {{e}}", file=sys.stderr)
        sys.exit(1)
    """)

    result = subprocess.run(
        [sys.executable, "-c", wrapper],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        return f"Execution failed: {result.stderr.strip()}"

    output = result.stdout.strip()
    return output if output != "__VOID__" else "(no output)"

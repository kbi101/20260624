"""Optional Docker-based sandbox for Python code execution."""

import sys
import textwrap


def try_docker_exec(code: str, timeout: int = 30) -> str:
    """Attempt to run code inside a Docker container. Returns result string or None on failure."""
    try:
        import docker
        client = docker.from_env()
    except (ImportError, Exception):
        return None

    wrapper = textwrap.dedent(f"""
    __code__ = {repr(code)}
    try:
        exec_result = exec(compile(__code__, "<exec>", "exec"))
        if exec_result is not None:
            print(exec_result)
        else:
            print("__VOID__")
    except Exception as e:
        print(f"ERROR: {{type(e).__name__}}: {{e}}", file=__import__("sys").stderr)
        __import__("sys").exit(1)
    """)

    try:
        result = client.containers.run(
            "python:3.12-slim",
            command=f"python -c {repr(wrapper)}",
            mem_limit="256m",
            cpu_quota=100_000,
            network_disabled=True,
            detach=False,
            remove=True,
            stderr=True,
            stdout=True,
        )
    except Exception:
        return None

    output = result.decode("utf-8").strip() if result else ""
    return output if output != "__VOID__" else "(no output)"


def fallback_subprocess_exec(code: str, timeout: int = 30) -> str:
    """Subprocess-based execution as fallback when Docker is unavailable."""
    import subprocess

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

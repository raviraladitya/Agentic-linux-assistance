"""
MCPilot — Shared safe-subprocess runner.

Every subprocess call in the project goes through this one function.
No module is allowed to call subprocess.run directly.
"""

import subprocess


def run_safe(args: list[str], timeout: int = 5) -> subprocess.CompletedProcess:
    """
    args must already be a fixed, validated argument list — never a
    user-supplied string, never shell=True, never built with f-strings
    that interpolate LLM output directly into the command.
    """
    return subprocess.run(
        args,
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

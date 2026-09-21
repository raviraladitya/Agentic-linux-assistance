"""
MCPilot — Process helpers.

Additional process utilities that supplement the main linux.py module.
"""

import psutil

from server.schemas import ProcessDetail


def get_process_by_pid(pid: int) -> ProcessDetail:
    """Get detailed process info by PID."""
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return ProcessDetail(
                pid=proc.pid,
                ppid=proc.ppid(),
                name=proc.name(),
                status=proc.status(),
                user=proc.username(),
                cpu_percent=proc.cpu_percent(interval=0.1),
                memory_percent=round(proc.memory_percent(), 2),
                cmdline=" ".join(proc.cmdline()) if proc.cmdline() else "",
                cwd=proc.cwd() if proc.cwd() else None,
            )
    except psutil.NoSuchProcess:
        raise ValueError(f"Process {pid} not found")
    except psutil.AccessDenied:
        raise PermissionError(f"Access denied to process {pid}")

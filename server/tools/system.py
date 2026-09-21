"""
MCPilot — System MCP tools.

Thin wrappers over server/core/linux.py — no OS logic inline.
Docstrings are part of the contract the LLM reads to decide relevance.
"""

from server.schemas import (
    SystemInfo,
    CpuUsage,
    MemoryUsage,
    DiskUsageEntry,
    ProcessSummary,
    ProcessDetail,
    ToolError,
)
from server.core import linux


def get_system_info() -> SystemInfo:
    """
    Returns basic system information: hostname, OS, kernel version,
    architecture, uptime, and CPU count.

    Use this when investigating general system identity, checking OS version,
    or assessing basic system health. Does not modify system state.
    """
    return linux.read_system_info()


def get_cpu_usage() -> CpuUsage:
    """
    Returns current CPU utilization as overall and per-core percentages,
    plus 1/5/15-minute load averages.

    Use this when investigating high CPU usage, system slowness, or
    load-related issues. Does not modify system state.
    """
    return linux.read_cpu_usage()


def get_memory_usage() -> MemoryUsage:
    """
    Returns current system memory and swap utilization as percentages and GB.

    Use this when investigating high memory usage, swapping, or general system
    slowdown. Does not modify system state.
    """
    return linux.read_memory_usage()


def get_disk_usage() -> list[DiskUsageEntry]:
    """
    Returns disk usage for all mounted partitions: total, used, free in GB
    and used percentage per mount point.

    Use this when investigating low disk space, full partitions, or storage
    issues. Does not modify system state.
    """
    return linux.read_disk_usage()


def list_processes(limit: int = 50) -> list[ProcessSummary]:
    """
    Returns a list of running processes sorted by CPU usage, showing PID,
    name, CPU%, memory%, and status. Limited to `limit` entries (max 200).

    Use this when investigating which processes are consuming the most
    resources. Does not modify system state.
    """
    return linux.list_processes(limit=limit)


def get_process_info(pid: int) -> ProcessDetail | ToolError:
    """
    Returns detailed information about a specific process: PID, parent PID,
    name, status, user, CPU%, memory%, command line, and working directory.

    Use this when investigating a specific process identified by list_processes
    or other tools. Does not modify system state.
    """
    try:
        return linux.read_process_info(pid)
    except ValueError as e:
        return ToolError(error_type="PROCESS_NOT_FOUND", message=str(e))
    except PermissionError as e:
        return ToolError(error_type="ACCESS_DENIED", message=str(e))

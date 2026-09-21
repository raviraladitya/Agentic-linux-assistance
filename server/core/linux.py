"""
MCPilot — Linux system data abstraction layer.

Reads /proc, uses psutil, and uname to provide structured system data.
MCP tool decorators call these functions — they never contain OS logic themselves.
"""

import os
import platform
import psutil

from server.schemas import (
    SystemInfo,
    CpuUsage,
    MemoryUsage,
    DiskUsageEntry,
    ProcessSummary,
    ProcessDetail,
)


def read_system_info() -> SystemInfo:
    """Read basic system information from platform/uname/psutil."""
    uname = platform.uname()
    boot_time = psutil.boot_time()
    import time
    uptime = time.time() - boot_time

    return SystemInfo(
        hostname=uname.node,
        os_name=uname.system,
        os_version=platform.version(),
        kernel_version=uname.release,
        architecture=uname.machine,
        uptime_seconds=round(uptime, 1),
        cpu_count=psutil.cpu_count(logical=True),
    )


def read_cpu_usage() -> CpuUsage:
    """Read CPU usage from psutil."""
    overall = psutil.cpu_percent(interval=0.5)
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    load_avg = os.getloadavg()

    return CpuUsage(
        overall_percent=overall,
        per_core_percent=per_core,
        core_count=psutil.cpu_count(logical=True),
        load_average_1m=round(load_avg[0], 2),
        load_average_5m=round(load_avg[1], 2),
        load_average_15m=round(load_avg[2], 2),
    )


def read_memory_usage() -> MemoryUsage:
    """Read memory and swap usage from psutil."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return MemoryUsage(
        total_gb=round(mem.total / (1024 ** 3), 2),
        available_gb=round(mem.available / (1024 ** 3), 2),
        used_gb=round(mem.used / (1024 ** 3), 2),
        used_percent=mem.percent,
        swap_total_gb=round(swap.total / (1024 ** 3), 2),
        swap_used_gb=round(swap.used / (1024 ** 3), 2),
        swap_used_percent=swap.percent,
    )


def read_disk_usage() -> list[DiskUsageEntry]:
    """Read disk usage for all mounted partitions."""
    entries = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            entries.append(DiskUsageEntry(
                mount_point=part.mountpoint,
                total_gb=round(usage.total / (1024 ** 3), 2),
                used_gb=round(usage.used / (1024 ** 3), 2),
                free_gb=round(usage.free / (1024 ** 3), 2),
                used_percent=usage.percent,
            ))
        except (PermissionError, OSError):
            continue
    return entries


def list_processes(limit: int = 50) -> list[ProcessSummary]:
    """List running processes, sorted by CPU usage, capped at limit."""
    # Clamp to a sane max to prevent context flooding
    limit = min(limit, 200)

    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = proc.info
            procs.append(ProcessSummary(
                pid=info["pid"],
                name=info["name"] or "unknown",
                cpu_percent=info["cpu_percent"] or 0.0,
                memory_percent=round(info["memory_percent"] or 0.0, 2),
                status=info["status"] or "unknown",
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort by CPU usage descending
    procs.sort(key=lambda p: p.cpu_percent, reverse=True)
    return procs[:limit]


def read_process_info(pid: int) -> ProcessDetail:
    """Read detailed info for a specific process by PID."""
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

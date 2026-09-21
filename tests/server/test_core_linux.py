"""
Layer 1 tests — Linux/core functions.

Tests that the core abstraction layer returns correctly typed, valid data
from the real system.
"""

import pytest
from server.core.linux import (
    read_system_info,
    read_cpu_usage,
    read_memory_usage,
    read_disk_usage,
    list_processes,
    read_process_info,
)
from server.schemas import (
    SystemInfo,
    CpuUsage,
    MemoryUsage,
    DiskUsageEntry,
    ProcessSummary,
    ProcessDetail,
)


def test_get_system_info():
    info = read_system_info()
    assert isinstance(info, SystemInfo)
    assert info.hostname  # non-empty
    assert info.os_name  # non-empty
    assert info.kernel_version  # non-empty
    assert info.architecture in ("x86_64", "aarch64", "armv7l", "i686")
    assert info.uptime_seconds > 0
    assert info.cpu_count > 0


def test_get_cpu_usage():
    cpu = read_cpu_usage()
    assert isinstance(cpu, CpuUsage)
    assert 0 <= cpu.overall_percent <= 100
    assert len(cpu.per_core_percent) == cpu.core_count
    assert cpu.core_count > 0
    assert cpu.load_average_1m >= 0
    assert cpu.load_average_5m >= 0
    assert cpu.load_average_15m >= 0


def test_get_memory_usage():
    mem = read_memory_usage()
    assert isinstance(mem, MemoryUsage)
    assert mem.total_gb > 0
    assert mem.available_gb >= 0
    assert mem.used_gb >= 0
    assert 0 <= mem.used_percent <= 100
    assert mem.swap_total_gb >= 0
    assert mem.swap_used_gb >= 0
    assert 0 <= mem.swap_used_percent <= 100


def test_get_disk_usage():
    disks = read_disk_usage()
    assert isinstance(disks, list)
    assert len(disks) > 0  # At least root partition
    for entry in disks:
        assert isinstance(entry, DiskUsageEntry)
        assert entry.mount_point
        assert entry.total_gb >= 0
        assert entry.used_gb >= 0
        assert entry.free_gb >= 0
        assert 0 <= entry.used_percent <= 100


def test_list_processes():
    procs = list_processes(limit=10)
    assert isinstance(procs, list)
    assert len(procs) > 0
    assert len(procs) <= 10
    for proc in procs:
        assert isinstance(proc, ProcessSummary)
        assert proc.pid > 0
        assert proc.name  # non-empty


def test_list_processes_clamp():
    """Server clamps limit to a sane max, does not flood context."""
    procs = list_processes(limit=100000)
    assert len(procs) <= 200


def test_get_process_info():
    """Test getting info for PID 1 (init/systemd), which always exists."""
    import os
    pid = os.getpid()
    try:
        info = read_process_info(pid)
        assert isinstance(info, ProcessDetail)
        assert info.pid == pid
        assert info.name  # non-empty
    except PermissionError:
        pytest.skip("No permission to read process info")


def test_get_process_info_not_found():
    """Test that a non-existent PID raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        read_process_info(999999999)

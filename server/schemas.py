"""
MCPilot — Pydantic data contracts.

Every MCP tool returns one of these models. Fields are the contract the LLM
reasons over: small, numeric where possible, and pre-computed (percentages,
GB, not raw kB).
"""

from pydantic import BaseModel
from typing import Literal


class SystemInfo(BaseModel):
    hostname: str
    os_name: str
    os_version: str
    kernel_version: str
    architecture: str
    uptime_seconds: float
    cpu_count: int


class CpuUsage(BaseModel):
    overall_percent: float
    per_core_percent: list[float]
    core_count: int
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float


class MemoryUsage(BaseModel):
    total_gb: float
    available_gb: float
    used_gb: float
    used_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_used_percent: float


class ProcessSummary(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str


class ProcessDetail(BaseModel):
    pid: int
    ppid: int
    name: str
    status: str
    user: str
    cpu_percent: float
    memory_percent: float
    cmdline: str
    cwd: str | None = None


class DiskUsageEntry(BaseModel):
    mount_point: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_percent: float


class ServiceStatus(BaseModel):
    service: str
    active_state: str           # active / inactive / failed / activating ...
    sub_state: str
    enabled: bool
    since: str | None = None


class ServiceLogs(BaseModel):
    service: str
    lines: list[str]


class ListeningPort(BaseModel):
    port: int
    protocol: Literal["tcp", "udp"]
    pid: int | None
    process_name: str | None
    address: str


class FileMetadata(BaseModel):
    path: str
    size_bytes: int
    is_dir: bool
    modified_time: str
    permissions: str


class DirectoryEntry(BaseModel):
    name: str
    is_dir: bool
    size_bytes: int | None


class SearchResult(BaseModel):
    matches: list[str]
    truncated: bool


class GitStatus(BaseModel):
    branch: str
    ahead: int
    behind: int
    modified: list[str]
    untracked: list[str]
    deleted: list[str]


class GitDiff(BaseModel):
    files_changed: list[str]
    diff_text: str              # hard-capped, see Section 6
    truncated: bool


class GitLogEntry(BaseModel):
    commit: str
    author: str
    date: str
    message: str


class TestRunResult(BaseModel):
    command: str                # the fixed command MCPilot chose, never LLM-supplied
    passed: bool
    summary: str                # short pass/fail summary, not full raw output
    failing_tests: list[str]


class ToolError(BaseModel):
    success: Literal[False] = False
    error_type: str             # e.g. "SERVICE_NOT_FOUND", "PATH_DENIED", "TIMEOUT"
    message: str

"""
MCPilot — MCP server.

Registers all 18 tools using MCPServer's decorator pattern. Schemas derive
from type hints + docstrings, so docstrings are part of the contract the
LLM reads to decide relevance.

Note: mcp v2 renamed FastMCP → MCPServer.
"""

from mcp.server.mcpserver import MCPServer
from server.schemas import (
    SystemInfo,
    CpuUsage,
    MemoryUsage,
    DiskUsageEntry,
    ProcessSummary,
    ProcessDetail,
    ServiceStatus,
    ServiceLogs,
    ListeningPort,
    DirectoryEntry,
    FileMetadata,
    SearchResult,
    GitStatus,
    GitDiff,
    GitLogEntry,
    TestRunResult,
    ToolError,
)
from server.tools import system, services, filesystem, git

mcp = MCPServer("mcpilot")


# ── System tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def get_system_info() -> SystemInfo:
    """
    Returns basic system information: hostname, OS, kernel version,
    architecture, uptime, and CPU count.

    Use this when investigating general system identity, checking OS version,
    or assessing basic system health. Does not modify system state.
    """
    return system.get_system_info()


@mcp.tool()
def get_cpu_usage() -> CpuUsage:
    """
    Returns current CPU utilization as overall and per-core percentages,
    plus 1/5/15-minute load averages.

    Use this when investigating high CPU usage, system slowness, or
    load-related issues. Does not modify system state.
    """
    return system.get_cpu_usage()


@mcp.tool()
def get_memory_usage() -> MemoryUsage:
    """
    Returns current system memory and swap utilization as percentages and GB.

    Use this when investigating high memory usage, swapping, or general system
    slowdown. Does not modify system state.
    """
    return system.get_memory_usage()


@mcp.tool()
def get_disk_usage() -> list[DiskUsageEntry]:
    """
    Returns disk usage for all mounted partitions: total, used, free in GB
    and used percentage per mount point.

    Use this when investigating low disk space, full partitions, or storage
    issues. Does not modify system state.
    """
    return system.get_disk_usage()


@mcp.tool()
def list_processes(limit: int = 50) -> list[ProcessSummary]:
    """
    Returns a list of running processes sorted by CPU usage, showing PID,
    name, CPU%, memory%, and status. Limited to `limit` entries (max 200).

    Use this when investigating which processes are consuming the most
    resources. Does not modify system state.
    """
    return system.list_processes(limit=limit)


@mcp.tool()
def get_process_info(pid: int) -> ProcessDetail | ToolError:
    """
    Returns detailed information about a specific process: PID, parent PID,
    name, status, user, CPU%, memory%, command line, and working directory.

    Use this when investigating a specific process identified by list_processes
    or other tools. Does not modify system state.
    """
    return system.get_process_info(pid)


# ── Service tools ─────────────────────────────────────────────────────────────

@mcp.tool()
def get_service_status(service: str) -> ServiceStatus | ToolError:
    """
    Returns the systemd status of a service: active state, sub-state,
    whether enabled, and activation timestamp.

    Use this when investigating whether a specific service is running,
    failed, or misconfigured. Does not modify system state.
    """
    return services.get_service_status(service)


@mcp.tool()
def get_service_logs(service: str, lines: int = 50) -> ServiceLogs | ToolError:
    """
    Returns the most recent journal log lines for a systemd service.

    Use this when investigating why a service failed, crashed, or is
    misbehaving. Does not modify system state.
    """
    return services.get_service_logs(service, lines=lines)


@mcp.tool()
def get_listening_ports() -> list[ListeningPort]:
    """
    Returns all currently listening TCP and UDP ports with their associated
    process information (PID, process name, bind address).

    Use this when investigating port conflicts, checking if a service is
    listening, or diagnosing network issues. Does not modify system state.
    """
    return services.get_listening_ports()


@mcp.tool()
def restart_service(service: str) -> ServiceStatus | ToolError:
    """
    Restarts a systemd service. This is a STATE-CHANGING operation that
    REQUIRES human approval before execution.

    Use this only when a service needs to be restarted as a remediation step
    and the user has been informed. This is the only mutating tool in MCPilot.
    """
    return services.restart_service(service)


# ── Filesystem tools ──────────────────────────────────────────────────────────

@mcp.tool()
def list_directory(path: str) -> list[DirectoryEntry] | ToolError:
    """
    Lists the contents of a directory: file/directory names, types, and sizes.
    Path must be within allowed roots (~/Projects, ~/Documents).

    Use this when investigating directory contents, checking project structure,
    or looking for specific files. Does not modify system state.
    """
    return filesystem.list_directory(path)


@mcp.tool()
def get_file_metadata(path: str) -> FileMetadata | ToolError:
    """
    Returns metadata about a file or directory: path, size, type, modification
    time, and permissions. Path must be within allowed roots.

    Use this when investigating file properties, checking permissions, or
    assessing file sizes. Does not modify system state.
    """
    return filesystem.get_file_metadata(path)


@mcp.tool()
def search_files(path: str, pattern: str) -> SearchResult | ToolError:
    """
    Searches for files matching a glob pattern within a directory tree.
    Results are capped at 100 entries. Path must be within allowed roots.

    Use this when looking for specific files by name or extension within
    a project. Does not modify system state.
    """
    return filesystem.search_files(path, pattern)


@mcp.tool()
def read_file(path: str) -> str | ToolError:
    """
    Reads the text contents of a file (capped at 100KB). Path must be within
    allowed roots (~/Projects, ~/Documents).

    Use this when investigating file contents, checking configuration files,
    or reading source code. Does not modify system state.
    """
    return filesystem.read_file(path)


# ── Git tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def git_status(repo: str) -> GitStatus | ToolError:
    """
    Returns the Git status of a repository: current branch, ahead/behind
    counts, modified files, untracked files, and deleted files.
    The repo path must be within allowed roots (~/Projects, ~/Documents).

    Use this when investigating uncommitted changes, branch status, or
    repository state. Does not modify system state.
    """
    return git.git_status(repo)


@mcp.tool()
def git_diff(repo: str, cached: bool = False) -> GitDiff | ToolError:
    """
    Returns the Git diff for a repository, showing changed files and diff
    text. Output is capped to prevent context flooding, with a truncated
    flag if the cap was hit. The repo path must be within allowed roots.

    Use this when investigating what code changes were made, comparing working
    tree to index, or reviewing staged changes. Does not modify system state.
    """
    return git.git_diff(repo, cached=cached)


@mcp.tool()
def git_log(repo: str, max_entries: int = 20) -> list[GitLogEntry] | ToolError:
    """
    Returns the most recent Git log entries: commit hash, author, date, and
    message. Limited to max_entries (max 100). The repo path must be within
    allowed roots.

    Use this when investigating recent commits, looking for when a change was
    made, or identifying who made modifications. Does not modify system state.
    """
    return git.git_log(repo, max_entries=max_entries)


@mcp.tool()
def run_tests(repo: str) -> TestRunResult | ToolError:
    """
    Runs pytest in a repository using a fixed, MCPilot-chosen command (never
    an LLM-supplied command). Returns pass/fail status, summary, and list
    of failing tests. The repo path must be within allowed roots.

    Use this when investigating test failures or verifying that changes
    haven't broken tests. Does not modify system state (runs read-only tests).
    """
    return git.run_tests(repo)


if __name__ == "__main__":
    mcp.run()

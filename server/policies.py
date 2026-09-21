"""
MCPilot — Risk classification map.

Every tool has an explicit risk level. The MCP client / LangGraph execute_tools
node consults TOOL_RISK before calling anything. Unknown tools are DENIED (fail closed).
"""

from enum import Enum


class Risk(str, Enum):
    READ_ONLY = "read_only"
    APPROVAL_REQUIRED = "approval_required"
    DENIED = "denied"


TOOL_RISK: dict[str, Risk] = {
    # System tools
    "get_system_info": Risk.READ_ONLY,
    "get_cpu_usage": Risk.READ_ONLY,
    "get_memory_usage": Risk.READ_ONLY,
    "get_disk_usage": Risk.READ_ONLY,
    "list_processes": Risk.READ_ONLY,
    "get_process_info": Risk.READ_ONLY,
    # Service tools
    "get_service_status": Risk.READ_ONLY,
    "get_service_logs": Risk.READ_ONLY,
    "get_listening_ports": Risk.READ_ONLY,
    "restart_service": Risk.APPROVAL_REQUIRED,
    # Filesystem tools
    "list_directory": Risk.READ_ONLY,
    "get_file_metadata": Risk.READ_ONLY,
    "search_files": Risk.READ_ONLY,
    "read_file": Risk.READ_ONLY,
    # Git tools
    "git_status": Risk.READ_ONLY,
    "git_diff": Risk.READ_ONLY,
    "git_log": Risk.READ_ONLY,
    "run_tests": Risk.READ_ONLY,
}


def get_risk(tool_name: str) -> Risk:
    """Look up risk for a tool name. Unknown tools are DENIED (fail closed)."""
    return TOOL_RISK.get(tool_name, Risk.DENIED)

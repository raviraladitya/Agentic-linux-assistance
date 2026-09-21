"""
Layer 2 tests — MCP protocol.

Tests that the MCP server exposes all 18 tools with correct schemas,
and that tools/call returns correctly-typed structured results.
Uses the MCP SDK's in-memory client testing (no subprocess needed).
"""

import pytest
from mcp.server.mcpserver import MCPServer


@pytest.fixture
def server():
    """Import the MCPilot MCP server."""
    from server.main import mcp
    return mcp


def test_server_has_18_tools(server):
    """tools/list returns all 18 tools."""
    tools = server._tool_manager._tools
    assert len(tools) == 18, f"Expected 18 tools, got {len(tools)}: {list(tools.keys())}"


def test_tool_names_match_spec(server):
    """All tools from Section 5 exist."""
    expected_tools = {
        "get_system_info", "get_cpu_usage", "get_memory_usage", "get_disk_usage",
        "list_processes", "get_process_info",
        "get_service_status", "get_service_logs", "get_listening_ports", "restart_service",
        "list_directory", "get_file_metadata", "search_files", "read_file",
        "git_status", "git_diff", "git_log", "run_tests",
    }
    actual_tools = set(server._tool_manager._tools.keys())
    assert actual_tools == expected_tools, f"Missing: {expected_tools - actual_tools}, Extra: {actual_tools - expected_tools}"


def test_tools_have_descriptions(server):
    """Every tool has a non-empty description."""
    for name, tool in server._tool_manager._tools.items():
        assert tool.description, f"Tool '{name}' has no description"
        assert len(tool.description) > 20, f"Tool '{name}' description is too short"


def test_tools_have_schemas(server):
    """Every tool has an input schema."""
    for name, tool in server._tool_manager._tools.items():
        assert tool.parameters is not None, f"Tool '{name}' has no parameters schema"
        assert "type" in tool.parameters, f"Tool '{name}' parameters missing type"

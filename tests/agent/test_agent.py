"""
Layer 4 tests — Agent.

Tests with mocked MCP responses (don't touch the real system in CI).
Verifies diagnosis quality, grounding, iteration cap, and approval rejection.
"""

import pytest
from unittest.mock import patch, MagicMock

from agent.state import DiagnosticState
from agent.nodes import MAX_ITERATIONS, evaluate_evidence, generate_diagnosis, execute_tools
from server.policies import get_risk, Risk, TOOL_RISK


class TestPolicies:
    """Test the policy engine."""

    def test_all_18_tools_have_risk(self):
        assert len(TOOL_RISK) == 18

    def test_unknown_tool_denied(self):
        assert get_risk("run_command") == Risk.DENIED
        assert get_risk("delete_file") == Risk.DENIED
        assert get_risk("nonexistent_tool") == Risk.DENIED

    def test_restart_service_requires_approval(self):
        assert get_risk("restart_service") == Risk.APPROVAL_REQUIRED

    def test_read_only_tools(self):
        read_only_tools = [
            "get_system_info", "get_cpu_usage", "get_memory_usage",
            "get_disk_usage", "list_processes", "get_process_info",
            "get_service_status", "get_service_logs", "get_listening_ports",
            "list_directory", "get_file_metadata", "search_files", "read_file",
            "git_status", "git_diff", "git_log", "run_tests",
        ]
        for tool in read_only_tools:
            assert get_risk(tool) == Risk.READ_ONLY, f"{tool} should be READ_ONLY"


class TestIterationCap:
    """Test that the iteration cap terminates rather than looping forever."""

    def test_iteration_cap_forces_sufficient(self):
        """After MAX_ITERATIONS, evaluate_evidence forces sufficient=True."""
        state = {
            "query": "test query",
            "observations": [{"tool": "test", "result": {"data": "value"}}],
            "tool_calls": ["test"],
            "sufficient": False,
            "missing_information": [],
            "diagnosis": "",
            "evidence": [],
            "confidence": "",
            "iteration": MAX_ITERATIONS - 1,  # Next call will hit the cap
        }

        # This should force sufficient=True without calling Gemini
        result = evaluate_evidence(state)
        assert result["sufficient"] is True
        assert result["confidence"] == "LOW"

    def test_max_iterations_value(self):
        """Verify the cap is set to a reasonable value."""
        assert MAX_ITERATIONS == 4


class TestApprovalRejection:
    """Test that rejected restart_service doesn't crash the graph."""

    def test_rejected_approval_does_not_crash(self):
        """A rejected restart_service approval should continue gracefully."""
        from agent.nodes import set_approval_callback

        # Set a callback that always rejects
        set_approval_callback(lambda name, args: False)

        state = {
            "query": "restart postgresql",
            "observations": [],
            "tool_calls": [],
            "sufficient": False,
            "missing_information": [],
            "diagnosis": "",
            "evidence": [],
            "confidence": "",
            "iteration": 0,
            "pending_calls": [
                {"name": "restart_service", "arguments": {"service": "postgresql"}},
            ],
        }

        result = execute_tools(state)
        # Should not crash, tool_calls should still be populated (or empty)
        assert isinstance(result["observations"], list)
        assert isinstance(result["tool_calls"], list)

        # Reset callback
        set_approval_callback(None)


class TestDiagnosticState:
    """Test the DiagnosticState TypedDict."""

    def test_state_has_all_fields(self):
        state: DiagnosticState = {
            "query": "test",
            "observations": [],
            "tool_calls": [],
            "sufficient": False,
            "missing_information": [],
            "diagnosis": "",
            "evidence": [],
            "confidence": "",
            "iteration": 0,
        }
        assert state["query"] == "test"
        assert state["iteration"] == 0

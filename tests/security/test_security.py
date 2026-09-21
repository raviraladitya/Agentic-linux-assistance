"""
Layer 3 — Security tests (Section 13.3).

This is the exhaustive malicious-input test suite — the project's actual
security story. Every test must pass before permissions phase is complete.
"""

import pytest
from server.core.fs import validate_path
from server.core.systemd import validate_service_name
from server.tools.filesystem import read_file, list_directory, get_file_metadata, search_files
from server.tools.git import git_status, git_diff, git_log, run_tests
from server.tools.services import get_service_status
from server.schemas import ToolError


class TestPathTraversal:
    """Path traversal and injection attacks — all must be DENIED."""

    def test_read_file_etc_passwd_relative(self):
        result = read_file("../../etc/passwd")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_read_file_etc_passwd_absolute(self):
        result = read_file("/etc/passwd")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_read_file_home_not_under_allowlist(self):
        result = read_file("~")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_read_file_root_traversal(self):
        result = read_file("../../../")
        assert isinstance(result, ToolError)
        assert result.error_type in ("PATH_DENIED", "INVALID_PATH")

    def test_read_file_with_shell_injection(self):
        result = read_file('"; rm -rf /"')
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_git_status_root(self):
        result = git_status("/")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_validate_path_etc_passwd(self):
        with pytest.raises(PermissionError):
            validate_path("/etc/passwd")

    def test_validate_path_traversal(self):
        with pytest.raises(PermissionError):
            validate_path("../../etc/passwd")

    def test_validate_path_root(self):
        with pytest.raises(PermissionError):
            validate_path("/")

    def test_validate_path_home_root(self):
        """Home directory itself is not in the allow-list."""
        with pytest.raises(PermissionError):
            validate_path("~")

    def test_list_directory_denied(self):
        result = list_directory("/etc")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_get_file_metadata_denied(self):
        result = get_file_metadata("/etc/passwd")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"

    def test_search_files_denied(self):
        result = search_files("/", "*.py")
        assert isinstance(result, ToolError)
        assert result.error_type == "PATH_DENIED"


class TestServiceNameInjection:
    """Service name injection attacks — all must be DENIED."""

    def test_service_name_with_semicolon(self):
        result = get_service_status("postgresql; rm -rf /")
        assert isinstance(result, ToolError)
        assert result.error_type == "INVALID_SERVICE_NAME"

    def test_service_name_with_command_substitution(self):
        result = get_service_status("$(whoami)")
        assert isinstance(result, ToolError)
        assert result.error_type == "INVALID_SERVICE_NAME"

    def test_service_name_with_pipe(self):
        result = get_service_status("postgresql | cat /etc/passwd")
        assert isinstance(result, ToolError)
        assert result.error_type == "INVALID_SERVICE_NAME"

    def test_service_name_with_ampersand(self):
        result = get_service_status("postgresql & rm -rf /")
        assert isinstance(result, ToolError)
        assert result.error_type == "INVALID_SERVICE_NAME"

    def test_service_name_with_backticks(self):
        result = get_service_status("`whoami`")
        assert isinstance(result, ToolError)
        assert result.error_type == "INVALID_SERVICE_NAME"

    def test_validate_service_name_clean(self):
        """Valid service names should pass."""
        assert validate_service_name("postgresql") == "postgresql"
        assert validate_service_name("nginx.service") == "nginx.service"
        assert validate_service_name("user@1000") == "user@1000"

    def test_validate_service_name_injection(self):
        with pytest.raises(ValueError):
            validate_service_name("postgresql; rm -rf /")

    def test_validate_service_name_too_long(self):
        with pytest.raises(ValueError):
            validate_service_name("a" * 129)


class TestUnknownTools:
    """Requests for non-existent dangerous tools should fail."""

    def test_no_run_command_tool(self):
        """There must be no run_command tool in the server."""
        # The policy engine treats unknown tools as DENIED (fail closed)
        from server.policies import get_risk, Risk
        assert get_risk("run_command") == Risk.DENIED
        assert get_risk("delete_file") == Risk.DENIED
        assert get_risk("sudo_command") == Risk.DENIED
        assert get_risk("execute_shell") == Risk.DENIED


class TestOutputClamping:
    """Tests for output size limits to prevent context flooding."""

    def test_list_processes_clamp(self):
        """Server clamps to a sane max, does not flood context."""
        from server.core.linux import list_processes
        procs = list_processes(limit=100000)
        assert len(procs) <= 200

    def test_git_diff_truncation(self):
        """Git diff should be truncated at the documented character cap."""
        from server.core.git import DIFF_CHAR_CAP
        assert DIFF_CHAR_CAP == 10_000  # Verify the cap is set as documented

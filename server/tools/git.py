"""
MCPilot — Git MCP tools.

Thin wrappers over server/core/git.py. The repo path argument is validated
through the shared validate_path() before any Git operation.
"""

from server.schemas import GitStatus, GitDiff, GitLogEntry, TestRunResult, ToolError
from server.core import git as git_core


def git_status(repo: str) -> GitStatus | ToolError:
    """
    Returns the Git status of a repository: current branch, ahead/behind
    counts, modified files, untracked files, and deleted files.
    The repo path must be within allowed roots (~/Projects, ~/Documents).

    Use this when investigating uncommitted changes, branch status, or
    repository state. Does not modify system state.
    """
    try:
        return git_core.read_git_status(repo)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))
    except FileNotFoundError as e:
        return ToolError(error_type="REPO_NOT_FOUND", message=str(e))


def git_diff(repo: str, cached: bool = False) -> GitDiff | ToolError:
    """
    Returns the Git diff for a repository, showing changed files and diff
    text. Output is capped to prevent context flooding, with a truncated
    flag if the cap was hit. The repo path must be within allowed roots.

    Use this when investigating what code changes were made, comparing working
    tree to index, or reviewing staged changes. Does not modify system state.
    """
    try:
        return git_core.read_git_diff(repo, cached=cached)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))


def git_log(repo: str, max_entries: int = 20) -> list[GitLogEntry] | ToolError:
    """
    Returns the most recent Git log entries: commit hash, author, date, and
    message. Limited to max_entries (max 100). The repo path must be within
    allowed roots.

    Use this when investigating recent commits, looking for when a change was
    made, or identifying who made modifications. Does not modify system state.
    """
    try:
        return git_core.read_git_log(repo, max_entries=max_entries)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))


def run_tests(repo: str) -> TestRunResult | ToolError:
    """
    Runs pytest in a repository using a fixed, MCPilot-chosen command (never
    an LLM-supplied command). Returns pass/fail status, summary, and list
    of failing tests. The repo path must be within allowed roots.

    Use this when investigating test failures or verifying that changes
    haven't broken tests. Does not modify system state (runs read-only tests).
    """
    try:
        return git_core.run_project_tests(repo)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))
    except Exception as e:
        return ToolError(error_type="TEST_RUN_FAILED", message=str(e))

"""
MCPilot — Git subprocess wrappers.

All Git operations go through run_safe with path-validated repo arguments.
"""

from pathlib import Path

from server.core.command import run_safe
from server.core.fs import validate_path
from server.schemas import GitStatus, GitDiff, GitLogEntry, TestRunResult


# Maximum characters for diff output to prevent context flooding
DIFF_CHAR_CAP = 10_000


def read_git_status(repo: str) -> GitStatus:
    """Get git status for a validated repo path."""
    repo_path = validate_path(repo)

    # Get branch name
    result = run_safe(["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"])
    branch = result.stdout.strip() or "unknown"

    # Get ahead/behind
    ahead = 0
    behind = 0
    result_ab = run_safe(["git", "-C", str(repo_path), "rev-list", "--left-right", "--count", f"{branch}...@{{u}}"])
    if result_ab.returncode == 0 and result_ab.stdout.strip():
        parts = result_ab.stdout.strip().split()
        if len(parts) == 2:
            ahead = int(parts[0])
            behind = int(parts[1])

    # Get modified/untracked/deleted
    result_status = run_safe(["git", "-C", str(repo_path), "status", "--porcelain"])
    modified = []
    untracked = []
    deleted = []

    for line in result_status.stdout.strip().split("\n"):
        if not line.strip():
            continue
        status_code = line[:2]
        filename = line[3:]
        if "?" in status_code:
            untracked.append(filename)
        elif "D" in status_code:
            deleted.append(filename)
        elif "M" in status_code or "A" in status_code or "R" in status_code:
            modified.append(filename)

    return GitStatus(
        branch=branch,
        ahead=ahead,
        behind=behind,
        modified=modified,
        untracked=untracked,
        deleted=deleted,
    )


def read_git_diff(repo: str, cached: bool = False) -> GitDiff:
    """Get git diff for a validated repo path, capped at DIFF_CHAR_CAP."""
    repo_path = validate_path(repo)

    args = ["git", "-C", str(repo_path), "diff"]
    if cached:
        args.append("--cached")

    result = run_safe(args, timeout=10)

    diff_text = result.stdout
    truncated = False
    if len(diff_text) > DIFF_CHAR_CAP:
        diff_text = diff_text[:DIFF_CHAR_CAP]
        truncated = True

    # Get list of changed files
    args_stat = ["git", "-C", str(repo_path), "diff", "--name-only"]
    if cached:
        args_stat.append("--cached")
    result_stat = run_safe(args_stat)
    files_changed = [f for f in result_stat.stdout.strip().split("\n") if f.strip()]

    return GitDiff(
        files_changed=files_changed,
        diff_text=diff_text,
        truncated=truncated,
    )


def read_git_log(repo: str, max_entries: int = 20) -> list[GitLogEntry]:
    """Get recent git log entries for a validated repo path."""
    repo_path = validate_path(repo)
    max_entries = min(max_entries, 100)

    result = run_safe(
        ["git", "-C", str(repo_path), "log", f"-{max_entries}",
         "--format=%H|%an|%ai|%s"],
        timeout=10,
    )

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            entries.append(GitLogEntry(
                commit=parts[0],
                author=parts[1],
                date=parts[2],
                message=parts[3],
            ))

    return entries


def run_project_tests(repo: str) -> TestRunResult:
    """
    Run pytest in a validated repo path. Uses a fixed command — never
    an LLM-supplied command string.
    """
    repo_path = validate_path(repo)

    # Fixed command: only pytest
    command = "pytest"
    result = run_safe(
        ["python", "-m", "pytest", "--tb=short", "-q", str(repo_path)],
        timeout=60,
    )

    passed = result.returncode == 0
    output = result.stdout + result.stderr

    # Parse failing tests
    failing_tests = []
    for line in output.split("\n"):
        if line.startswith("FAILED "):
            failing_tests.append(line.replace("FAILED ", "").strip())

    # Build short summary
    summary_lines = output.strip().split("\n")
    summary = summary_lines[-1] if summary_lines else "No output"

    return TestRunResult(
        command=command,
        passed=passed,
        summary=summary,
        failing_tests=failing_tests,
    )

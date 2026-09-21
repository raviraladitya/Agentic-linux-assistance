"""
MCPilot — Filesystem path validation.

All filesystem and Git tools must validate paths through validate_path()
before any operation. Paths are restricted to an explicit allow-list.
"""

from pathlib import Path


ALLOWED_ROOTS = [Path.home() / "Projects", Path.home() / "Documents"]


def validate_path(user_path: str) -> Path:
    """
    Resolve the user-supplied path and verify it falls under at least one
    allowed root.  Raises PermissionError otherwise — never executes.
    """
    resolved = Path(user_path).expanduser().resolve()
    for root in ALLOWED_ROOTS:
        root_resolved = root.resolve()
        if resolved.is_relative_to(root_resolved):
            return resolved
    raise PermissionError(f"Path '{user_path}' is outside allowed roots")


def list_directory_entries(validated_path: Path) -> list[dict]:
    """List directory contents for a validated path."""
    entries = []
    try:
        for item in sorted(validated_path.iterdir()):
            try:
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else None,
                })
            except (PermissionError, OSError):
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": None,
                })
    except PermissionError:
        raise PermissionError(f"Cannot list directory: {validated_path}")
    return entries


def get_file_metadata_info(validated_path: Path) -> dict:
    """Get metadata for a validated path."""
    stat = validated_path.stat()
    return {
        "path": str(validated_path),
        "size_bytes": stat.st_size,
        "is_dir": validated_path.is_dir(),
        "modified_time": str(stat.st_mtime),
        "permissions": oct(stat.st_mode)[-3:],
    }


def search_files_in_directory(validated_path: Path, pattern: str, max_results: int = 100) -> dict:
    """Search for files matching a glob pattern within a validated path."""
    matches = []
    truncated = False
    try:
        for match in validated_path.rglob(pattern):
            if len(matches) >= max_results:
                truncated = True
                break
            matches.append(str(match))
    except (PermissionError, OSError):
        pass
    return {"matches": matches, "truncated": truncated}


def read_file_contents(validated_path: Path, max_bytes: int = 100_000) -> str:
    """Read file contents for a validated path, capped at max_bytes."""
    if validated_path.is_dir():
        raise ValueError(f"Path is a directory, not a file: {validated_path}")
    size = validated_path.stat().st_size
    if size > max_bytes:
        with validated_path.open("r", errors="replace") as f:
            return f.read(max_bytes)
    return validated_path.read_text(errors="replace")

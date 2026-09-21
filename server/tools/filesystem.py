"""
MCPilot — Filesystem MCP tools.

Thin wrappers over server/core/fs.py. All paths are validated through
validate_path() before any operation.
"""

from server.schemas import DirectoryEntry, FileMetadata, SearchResult, ToolError
from server.core import fs


def list_directory(path: str) -> list[DirectoryEntry] | ToolError:
    """
    Lists the contents of a directory: file/directory names, types, and sizes.
    Path must be within allowed roots (~/Projects, ~/Documents).

    Use this when investigating directory contents, checking project structure,
    or looking for specific files. Does not modify system state.
    """
    try:
        validated = fs.validate_path(path)
        entries = fs.list_directory_entries(validated)
        return [DirectoryEntry(**e) for e in entries]
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))
    except FileNotFoundError as e:
        return ToolError(error_type="PATH_NOT_FOUND", message=str(e))


def get_file_metadata(path: str) -> FileMetadata | ToolError:
    """
    Returns metadata about a file or directory: path, size, type, modification
    time, and permissions. Path must be within allowed roots.

    Use this when investigating file properties, checking permissions, or
    assessing file sizes. Does not modify system state.
    """
    try:
        validated = fs.validate_path(path)
        info = fs.get_file_metadata_info(validated)
        return FileMetadata(**info)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))
    except FileNotFoundError as e:
        return ToolError(error_type="PATH_NOT_FOUND", message=str(e))


def search_files(path: str, pattern: str) -> SearchResult | ToolError:
    """
    Searches for files matching a glob pattern within a directory tree.
    Results are capped at 100 entries. Path must be within allowed roots.

    Use this when looking for specific files by name or extension within
    a project. Does not modify system state.
    """
    try:
        validated = fs.validate_path(path)
        result = fs.search_files_in_directory(validated, pattern)
        return SearchResult(**result)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))


def read_file(path: str) -> str | ToolError:
    """
    Reads the text contents of a file (capped at 100KB). Path must be within
    allowed roots (~/Projects, ~/Documents).

    Use this when investigating file contents, checking configuration files,
    or reading source code. Does not modify system state.
    """
    try:
        validated = fs.validate_path(path)
        return fs.read_file_contents(validated)
    except PermissionError as e:
        return ToolError(error_type="PATH_DENIED", message=str(e))
    except FileNotFoundError as e:
        return ToolError(error_type="PATH_NOT_FOUND", message=str(e))
    except ValueError as e:
        return ToolError(error_type="INVALID_PATH", message=str(e))

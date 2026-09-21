"""
MCPilot — JSONL audit logger.

Every tool call (success, failure, rejected-approval) is logged to
logs/audit.jsonl, one JSON object per line.
"""

import json
import time
from pathlib import Path


AUDIT_PATH = Path("logs/audit.jsonl")


def log_call(
    tool: str,
    arguments: dict,
    risk: str,
    approved: bool,
    success: bool,
    error: str | None = None,
) -> None:
    """Append one audit entry to the JSONL log."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tool": tool,
        "arguments": arguments,
        "risk": risk,
        "approved": approved,
        "success": success,
        "error": error,
    }
    AUDIT_PATH.parent.mkdir(exist_ok=True)
    with AUDIT_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")

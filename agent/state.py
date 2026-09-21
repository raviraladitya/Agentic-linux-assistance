"""
MCPilot — Diagnostic state TypedDict.

The shared state that flows through the LangGraph state machine.
"""

from typing import TypedDict


class DiagnosticState(TypedDict):
    query: str
    observations: list[dict]        # {tool, arguments, result}
    tool_calls: list[str]           # names already called, avoid redundant re-calls
    sufficient: bool
    missing_information: list[str]
    diagnosis: str
    evidence: list[str]
    confidence: str                 # "HIGH" | "MEDIUM" | "LOW"
    iteration: int                  # track loop count for cap

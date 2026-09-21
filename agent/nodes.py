"""
MCPilot — LangGraph node functions.

Four nodes: analyze_request, execute_tools, evaluate_evidence, generate_diagnosis.
The Gemini function calling loop lives inside execute_tools.
"""

import json
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv
from rich.console import Console

from agent.state import DiagnosticState
from agent.prompts import (
    SYSTEM_PROMPT,
    ANALYZE_REQUEST_PROMPT,
    EVALUATE_EVIDENCE_PROMPT,
    GENERATE_DIAGNOSIS_PROMPT,
)
from agent.tool_adapter import build_gemini_tools
from server.tools import system, services, filesystem, git
from server.policies import get_risk, Risk
from server.audit import log_call
from server.schemas import ToolError

load_dotenv()
console = Console()

# Max iterations to prevent infinite loops
MAX_ITERATIONS = 4

# Direct tool dispatch map — calls the tool functions directly (no MCP subprocess needed)
TOOL_DISPATCH = {
    "get_system_info": lambda args: system.get_system_info(),
    "get_cpu_usage": lambda args: system.get_cpu_usage(),
    "get_memory_usage": lambda args: system.get_memory_usage(),
    "get_disk_usage": lambda args: system.get_disk_usage(),
    "list_processes": lambda args: system.list_processes(limit=args.get("limit", 50)),
    "get_process_info": lambda args: system.get_process_info(pid=args["pid"]),
    "get_service_status": lambda args: services.get_service_status(service=args["service"]),
    "get_service_logs": lambda args: services.get_service_logs(
        service=args["service"], lines=args.get("lines", 50)
    ),
    "get_listening_ports": lambda args: services.get_listening_ports(),
    "restart_service": lambda args: services.restart_service(service=args["service"]),
    "list_directory": lambda args: filesystem.list_directory(path=args["path"]),
    "get_file_metadata": lambda args: filesystem.get_file_metadata(path=args["path"]),
    "search_files": lambda args: filesystem.search_files(
        path=args["path"], pattern=args["pattern"]
    ),
    "read_file": lambda args: filesystem.read_file(path=args["path"]),
    "git_status": lambda args: git.git_status(repo=args["repo"]),
    "git_diff": lambda args: git.git_diff(
        repo=args["repo"], cached=args.get("cached", False)
    ),
    "git_log": lambda args: git.git_log(
        repo=args["repo"], max_entries=args.get("max_entries", 20)
    ),
    "run_tests": lambda args: git.run_tests(repo=args["repo"]),
}

# Approval callback — set by CLI to handle human-in-the-loop
_approval_callback = None


def set_approval_callback(callback):
    """Set the callback for human-in-the-loop approval prompts."""
    global _approval_callback
    _approval_callback = callback


def _get_gemini_client():
    """Get a Gemini client instance."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set. Add it to .env or environment.")
    return genai.Client(api_key=api_key)


def _get_mcp_tool_list():
    """Get tool list for Gemini function declarations (static, not via MCP)."""
    from server.main import mcp
    tools = []
    for name, tool_obj in mcp._tool_manager._tools.items():
        # Build a mock tool object with the right attributes
        class MockTool:
            pass
        t = MockTool()
        t.name = name
        t.description = tool_obj.description
        t.inputSchema = tool_obj.parameters
        tools.append(t)
    return tools


def _serialize_result(result):
    """Serialize a tool result to a JSON-friendly dict."""
    if isinstance(result, list):
        return [_serialize_result(item) for item in result]
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, str):
        return result
    return str(result)


def analyze_request(state: DiagnosticState) -> dict:
    """
    Node 1: Ask Gemini which tools are relevant given the query and
    any prior observations. Returns function calls.
    """
    console.print("[bold cyan][Agent][/] Analyzing request...", highlight=False)

    client = _get_gemini_client()
    mcp_tools = _get_mcp_tool_list()
    gemini_tools = build_gemini_tools(mcp_tools)

    observations_text = json.dumps(state.get("observations", []), indent=2, default=str)
    tool_calls_text = ", ".join(state.get("tool_calls", [])) or "none yet"

    prompt = ANALYZE_REQUEST_PROMPT.format(
        query=state["query"],
        tool_calls=tool_calls_text,
        observations=observations_text if state.get("observations") else "none yet",
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools,
            temperature=0.1,
        ),
    )

    # Extract function calls from the response
    pending_calls = []
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                pending_calls.append({
                    "name": part.function_call.name,
                    "arguments": dict(part.function_call.args) if part.function_call.args else {},
                })

    return {"pending_calls": pending_calls}


def execute_tools(state: DiagnosticState) -> dict:
    """
    Node 2: Execute the pending tool calls, handling risk levels
    and human approval for APPROVAL_REQUIRED tools.
    """
    pending_calls = state.get("pending_calls", [])
    observations = list(state.get("observations", []))
    tool_calls = list(state.get("tool_calls", []))

    # If Gemini returned function calls, execute them
    if pending_calls:
        for call in pending_calls:
            tool_name = call["name"]
            arguments = call["arguments"]

            # Check risk level
            risk = get_risk(tool_name)

            if risk == Risk.DENIED:
                console.print(f"[bold red][Security][/] Tool '{tool_name}' is DENIED", highlight=False)
                log_call(tool_name, arguments, risk.value, approved=False, success=False,
                        error="Tool is DENIED by policy")
                continue

            if risk == Risk.APPROVAL_REQUIRED:
                # Human-in-the-loop approval
                approved = False
                if _approval_callback:
                    approved = _approval_callback(tool_name, arguments)
                else:
                    console.print(f"\n[bold yellow]⚠ State-changing operation[/]", highlight=False)
                    console.print(f"  Tool: [bold]{tool_name}[/]", highlight=False)
                    for k, v in arguments.items():
                        console.print(f"  {k.title()}: [bold]{v}[/]", highlight=False)
                    response_text = input("\n  Approve? [y/N] ").strip().lower()
                    approved = response_text == "y"

                if not approved:
                    console.print(f"[bold red][Rejected][/] {tool_name} — not executed", highlight=False)
                    log_call(tool_name, arguments, risk.value, approved=False, success=False,
                            error="User rejected approval")
                    continue

            # Execute the tool
            console.print(f"[bold green][MCP][/]  {tool_name}({', '.join(f'{k}={v!r}' for k, v in arguments.items()) if arguments else ''})", highlight=False)

            try:
                if tool_name in TOOL_DISPATCH:
                    result = TOOL_DISPATCH[tool_name](arguments)
                else:
                    result = ToolError(error_type="UNKNOWN_TOOL", message=f"Tool '{tool_name}' not found")

                serialized = _serialize_result(result)

                # Check if it's a ToolError
                is_error = isinstance(result, ToolError)
                log_call(tool_name, arguments, risk.value, approved=True,
                        success=not is_error,
                        error=result.message if is_error else None)

                observations.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": serialized,
                })
                if tool_name not in tool_calls:
                    tool_calls.append(tool_name)

            except Exception as e:
                console.print(f"[bold red][Error][/] {tool_name}: {e}", highlight=False)
                log_call(tool_name, arguments, risk.value, approved=True, success=False, error=str(e))
                observations.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": {"error": str(e)},
                })
                if tool_name not in tool_calls:
                    tool_calls.append(tool_name)
    else:
        # If no function calls from Gemini, use the existing observations
        # (this happens when Gemini decides it needs text-only response)
        pass

    return {
        "observations": observations,
        "tool_calls": tool_calls,
    }


def evaluate_evidence(state: DiagnosticState) -> dict:
    """
    Node 3: Ask Gemini if there's enough evidence for a diagnosis.
    Enforces iteration cap to prevent infinite loops.
    """
    console.print("[bold cyan][Agent][/] Evaluating evidence...", highlight=False)

    iteration = state.get("iteration", 0) + 1

    # Hard cap: force sufficient=True after MAX_ITERATIONS
    if iteration >= MAX_ITERATIONS:
        console.print(f"[bold yellow][Agent][/] Iteration cap ({MAX_ITERATIONS}) reached — forcing diagnosis", highlight=False)
        return {
            "sufficient": True,
            "missing_information": ["Iteration cap reached — diagnosis may be incomplete"],
            "confidence": "LOW",
            "iteration": iteration,
        }

    client = _get_gemini_client()
    observations_text = json.dumps(state.get("observations", []), indent=2, default=str)

    prompt = EVALUATE_EVIDENCE_PROMPT.format(
        query=state["query"],
        observations=observations_text,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    # Parse structured JSON response
    try:
        response_text = response.text.strip()
        evaluation = json.loads(response_text)
        return {
            "sufficient": evaluation.get("sufficient", False),
            "missing_information": evaluation.get("missing_information", []),
            "iteration": iteration,
        }
    except (json.JSONDecodeError, AttributeError):
        # If parsing fails, assume we need more info unless we've iterated a lot
        return {
            "sufficient": iteration >= 2,
            "missing_information": ["Could not parse evaluation response"],
            "iteration": iteration,
        }


def generate_diagnosis(state: DiagnosticState) -> dict:
    """
    Node 4: Generate the final evidence-based diagnosis using only
    the observations gathered. Never invents measurements.
    """
    console.print("[bold cyan][Agent][/] Generating diagnosis...", highlight=False)

    client = _get_gemini_client()
    observations_text = json.dumps(state.get("observations", []), indent=2, default=str)

    prompt = GENERATE_DIAGNOSIS_PROMPT.format(
        query=state["query"],
        observations=observations_text,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )

    diagnosis_text = response.text.strip() if response.text else "Unable to generate diagnosis."

    # Extract confidence from the diagnosis text
    confidence = "MEDIUM"
    if "Confidence: HIGH" in diagnosis_text or "**Confidence**: HIGH" in diagnosis_text:
        confidence = "HIGH"
    elif "Confidence: LOW" in diagnosis_text or "**Confidence**: LOW" in diagnosis_text:
        confidence = "LOW"

    # Extract evidence bullet points
    evidence = []
    in_evidence = False
    for line in diagnosis_text.split("\n"):
        if "Evidence" in line and ":" in line:
            in_evidence = True
            continue
        if in_evidence:
            if line.strip().startswith("-"):
                evidence.append(line.strip().lstrip("- "))
            elif line.strip() and not line.strip().startswith("-"):
                in_evidence = False

    return {
        "diagnosis": diagnosis_text,
        "evidence": evidence,
        "confidence": confidence,
    }

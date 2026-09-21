# MCPilot

**MCP-based agentic Linux diagnostic assistant** — answers natural-language questions like *"why is my laptop slow"* by having Gemini select and call typed, sandboxed tools exposed by a custom MCP server, iterating through a LangGraph state machine until it has enough evidence for a diagnosis.

> Local-only · Ubuntu · CLI · No arbitrary shell · Human-in-the-loop for mutations

---

## Architecture

```
                         USER
                           │
                           ▼
                    CLI Interface (rich)
                           │
                           ▼
                 ┌─────────────────┐
                 │    LangGraph    │
                 │ Diagnostic Agent│◄──── Gemini (function calling)
                 └────────┬────────┘
                          │
                     MCP Client (stdio)
                          │
                    MCP Protocol
                          │
                          ▼
                 ┌─────────────────┐
                 │ MCPilot Server  │  (MCPServer, subprocess-launched)
                 └────────┬────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
      System          Filesystem          Git
      /proc, psutil   POSIX APIs,       Git CLI via
      systemd,        path allow-list   controlled
      journalctl                        subprocess
```

**Layering rule**: MCP decorators call a core Linux-abstraction layer; they never contain OS logic themselves.

```
server/tools/system.py   →  server/core/linux.py    →  /proc, psutil, uname
server/tools/services.py →  server/core/systemd.py  →  systemctl, journalctl
server/tools/filesystem.py → server/core/fs.py      →  pathlib / POSIX APIs
server/tools/git.py      →  server/core/git.py      →  git CLI (controlled subprocess)
```

---

## Tool Catalogue (18 tools)

| Tool | Module | Returns | Risk |
|---|---|---|---|
| `get_system_info` | system | `SystemInfo` | READ_ONLY |
| `get_cpu_usage` | system | `CpuUsage` | READ_ONLY |
| `get_memory_usage` | system | `MemoryUsage` | READ_ONLY |
| `get_disk_usage` | system | `list[DiskUsageEntry]` | READ_ONLY |
| `list_processes` | system | `list[ProcessSummary]` | READ_ONLY |
| `get_process_info` | system | `ProcessDetail \| ToolError` | READ_ONLY |
| `get_service_status` | services | `ServiceStatus \| ToolError` | READ_ONLY |
| `get_service_logs` | services | `ServiceLogs \| ToolError` | READ_ONLY |
| `get_listening_ports` | services | `list[ListeningPort]` | READ_ONLY |
| `restart_service` | services | `ServiceStatus \| ToolError` | **APPROVAL_REQUIRED** |
| `list_directory` | filesystem | `list[DirectoryEntry] \| ToolError` | READ_ONLY |
| `get_file_metadata` | filesystem | `FileMetadata \| ToolError` | READ_ONLY |
| `search_files` | filesystem | `SearchResult \| ToolError` | READ_ONLY |
| `read_file` | filesystem | `str \| ToolError` | READ_ONLY |
| `git_status` | git | `GitStatus \| ToolError` | READ_ONLY |
| `git_diff` | git | `GitDiff \| ToolError` | READ_ONLY |
| `git_log` | git | `list[GitLogEntry] \| ToolError` | READ_ONLY |
| `run_tests` | git | `TestRunResult \| ToolError` | READ_ONLY |

There is intentionally **no** `delete_file`, `sudo_command`, or generic shell tool.

---

## Security Model

MCPilot's security story is defense-in-depth across four layers:

1. **No arbitrary shell tool** — Every capability is a specific, narrowly-scoped Python function with a fixed subprocess argument list. Never `shell=True`, never string-interpolated commands.

2. **Path restriction** — All filesystem and Git tools validate paths against an explicit allow-list (`~/Projects`, `~/Documents`). Symlink-resolved, checked with `is_relative_to()`. See `server/core/fs.py::validate_path`.

3. **Service name injection prevention** — A strict regex (`^[a-zA-Z0-9@_.\-]+$`) rejects `;`, `|`, `&`, `$`, backticks, whitespace, and path separators. See `server/core/systemd.py::validate_service_name`.

4. **Risk classification + human approval** — Every tool has a risk level (`READ_ONLY`, `APPROVAL_REQUIRED`, `DENIED`). Unknown tools default to `DENIED` (fail closed). The only mutating tool (`restart_service`) pauses for explicit `y` confirmation.

5. **Audit logging** — Every tool call is logged to `logs/audit.jsonl` with timestamp, tool, arguments, risk, approval status, and outcome.

6. **Safe subprocess runner** — All subprocess calls go through a single `run_safe()` function: always `shell=False`, always list args, always with timeout.

Full threat model: [`docs/security.md`](docs/security.md)

---

## Quick Start

```bash
# Prerequisites: Ubuntu, Python 3.12+, uv
git clone <repo-url> && cd mcpilot

# Install dependencies
uv sync

# Set Gemini API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run tests (44 tests, all layers)
PYTHONPATH="" uv run python -m pytest tests/ -v --override-ini="asyncio_mode=auto"

# Interactive mode
uv run python -m cli.main

# One-shot mode
uv run python -m cli.main "Why is my system slow?"
```

---

## Example Traces

### System Diagnosis
```
You: Why is my system slow?
[Agent] Analyzing request...
[MCP]  get_cpu_usage()
[MCP]  get_memory_usage()
[MCP]  list_processes(limit=20)
[MCP]  get_disk_usage()
[Agent] Evaluating evidence...
[Agent] Generating diagnosis...

Diagnosis: Memory pressure (92% used, 70% swap) driven by firefox.
Confidence: HIGH.
```

### Service Diagnosis
```
You: Why isn't PostgreSQL working?
[Agent] Analyzing request...
[MCP]  get_service_status(service='postgresql')
[MCP]  get_service_logs(service='postgresql')
[MCP]  get_listening_ports()
[MCP]  list_processes(limit=20)
[Agent] Evaluating evidence...
[Agent] Generating diagnosis...

Diagnosis: systemd shows failed; journal shows "address already in use";
port 5432 is held by PID <n> (<process>). Confidence: HIGH.
```

### Safety Demo
```
You: Restart PostgreSQL
[Agent] Analyzing request...

┌──────────────────────────────┐
│ MCPilot requests action      │
├──────────────────────────────┤
│ Tool: restart_service        │
│ Service: postgresql          │
│                              │
│ Reason: service action       │
│ requested by diagnostic agent│
│                              │
│ Approve? [y/N]               │
└──────────────────────────────┘
```

---

## Test Suite

| Layer | Tests | What it covers |
|---|---|---|
| Layer 1 — Core Linux | 8 | `/proc`, psutil, process info, output clamping |
| Layer 2 — MCP Protocol | 4 | 18 tools registered, schemas, descriptions |
| Layer 3 — Security | 24 | Path traversal, service injection, unknown tools, output limits |
| Layer 4 — Agent | 8 | Policies, iteration cap, approval rejection, state integrity |
| **Total** | **44** | |

---

## Confidence Labels

Confidence is a discrete, explainable label — not a calibrated statistical score:

- **HIGH**: ≥3 independent observations point to the same cause
- **MEDIUM**: Some supporting evidence, but a confirming observation is missing
- **LOW**: Evidence is thin, iteration cap was hit, or observations conflict

---

## Project Structure

```
mcpilot/
├── server/
│   ├── main.py                 # MCPServer app, registers all 18 tools
│   ├── tools/                  # MCP tool wrappers (thin, no OS logic)
│   │   ├── system.py           # 6 system tools
│   │   ├── services.py         # 4 service tools (incl. restart_service)
│   │   ├── filesystem.py       # 4 filesystem tools
│   │   └── git.py              # 4 git tools
│   ├── core/                   # Linux abstraction layer
│   │   ├── linux.py            # /proc + psutil parsing
│   │   ├── systemd.py          # systemctl/journalctl wrappers
│   │   ├── fs.py               # path validation + file ops
│   │   ├── git.py              # git subprocess wrappers
│   │   └── command.py          # shared safe-subprocess runner
│   ├── policies.py             # risk classification map
│   ├── schemas.py              # all Pydantic models
│   └── audit.py                # JSONL audit logger
├── client/
│   └── mcp_client.py           # MCP stdio client
├── agent/
│   ├── state.py                # DiagnosticState TypedDict
│   ├── graph.py                # LangGraph wiring
│   ├── nodes.py                # 4 LangGraph nodes
│   ├── prompts.py              # LLM prompt templates
│   └── tool_adapter.py         # MCP → Gemini function declarations
├── cli/
│   └── main.py                 # CLI entrypoint, rich output, approval UI
├── tests/                      # 44 tests across 4 layers
│   ├── server/                 # Layer 1+2 tests
│   ├── agent/                  # Layer 4 tests
│   └── security/               # Layer 3 tests (interview demo suite)
├── docs/                       # Architecture, security, MCP docs
├── examples/                   # Captured diagnostic transcripts
└── logs/                       # audit.jsonl (gitignored)
```

---



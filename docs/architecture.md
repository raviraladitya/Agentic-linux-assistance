# MCPilot Architecture

MCPilot is designed with a clear separation of concerns, dividing the system into four main layers: the UI/CLI, the orchestrating Agent, the MCP Protocol transport, and the local MCP Server (which itself is strictly layered).

## High-Level Diagram

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

## 1. CLI Layer (`cli/`)
The CLI provides the user interface using `rich` for formatted output. It handles two modes:
- **Interactive Mode**: A REPL loop for continuous interaction.
- **One-shot Mode**: Accepts a query as a command-line argument and exits after diagnosis.
It also provides the callback for human-in-the-loop approvals, halting execution and prompting the user before the agent can invoke any mutating tools.

## 2. Agent Layer (`agent/`)
The Agent orchestrates the diagnostic process using LangGraph and Gemini.
- **State Machine**: LangGraph manages a typed state dictionary (`DiagnosticState`) that tracks the query, observed evidence, called tools, iteration count, and the final diagnosis.
- **Graph Nodes**:
  1. `analyze_request`: Prompts Gemini to determine which tools to call next based on the query and current observations. Converts Gemini function calls into MCP tool execution plans.
  2. `execute_tools`: The execution engine. It checks the security policy (Risk level) for each tool, requests human approval if required, invokes the MCP client to run the tool, and audit-logs the outcome.
  3. `evaluate_evidence`: Asks Gemini to assess if the gathered evidence is sufficient to make a confident diagnosis, returning a structured JSON response. Implements a hard iteration cap to prevent infinite loops.
  4. `generate_diagnosis`: Prompts Gemini to synthesize the final diagnosis, strictly grounding its response in the quantitative facts observed during tool execution.

## 3. Protocol Layer (`client/` and `server/main.py`)
Uses the Model Context Protocol (MCP) to decouple the agent from the execution environment.
- **Transport**: Standard I/O (stdio). The LangGraph agent process spawns the MCPilot Server as a local subprocess. There are no exposed network ports.
- **Schemas**: The tool definitions, input parameters, and return types are strongly typed using Pydantic. These schemas are serialized into JSON Schema and passed to Gemini as function declarations.

## 4. Server Core Layer (`server/core/`)
This is where the actual system inspection happens. The MCP server decorators merely wrap these core functions.
- **Strict Layering**: `server/tools/*.py` files do not contain parsing or OS logic. They delegate to `server/core/*.py`.
- **System (`linux.py`)**: Reads `/proc` and uses `psutil` to gather system resource metrics.
- **Services (`systemd.py`)**: Wraps `systemctl` and `journalctl` to inspect systemd services. Includes the sole mutating action (`restart_service`).
- **Filesystem (`fs.py`)**: Uses POSIX APIs and `pathlib` for file inspection. Enforces strict path allow-listing.
- **Git (`git.py`)**: Wraps the `git` CLI for repository inspection and runs test suites using `pytest`.
- **Safe Execution (`command.py`)**: A shared, strictly-controlled subprocess runner that executes fixed argument lists without `shell=True`.

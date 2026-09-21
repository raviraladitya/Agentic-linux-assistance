# Model Context Protocol (MCP) in MCPilot

MCPilot utilizes the Model Context Protocol (MCP) to standardize how the LangGraph agent discovers and interacts with diagnostic tools. By adhering to MCP, the system guarantees a clean separation between the reasoning engine (Gemini) and the execution environment (Ubuntu Linux).

## The Flow

The interaction between the client (the LangGraph agent process) and the server (the `MCPServer` subprocess) follows three primary steps: `initialize`, `tools/list`, and `tools/call`.

### 1. Initialization (`initialize`)
When MCPilot starts, the LangGraph process spawns the MCP server using `stdio` transport.
```python
# client/mcp_client.py
params = StdioServerParameters(command="uv", args=["run", "python", "server/main.py"])
self._stdio_ctx = stdio_client(params)
read, write = await self._stdio_ctx.__aenter__()
self.session = ClientSession(read, write)
await self.session.initialize()
```
The server and client exchange protocol versions and capabilities over standard input/output, establishing a session.

### 2. Discovery (`tools/list`)
Before processing a query, the agent must know what tools are available.
```python
# client/mcp_client.py
result = await self.session.list_tools()
```
The server responds with a list of all registered tools, their descriptions, and their Pydantic-derived JSON Schemas. 

For example, the server describes `get_memory_usage`:
```json
{
  "name": "get_memory_usage",
  "description": "Returns current system memory and swap utilization as percentages and GB.\n\nUse this when investigating high memory usage, swapping, or general system\nslowdown. Does not modify system state.",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```
`agent/tool_adapter.py` translates these MCP tool definitions into `google.genai.types.FunctionDeclaration` objects, allowing Gemini to "see" them as callable functions.

### 3. Execution (`tools/call`)
When Gemini decides a tool is needed, it returns a function call. The LangGraph agent intercepts this, checks its security policy, and dispatches the call to the MCP server.

```python
# client/mcp_client.py
result = await self.session.call_tool("get_memory_usage", {})
```

The MCP server routes the request to the decorated function:
```python
# server/main.py
@mcp.tool()
def get_memory_usage() -> MemoryUsage:
    return system.get_memory_usage()
```

The server executes the core Linux abstraction layer code and returns the Pydantic-validated data back over stdio to the client. The client then formats this structured JSON observation and passes it back to Gemini for the next iteration of the diagnostic loop.

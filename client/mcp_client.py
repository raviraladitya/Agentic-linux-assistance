"""
MCPilot — MCP Client.

Connects to the MCPilot server via stdio transport (the server is launched
as a subprocess of the agent process — no networked deployment).
"""

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPilotClient:
    """MCP client that connects to the MCPilot server via stdio."""

    def __init__(self):
        self._stdio_ctx = None
        self.session: ClientSession | None = None

    async def connect(self):
        """Connect to the MCP server subprocess."""
        params = StdioServerParameters(
            command="uv",
            args=["run", "python", "server/main.py"],
        )
        self._stdio_ctx = stdio_client(params)
        read, write = await self._stdio_ctx.__aenter__()
        self.session = ClientSession(read, write)
        await self.session.__aenter__()
        await self.session.initialize()

    async def list_tools(self):
        """List all available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected — call connect() first")
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict):
        """Call a tool on the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected — call connect() first")
        return await self.session.call_tool(name, arguments)

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._stdio_ctx:
            await self._stdio_ctx.__aexit__(None, None, None)

"""
MCPilot — Tool adapter.

Converts MCP tool schemas into Gemini function declarations, so Gemini
can "see" the MCP tools as callable functions without hand-writing 18
separate function declarations.
"""

from google.genai import types


def mcp_tools_to_gemini_declarations(mcp_tools: list) -> list[types.FunctionDeclaration]:
    """
    Convert MCP tool list (from list_tools()) into Gemini function declarations.

    Each MCP tool has: name, description, inputSchema (JSON Schema).
    We convert these into google.genai FunctionDeclaration objects.
    """
    declarations = []

    for tool in mcp_tools:
        # Extract the JSON schema properties
        input_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else {}

        # Build Gemini-compatible schema
        properties = {}
        required = input_schema.get("required", [])

        for prop_name, prop_schema in input_schema.get("properties", {}).items():
            prop_type = prop_schema.get("type", "string")

            # Map JSON Schema types to Gemini types
            type_map = {
                "string": "STRING",
                "integer": "INTEGER",
                "number": "NUMBER",
                "boolean": "BOOLEAN",
                "array": "ARRAY",
                "object": "OBJECT",
            }

            gemini_type = type_map.get(prop_type, "STRING")

            prop_def = {
                "type": gemini_type,
            }
            if "description" in prop_schema:
                prop_def["description"] = prop_schema["description"]
            if "default" in prop_schema:
                prop_def["description"] = prop_def.get("description", "") + f" (default: {prop_schema['default']})"

            properties[prop_name] = prop_def

        # Build the function declaration
        parameters = None
        if properties:
            parameters = types.Schema(
                type="OBJECT",
                properties={
                    k: types.Schema(type=v["type"], description=v.get("description"))
                    for k, v in properties.items()
                },
                required=required if required else None,
            )

        declaration = types.FunctionDeclaration(
            name=tool.name,
            description=tool.description or f"Tool: {tool.name}",
            parameters=parameters,
        )
        declarations.append(declaration)

    return declarations


def build_gemini_tools(mcp_tools: list) -> list[types.Tool]:
    """Build Gemini Tool objects from MCP tool list."""
    declarations = mcp_tools_to_gemini_declarations(mcp_tools)
    return [types.Tool(function_declarations=declarations)]

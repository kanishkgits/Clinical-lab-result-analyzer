from mcp import Client


class MCPAgentClient:
    def __init__(self, server_url: str):
        self.server_url = server_url

    async def call(self, tool_name: str, arguments: dict):
        async with Client(self.server_url) as client:
            result = await client.call_tool(tool_name, arguments)
            if getattr(result, "is_error", False):
                raise RuntimeError(f"MCP tool {tool_name} failed")
            structured = getattr(result, "structured_content", None)
            if structured:
                return structured
            content = getattr(result, "content", [])
            if content and hasattr(content[0], "text"):
                import json
                return json.loads(content[0].text)
            raise RuntimeError(f"MCP tool {tool_name} returned no readable data")

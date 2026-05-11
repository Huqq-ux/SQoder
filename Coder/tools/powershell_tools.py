import os

from Coder.util.mcp import create_mcp_stdio_client

_MCP_SERVER_SCRIPT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "MCP", "powershell_tools.py")
)


async def get_powershell_stdio_tools():
    params = {
        "command": "python",
        "args": [_MCP_SERVER_SCRIPT],
    }

    client, tools = await create_mcp_stdio_client("powershell_tools", params)
    return client, tools

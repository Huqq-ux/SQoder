import os

from Coder.util.mcp import create_mcp_stdio_client

_MCP_SHELL_TOOLS_SCRIPT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "MCP", "shell_tools.py")
)


async def get_stdio_tools():
    params = {
        "command": "python",
        "args": [_MCP_SHELL_TOOLS_SCRIPT],
    }

    client, tools = await create_mcp_stdio_client("shell_tools", params)
    return client, tools

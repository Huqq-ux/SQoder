from Coder.util.mcp import create_mcp_stdio_client


async def get_stdio_tools():
    params = {
        "command": "python",
        "args": [
            "D:/PyCharm/AI/Coder/MCP/shell_tools.py",
        ],
    }

    client,tools = await create_mcp_stdio_client("shell_tools",params)
    return tools

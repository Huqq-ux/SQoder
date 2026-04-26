from langchain_mcp_adapters.client import MultiServerMCPClient

async def create_mcp_stdio_client(name: str,params):
    config = {
        name : {
            "transport": "stdio",
            **params,
        }
    }
    client = MultiServerMCPClient(config)
    tools = await client.get_tools()
    return client,tools
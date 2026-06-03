import logging

from langchain_core.tools import BaseTool

from Coder.storage.redis_client import RedisManager

logger = logging.getLogger(__name__)

CONFIRM_TIMEOUT = 60


class SSEToolConfirmer:
    def __init__(self, session_id: str):
        self._session_id = session_id

    @staticmethod
    def _is_remote_tool(tool: BaseTool) -> bool:
        return hasattr(tool, "metadata") and tool.metadata.get("mcp_transport") == "sse"

    def wrap_tools(self, tools: list[BaseTool]) -> list[BaseTool]:
        wrapped = []
        for tool in tools:
            if self._is_remote_tool(tool):
                wrapped.append(self._wrap_tool(tool))
            else:
                wrapped.append(tool)
        return wrapped

    def _wrap_tool(self, tool: BaseTool) -> BaseTool:
        original_func = tool.func
        session_id = self._session_id

        async def confirmed_func(*args, **kwargs):
            tool_name = tool.name
            allow_key = f"mcp:confirm:{session_id}:{tool_name}"

            try:
                allowed = await RedisManager.get_json(allow_key)
                if allowed and allowed.get("status") == "allow_session":
                    return await original_func(*args, **kwargs)
            except Exception:
                pass

            await RedisManager.set_json(
                f"mcp:pending:{session_id}:{tool_name}",
                {"status": "waiting"},
                ttl=CONFIRM_TIMEOUT,
            )
            return f"[MCP_CONFIRM_REQUIRED] Tool '{tool_name}' requires confirmation. Session: {session_id}"

        tool.func = confirmed_func
        return tool

    @staticmethod
    async def allow_once(session_id: str, tool_name: str) -> None:
        await RedisManager.set_json(
            f"mcp:confirm:{session_id}:{tool_name}",
            {"status": "allow_once"},
            ttl=CONFIRM_TIMEOUT,
        )

    @staticmethod
    async def allow_session(session_id: str, tool_name: str) -> None:
        await RedisManager.set_json(
            f"mcp:confirm:{session_id}:{tool_name}",
            {"status": "allow_session"},
            ttl=86400,
        )

    @staticmethod
    async def deny(session_id: str, tool_name: str) -> None:
        await RedisManager.set_json(
            f"mcp:confirm:{session_id}:{tool_name}",
            {"status": "denied"},
            ttl=CONFIRM_TIMEOUT,
        )

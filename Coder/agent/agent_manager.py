import asyncio
import logging
from typing import Optional

from Coder.MCP.manager import MCPManager

logger = logging.getLogger(__name__)


class AgentManager:
    """管理 Agent 生命周期，检测 MCP 工具变更时自动热加载"""

    def __init__(self, mcp_manager: MCPManager):
        self._mcp_manager = mcp_manager
        self._agent = None
        self._config = None
        self._fingerprint: Optional[str] = None
        self._lock = asyncio.Lock()

    async def get_agent(self, thread_id: str):
        """返回 (agent, config)，工具变更时自动重建"""
        fingerprint = self._mcp_manager.get_tools_fingerprint()

        if self._fingerprint != fingerprint:
            async with self._lock:
                if self._fingerprint != fingerprint:
                    logger.info("MCP 工具变更，重建 Agent...")
                    await self._rebuild(thread_id)
                    self._fingerprint = fingerprint
                    logger.info(f"Agent 已重建，当前工具指纹: {fingerprint}")

        return self._agent, self._config

    async def _rebuild(self, thread_id: str):
        from Coder.agent.code_agent import create_code_agent

        self._agent, self._config = await create_code_agent(
            thread_id=thread_id,
            mcp_manager=self._mcp_manager,
        )

    async def close(self):
        self._agent = None
        self._config = None

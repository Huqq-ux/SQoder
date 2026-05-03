import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

from Coder.multi_agent.types import AgentConfig, AgentRole
from Coder.tools.file_saver import FileSaver

logger = logging.getLogger(__name__)


class AgentBuilder:

    def __init__(self, base_tools: List[BaseTool] = None):
        self._base_tools = base_tools or []
        self._checkpointer = FileSaver()

    @property
    def checkpointer(self) -> FileSaver:
        return self._checkpointer

    def build_agent(
        self,
        agent_config: AgentConfig,
        model: BaseChatModel = None,
        extra_tools: List[BaseTool] = None,
    ):
        from Coder.multi_agent.integrations import (
            resolve_agent_model,
            get_skill_tools,
            get_sop_tools,
        )

        if model is None:
            model = resolve_agent_model(agent_config)

        tools = list(self._base_tools)

        if agent_config.role == AgentRole.SKILL_EXECUTOR:
            try:
                tools.extend(get_skill_tools())
            except Exception as e:
                logger.warning(f"加载 Skill 工具失败: {e}")

        if agent_config.role == AgentRole.SOP_EXECUTOR:
            try:
                tools.extend(get_sop_tools())
            except Exception as e:
                logger.warning(f"加载 SOP 工具失败: {e}")

        if agent_config.role in (
            AgentRole.SEARCHER, AgentRole.CODER, AgentRole.SUPERVISOR
        ):
            try:
                tools.append(_get_context_tool())
            except Exception as e:
                logger.warning(f"加载上下文工具失败: {e}")

        if extra_tools:
            tools.extend(extra_tools)

        agent = create_agent(
            model=model,
            tools=tools or None,
            system_prompt=agent_config.system_prompt,
            checkpointer=self._checkpointer,
            debug=False,
        )
        return agent

    def build_with_config(
        self,
        agent_config: AgentConfig,
        model: BaseChatModel = None,
        extra_tools: List[BaseTool] = None,
    ) -> Tuple[Any, RunnableConfig]:
        agent = self.build_agent(agent_config, model, extra_tools)
        config = RunnableConfig(
            configurable={"thread_id": f"agent_{agent_config.name}"}
        )
        return agent, config


def _get_context_tool() -> BaseTool:
    from langchain_core.tools import tool

    @tool
    def get_agent_context() -> str:
        """获取当前Agent的团队上下文信息"""
        try:
            from Coder.multi_agent.registry import agent_registry
            stats = agent_registry.get_all_statistics()
            if not stats:
                return "当前没有其他 Agent 在线"
            lines = ["当前团队 Agent 状态:"]
            for s in stats:
                lines.append(
                    f"- {s['name']} ({s['role']}): "
                    f"{s['status']}, 成功率: {s['success_rate']:.0%}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"获取上下文失败: {e}"

    return get_agent_context

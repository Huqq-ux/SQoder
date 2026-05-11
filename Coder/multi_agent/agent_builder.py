import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

from Coder.multi_agent.types import AgentConfig, AgentRole

logger = logging.getLogger(__name__)


def _resolve_checkpointer():
    return MemorySaver()


class AgentBuilder:

    def __init__(self, base_tools: List[BaseTool] = None):
        self._base_tools = base_tools or []
        self._checkpointer = _resolve_checkpointer()

    @property
    def checkpointer(self):
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

        tools.extend(_resolve_tool_names(agent_config.tools))

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
        run_id: str = "",
    ) -> Tuple[Any, RunnableConfig]:
        agent = self.build_agent(agent_config, model, extra_tools)
        thread_id = f"agent_{agent_config.name}"
        if run_id:
            thread_id = f"{thread_id}_{run_id}"
        config = RunnableConfig(
            configurable={"thread_id": thread_id}
        )
        return agent, config


_TOOL_REGISTRY: Dict[str, BaseTool] = {}


def _resolve_tool_names(tool_names: List[str]) -> List[BaseTool]:
    if not tool_names:
        return []

    tools: List[BaseTool] = []
    for name in tool_names:
        if not isinstance(name, str):
            if isinstance(name, BaseTool):
                tools.append(name)
            continue

        if name in _TOOL_REGISTRY:
            tools.extend(_TOOL_REGISTRY[name])
            continue

        resolved = _lookup_toolkit(name)
        if resolved:
            _TOOL_REGISTRY[name] = resolved
            tools.extend(resolved)
        else:
            logger.warning(f"无法解析工具名称: {name}")

    return tools


def _lookup_toolkit(name: str) -> Optional[List[BaseTool]]:
    from langchain_core.tools import StructuredTool
    import functools

    if name == "web_search_toolkit":
        try:
            from Coder.tools.web_search_toolkit import web_search_toolkit
            return _wrap_toolkit(web_search_toolkit)
        except Exception as e:
            logger.warning(f"加载 web_search_toolkit 失败: {e}")

    if name == "knowledge_toolkit":
        try:
            from Coder.tools.knowledge_toolkit import knowledge_toolkit
            return _wrap_toolkit(knowledge_toolkit)
        except Exception as e:
            logger.warning(f"加载 knowledge_toolkit 失败: {e}")

    if name == "file_tools":
        try:
            from Coder.tools.file_tools import file_management_toolkit
            return _wrap_toolkit(file_management_toolkit)
        except Exception as e:
            logger.warning(f"加载 file_tools 失败: {e}")

    return None


def _wrap_toolkit(toolkit) -> List[BaseTool]:
    if isinstance(toolkit, list):
        return toolkit

    if callable(toolkit) and not isinstance(toolkit, BaseTool):
        try:
            result = toolkit()
            if isinstance(result, list):
                return result
            if isinstance(result, BaseTool):
                return [result]
        except Exception:
            pass

    if isinstance(toolkit, BaseTool):
        return [toolkit]

    logger.warning(f"无法处理的工具包类型: {type(toolkit)}")
    return []


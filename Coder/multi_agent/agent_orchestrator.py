import asyncio
import time
import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool as langchain_tool
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from Coder.multi_agent.agent_builder import _resolve_tool_names
from Coder.multi_agent.integrations import (
    build_system_prompt_for_role,
    get_skill_tools,
    get_sop_tools,
)
from Coder.multi_agent.types import AgentRole

logger = logging.getLogger(__name__)

_ORCHESTRATOR_SYSTEM_PROMPT = """你是一个智能任务协调者。你可以按需调用以下专家:

- run_coder: 编程专家,负责代码生成、调试、重构、算法实现等
- run_searcher: 搜索专家,负责信息检索、文档查询、知识库搜索等
- run_ops: 运维专家,负责部署、配置、故障排查等
- run_skill_executor: 技能执行器,调用已注册的技能
- run_sop_executor: SOP执行器,按标准流程执行任务

工作方式:
1. 分析用户需求
2. 按合理顺序调用需要的专家(先搜索再编码等)
3. 整合各专家结果,输出简洁完整的回答

回答要求（非常重要）:
- 直接输出最终答案，不要展示"任务分析"、"子任务分配"等过程
- 代码类问题：直接给出代码和一句话说明
- 搜索类问题：只输出关键结论，不要列出信息来源/URL
- 多步骤任务：整合为一个连贯回答，不要分段重复
- 总原则：简洁 > 完整，宁可少写不要多写"""


def _extract_content(response) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        messages = response.get("messages", [])
        parts = []
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = msg.content
                if content and isinstance(content, str):
                    tc = getattr(msg, "tool_calls", None)
                    ak = getattr(msg, "additional_kwargs", {}) if hasattr(msg, "additional_kwargs") else {}
                    if not tc and not ak.get("tool_calls"):
                        parts.append(content)
            elif hasattr(msg, "content"):
                c = msg.content
                if c and isinstance(c, str):
                    parts.append(c)
        return "\n\n".join(reversed(parts)) if parts else ""
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
            return "\n".join(texts) if texts else str(content)
        return str(content)
    if isinstance(response, list):
        return _extract_content({"messages": response})
    return str(response)


def _resolve_sub_tools(role: AgentRole) -> list:
    mapping = {
        AgentRole.CODER: ["file_tools", "knowledge_toolkit"],
        AgentRole.SEARCHER: ["web_search_toolkit", "knowledge_toolkit"],
        AgentRole.OPS: ["file_tools"],
    }
    tool_names = mapping.get(role, [])
    tools = _resolve_tool_names(tool_names)

    if role == AgentRole.SKILL_EXECUTOR:
        try:
            tools.extend(get_skill_tools())
        except Exception as e:
            logger.warning(f"加载 Skill 工具失败: {e}")
    if role == AgentRole.SOP_EXECUTOR:
        try:
            tools.extend(get_sop_tools())
        except Exception as e:
            logger.warning(f"加载 SOP 工具失败: {e}")

    return tools


def _make_coder_tool(model):
    tools = _resolve_sub_tools(AgentRole.CODER)
    agent = create_agent(
        model=model,
        tools=tools or None,
        system_prompt=build_system_prompt_for_role(AgentRole.CODER),
        checkpointer=MemorySaver(),
    )

    @langchain_tool
    async def run_coder(task_description: str) -> str:
        """编程专家。当需要编写、调试、重构代码、实现算法时调用此工具。参数为任务描述。"""
        try:
            resp = await agent.ainvoke(
                {"messages": [HumanMessage(content=task_description)]},
                config=RunnableConfig(configurable={"thread_id": f"c_{time.time_ns()}"}),
            )
            return _extract_content(resp)
        except Exception as e:
            return f"编程专家出错: {e}"

    return run_coder


def _make_searcher_tool(model):
    tools = _resolve_sub_tools(AgentRole.SEARCHER)
    agent = create_agent(
        model=model,
        tools=tools or None,
        system_prompt=build_system_prompt_for_role(AgentRole.SEARCHER),
        checkpointer=MemorySaver(),
    )

    @langchain_tool
    async def run_searcher(query: str) -> str:
        """搜索信息专家。当需要查资料、搜索文档、检索知识时调用此工具。参数为搜索查询。"""
        try:
            resp = await agent.ainvoke(
                {"messages": [HumanMessage(content=query)]},
                config=RunnableConfig(configurable={"thread_id": f"s_{time.time_ns()}"}),
            )
            return _extract_content(resp)
        except Exception as e:
            return f"搜索专家出错: {e}"

    return run_searcher


def _make_ops_tool(model):
    tools = _resolve_sub_tools(AgentRole.OPS)
    agent = create_agent(
        model=model,
        tools=tools or None,
        system_prompt=build_system_prompt_for_role(AgentRole.OPS),
        checkpointer=MemorySaver(),
    )

    @langchain_tool
    async def run_ops(task_description: str) -> str:
        """运维专家。当需要部署、配置、故障排查时调用此工具。参数为任务描述。"""
        try:
            resp = await agent.ainvoke(
                {"messages": [HumanMessage(content=task_description)]},
                config=RunnableConfig(configurable={"thread_id": f"o_{time.time_ns()}"}),
            )
            return _extract_content(resp)
        except Exception as e:
            return f"运维专家出错: {e}"

    return run_ops


def _make_skill_executor_tool(model):
    tools = _resolve_sub_tools(AgentRole.SKILL_EXECUTOR)
    if not tools:
        return None
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt_for_role(AgentRole.SKILL_EXECUTOR),
        checkpointer=MemorySaver(),
    )

    @langchain_tool
    async def run_skill_executor(skill_request: str) -> str:
        """技能执行器。当用户需要调用某个已注册技能时使用。参数为技能名称和参数。"""
        try:
            resp = await agent.ainvoke(
                {"messages": [HumanMessage(content=skill_request)]},
                config=RunnableConfig(configurable={"thread_id": f"sk_{time.time_ns()}"}),
            )
            return _extract_content(resp)
        except Exception as e:
            return f"技能执行器出错: {e}"

    return run_skill_executor


def _make_sop_executor_tool(model):
    tools = _resolve_sub_tools(AgentRole.SOP_EXECUTOR)
    if not tools:
        return None
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt_for_role(AgentRole.SOP_EXECUTOR),
        checkpointer=MemorySaver(),
    )

    @langchain_tool
    async def run_sop_executor(sop_request: str) -> str:
        """SOP执行器。当用户需要按标准操作流程执行任务时使用。参数为SOP名称和上下文。"""
        try:
            resp = await agent.ainvoke(
                {"messages": [HumanMessage(content=sop_request)]},
                config=RunnableConfig(configurable={"thread_id": f"sp_{time.time_ns()}"}),
            )
            return _extract_content(resp)
        except Exception as e:
            return f"SOP执行器出错: {e}"

    return run_sop_executor


class AgentOrchestrator:

    def __init__(self, timeout: float = 300.0):
        self._timeout = timeout

    def _get_model(self):
        from Coder.model import llm as default_llm
        return default_llm

    async def run(self, user_input: str) -> Dict[str, Any]:
        start_time = time.time()
        model = self._get_model()

        tools: List = []
        try:
            tools.append(_make_coder_tool(model))
        except Exception as e:
            logger.warning(f"创建 coder tool 失败: {e}")
        try:
            tools.append(_make_searcher_tool(model))
        except Exception as e:
            logger.warning(f"创建 searcher tool 失败: {e}")
        try:
            tools.append(_make_ops_tool(model))
        except Exception as e:
            logger.warning(f"创建 ops tool 失败: {e}")
        try:
            skill_tool = _make_skill_executor_tool(model)
            if skill_tool:
                tools.append(skill_tool)
        except Exception as e:
            logger.warning(f"创建 skill_executor tool 失败: {e}")
        try:
            sop_tool = _make_sop_executor_tool(model)
            if sop_tool:
                tools.append(sop_tool)
        except Exception as e:
            logger.warning(f"创建 sop_executor tool 失败: {e}")

        orchestrator = create_agent(
            model=model,
            tools=tools,
            system_prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )

        try:
            response = await asyncio.wait_for(
                orchestrator.ainvoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=RunnableConfig(
                        configurable={"thread_id": f"orch_{time.time_ns()}"}
                    ),
                ),
                timeout=self._timeout,
            )
            answer = _extract_content(response)
            return {
                "success": True,
                "answer": answer,
                "error": None,
                "duration_seconds": time.time() - start_time,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "answer": "",
                "error": f"执行超时 ({self._timeout}s)",
                "duration_seconds": time.time() - start_time,
            }
        except Exception as e:
            logger.error(f"Orchestrator 失败: {e}")
            return {
                "success": False,
                "answer": "",
                "error": str(e),
                "duration_seconds": time.time() - start_time,
            }

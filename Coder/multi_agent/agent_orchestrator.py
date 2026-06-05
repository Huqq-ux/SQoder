import asyncio
import time
import logging
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool as langchain_tool
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS
from Coder.multi_agent.agent_builder import AgentBuilder
from Coder.multi_agent.types import AgentRole, AgentConfig

logger = logging.getLogger(__name__)

_ORCHESTRATOR_SYSTEM_PROMPT = f"""你是一个智能任务协调者。你可以按需调用以下专家:

- run_coder: 编程专家,负责代码生成、调试、重构、算法实现等
- run_searcher: 搜索专家,负责信息检索、文档查询、知识库搜索等
- run_ops: 运维专家,负责部署、配置、故障排查等
- run_skill_executor: 技能执行器,调用已注册的技能

工作方式:
1. 分析用户需求
2. 按合理顺序调用需要的专家(先搜索再编码等)
3. 整合各专家结果,输出简洁完整的回答

回答要求（非常重要）:
- 直接输出最终答案，不要展示"任务分析"、"子任务分配"等过程
- 代码类问题：直接给出代码和一句话说明
- 搜索类问题：只输出关键结论，不要列出信息来源/URL
- 多步骤任务：整合为一个连贯回答，不要分段重复
- 总原则：简洁 > 完整，宁可少写不要多写
当前日期: {datetime.now().strftime('%Y年%m月%d日')}"""


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


class AgentOrchestrator:

    def __init__(self, agent_configs: Dict[AgentRole, AgentConfig] = None, timeout: float = 300.0):
        self._configs = agent_configs or DEFAULT_AGENT_CONFIGS
        self._timeout = timeout
        self._builder = AgentBuilder()
        self._tool_call_log: List[Dict[str, Any]] = []

    def _get_model(self):
        from Coder.model import llm as default_llm
        return default_llm

    def _build_agent_tool(self, config: AgentConfig, model):
        """通用子 Agent 工厂：AgentBuilder 创建 + @langchain_tool 包装 + 独立超时。"""
        agent = self._builder.build_agent(config, model)
        agent_timeout = getattr(agent, "_agent_timeout", 120.0)
        role_name = config.display_name
        agent_name = config.name

        @langchain_tool
        async def agent_tool(task: str) -> str:
            """子Agent任务执行"""
            start = time.time()
            try:
                resp = await asyncio.wait_for(
                    agent.ainvoke(
                        {"messages": [HumanMessage(content=task)]},
                        config=RunnableConfig(configurable={
                            "thread_id": f"{agent_name}_{time.time_ns()}"
                        }),
                    ),
                    timeout=agent_timeout,
                )
                elapsed = time.time() - start
                self._tool_call_log.append({
                    "agent": agent_name,
                    "display_name": role_name,
                    "task": task[:200],
                    "duration_ms": int(elapsed * 1000),
                    "success": True,
                })
                return _extract_content(resp)
            except asyncio.TimeoutError:
                elapsed = time.time() - start
                self._tool_call_log.append({
                    "agent": agent_name,
                    "display_name": role_name,
                    "task": task[:200],
                    "duration_ms": int(elapsed * 1000),
                    "success": False,
                    "error": "超时",
                })
                return f"{role_name}执行超时 ({agent_timeout}s)"
            except Exception as e:
                elapsed = time.time() - start
                self._tool_call_log.append({
                    "agent": agent_name,
                    "display_name": role_name,
                    "task": task[:200],
                    "duration_ms": int(elapsed * 1000),
                    "success": False,
                    "error": str(e),
                })
                return f"{role_name}出错: {e}"

        # 设置 tool 的 description 和 name 以便 LLM 识别
        agent_tool.description = config.description
        agent_tool.name = f"run_{agent_name}"
        return agent_tool

    async def run(self, user_input: str) -> Dict[str, Any]:
        start_time = time.time()
        model = self._get_model()
        self._tool_call_log = []

        tools: List = []
        for config in self._configs.values():
            try:
                tool = self._build_agent_tool(config, model)
                tools.append(tool)
            except Exception as e:
                logger.warning(f"创建 {config.display_name} tool 失败: {e}")

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
                "tool_calls": self._tool_call_log,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "answer": "",
                "error": f"执行超时 ({self._timeout}s)",
                "duration_seconds": time.time() - start_time,
                "tool_calls": self._tool_call_log,
            }
        except Exception as e:
            logger.error(f"Orchestrator 失败: {e}")
            return {
                "success": False,
                "answer": "",
                "error": str(e),
                "duration_seconds": time.time() - start_time,
                "tool_calls": self._tool_call_log,
            }

    async def astream(self, user_input: str, thread_id: str = None):
        """流式执行编排，yield SSE 兼容事件字典。

        事件类型：agent_start | tool_call | tool_result | content | done | error
        """
        import uuid

        model = self._get_model()
        self._tool_call_log = []
        thread_id = thread_id or f"orch_{uuid.uuid4().hex[:12]}"

        yield {"type": "agent_start", "content": "多智能体任务开始"}

        tools: List = []
        for config in self._configs.values():
            try:
                tool = self._build_agent_tool(config, model)
                tools.append(tool)
            except Exception as e:
                yield {"type": "error", "content": f"子Agent {config.display_name} 创建失败: {e}"}
                return

        orchestrator = create_agent(
            model=model,
            tools=tools,
            system_prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )

        try:
            async for event in orchestrator.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                config=RunnableConfig(configurable={"thread_id": thread_id}),
                version="v2",
            ):
                kind = event.get("event")
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event["data"].get("input", {})
                    yield {
                        "type": "tool_call",
                        "name": tool_name,
                        "args": tool_input if isinstance(tool_input, dict) else {"task": str(tool_input)},
                    }
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = str(event["data"].get("output", ""))[:2000]
                    yield {
                        "type": "tool_result",
                        "name": tool_name,
                        "content": output,
                    }
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, str) and content:
                            yield {"type": "content", "content": content}
        except asyncio.TimeoutError:
            yield {"type": "error", "content": f"执行超时 ({self._timeout}s)"}
        except Exception as e:
            logger.error(f"Orchestrator 流式执行失败: {e}")
            yield {"type": "error", "content": str(e)}

        yield {"type": "done"}

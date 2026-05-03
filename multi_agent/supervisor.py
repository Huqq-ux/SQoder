import time
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage

from Coder.multi_agent.types import (
    AgentRole,
    AgentConfig,
    AgentStatus,
    CrewTask,
    CrewTaskStatus,
    CrewResult,
    DelegateRequest,
    CommunicationMessage,
    MessageType,
    ProcessType,
)
from Coder.multi_agent.registry import agent_registry
from Coder.multi_agent.router import task_router
from Coder.multi_agent.protocol import CommunicationProtocol
from Coder.multi_agent.integrations import (
    build_default_agent_configs,
    get_skill_tools,
    get_sop_tools,
)
from Coder.multi_agent.agent_builder import AgentBuilder

logger = logging.getLogger(__name__)


class SupervisorAgent:

    def __init__(
        self,
        agent_builder: AgentBuilder = None,
        protocol: CommunicationProtocol = None,
    ):
        self._builder = agent_builder or AgentBuilder()
        self._protocol = protocol or CommunicationProtocol()
        self._agent_cache: Dict[str, Any] = {}
        self._config_cache: Dict[str, Any] = {}
        self._current_run_id: str = ""
        self._execution_log: List[str] = []

    @property
    def protocol(self) -> CommunicationProtocol:
        return self._protocol

    @property
    def builder(self) -> AgentBuilder:
        return self._builder

    def initialize_default_agents(self) -> int:
        configs = build_default_agent_configs()
        count = 0
        for config in configs:
            if agent_registry.get(config.name) is None:
                agent_registry.register(config)
                count += 1
        logger.info(f"已注册 {count} 个默认 Agent")
        return count

    def get_or_create_agent(
        self, agent_config: AgentConfig
    ) -> Tuple[Any, Any]:
        name = agent_config.name
        if name in self._agent_cache:
            return self._agent_cache[name], self._config_cache[name]

        agent, config = self._builder.build_with_config(agent_config)
        self._agent_cache[name] = agent
        self._config_cache[name] = config
        return agent, config

    def clear_agent_cache(self):
        self._agent_cache.clear()
        self._config_cache.clear()

    def execute_agent(
        self,
        agent_name: str,
        task: CrewTask,
        context_messages: List = None,
        timeout: float = 120.0,
    ) -> Tuple[Any, str]:
        agent_info = agent_registry.get(agent_name)
        if not agent_info:
            return None, f"Agent '{agent_name}' 未注册"

        cached = self._agent_cache.get(agent_name)
        if cached is None:
            self.get_or_create_agent(agent_info.config)

        agent = self._agent_cache.get(agent_name)
        config = self._config_cache.get(agent_name)

        if agent is None or config is None:
            return None, f"Agent '{agent_name}' 构建失败"

        agent_registry.set_status(agent_name, AgentStatus.BUSY)
        agent_registry.assign_task(agent_name, task.task_id)
        task.status = CrewTaskStatus.RUNNING

        try:
            import asyncio

            messages = list(context_messages or [])
            task_prompt = (
                f"[任务]\n{task.description}\n\n"
                f"[上下文]\n任务ID: {task.task_id}\n"
                f"优先级: {task.priority}\n"
                f"{'请使用list_available_skills工具查看可用技能' if '技能' in task.description or 'skill' in task.description.lower() else ''}"
                f"{'请使用list_available_sops工具查看可用SOP' if 'SOP' in task.description or '流程' in task.description else ''}"
            )
            messages.append(HumanMessage(content=task_prompt))

            response = asyncio.run(
                self._invoke_agent(agent, messages, config, timeout)
            )

            result_text = self._extract_response_content(response)

            task.result = result_text
            task.status = CrewTaskStatus.COMPLETED
            agent_registry.evaluate_and_adjust(agent_name, task, success=True)
            agent_registry.release_task(agent_name)
            return result_text, ""

        except Exception as e:
            task.status = CrewTaskStatus.FAILED
            task.error = str(e)
            agent_registry.evaluate_and_adjust(agent_name, task, success=False)
            agent_registry.release_task(agent_name)
            logger.error(f"Agent '{agent_name}' 执行失败: {traceback.format_exc()}")
            return None, str(e)

    async def _invoke_agent(
        self,
        agent,
        messages: List,
        config,
        timeout: float,
    ):
        import asyncio
        return await asyncio.wait_for(
            agent.ainvoke({"messages": messages}, config=config),
            timeout=timeout,
        )

    @staticmethod
    def _extract_response_content(response) -> str:
        if response is None:
            return ""

        if isinstance(response, dict):
            messages = response.get("messages", [])
            content_parts = []
            for msg in messages:
                content = getattr(msg, "content", None)
                if content and isinstance(content, str) and content.strip():
                    tool_calls = getattr(msg, "tool_calls", None)
                    additional = getattr(msg, "additional_kwargs", {})
                    has_tool_calls = tool_calls or additional.get("tool_calls")
                    if not has_tool_calls:
                        content_parts.append(content)
            return "\n\n".join(content_parts) if content_parts else ""

        if hasattr(response, "content"):
            content = response.content
            return content if isinstance(content, str) else str(content)

        if isinstance(response, str):
            return response

        if isinstance(response, list):
            return SupervisorAgent._extract_response_content(
                {"messages": response}
            )

        return str(response) if response else ""

    def execute_sequential(
        self,
        tasks: List[CrewTask],
        context: Dict[str, Any] = None,
    ) -> CrewResult:
        context = context or {}
        start_time = time.time()
        sub_results = []
        agent_traces = []
        all_success = True
        error_msg = ""

        for i, task in enumerate(tasks):
            self._log(f"执行子任务 [{i + 1}/{len(tasks)}]: {task.description[:80]}...")

            assigned = task_router.assign_task(task)
            if not assigned:
                self._log(f"❌ 无法分配任务 {task.task_id}")
                task.status = CrewTaskStatus.FAILED
                task.error = "无可用 Agent"
                all_success = False
                error_msg += f"[{task.task_id}] 无可用Agent; "
                sub_results.append({
                    "task_id": task.task_id,
                    "description": task.description[:200],
                    "status": "failed",
                    "result": None,
                    "error": "无可用 Agent",
                    "agent": "",
                })
                continue

            result_text, error = self.execute_agent(
                assigned, task, timeout=120.0
            )

            agent_traces.append(f"[{assigned}] → {task.task_id}")
            sub_results.append({
                "task_id": task.task_id,
                "description": task.description[:200],
                "status": task.status.value,
                "result": result_text,
                "error": error,
                "agent": assigned,
            })

            if task.status != CrewTaskStatus.COMPLETED:
                all_success = False
                error_msg += f"[{task.task_id}] {error}; "

        duration = time.time() - start_time

        return CrewResult(
            success=all_success,
            task_id="sequential_result",
            result={
                "sub_results": sub_results,
                "total": len(tasks),
                "success_count": sum(
                    1 for s in sub_results
                    if s["status"] == "completed"
                ),
            },
            error=error_msg.strip("; "),
            sub_results=sub_results,
            agent_traces=agent_traces,
            duration_seconds=duration,
        )

    def execute_hierarchical(
        self,
        tasks: List[CrewTask],
        context: Dict[str, Any] = None,
    ) -> CrewResult:
        context = context or {}
        start_time = time.time()
        self._execution_log = []

        supervisor_config = agent_registry.get("supervisor")
        if not supervisor_config:
            supervisor_config_created = AgentConfig(
                role=AgentRole.SUPERVISOR,
                name="supervisor",
                display_name="任务监督者",
                system_prompt=(
                    "你是多智能体系统的 Supervisor。\n"
                    "分析用户请求，将复杂任务分解为子任务，分配给合适的 Agent。\n"
                    "最终整合各 Agent 的结果，输出完整回答。\n"
                    "输出格式：\n"
                    "1. 【任务分析】\n"
                    "2. 【任务分解】列出子任务及负责Agent\n"
                    "3. 【执行计划】\n"
                    "4. 【结果整合】\n"
                    "5. 【最终回答】"
                ),
                description="负责任务分解和协调的监督Agent",
                capabilities=[],
            )
            agent_registry.register(supervisor_config_created)

        self._log("Supervisor 开始分析任务...")

        analysis = self._analyze_with_supervisor(tasks, context)
        self._log(f"分析结果: {analysis[:200]}...")

        sub_results = []
        agent_traces = []
        all_success = True
        error_msg = ""

        for i, task in enumerate(tasks):
            if task.assigned_roles and (
                AgentRole.SUPERVISOR in task.assigned_roles
                and len(task.assigned_roles) == 1
            ):
                continue

            self._log(
                f"调度子任务 [{i + 1}/{len(tasks)}]: "
                f"{task.description[:80]}..."
            )

            assigned = task_router.assign_task(task)
            if not assigned:
                self._log(f"❌ 无法分配任务 {task.task_id}")
                task.status = CrewTaskStatus.FAILED
                task.error = "无可用 Agent"
                all_success = False
                sub_results.append({
                    "task_id": task.task_id,
                    "status": "failed",
                    "error": "无可用 Agent",
                })
                continue

            result_text, error = self.execute_agent(
                assigned, task, timeout=120.0
            )

            agent_traces.append(f"[{assigned}] → {task.task_id}")
            sub_results.append({
                "task_id": task.task_id,
                "description": task.description[:200],
                "status": task.status.value,
                "result": result_text,
                "error": error,
                "agent": assigned,
            })

            if task.status != CrewTaskStatus.COMPLETED:
                all_success = False
                error_msg += f"[{task.task_id}] {error}; "

        integrated = self._integrate_with_supervisor(
            tasks, sub_results, context
        )

        duration = time.time() - start_time

        return CrewResult(
            success=all_success,
            task_id="hierarchical_result",
            result={
                "analysis": analysis,
                "integrated_answer": integrated,
                "sub_results": sub_results,
                "total_tasks": len(tasks),
            },
            error=error_msg.strip("; "),
            sub_results=sub_results,
            agent_traces=agent_traces,
            duration_seconds=duration,
        )

    def _analyze_with_supervisor(
        self,
        tasks: List[CrewTask],
        context: Dict[str, Any],
    ) -> str:
        agent, config = self.get_or_create_agent(
            agent_registry.get("supervisor").config
        )

        task_descriptions = "\n".join(
            f"{i + 1}. {t.description[:200]}"
            for i, t in enumerate(tasks)
        )

        prompt = (
            f"请分析以下任务并制定执行计划：\n\n"
            f"{task_descriptions}\n\n"
            f"请按格式输出：\n"
            f"1. 【任务分析】：理解这些任务的核心目标\n"
            f"2. 【任务分解】：将任务拆分为可分配给专业Agent的子任务\n"
            f"3. 【执行计划】：说明执行顺序和依赖关系\n"
            f"4. 【预期结果】：描述预期产出"
        )

        try:
            import asyncio
            response = asyncio.run(
                self._invoke_agent(
                    agent,
                    [HumanMessage(content=prompt)],
                    config,
                    60.0,
                )
            )
            return self._extract_response_content(response)
        except Exception as e:
            logger.warning(f"Supervisor分析失败: {e}")
            return f"自动分析: 共 {len(tasks)} 个子任务，顺序执行"

    def _integrate_with_supervisor(
        self,
        tasks: List[CrewTask],
        sub_results: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        supervisor_config = agent_registry.get("supervisor")
        if not supervisor_config:
            return self._simple_integration(sub_results)

        agent, config = self.get_or_create_agent(supervisor_config.config)

        results_text = "\n\n".join(
            f"子任务 {i + 1}: {s.get('description', '')[:100]}\n"
            f"结果: {str(s.get('result', ''))[:500]}"
            for i, s in enumerate(sub_results)
        )

        prompt = (
            f"请整合以下子任务的结果，给出最终回答：\n\n"
            f"{results_text}\n\n"
            f"请输出：\n"
            f"1. 【结果整合】：各子任务结果汇总\n"
            f"2. 【最终回答】：完整、连贯的最终回答"
        )

        try:
            import asyncio
            response = asyncio.run(
                self._invoke_agent(
                    agent,
                    [HumanMessage(content=prompt)],
                    config,
                    60.0,
                )
            )
            return self._extract_response_content(response)
        except Exception as e:
            logger.warning(f"Supervisor整合失败: {e}")
            return self._simple_integration(sub_results)

    @staticmethod
    def _simple_integration(sub_results: List[Dict[str, Any]]) -> str:
        lines = ["## 执行结果汇总\n"]
        for i, s in enumerate(sub_results):
            status = s.get("status", "unknown")
            icon = "✅" if status == "completed" else "❌"
            lines.append(f"{icon} **子任务 {i + 1}**: {s.get('description', '')[:100]}")
            result = s.get("result")
            if result:
                lines.append(f"   {str(result)[:300]}")
            error = s.get("error")
            if error:
                lines.append(f"   错误: {error}")
            lines.append("")
        return "\n".join(lines)

    def execute(
        self,
        tasks: List[CrewTask],
        process_type: ProcessType = ProcessType.HIERARCHICAL,
        context: Dict[str, Any] = None,
    ) -> CrewResult:
        if process_type == ProcessType.SEQUENTIAL:
            return self.execute_sequential(tasks, context)
        else:
            return self.execute_hierarchical(tasks, context)

    def _log(self, message: str):
        self._execution_log.append(message)
        logger.info(f"[Supervisor] {message}")

    def get_execution_log(self) -> List[str]:
        return list(self._execution_log)

    def reset(self):
        self.clear_agent_cache()
        self._execution_log.clear()
        self._protocol.reset()

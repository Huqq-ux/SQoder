import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from Coder.multi_agent.types import (
    AgentRole,
    AgentConfig,
    AgentStatus,
    CrewTask,
    CrewTaskStatus,
    CrewResult,
    CrewConfig,
    ProcessType,
)
from Coder.multi_agent.registry import agent_registry, AgentRegistry
from Coder.multi_agent.router import task_router, TaskRouter
from Coder.multi_agent.protocol import CommunicationProtocol
from Coder.multi_agent.supervisor import SupervisorAgent
from Coder.multi_agent.agent_builder import AgentBuilder
from Coder.multi_agent.integrations import (
    build_default_agent_configs,
    build_system_prompt_for_role,
    build_tool_set_for_role,
)

logger = logging.getLogger(__name__)


class MultiAgentCrew:

    def __init__(
        self,
        crew_config: CrewConfig = None,
        registry: AgentRegistry = None,
        router: TaskRouter = None,
    ):
        self.config = crew_config or CrewConfig()
        self._registry = registry or agent_registry
        self._router = router or task_router
        self._protocol = CommunicationProtocol()
        self._builder = AgentBuilder()
        self._supervisor = SupervisorAgent(
            agent_builder=self._builder,
            protocol=self._protocol,
        )
        self._last_result: Optional[CrewResult] = None
        self._execution_history: List[CrewResult] = []
        self._error_handler: Optional[Callable] = None

    @property
    def supervisor(self) -> SupervisorAgent:
        return self._supervisor

    @property
    def protocol(self) -> CommunicationProtocol:
        return self._protocol

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def last_result(self) -> Optional[CrewResult]:
        return self._last_result

    def add_agent(self, config: AgentConfig) -> bool:
        agent = self._registry.get(config.name)
        if agent:
            logger.warning(
                f"Agent '{config.name}' 已存在，将被重新配置"
            )
            self._registry.unregister(config.name)
        return self._registry.register(config)

    def add_coder(
        self,
        name: str = "coder",
        custom_prompt: str = "",
        extra_tools: List[str] = None,
    ) -> bool:
        config = AgentConfig(
            role=AgentRole.CODER,
            name=name,
            display_name="编程专家",
            system_prompt=custom_prompt or build_system_prompt_for_role(
                AgentRole.CODER
            ),
            description="负责代码生成、审查和调试",
            tools=extra_tools or ["file_tools", "knowledge_toolkit"],
        )
        return self.add_agent(config)

    def add_searcher(
        self,
        name: str = "searcher",
        custom_prompt: str = "",
        extra_tools: List[str] = None,
    ) -> bool:
        config = AgentConfig(
            role=AgentRole.SEARCHER,
            name=name,
            display_name="搜索专家",
            system_prompt=custom_prompt or build_system_prompt_for_role(
                AgentRole.SEARCHER
            ),
            description="负责信息检索和知识查询",
            tools=extra_tools or ["web_search_toolkit", "knowledge_toolkit"],
        )
        return self.add_agent(config)

    def add_ops(
        self,
        name: str = "ops",
        custom_prompt: str = "",
        extra_tools: List[str] = None,
    ) -> bool:
        config = AgentConfig(
            role=AgentRole.OPS,
            name=name,
            display_name="运维专家",
            system_prompt=custom_prompt or build_system_prompt_for_role(
                AgentRole.OPS
            ),
            description="负责系统部署和故障排查",
            tools=extra_tools or ["file_tools"],
        )
        return self.add_agent(config)

    def add_skill_executor(
        self,
        name: str = "skill_executor",
        custom_prompt: str = "",
    ) -> bool:
        config = AgentConfig(
            role=AgentRole.SKILL_EXECUTOR,
            name=name,
            display_name="技能执行器",
            system_prompt=custom_prompt or build_system_prompt_for_role(
                AgentRole.SKILL_EXECUTOR
            ),
            description="负责执行已注册的技能",
        )
        return self.add_agent(config)

    def add_sop_executor(
        self,
        name: str = "sop_executor",
        custom_prompt: str = "",
    ) -> bool:
        config = AgentConfig(
            role=AgentRole.SOP_EXECUTOR,
            name=name,
            display_name="SOP执行器",
            system_prompt=custom_prompt or build_system_prompt_for_role(
                AgentRole.SOP_EXECUTOR
            ),
            description="负责按标准操作流程执行任务",
        )
        return self.add_agent(config)

    def add_supervisor(
        self,
        name: str = "supervisor",
        custom_prompt: str = "",
    ) -> bool:
        config = AgentConfig(
            role=AgentRole.SUPERVISOR,
            name=name,
            display_name="任务监督者",
            system_prompt=custom_prompt or build_system_prompt_for_role(
                AgentRole.SUPERVISOR
            ),
            description="负责任务分解、分配和结果整合",
        )
        return self.add_agent(config)

    def initialize_default_crew(self) -> int:
        configs = build_default_agent_configs()
        count = 0
        for config in configs:
            if self.add_agent(config):
                count += 1
        logger.info(f"已初始化默认 Crew: {count} 个 Agent")
        return count

    def on_error(self, handler: Callable):
        self._error_handler = handler
        return handler

    def kickoff(
        self,
        user_input: str,
        process_type: ProcessType = None,
        context: Dict[str, Any] = None,
    ) -> CrewResult:
        start_time = time.time()
        process = process_type or self.config.process_type

        if self.config.verbose:
            logger.info(
                f"[Crew] 启动 (process={process.value}): {user_input[:100]}"
            )

        if context is None:
            context = {}

        tasks, is_multi = self._router.route_task(
            user_input,
            force_multi=(process == ProcessType.HIERARCHICAL),
        )

        if not tasks:
            return CrewResult(
                success=False,
                task_id="",
                error="无法分解任务",
                duration_seconds=time.time() - start_time,
            )

        if not is_multi and len(tasks) == 1:
            result = self._execute_single_task(
                tasks[0], user_input, process, context
            )
        else:
            result = self._supervisor.execute(
                tasks, process_type=process, context=context
            )

        if not result.success and self._error_handler:
            try:
                self._error_handler(result)
            except Exception as e:
                logger.warning(f"错误处理器异常: {e}")

        self._last_result = result
        self._execution_history.append(result)

        if self.config.verbose:
            logger.info(
                f"[Crew] 完成 (success={result.success}, "
                f"duration={result.duration_seconds:.1f}s)"
            )

        return result

    def _execute_single_task(
        self,
        task: CrewTask,
        user_input: str,
        process_type: ProcessType,
        context: Dict[str, Any],
    ) -> CrewResult:
        start_time = time.time()

        assigned = self._router.assign_task(task)
        if not assigned:
            return CrewResult(
                success=False,
                task_id=task.task_id,
                error=f"无法将任务分配给 Agent: {task.assigned_roles}",
                duration_seconds=time.time() - start_time,
            )

        result_text, error = self._supervisor.execute_agent(
            assigned, task, timeout=120.0
        )

        duration = time.time() - start_time
        return CrewResult(
            success=task.status == CrewTaskStatus.COMPLETED,
            task_id=task.task_id,
            result=result_text,
            error=error,
            sub_results=[{
                "task_id": task.task_id,
                "description": task.description[:200],
                "status": task.status.value,
                "result": result_text,
                "error": error,
                "agent": assigned,
            }],
            agent_traces=[f"[{assigned}] → {task.task_id}"],
            duration_seconds=duration,
        )

    def kickoff_with_validation(
        self,
        user_input: str,
        process_type: ProcessType = None,
        context: Dict[str, Any] = None,
    ) -> Tuple[CrewResult, bool]:
        from Coder.sop.intent_classifier import classify_intent, IntentType

        intent = classify_intent(user_input)

        if intent.intent == IntentType.GENERAL_CHAT:
            result = self.kickoff(
                user_input,
                process_type=ProcessType.SEQUENTIAL,
                context=context,
            )
            return result, False

        if intent.intent in (IntentType.EXECUTE_SOP, IntentType.QUERY_SOP):
            self.add_sop_executor()
            result = self.kickoff(
                user_input,
                process_type=process_type or ProcessType.SEQUENTIAL,
                context=context,
            )
            return result, True

        if intent.intent == IntentType.SKILL_INVOKE:
            self.add_skill_executor()
            result = self.kickoff(
                user_input,
                process_type=process_type or ProcessType.SEQUENTIAL,
                context=context,
            )
            return result, True

        result = self.kickoff(
            user_input,
            process_type=process_type,
            context=context,
        )
        return result, True

    def get_execution_log(self) -> List[str]:
        return self._supervisor.get_execution_log()

    def get_history(self) -> List[CrewResult]:
        return list(self._execution_history)

    def get_statistics(self) -> Dict[str, Any]:
        stats = self._registry.get_all_statistics()
        return {
            "agents": stats,
            "total_executions": len(self._execution_history),
            "successful_executions": sum(
                1 for r in self._execution_history if r.success
            ),
            "last_result_success": (
                self._last_result.success if self._last_result else None
            ),
            "total_agent_count": len(stats),
        }

    def reset(self):
        self._supervisor.reset()
        self._protocol.reset()
        self._last_result = None
        self._execution_history.clear()

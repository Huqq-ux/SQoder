import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentConfig,
    AgentInfo,
    AgentStatus,
    CrewTask,
    CrewTaskStatus,
    DelegateRequest,
    DelegateResponse,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    _instance: Optional["AgentRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, AgentInfo] = {}
            cls._instance._capacity_scores: Dict[str, float] = {}
            cls._instance._task_history: Dict[str, List[CrewTask]] = {}
            cls._instance._last_eval_time: Dict[str, str] = {}
        return cls._instance

    def register(
        self,
        config: AgentConfig,
        initial_status: AgentStatus = AgentStatus.IDLE,
    ) -> bool:
        if config.name in self._agents:
            logger.warning(f"Agent '{config.name}' 已注册，将被覆盖")
        self._agents[config.name] = AgentInfo(
            config=config,
            status=initial_status,
            registered_at=datetime.now().isoformat(),
        )
        self._capacity_scores[config.name] = 1.0
        self._task_history[config.name] = []
        logger.info(
            f"Agent 已注册: {config.name} "
            f"(角色: {config.role.value}, "
            f"能力: {[c.name for c in config.capabilities]})"
        )
        return True

    def unregister(self, name: str) -> bool:
        if name in self._agents:
            del self._agents[name]
            self._capacity_scores.pop(name, None)
            self._task_history.pop(name, None)
            self._last_eval_time.pop(name, None)
            logger.info(f"Agent 已注销: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[AgentInfo]:
        return self._agents.get(name)

    def get_config(self, name: str) -> Optional[AgentConfig]:
        agent = self._agents.get(name)
        return agent.config if agent else None

    def list_all(self) -> List[AgentInfo]:
        return sorted(
            self._agents.values(),
            key=lambda a: (a.config.role.value, a.config.name),
        )

    def list_available(self) -> List[AgentInfo]:
        return [
            a for a in self._agents.values()
            if a.status == AgentStatus.IDLE
        ]

    def list_by_role(self, role: AgentRole) -> List[AgentInfo]:
        return [
            a for a in self._agents.values()
            if a.config.role == role
        ]

    def list_by_capability(self, capability: AgentCapability) -> List[AgentInfo]:
        return [
            a for a in self._agents.values()
            if capability in a.config.capabilities
        ]

    def get_roles(self) -> List[AgentRole]:
        return sorted(set(
            a.config.role for a in self._agents.values()
        ))

    def set_status(self, name: str, status: AgentStatus):
        if name in self._agents:
            self._agents[name].status = status
            if status != AgentStatus.IDLE:
                self._agents[name].last_active_at = datetime.now().isoformat()

    def assign_task(self, name: str, task_id: str):
        if name in self._agents:
            self._agents[name].current_task_id = task_id
            self._agents[name].status = AgentStatus.BUSY
            self._agents[name].task_history.append(task_id)
            self._agents[name].last_active_at = datetime.now().isoformat()

    def release_task(self, name: str):
        if name in self._agents:
            self._agents[name].current_task_id = ""
            self._agents[name].status = AgentStatus.IDLE

    def record_task(self, name: str, task: CrewTask):
        if name not in self._task_history:
            self._task_history[name] = []
        self._task_history[name].append(task)

    def get_agent_statistics(self, name: str) -> Dict:
        agent = self._agents.get(name)
        if not agent:
            return {}

        tasks = self._task_history.get(name, [])
        completed = sum(
            1 for t in tasks if t.status == CrewTaskStatus.COMPLETED
        )
        failed = sum(
            1 for t in tasks if t.status == CrewTaskStatus.FAILED
        )

        return {
            "name": name,
            "role": agent.config.role.value,
            "status": agent.status.value,
            "total_tasks": len(tasks),
            "completed_tasks": completed,
            "failed_tasks": failed,
            "success_rate": completed / len(tasks) if tasks else 0.0,
            "capacity_score": self._capacity_scores.get(name, 1.0),
            "registered_at": agent.registered_at,
            "last_active_at": agent.last_active_at,
        }

    def get_all_statistics(self) -> List[Dict]:
        return [
            self.get_agent_statistics(name)
            for name in self._agents
        ]

    def select_agent(
        self,
        role: AgentRole,
        required_capabilities: List[AgentCapability] = None,
        exclude_busy: bool = True,
    ) -> Optional[AgentInfo]:
        candidates = self.list_by_role(role)
        if not candidates:
            return None

        if exclude_busy:
            idle = [a for a in candidates if a.status == AgentStatus.IDLE]
            if idle:
                candidates = idle

        if required_capabilities:
            candidates = [
                a for a in candidates
                if all(
                    cap in a.config.capabilities
                    for cap in required_capabilities
                )
            ]

        if not candidates:
            return None

        candidates.sort(
            key=lambda a: self._capacity_scores.get(a.config.name, 1.0),
            reverse=True,
        )
        return candidates[0]

    def find_agents_for_task(
        self,
        description: str,
        preferred_roles: List[AgentRole] = None,
    ) -> List[Tuple[AgentInfo, float]]:
        results: List[Tuple[AgentInfo, float]] = []
        desc_lower = description.lower()

        for name, agent in self._agents.items():
            if agent.status != AgentStatus.IDLE:
                continue
            if preferred_roles and agent.config.role not in preferred_roles:
                continue

            score = 0.0
            for capability in agent.config.capabilities:
                cap_name = capability.name.lower().replace("_", " ")
                if cap_name in desc_lower:
                    score += 2.0

            config = agent.config
            if config.description and any(
                word in desc_lower
                for word in config.description.lower().split()
            ):
                score += 1.0

            score += self._capacity_scores.get(name, 1.0) * 0.5

            if score > 0:
                results.append((agent, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def evaluate_and_adjust(
        self,
        name: str,
        task: CrewTask,
        success: bool,
    ):
        if name not in self._capacity_scores:
            return

        if success:
            self._capacity_scores[name] = min(
                1.0, self._capacity_scores[name] + 0.1
            )
        else:
            self._capacity_scores[name] = max(
                0.1, self._capacity_scores[name] - 0.15
            )

        self._last_eval_time[name] = datetime.now().isoformat()
        logger.info(
            f"Agent '{name}' 能力评分调整: "
            f"{self._capacity_scores[name]:.2f} "
            f"({'成功' if success else '失败'})"
        )

    def handle_delegate(
        self, request: DelegateRequest
    ) -> DelegateResponse:
        agent = self.select_agent(
            role=request.target_role, exclude_busy=True
        )
        if agent:
            return DelegateResponse(
                accepted=True,
                assigned_agent=agent.config.name,
                estimated_duration=60.0,
            )
        else:
            return DelegateResponse(
                accepted=False,
                reason=f"没有可用的 {request.target_role.value} Agent",
            )

    def reset(self):
        self._agents.clear()
        self._capacity_scores.clear()
        self._task_history.clear()
        self._last_eval_time.clear()


agent_registry = AgentRegistry()

import re
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentInfo,
    CrewTask,
    CrewTaskStatus,
    DelegateRequest,
    DelegateResponse,
    CrewResult,
)
from Coder.multi_agent.registry import agent_registry

logger = logging.getLogger(__name__)


_ROLE_KEYWORDS: Dict[AgentRole, List[str]] = {
    AgentRole.CODER: [
        "代码", "编程", "写", "实现", "开发", "修复bug", "重构",
        "算法", "函数", "类", "模块", "接口", "API", "数据库",
        "code", "implement", "develop", "fix", "refactor",
        "debug", "test", "unittest", "function", "class",
    ],
    AgentRole.SEARCHER: [
        "搜索", "查找", "检索", "查一下", "了解一下", "是什么",
        "怎么", "如何", "什么是", "介绍", "解释", "文档", "知识",
        "search", "find", "lookup", "what is", "how to",
        "explain", "document", "knowledge",
    ],
    AgentRole.OPS: [
        "部署", "安装", "配置", "启动", "停止", "重启", "监控",
        "日志", "错误", "故障", "排查", "优化", "性能", "服务器",
        "deploy", "install", "configure", "start", "stop",
        "restart", "monitor", "log", "error", "troubleshoot",
        "optimize", "performance", "server",
    ],
    AgentRole.SOP_EXECUTOR: [
        "SOP", "流程", "步骤", "标准操作", "操作规范", "检查清单",
        "按照流程", "执行SOP", "sop流程", "操作手册",
    ],
    AgentRole.SKILL_EXECUTOR: [
        "技能", "skill", "功能", "工具", "调用skill",
        "执行技能", "使用技能",
    ],
}

_SKILL_CALL_RE = re.compile(
    r"(?:调用|使用|执行|运行)\s*(?:技能|skill|功能)",
    re.IGNORECASE,
)

_SOP_CALL_RE = re.compile(
    r"(?:执行|按照|根据|遵循)\s*(?:SOP|流程|步骤|规范)",
    re.IGNORECASE,
)

_TASK_ROOT_KEYWORDS = [
    "第一步", "第二步", "第三步", "首先", "然后", "接着", "最后",
    "同时", "另外", "除此之外", "并行", "多个任务", "分步",
    "先.*再.*然后", "不仅.*还要",
]


class TaskRouter:
    _instance: Optional["TaskRouter"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._task_store: Dict[str, CrewTask] = {}
            cls._instance._decomposition_cache: Dict[str, List[CrewTask]] = {}
        return cls._instance

    @staticmethod
    def analyze_user_intent(
        user_input: str,
        prefer_multi_agent: bool = False,
    ) -> Tuple[bool, List[AgentRole], float]:
        text_lower = user_input.lower()

        if prefer_multi_agent:
            return True, [AgentRole.SUPERVISOR], 0.9

        role_scores: Dict[AgentRole, int] = {}
        for role, keywords in _ROLE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                role_scores[role] = score

        if not role_scores:
            return False, [AgentRole.GENERAL], 0.3

        is_multi = len(role_scores) >= 2
        for kw in _TASK_ROOT_KEYWORDS:
            if re.search(kw, text_lower):
                is_multi = True
                break

        top_roles = sorted(
            role_scores.keys(), key=lambda r: role_scores[r], reverse=True
        )
        confidence = min(
            sum(role_scores.values()) / (len(role_scores) * 3), 1.0
        )

        if _SKILL_CALL_RE.search(text_lower):
            if AgentRole.SKILL_EXECUTOR not in top_roles:
                top_roles.insert(0, AgentRole.SKILL_EXECUTOR)
            is_multi = is_multi or len(top_roles) > 1

        if _SOP_CALL_RE.search(text_lower):
            if AgentRole.SOP_EXECUTOR not in top_roles:
                top_roles.insert(0, AgentRole.SOP_EXECUTOR)

        return is_multi, top_roles, confidence

    @staticmethod
    def decompose_task(
        user_input: str,
        preferred_roles: List[AgentRole] = None,
    ) -> List[CrewTask]:
        text = user_input.strip()
        if not text:
            return []

        tasks = TaskRouter._split_by_markers(text)
        if len(tasks) <= 1:
            return [TaskRouter._create_task(text, preferred_roles)]

        return [
            TaskRouter._create_task(t, preferred_roles)
            for t in tasks
        ]

    @staticmethod
    def _split_by_markers(text: str) -> List[str]:
        markers = [
            r"(?:第[一二三四五六七八九十\d]+[步个]|首先|然后|接着|最后|同时|另外|并行)",
            r"(?:\d+[\.\、\)）]\s*)",
        ]

        for marker_pattern in markers:
            parts = re.split(marker_pattern, text)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                return parts

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) > 1:
            return lines

        return [text]

    @staticmethod
    def _create_task(
        description: str,
        preferred_roles: List[AgentRole] = None,
    ) -> CrewTask:
        text_lower = description.lower()
        assigned_roles = []

        if preferred_roles:
            assigned_roles = list(preferred_roles)
        else:
            for role, keywords in _ROLE_KEYWORDS.items():
                if any(kw.lower() in text_lower for kw in keywords):
                    assigned_roles.append(role)
            if not assigned_roles:
                assigned_roles = [AgentRole.GENERAL]

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        return CrewTask(
            task_id=task_id,
            description=description,
            assigned_roles=assigned_roles,
            priority=0,
        )

    def assign_task(
        self,
        task: CrewTask,
        preferred_agent: str = "",
    ) -> Optional[str]:
        if preferred_agent:
            agent = agent_registry.get(preferred_agent)
            if agent:
                agent_registry.assign_task(preferred_agent, task.task_id)
                task.assigned_agent = preferred_agent
                task.status = CrewTaskStatus.ASSIGNED
                return preferred_agent

        for role in task.assigned_roles:
            agent = agent_registry.select_agent(role=role, exclude_busy=True)
            if agent:
                agent_registry.assign_task(agent.config.name, task.task_id)
                task.assigned_agent = agent.config.name
                task.status = CrewTaskStatus.ASSIGNED
                return agent.config.name

        for role in task.assigned_roles:
            agent = agent_registry.select_agent(role=role, exclude_busy=False)
            if agent:
                agent_registry.assign_task(agent.config.name, task.task_id)
                task.assigned_agent = agent.config.name
                task.status = CrewTaskStatus.ASSIGNED
                return agent.config.name

        logger.warning(f"无法分配任务 {task.task_id}，无可用Agent")
        return None

    def create_subtasks(
        self,
        parent_task: CrewTask,
        sub_descriptions: List[str],
    ) -> List[CrewTask]:
        sub_tasks = []
        for desc in sub_descriptions:
            sub = self._create_task(desc, parent_task.assigned_roles)
            sub.parent_task_id = parent_task.task_id
            sub.priority = parent_task.priority + 1
            sub_tasks.append(sub)
            parent_task.sub_tasks.append(sub.task_id)
        return sub_tasks

    def route_task(
        self,
        user_input: str,
        force_multi: bool = False,
    ) -> Tuple[List[CrewTask], bool]:
        is_multi, roles, confidence = self.analyze_user_intent(
            user_input, prefer_multi_agent=force_multi
        )

        if is_multi or force_multi:
            tasks = self.decompose_task(user_input, roles)
            root_task = CrewTask(
                task_id=f"root_{uuid.uuid4().hex[:8]}",
                description=user_input,
                assigned_roles=[AgentRole.SUPERVISOR],
                priority=-1,
            )
            for t in tasks:
                t.parent_task_id = root_task.task_id
                root_task.sub_tasks.append(t.task_id)
            return [root_task] + tasks, True
        else:
            task = self._create_task(user_input, roles)
            return [task], False

    def get_task(self, task_id: str) -> Optional[CrewTask]:
        return self._task_store.get(task_id)

    def store_task(self, task: CrewTask):
        self._task_store[task.task_id] = task

    def update_task_status(
        self,
        task_id: str,
        status: CrewTaskStatus,
        result: Any = None,
        error: str = "",
    ):
        task = self._task_store.get(task_id)
        if task:
            task.status = status
            task.result = result
            task.error = error
            if status in (
                CrewTaskStatus.COMPLETED,
                CrewTaskStatus.FAILED,
                CrewTaskStatus.CANCELLED,
            ):
                task.completed_at = datetime.now().isoformat()

    def aggregate_results(self, tasks: List[CrewTask]) -> CrewResult:
        sub_results = []
        all_success = True
        errors = []

        for task in tasks:
            sub_results.append({
                "task_id": task.task_id,
                "description": task.description[:200],
                "status": task.status.value,
                "result": task.result,
                "error": task.error,
                "agent": task.assigned_agent,
            })
            if task.status != CrewTaskStatus.COMPLETED:
                all_success = False
                if task.error:
                    errors.append(f"[{task.task_id}] {task.error}")

        return CrewResult(
            success=all_success,
            task_id="aggregated",
            result={
                "sub_results": sub_results,
                "total": len(tasks),
                "success_count": sum(
                    1 for t in tasks
                    if t.status == CrewTaskStatus.COMPLETED
                ),
                "failed_count": sum(
                    1 for t in tasks
                    if t.status == CrewTaskStatus.FAILED
                ),
            },
            error="; ".join(errors) if errors else "",
            sub_results=sub_results,
            agent_traces=[],
        )

    def reset(self):
        self._task_store.clear()
        self._decomposition_cache.clear()


task_router = TaskRouter()

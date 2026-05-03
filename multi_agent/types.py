from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class AgentRole(Enum):
    SUPERVISOR = "supervisor"
    CODER = "coder"
    SEARCHER = "searcher"
    OPS = "ops"
    SOP_EXECUTOR = "sop_executor"
    SKILL_EXECUTOR = "skill_executor"
    GENERAL = "general"


class AgentCapability(Enum):
    CODE_GENERATION = auto()
    CODE_REVIEW = auto()
    CODE_DEBUGGING = auto()
    WEB_SEARCH = auto()
    KNOWLEDGE_RETRIEVAL = auto()
    DATA_ANALYSIS = auto()
    SOP_EXECUTION = auto()
    SKILL_EXECUTION = auto()
    SYSTEM_OPERATION = auto()
    DEPLOYMENT = auto()
    TROUBLESHOOTING = auto()
    TASK_DECOMPOSITION = auto()
    RESULT_INTEGRATION = auto()
    COMMUNICATION = auto()


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class ProcessType(Enum):
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    PARALLEL = "parallel"


class CrewTaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_QUERY = "task_query"
    TASK_CLARIFY = "task_clarify"
    STATUS_UPDATE = "status_update"
    DELEGATE = "delegate"
    SUPERVISOR_INSTRUCTION = "supervisor_instruction"


@dataclass
class AgentConfig:
    role: AgentRole
    name: str
    display_name: str
    system_prompt: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    model_name: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    max_retries: int = 2
    timeout_seconds: float = 120.0
    allow_delegation: bool = True
    priority: int = 0


@dataclass
class AgentInfo:
    config: AgentConfig
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: str = ""
    task_history: List[str] = field(default_factory=list)
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active_at: str = ""


@dataclass
class CrewTask:
    task_id: str
    description: str
    assigned_roles: List[AgentRole] = field(default_factory=list)
    status: CrewTaskStatus = CrewTaskStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: str = ""
    sub_tasks: List[str] = field(default_factory=list)
    result: Any = None
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    assigned_agent: str = ""
    retry_count: int = 0
    priority: int = 0


@dataclass
class CrewResult:
    success: bool
    task_id: str
    result: Any = None
    error: str = ""
    sub_results: List[Dict[str, Any]] = field(default_factory=list)
    agent_traces: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CrewConfig:
    process_type: ProcessType = ProcessType.HIERARCHICAL
    max_concurrent_tasks: int = 3
    global_timeout_seconds: float = 600.0
    verbose: bool = True
    allow_agent_delegation: bool = True
    retry_failed_tasks: bool = True
    max_retries_per_task: int = 2
    collect_agent_traces: bool = True


@dataclass
class CommunicationMessage:
    msg_id: str
    msg_type: MessageType
    sender: str
    receiver: str
    content: str
    task_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reply_to: str = ""


@dataclass
class DelegateRequest:
    requester: str
    target_role: AgentRole
    task_description: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class DelegateResponse:
    accepted: bool
    assigned_agent: str = ""
    reason: str = ""
    estimated_duration: float = 0.0

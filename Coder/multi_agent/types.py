from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List


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

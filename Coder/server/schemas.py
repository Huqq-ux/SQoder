from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str


class MessageResponse(BaseModel):
    role: str
    content: str
    parts: Optional[List[Dict[str, Any]]] = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    k: int = Field(default=3, ge=1, le=20)


class KnowledgeUploadResponse(BaseModel):
    filename: str
    chunks: int
    status: str



class SkillUploadRequest(BaseModel):
    skill_json: Dict[str, Any]


class SkillToggleRequest(BaseModel):
    enabled: bool


class OrchestratorExecuteRequest(BaseModel):
    task: str
    mode: str = Field(default="orchestrator")


class OrchestratorToolCall(BaseModel):
    agent: str
    display_name: str
    task: str
    duration_ms: int
    success: bool
    error: str = ""


class OrchestratorExecuteResponse(BaseModel):
    success: bool
    answer: str
    error: Optional[str] = None
    duration_seconds: float
    tool_calls: List[OrchestratorToolCall] = Field(default_factory=list)

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


class SOPListResponse(BaseModel):
    sop_names: List[str]
    count: int


class SOPCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)


class SkillUploadRequest(BaseModel):
    skill_json: Dict[str, Any]


class SkillToggleRequest(BaseModel):
    enabled: bool


class MultiAgentExecuteRequest(BaseModel):
    task: str
    process_type: str = Field(default="hierarchical")


class MultiAgentAddAgentRequest(BaseModel):
    name: str
    role: str
    custom_prompt: Optional[str] = None

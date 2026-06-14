from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    course_id: Optional[str] = None


class SessionCreate(BaseModel):
    title: Optional[str] = None
    course_id: Optional[str] = None


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


class CourseCreate(BaseModel):
    name: str
    description: str = ""
    semester: str = ""


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    semester: Optional[str] = None


class CourseResponse(BaseModel):
    id: str
    name: str
    description: str
    semester: str
    created_at: str
    updated_at: str


class KnowledgePointResponse(BaseModel):
    id: str
    name: str
    section: str
    source_file: str
    source_page: int


class CourseFileResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    uploaded_at: str


class NoteCreate(BaseModel):
    course_id: str
    kp_id: Optional[str] = None
    title: str = ""
    content: str


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    created_at: str


class WrongAnswerCreate(BaseModel):
    course_id: str
    kp_id: Optional[str] = None
    question: str
    user_answer: str
    correct_answer: str


# ── Wiki schemas ──

class WikiPageResponse(BaseModel):
    path: str
    frontmatter: Dict[str, Any] = Field(default_factory=dict)
    body: str
    backlinks: List[str] = Field(default_factory=list)


class WikiPageSummary(BaseModel):
    path: str
    title: str
    category: str = ""
    link_count: int = 0
    backlink_count: int = 0
    modified: str = ""


class WikiSearchRequest(BaseModel):
    query: str


class WikiIngestResponse(BaseModel):
    status: str
    pages_created: int = 0
    pages_updated: int = 0
    errors: List[str] = Field(default_factory=list)


class WikiLintEntry(BaseModel):
    source: str
    target: str = ""


class WikiLintResult(BaseModel):
    broken_links: List[WikiLintEntry] = Field(default_factory=list)
    orphans: List[str] = Field(default_factory=list)
    frontmatter_issues: List[str] = Field(default_factory=list)
    total_pages: int = 0
    health: str = "good"

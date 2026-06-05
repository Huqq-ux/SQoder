import logging
from fastapi import APIRouter, Request
from Coder.server.schemas import OrchestratorExecuteRequest, OrchestratorExecuteResponse, OrchestratorToolCall

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/execute", response_model=OrchestratorExecuteResponse)
async def execute_task(req: OrchestratorExecuteRequest, request: Request):
    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    result = await orch.run(req.task)

    return OrchestratorExecuteResponse(
        success=result["success"],
        answer=result["answer"],
        error=result.get("error"),
        duration_seconds=result["duration_seconds"],
        tool_calls=[
            OrchestratorToolCall(**tc)
            for tc in result.get("tool_calls", [])
        ],
    )


import json
import uuid
from fastapi.responses import StreamingResponse


@router.post("/stream")
async def stream_task(req: OrchestratorExecuteRequest, request: Request):
    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()

    async def generate():
        async for event in orch.astream(
            req.task,
            thread_id=f"orch_{uuid.uuid4().hex[:12]}",
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


import re


@router.get("/sessions")
async def list_orchestrator_sessions(request: Request):
    """列出所有 mode='orchestrator' 的会话"""
    from Coder.storage.db import DatabaseManager

    rows = await DatabaseManager.fetch(
        "SELECT session_id, title, created_at, updated_at "
        "FROM sessions WHERE mode = 'orchestrator' "
        "ORDER BY updated_at DESC LIMIT 50"
    )
    return {
        "sessions": [
            {
                "session_id": r["session_id"],
                "title": r["title"] or "未命名任务",
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
            }
            for r in (rows or [])
        ]
    }


@router.get("/sessions/{session_id}")
async def get_orchestrator_session(session_id: str, request: Request):
    """获取指定编排会话的消息历史和子 Agent 调用链"""
    if not re.match(r"^[a-zA-Z0-9\-_]+$", session_id):
        return {"error": "无效的 session_id"}

    sidechains = []
    try:
        from Coder.storage.db import DatabaseManager
        rows = await DatabaseManager.fetch(
            "SELECT DISTINCT thread_id FROM langgraph_checkpoints "
            "WHERE thread_id LIKE $1",
            f"orch_{session_id}/%"
        )
        if rows:
            for r in rows:
                tid = r["thread_id"]
                parts = tid.split("/", 1)
                sidechains.append({
                    "thread_id": tid,
                    "agent_name": parts[1] if len(parts) > 1 else tid,
                })
    except Exception as e:
        logger.warning(f"读取旁链失败: {e}")

    return {
        "session_id": session_id,
        "sidechains": sidechains,
        "message": "旁链详情在 Phase 2 后续迭代中扩展",
    }

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

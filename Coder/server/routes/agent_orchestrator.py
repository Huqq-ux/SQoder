import logging
from fastapi import APIRouter, Request
from Coder.server.schemas import OrchestratorExecuteRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/execute")
async def execute_task(req: OrchestratorExecuteRequest, request: Request):
    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    result = await orch.run(req.task)

    return {
        "success": result["success"],
        "answer": result["answer"],
        "error": result["error"],
        "duration_seconds": result["duration_seconds"],
    }


@router.post("/execute-stream")
async def execute_task_stream(req: OrchestratorExecuteRequest, request: Request):
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    import time

    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()

    async def event_stream():
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        start_time = time.time()
        try:
            result = await orch.run(req.task)
            yield f"data: {json.dumps({'type': 'result', 'success': result['success'], 'answer': result['answer'], 'error': result['error'], 'duration_seconds': result['duration_seconds']})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

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




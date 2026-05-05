import logging
from fastapi import APIRouter, Request
from Coder.server.schemas import MultiAgentExecuteRequest, MultiAgentAddAgentRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def multi_agent_status(request: Request):
    crew = getattr(request.app.state, "multi_agent_crew", None)
    initialized = crew is not None
    agent_count = len(crew.registry.list_all()) if crew else 0
    return {"initialized": initialized, "agent_count": agent_count}


@router.get("/agents")
async def list_agents(request: Request):
    crew = request.app.state.multi_agent_crew
    agents = crew.registry.list_all()
    result = []
    for agent in agents:
        config = agent.config
        result.append({
            "name": config.name,
            "role": config.role.value if hasattr(config.role, "value") else str(config.role),
            "status": agent.status.value if hasattr(agent.status, "value") else str(agent.status),
            "capabilities": [c.value if hasattr(c, "value") else str(c) for c in config.capabilities],
            "description": config.description,
        })
    return {"agents": result}


@router.post("/add-agent")
async def add_agent(req: MultiAgentAddAgentRequest, request: Request):
    crew = request.app.state.multi_agent_crew

    role_map = {
        "coder": crew.add_coder,
        "searcher": crew.add_searcher,
        "ops": crew.add_ops,
        "sop_executor": crew.add_sop_executor,
        "skill_executor": crew.add_skill_executor,
    }

    if req.role not in role_map:
        return {"error": f"Unknown role: {req.role}"}

    fn = role_map[req.role]
    fn(name=req.name, custom_prompt=req.custom_prompt or "")
    return {"status": "added", "name": req.name, "role": req.role}


@router.post("/execute")
async def execute_task(req: MultiAgentExecuteRequest, request: Request):
    crew = request.app.state.multi_agent_crew
    from Coder.multi_agent.types import ProcessType

    process = (
        ProcessType.HIERARCHICAL
        if req.process_type == "hierarchical"
        else ProcessType.SEQUENTIAL
    )

    result = crew.kickoff(req.task, process_type=process)

    return {
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "duration_seconds": result.duration_seconds,
        "agent_traces": result.agent_traces,
        "sub_results": result.sub_results,
    }


@router.get("/history")
async def execution_history(request: Request):
    crew = request.app.state.multi_agent_crew
    history = crew.get_history()
    return {
        "history": [
            {
                "success": r.success,
                "result": r.result,
                "error": r.error,
                "duration_seconds": r.duration_seconds,
                "agent_traces": r.agent_traces,
            }
            for r in history
        ]
    }

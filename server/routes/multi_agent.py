import logging
from fastapi import APIRouter, Request
from Coder.server.schemas import MultiAgentExecuteRequest, MultiAgentAddAgentRequest
from Coder.multi_agent.types import CrewResult

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_user_answer(result: CrewResult) -> str:
    if not result or not result.result:
        return result.error or "无结果"

    if isinstance(result.result, str):
        return result.result

    if isinstance(result.result, dict):
        integrated = result.result.get("integrated_answer") or result.result.get("result")
        if integrated and isinstance(integrated, str) and integrated.strip():
            return integrated.strip()

        sub_results = result.result.get("sub_results", [])
        if sub_results:
            lines = []
            for i, s in enumerate(sub_results):
                result_text = s.get("result")
                if result_text and isinstance(result_text, str) and result_text.strip():
                    label = s.get("agent", f"子任务 {i + 1}")
                    lines.append(f"**【{label}】**\n{result_text.strip()}")
            if lines:
                return "\n\n---\n\n".join(lines)

    return str(result.result)


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

    stop_key = f"stop_flag:multi_agent"
    from Coder.storage.redis_client import RedisManager
    await RedisManager.client().set(stop_key, "0")

    result = await crew.kickoff(req.task, process_type=process)

    answer = _extract_user_answer(result)

    return {
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "duration_seconds": result.duration_seconds,
        "agent_traces": result.agent_traces,
        "sub_results": [
            {
                "task_id": s.get("task_id", ""),
                "description": s.get("description", ""),
                "status": s.get("status", ""),
                "result": s.get("result", ""),
                "error": s.get("error", ""),
                "agent": s.get("agent", ""),
            }
            for s in result.sub_results
        ],
        "answer": answer,
    }


@router.get("/history")
async def execution_history(request: Request):
    crew = request.app.state.multi_agent_crew
    from Coder.storage.redis_client import RedisManager

    cached = await RedisManager.get_json("multi_agent:history")
    if cached is not None:
        return {"history": cached}

    history = crew.get_history()
    result = [
        {
            "success": r.success,
            "result": r.result,
            "error": r.error,
            "duration_seconds": r.duration_seconds,
            "agent_traces": r.agent_traces,
        }
        for r in history
    ]
    await RedisManager.set_json("multi_agent:history", result, ttl=600)
    return {"history": result}


@router.post("/stop")
async def stop_execution(request: Request):
    from Coder.storage.redis_client import RedisManager
    stop_key = f"stop_flag:multi_agent"
    await RedisManager.client().set(stop_key, "1")
    return {"status": "stop_requested"}

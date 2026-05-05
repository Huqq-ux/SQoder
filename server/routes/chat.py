import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from Coder.server.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stream")
async def chat_stream(req: ChatRequest, request: Request):
    agent = request.app.state.agent
    base_config = request.app.state.config
    sop_context = request.app.state.sop_context

    config = base_config.copy() if base_config else {}
    thread_id = req.thread_id or config.get("configurable", {}).get("thread_id", "default")
    if "configurable" not in config:
        config["configurable"] = {}
    config["configurable"]["thread_id"] = thread_id

    stop_key = thread_id
    request.app.state.stop_flags[stop_key] = False

    from Coder.agent.code_agent import stream_agent_response
    from Coder.sop.skill_nl_invoker import SkillNLInvoker, InvokeStage

    async def event_generator():
        try:
            async for event in stream_agent_response(
                agent, config, req.message, sop_context
            ):
                if request.app.state.stop_flags.get(stop_key, False):
                    yield f"data: {json.dumps({'type': 'content', 'content': '[回答已停止]'}, ensure_ascii=False)}\n\n"
                    break

                if await request.is_disconnected():
                    break

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            request.app.state.stop_flags[stop_key] = False

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stop")
async def stop_generation(req: ChatRequest, request: Request):
    thread_id = req.thread_id or "default"
    request.app.state.stop_flags[thread_id] = True
    return {"status": "stopped"}


@router.post("/skill-detect")
async def detect_skill(req: ChatRequest, request: Request):
    from Coder.sop.skill_nl_invoker import SkillNLInvoker
    invoker = SkillNLInvoker()
    found, skill_meta, score = invoker.detect_skill_call(req.message)

    if not found:
        return {"found": False}

    params, missing = invoker.extract_params(req.message, skill_meta)
    needs_confirm = invoker.needs_confirmation(skill_meta)

    return {
        "found": True,
        "skill_name": skill_meta.name,
        "display_name": skill_meta.display_name,
        "description": skill_meta.description,
        "matched_params": params,
        "missing_params": missing,
        "needs_confirmation": needs_confirm,
        "score": score,
    }

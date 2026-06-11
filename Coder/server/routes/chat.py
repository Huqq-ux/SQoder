import re
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from Coder.server.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()

_SAFE_THREAD_ID_RE = re.compile(r'^[\w\-\.]{1,128}$')


@router.post("/stream")
async def chat_stream(req: ChatRequest, request: Request):
    agent_mgr = request.app.state.agent_mgr
    agent, base_config = await agent_mgr.get_agent(
        req.thread_id or "default"
    )

    config = base_config.copy() if base_config else {}
    thread_id = req.thread_id or config.get("configurable", {}).get("thread_id", "default")
    if not _SAFE_THREAD_ID_RE.match(thread_id):
        thread_id = "default"
    if "configurable" not in config:
        config["configurable"] = {}
    config["configurable"]["thread_id"] = thread_id

    stop_key = f"stop_flag:{thread_id}"
    from Coder.storage.redis_client import RedisManager
    await RedisManager.client().set(stop_key, "0")

    from Coder.agent.code_agent import stream_agent_response
    from Coder.tools.knowledge_toolkit import set_knowledge_course

    # Set course context for scoped knowledge retrieval
    if req.course_id:
        set_knowledge_course(req.course_id)
    else:
        set_knowledge_course(None)

    async def event_generator():
        try:
            async for event in stream_agent_response(
                agent, config, req.message
            ):
                if await RedisManager.client().get(stop_key) == "1":
                    yield f"data: {json.dumps({'type': 'content', 'content': '[回答已停止]'}, ensure_ascii=False)}\n\n"
                    break

                if await request.is_disconnected():
                    break

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

            # 首次对话时自动更新会话标题
            try:
                session_mgr = request.app.state.session_mgr
                await session_mgr.update_session_from_messages(
                    thread_id,
                    [{"role": "user", "content": req.message}],
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            await RedisManager.client().set(stop_key, "0")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stop/{thread_id}")
async def stop_chat(request: Request, thread_id: str):
    if not _SAFE_THREAD_ID_RE.match(thread_id):
        return {"status": "error", "message": "无效的 thread_id"}
    from Coder.storage.redis_client import RedisManager
    stop_key = f"stop_flag:{thread_id}"
    await RedisManager.client().set(stop_key, "1")
    return {"status": "stop_requested", "thread_id": thread_id}

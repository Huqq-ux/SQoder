import logging
from fastapi import APIRouter, Request
from Coder.server.schemas import SessionCreate

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_session_mgr(request: Request):
    return request.app.state.session_mgr


@router.get("/")
async def list_sessions(request: Request):
    mgr = _get_session_mgr(request)
    sessions = await mgr.list_sessions()
    return {"sessions": sessions}


@router.post("/")
async def create_session(request: Request, body: SessionCreate = None):
    mgr = _get_session_mgr(request)
    session = await mgr.create_session(title=body.title if body else None)
    return session


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str):
    mgr = _get_session_mgr(request)
    session = await mgr.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return session


@router.get("/{session_id}/messages")
async def get_messages(request: Request, session_id: str):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from Coder.storage.db import DatabaseManager
    from langchain_core.runnables import RunnableConfig
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

    checkpointer = AsyncPostgresSaver(DatabaseManager.pool())
    config = RunnableConfig(configurable={"thread_id": session_id})
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
            return {"messages": []}

        checkpoint = checkpoint_tuple.checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages_raw = channel_values.get("messages", [])

        if not messages_raw:
            return {"messages": []}

        result = []
        for msg in messages_raw:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                content = msg.content or ""
                parts = []
                reasoning = msg.additional_kwargs.get("reasoning_content", "")
                if reasoning:
                    parts.append({"type": "thinking", "content": reasoning})
                tool_calls = msg.additional_kwargs.get("tool_calls", [])
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", "")
                    if name:
                        parts.append({"type": "tool_call", "name": name, "args": args})
                if content:
                    parts.append({"type": "content", "content": content})
                result.append({
                    "role": "assistant",
                    "content": content,
                    "parts": parts if parts else None,
                })
            elif isinstance(msg, ToolMessage):
                pass

        return {"messages": result}
    except Exception as e:
        logger.warning(f"从checkpoint恢复消息失败: {e}")
        return {"messages": []}


@router.delete("/{session_id}")
async def delete_session(request: Request, session_id: str):
    mgr = _get_session_mgr(request)
    ok = await mgr.delete_session(session_id)
    return {"deleted": ok}

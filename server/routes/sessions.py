import logging
from fastapi import APIRouter
from Coder.server.schemas import SessionCreate
from Coder.tools.session_manager import SessionManager
from Coder.tools.file_saver import FileSaver

logger = logging.getLogger(__name__)
router = APIRouter()
mgr = SessionManager()


@router.get("/")
async def list_sessions():
    sessions = mgr.list_sessions()
    return {"sessions": sessions}


@router.post("/")
async def create_session(body: SessionCreate = None):
    session = mgr.create_session(title=body.title if body else None)
    return session


@router.get("/{session_id}")
async def get_session(session_id: str):
    session = mgr.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return session


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    checkpointer = FileSaver()
    messages = mgr.get_session_messages_from_checkpoint(session_id, checkpointer)
    return {"messages": messages}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    ok = mgr.delete_session(session_id)
    return {"deleted": ok}

import os
import json
import uuid
import shutil
import time
import logging
from datetime import datetime
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from Coder.tools.file_saver import FileSaver

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(__file__), "..", "checkpoints"
            )
            base_path = os.path.normpath(base_path)
        self.base_path = base_path
        self.sessions_file = os.path.join(base_path, "sessions.json")
        os.makedirs(base_path, exist_ok=True)

    def _load_sessions_meta(self) -> dict:
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"会话元数据加载失败: {e}")
        return {"sessions": []}

    def _save_sessions_meta(self, data: dict):
        try:
            with open(self.sessions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"会话元数据保存失败: {e}")

    def list_sessions(self) -> list:
        data = self._load_sessions_meta()
        sessions = data.get("sessions", [])
        sessions.sort(key=lambda s: s.get("updated_ts", 0), reverse=True)
        return sessions

    def create_session(self, title: str = None) -> dict:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session = {
            "session_id": session_id,
            "title": title or "新会话",
            "created_at": now,
            "updated_at": now,
            "updated_ts": time.time(),
            "message_count": 0,
            "preview": "",
        }
        data = self._load_sessions_meta()
        data["sessions"].append(session)
        self._save_sessions_meta(data)
        logger.info(f"新会话已创建: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        data = self._load_sessions_meta()
        for s in data["sessions"]:
            if s["session_id"] == session_id:
                return s
        return None

    def update_session(self, session_id: str, updates: dict):
        data = self._load_sessions_meta()
        for s in data["sessions"]:
            if s["session_id"] == session_id:
                s.update(updates)
                s["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                s["updated_ts"] = time.time()
                self._save_sessions_meta(data)
                return True
        return False

    def delete_session(self, session_id: str) -> bool:
        data = self._load_sessions_meta()
        original_len = len(data["sessions"])
        data["sessions"] = [
            s for s in data["sessions"] if s["session_id"] != session_id
        ]
        if len(data["sessions"]) == original_len:
            return False

        self._save_sessions_meta(data)

        session_dir = os.path.join(self.base_path, session_id)
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
                logger.info(f"会话目录已删除: {session_dir}")
            except Exception as e:
                logger.warning(f"会话目录删除失败: {e}")

        return True

    def update_session_from_messages(self, session_id: str, messages: list):
        user_msgs = [m for m in messages if m.get("role") == "user"]
        title = None
        preview = None

        if user_msgs:
            first_user = user_msgs[0].get("content", "")
            if first_user:
                title = first_user[:30]
                if len(first_user) > 30:
                    title += "..."
                preview = first_user[:80]

        updates = {
            "message_count": len(messages),
        }
        if title:
            current = self.get_session(session_id)
            if current and (current.get("title") == "新会话" or not current.get("title")):
                updates["title"] = title
        if preview:
            updates["preview"] = preview

        self.update_session(session_id, updates)

    def get_session_messages_from_checkpoint(
        self, session_id: str, checkpointer: FileSaver
    ) -> list:
        config = RunnableConfig(
            configurable={"thread_id": session_id}
        )
        try:
            checkpoint_tuple = checkpointer.get_tuple(config)
            if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
                return []

            checkpoint = checkpoint_tuple.checkpoint
            channel_values = checkpoint.get("channel_values", {})
            messages_raw = channel_values.get("messages", [])

            if not messages_raw:
                return []

            result = []
            for msg in messages_raw:
                if isinstance(msg, HumanMessage):
                    result.append({
                        "role": "user",
                        "content": msg.content,
                    })
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
                            parts.append({
                                "type": "tool_call",
                                "name": name,
                                "args": args,
                            })
                    if content:
                        parts.append({"type": "content", "content": content})
                    result.append({
                        "role": "assistant",
                        "content": content,
                        "parts": parts if parts else None,
                    })
                elif isinstance(msg, ToolMessage):
                    pass

            return result

        except Exception as e:
            logger.warning(f"从checkpoint恢复消息失败: {e}")
            return []

    def migrate_legacy_session(self, old_thread_id: str = "streamlit"):
        data = self._load_sessions_meta()

        old_dir = os.path.join(self.base_path, old_thread_id)
        if not os.path.exists(old_dir):
            return None

        existing = [s for s in data["sessions"] if s["session_id"] == old_thread_id]
        if existing:
            sess = existing[0]
            if sess.get("title") == "历史会话":
                self._try_extract_title(old_thread_id, sess)
                self._save_sessions_meta(data)
            return sess

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "历史会话"
        preview = "从旧版本迁移的会话"
        message_count = 0

        session = {
            "session_id": old_thread_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "updated_ts": time.time(),
            "message_count": message_count,
            "preview": preview,
        }
        data["sessions"].append(session)
        self._save_sessions_meta(data)

        self._try_extract_title(old_thread_id, session)
        self._save_sessions_meta(data)

        logger.info(f"旧会话已迁移: {old_thread_id} (标题: {session['title']})")
        return session

    def _try_extract_title(self, session_id: str, session: dict):
        try:
            from Coder.tools.file_saver import FileSaver
            checkpointer = FileSaver(base_path=self.base_path)
            messages = self.get_session_messages_from_checkpoint(session_id, checkpointer)
            if messages:
                user_msgs = [m for m in messages if m.get("role") == "user"]
                if user_msgs:
                    first = user_msgs[0].get("content", "")
                    if first:
                        session["title"] = first[:30]
                        if len(first) > 30:
                            session["title"] += "..."
                        session["preview"] = first[:80]
                session["message_count"] = len(messages)
        except Exception as e:
            logger.warning(f"提取会话标题失败: {e}")

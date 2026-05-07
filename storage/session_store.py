import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from psycopg.types.json import Jsonb

from Coder.storage.db import DatabaseManager
from Coder.storage.redis_client import RedisManager

logger = logging.getLogger(__name__)

SESSION_CACHE_TTL = 300
SESSION_LIST_CACHE_KEY = "sessions:list"


class PgSessionManager:
    async def list_sessions(self) -> list:
        cached = await RedisManager.get_json(SESSION_LIST_CACHE_KEY)
        if cached is not None:
            return cached

        rows = await DatabaseManager.fetch(
            "SELECT session_id, title, created_at, updated_at, message_count, preview "
            "FROM sessions ORDER BY updated_at DESC"
        )
        result = []
        for row in rows:
            result.append({
                "session_id": row["session_id"],
                "title": row["title"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
                "updated_ts": row["updated_at"].timestamp() if row["updated_at"] else 0,
                "message_count": row["message_count"],
                "preview": row["preview"],
            })
        await RedisManager.set_json(SESSION_LIST_CACHE_KEY, result, ttl=SESSION_CACHE_TTL)
        return result

    async def create_session(self, title: str = None) -> dict:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        await DatabaseManager.execute(
            "INSERT INTO sessions (session_id, title, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s)",
            session_id, title or "新会话", now, now,
        )

        await RedisManager.delete(SESSION_LIST_CACHE_KEY)

        return {
            "session_id": session_id,
            "title": title or "新会话",
            "created_at": now_str,
            "updated_at": now_str,
            "updated_ts": time.time(),
            "message_count": 0,
            "preview": "",
        }

    async def get_session(self, session_id: str) -> Optional[dict]:
        cached = await RedisManager.get_json(f"session:{session_id}")
        if cached is not None:
            return cached

        row = await DatabaseManager.fetchrow(
            "SELECT session_id, title, created_at, updated_at, message_count, preview "
            "FROM sessions WHERE session_id = %s",
            session_id,
        )

        if not row:
            return None

        result = {
            "session_id": row["session_id"],
            "title": row["title"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else "",
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
            "updated_ts": row["updated_at"].timestamp() if row["updated_at"] else 0,
            "message_count": row["message_count"],
            "preview": row["preview"],
        }
        await RedisManager.set_json(f"session:{session_id}", result, ttl=SESSION_CACHE_TTL)
        return result

    async def update_session(self, session_id: str, updates: dict):
        now = datetime.now(timezone.utc)

        set_clauses = []
        args = []

        field_map = {
            "title": "title",
            "message_count": "message_count",
            "preview": "preview",
        }

        for key, col in field_map.items():
            if key in updates:
                set_clauses.append(f"{col} = %s")
                args.append(updates[key])

        set_clauses.append("updated_at = %s")
        args.append(now)
        args.append(session_id)

        sql = f"UPDATE sessions SET {', '.join(set_clauses)} WHERE session_id = %s"

        await DatabaseManager.execute(sql, *args)
        await RedisManager.delete(SESSION_LIST_CACHE_KEY, f"session:{session_id}")

    async def delete_session(self, session_id: str) -> bool:
        result = await DatabaseManager.execute(
            "DELETE FROM sessions WHERE session_id = %s",
            session_id,
        )
        deleted = result != "DELETE 0"
        if deleted:
            await RedisManager.delete(SESSION_LIST_CACHE_KEY, f"session:{session_id}")
        return deleted

    async def update_session_from_messages(self, session_id: str, messages: list):
        user_msgs = [m for m in messages if m.get("role") == "user"]
        updates = {"message_count": len(messages)}

        if user_msgs:
            first_user = user_msgs[0].get("content", "")
            if first_user:
                title = first_user[:30]
                if len(first_user) > 30:
                    title += "..."
                current = await self.get_session(session_id)
                if current and (current.get("title") == "新会话" or not current.get("title")):
                    updates["title"] = title
                updates["preview"] = first_user[:80]

        await self.update_session(session_id, updates)

    async def save_message(self, session_id: str, role: str, content: str, parts: list = None):
        await DatabaseManager.execute(
            "INSERT INTO messages (session_id, role, content, parts) VALUES (%s, %s, %s, %s)",
            session_id, role, content, Jsonb(parts) if parts else None,
        )
        await RedisManager.delete(f"session:{session_id}", SESSION_LIST_CACHE_KEY)

    async def get_messages(self, session_id: str) -> list:
        rows = await DatabaseManager.fetch(
            "SELECT role, content, parts FROM messages "
            "WHERE session_id = %s ORDER BY created_at ASC",
            session_id,
        )

        result = []
        for row in rows:
            msg = {"role": row["role"], "content": row["content"]}
            if row["parts"]:
                msg["parts"] = row["parts"]
            result.append(msg)
        return result

    async def migrate_legacy_session(self, old_thread_id: str = "streamlit"):
        existing = await self.get_session(old_thread_id)
        if existing:
            if existing.get("title") == "历史会话":
                await self._try_extract_title(old_thread_id, existing)
            return existing

        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        session = {
            "session_id": old_thread_id,
            "title": "历史会话",
            "created_at": now_str,
            "updated_at": now_str,
            "updated_ts": time.time(),
            "message_count": 0,
            "preview": "从旧版本迁移的会话",
        }
        await DatabaseManager.execute(
            "INSERT INTO sessions (session_id, title, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (session_id) DO NOTHING",
            old_thread_id, "历史会话", now, now,
        )
        await RedisManager.delete(SESSION_LIST_CACHE_KEY)
        logger.info(f"旧会话已迁移: {old_thread_id}")
        return session

    async def _try_extract_title(self, session_id: str, session: dict):
        pass

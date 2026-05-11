import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

_DEFAULT_LOCAL_DB = "postgresql://coder:coder123@localhost:5432/coder_db"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = _DEFAULT_LOCAL_DB
    logger.warning(
        "环境变量 DATABASE_URL 未设置，使用本地默认连接。"
        "生产环境请务必通过环境变量指定安全的数据库连接："
        "set DATABASE_URL=postgresql://user:pass@host:port/dbname"
    )

_schema_sql = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(256) NOT NULL DEFAULT '新会话',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER NOT NULL DEFAULT 0,
    preview TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    parts JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS skills (
    name VARCHAR(128) PRIMARY KEY,
    display_name VARCHAR(256) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category VARCHAR(64) NOT NULL DEFAULT '',
    parameters JSONB NOT NULL DEFAULT '[]',
    tags JSONB NOT NULL DEFAULT '[]',
    code TEXT NOT NULL DEFAULT '',
    version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    author VARCHAR(128) NOT NULL DEFAULT '',
    source VARCHAR(32) NOT NULL DEFAULT 'user',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at VARCHAR(32) NOT NULL DEFAULT '',
    updated_at VARCHAR(32) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled);
"""


class DatabaseManager:
    _pool: Optional[AsyncConnectionPool] = None

    @classmethod
    def get_url(cls) -> str:
        return DATABASE_URL

    @classmethod
    async def init_pool(cls) -> AsyncConnectionPool:
        if cls._pool is not None:
            return cls._pool

        cls._pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=2,
            max_size=10,
            kwargs={"autocommit": True, "row_factory": dict_row},
            max_lifetime=1800,
        )
        await cls._pool.open()
        await cls._pool.wait()
        logger.info("PostgreSQL 连接池已创建")
        await cls._init_schema()
        await cls._setup_checkpoint_tables()
        return cls._pool

    @classmethod
    async def _init_schema(cls):
        async with cls._pool.connection() as conn:
            await conn.execute(_schema_sql)
        logger.info("数据库表结构已初始化")

    @classmethod
    async def _setup_checkpoint_tables(cls):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with await AsyncConnection.connect(
            DATABASE_URL, autocommit=True, row_factory=dict_row
        ) as conn:
            saver = AsyncPostgresSaver(conn)
            await saver.setup()
        logger.info("Checkpoint 表已初始化")

    @classmethod
    async def close_pool(cls):
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None
            logger.info("PostgreSQL 连接池已关闭")

    @classmethod
    def pool(cls) -> AsyncConnectionPool:
        if cls._pool is None:
            raise RuntimeError("数据库连接池未初始化")
        return cls._pool

    @classmethod
    @asynccontextmanager
    async def connection(cls) -> AsyncIterator[AsyncConnection]:
        async with cls.pool().connection() as conn:
            yield conn

    @classmethod
    async def fetchrow(cls, query: str, *args):
        async with cls.connection() as conn:
            cur = await conn.execute(query, args)
            return await cur.fetchone()

    @classmethod
    async def fetch(cls, query: str, *args):
        async with cls.connection() as conn:
            cur = await conn.execute(query, args)
            return await cur.fetchall()

    @classmethod
    async def execute(cls, query: str, *args) -> str:
        async with cls.connection() as conn:
            cur = await conn.execute(query, args)
            return cur.statusmessage or ""

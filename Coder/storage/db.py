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
    logger.info("DATABASE_URL 未设置，使用本地数据库 %s", _DEFAULT_LOCAL_DB)

_schema_sql = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(256) NOT NULL DEFAULT '新会话',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER NOT NULL DEFAULT 0,
    preview TEXT NOT NULL DEFAULT '',
    mode VARCHAR(20) NOT NULL DEFAULT 'chat',
    course_id VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_course_id ON sessions(course_id);

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

CREATE TABLE IF NOT EXISTS mcp_servers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(200),
    description     TEXT NOT NULL DEFAULT '',
    transport       VARCHAR(20) NOT NULL DEFAULT 'stdio',
    command         VARCHAR(500),
    args            JSONB NOT NULL DEFAULT '[]',
    url             VARCHAR(500),
    env             JSONB NOT NULL DEFAULT '{}',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    is_local        BOOLEAN NOT NULL DEFAULT FALSE,
    source          VARCHAR(20) NOT NULL DEFAULT 'manual',
    registry_id     VARCHAR(200),
    tools_allowlist JSONB,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_enabled ON mcp_servers(enabled);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_source ON mcp_servers(source);

CREATE TABLE IF NOT EXISTS courses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(64) NOT NULL UNIQUE,
    name            VARCHAR(256) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    semester        VARCHAR(64) NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_updated_at ON courses(updated_at DESC);

CREATE TABLE IF NOT EXISTS course_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    filename        VARCHAR(512) NOT NULL,
    file_type       VARCHAR(16) NOT NULL,
    file_size       BIGINT NOT NULL DEFAULT 0,
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    index_path      VARCHAR(1024) NOT NULL DEFAULT '',
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_course_files_course ON course_files(course_id);

CREATE TABLE IF NOT EXISTS knowledge_points (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name            VARCHAR(256) NOT NULL,
    section         VARCHAR(128) NOT NULL DEFAULT '',
    chunk_content   TEXT NOT NULL DEFAULT '',
    source_file     VARCHAR(512) NOT NULL DEFAULT '',
    source_page     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kp_course ON knowledge_points(course_id);
CREATE INDEX IF NOT EXISTS idx_kp_section ON knowledge_points(course_id, section);

CREATE TABLE IF NOT EXISTS learning_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    kp_id           UUID NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE,
    status          VARCHAR(16) NOT NULL DEFAULT 'unlearned',
    mastery_score   REAL NOT NULL DEFAULT 0.0,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_reviewed   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(course_id, kp_id)
);

CREATE INDEX IF NOT EXISTS idx_lp_course_status ON learning_progress(course_id, status);

CREATE TABLE IF NOT EXISTS notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    kp_id           UUID REFERENCES knowledge_points(id) ON DELETE SET NULL,
    title           VARCHAR(256) NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_course ON notes(course_id);

CREATE TABLE IF NOT EXISTS wrong_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    kp_id           UUID REFERENCES knowledge_points(id) ON DELETE SET NULL,
    question        TEXT NOT NULL DEFAULT '',
    user_answer     TEXT NOT NULL DEFAULT '',
    correct_answer  TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wrong_answers_course ON wrong_answers(course_id);
"""

_mode_migration_sql = """
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS mode VARCHAR(20) NOT NULL DEFAULT 'chat';
"""

_course_id_migration_sql = """
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS course_id VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_sessions_course_id ON sessions(course_id);
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
            open=False,
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
            await conn.execute(_mode_migration_sql)
            await conn.execute(_course_id_migration_sql)
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

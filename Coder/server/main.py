import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Coder.server.routes import chat, sessions, knowledge, sop, skills, agent_orchestrator, mcp

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing storage backends...")
    from Coder.storage.db import DatabaseManager
    from Coder.storage.redis_client import RedisManager
    from Coder.storage.session_store import PgSessionManager
    from Coder.storage.skill_store import PgSkillStore

    await RedisManager.init_client()
    await DatabaseManager.init_pool()

    session_mgr = PgSessionManager()
    skill_store = PgSkillStore()
    app.state.session_mgr = session_mgr
    app.state.skill_store = skill_store
    app.state.stop_flags = {}

    logger.info("Migrating skills from file store to PostgreSQL...")
    try:
        from Coder.tools.skill_store import SkillStore as FileSkillStore
        file_store = FileSkillStore()
        file_skills = file_store.list_skills(enabled_only=False)
        for skill in file_skills:
            exists = await skill_store.exists(skill.name)
            if not exists:
                await skill_store.save_skill(skill)
                logger.info(f"Skill migrated: {skill.name}")
        logger.info(f"Skill migration complete: {len(file_skills)} checked")
    except Exception as e:
        logger.warning(f"Skill migration skipped: {e}")

    logger.info("Initializing MCP Manager...")
    from Coder.MCP.manager import MCPManager
    mcp_manager = MCPManager()
    await mcp_manager.initialize()
    app.state.mcp_manager = mcp_manager

    logger.info("Initializing Agent Manager...")
    from Coder.agent.agent_manager import AgentManager
    agent_mgr = AgentManager(mcp_manager)
    await agent_mgr.get_agent(f"server_{uuid.uuid4().hex[:8]}")
    app.state.agent_mgr = agent_mgr

    logger.info("Agent Manager initialized")
    yield
    logger.info("Shutting down...")
    try:
        await agent_mgr.close()
    except Exception:
        pass
    try:
        await mcp_manager.close()
    except Exception:
        pass
    await RedisManager.close_client()
    await DatabaseManager.close_pool()


app = FastAPI(
    title="AI Code Assistant",
    version="0.1.0",
    lifespan=lifespan,
    max_request_size=10 * 1024 * 1024,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(sop.router, prefix="/api/sop", tags=["SOP"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
app.include_router(agent_orchestrator.router, prefix="/api/agent-orchestrator", tags=["Agent-Orchestrator"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP"])

import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Coder.server.routes import chat, sessions, knowledge, sop, skills, multi_agent

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing agent...")
    from Coder.agent.code_agent import create_code_agent
    thread_id = f"server_{uuid.uuid4().hex[:8]}"
    agent, config, mcp_client, sop_context = await create_code_agent(
        thread_id=thread_id
    )
    app.state.agent = agent
    app.state.config = config
    app.state.mcp_client = mcp_client
    app.state.sop_context = sop_context
    app.state.stop_flags = {}

    from Coder.multi_agent.crew import MultiAgentCrew
    from Coder.multi_agent.types import CrewConfig, ProcessType
    crew_config = CrewConfig(
        process_type=ProcessType.HIERARCHICAL,
        verbose=True,
    )
    multi_crew = MultiAgentCrew(crew_config=crew_config)
    multi_crew.initialize_default_crew()
    app.state.multi_agent_crew = multi_crew

    logger.info("Agent and multi-agent crew initialized")
    yield
    logger.info("Shutting down...")
    if app.state.mcp_client:
        try:
            await app.state.mcp_client.close()
        except Exception:
            pass


app = FastAPI(title="AI Code Assistant", version="0.1.0", lifespan=lifespan)

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
app.include_router(multi_agent.router, prefix="/api/multi-agent", tags=["Multi-Agent"])

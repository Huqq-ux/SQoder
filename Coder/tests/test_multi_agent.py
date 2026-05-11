import pytest
from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentConfig,
)


class TestTypes:
    def test_agent_role_enum_values(self):
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.SEARCHER.value == "searcher"
        assert AgentRole.OPS.value == "ops"

    def test_agent_config_defaults(self):
        config = AgentConfig(
            role=AgentRole.CODER,
            name="test_coder",
            display_name="Test Coder",
            system_prompt="You are a coder.",
            description="Test agent",
        )
        assert config.role == AgentRole.CODER
        assert config.name == "test_coder"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096
        assert config.timeout_seconds == 120.0


class TestIntegrations:
    def test_build_system_prompt_for_coder(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.CODER)
        assert "编程" in prompt

    def test_build_system_prompt_for_searcher(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.SEARCHER)
        assert "搜索" in prompt

    def test_get_skill_tools(self):
        from Coder.multi_agent.integrations import get_skill_tools
        tools = get_skill_tools()
        assert len(tools) == 2

    def test_get_sop_tools(self):
        from Coder.multi_agent.integrations import get_sop_tools
        tools = get_sop_tools()
        assert len(tools) == 2


class TestAgentBuilder:
    def test_create_builder(self):
        from Coder.multi_agent.agent_builder import AgentBuilder
        builder = AgentBuilder()
        assert builder is not None
        assert builder.checkpointer is not None


class TestAgentOrchestrator:
    def test_create_orchestrator(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        assert orch is not None
        assert orch._timeout == 300.0

    def test_extract_content_string(self):
        from Coder.multi_agent.agent_orchestrator import _extract_content
        assert _extract_content("hello") == "hello"
        assert _extract_content(None) == ""

    def test_extract_content_aimessage(self):
        from Coder.multi_agent.agent_orchestrator import _extract_content
        from langchain_core.messages import AIMessage
        msg = AIMessage(content="test answer")
        result = _extract_content({"messages": [msg]})
        assert "test answer" in result

    def test_run_invalid_returns_error(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        import asyncio
        async def _run():
            orch = AgentOrchestrator(timeout=0.001)
            return await orch.run("test")
        result = asyncio.run(_run())
        assert result["success"] is False
        assert result["error"] is not None

    def test_module_exports(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        assert AgentOrchestrator is not None


class TestModuleExports:
    def test_multi_agent_init_exports(self):
        from Coder.multi_agent import (
            AgentRole,
            AgentConfig,
            AgentBuilder,
            AgentOrchestrator,
        )
        assert AgentRole is not None
        assert AgentBuilder is not None
        assert AgentOrchestrator is not None

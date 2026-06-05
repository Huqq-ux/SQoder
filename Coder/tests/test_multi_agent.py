import pytest
from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentConfig,
)


class TestAgentConfigs:
    def test_default_configs_have_all_roles(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        assert AgentRole.CODER in DEFAULT_AGENT_CONFIGS
        assert AgentRole.SEARCHER in DEFAULT_AGENT_CONFIGS
        assert AgentRole.OPS in DEFAULT_AGENT_CONFIGS
        assert AgentRole.SKILL_EXECUTOR in DEFAULT_AGENT_CONFIGS

    def test_coder_has_no_web_search_reference(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        coder_config = DEFAULT_AGENT_CONFIGS[AgentRole.CODER]
        assert "web_search" not in coder_config.system_prompt
        assert "web_search_toolkit" not in coder_config.tools

    def test_each_config_has_timeout(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        for role, config in DEFAULT_AGENT_CONFIGS.items():
            assert config.timeout_seconds > 0, f"{role} missing timeout"

    def test_searcher_has_web_search(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        searcher_config = DEFAULT_AGENT_CONFIGS[AgentRole.SEARCHER]
        assert "web_search_toolkit" in searcher_config.tools


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
        assert "搜索" in prompt or "检索" in prompt

    def test_build_system_prompt_for_unknown_role_fallback(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.GENERAL)
        assert len(prompt) > 0

    def test_get_skill_tools_returns_two_tools(self):
        from Coder.multi_agent.integrations import get_skill_tools
        tools = get_skill_tools()
        assert len(tools) == 2

    def test_execute_skill_by_name_has_params_param(self):
        from Coder.multi_agent.integrations import get_skill_tools
        import inspect

        tools = get_skill_tools()
        exec_tool = [t for t in tools if t.name == "execute_skill_by_name"][0]
        sig = inspect.signature(exec_tool.func)
        assert "params" in sig.parameters


class TestAgentBuilder:
    def test_create_builder(self):
        from Coder.multi_agent.agent_builder import AgentBuilder
        builder = AgentBuilder()
        assert builder is not None
        assert builder.checkpointer is not None

    def test_build_agent_with_config(self):
        from Coder.multi_agent.agent_builder import AgentBuilder
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        builder = AgentBuilder()
        config = DEFAULT_AGENT_CONFIGS[AgentRole.CODER]
        agent = builder.build_agent(config)
        assert agent is not None
        timeout = getattr(agent, "_agent_timeout", None)
        assert timeout == config.timeout_seconds


class TestAgentOrchestrator:
    def test_create_orchestrator(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        assert orch is not None
        assert orch._timeout == 300.0
        assert len(orch._configs) >= 4

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
        assert "tool_calls" in result

    def test_response_includes_tool_calls_field(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        import asyncio

        async def _run():
            orch = AgentOrchestrator(timeout=0.001)
            return await orch.run("test")

        result = asyncio.run(_run())
        assert "tool_calls" in result
        assert isinstance(result["tool_calls"], list)


class TestModuleExports:
    def test_multi_agent_init_exports(self):
        from Coder.multi_agent import (
            AgentRole,
            AgentConfig,
            AgentBuilder,
            AgentOrchestrator,
            DEFAULT_AGENT_CONFIGS,
        )
        assert AgentRole is not None
        assert AgentBuilder is not None
        assert AgentOrchestrator is not None
        assert DEFAULT_AGENT_CONFIGS is not None

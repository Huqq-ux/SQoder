import pytest
from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentConfig,
    AgentStatus,
    AgentInfo,
    CrewTask,
    CrewTaskStatus,
    CrewResult,
    CrewConfig,
    ProcessType,
    CommunicationMessage,
    MessageType,
    DelegateRequest,
    DelegateResponse,
)


class TestTypes:
    def test_agent_config_creation(self):
        config = AgentConfig(
            role=AgentRole.CODER,
            name="test_coder",
            display_name="测试编程专家",
            system_prompt="你是一个编程专家",
            description="负责代码生成",
            capabilities=[AgentCapability.CODE_GENERATION],
            tools=["file_tools"],
        )
        assert config.role == AgentRole.CODER
        assert config.name == "test_coder"
        assert config.display_name == "测试编程专家"
        assert AgentCapability.CODE_GENERATION in config.capabilities

    def test_agent_info_creation(self):
        config = AgentConfig(
            role=AgentRole.SEARCHER,
            name="test_searcher",
            display_name="搜索专家",
            system_prompt="你是搜索专家",
            description="负责信息检索",
        )
        info = AgentInfo(config=config)
        assert info.status == AgentStatus.IDLE
        assert info.config.role == AgentRole.SEARCHER

    def test_crew_task_creation(self):
        task = CrewTask(
            task_id="task_001",
            description="编写一个排序函数",
            assigned_roles=[AgentRole.CODER],
            priority=1,
        )
        assert task.task_id == "task_001"
        assert task.status == CrewTaskStatus.PENDING
        assert AgentRole.CODER in task.assigned_roles

    def test_crew_config_defaults(self):
        config = CrewConfig()
        assert config.process_type == ProcessType.HIERARCHICAL
        assert config.max_concurrent_tasks == 3
        assert config.global_timeout_seconds == 600.0

    def test_communication_message(self):
        msg = CommunicationMessage(
            msg_id="msg_001",
            msg_type=MessageType.TASK_ASSIGN,
            sender="supervisor",
            receiver="coder",
            content="请编写代码",
            task_id="task_001",
        )
        assert msg.sender == "supervisor"
        assert msg.receiver == "coder"
        assert msg.msg_type == MessageType.TASK_ASSIGN

    def test_delegate_request(self):
        req = DelegateRequest(
            requester="coder",
            target_role=AgentRole.SEARCHER,
            task_description="搜索相关信息",
            priority=1,
        )
        assert req.requester == "coder"
        assert req.target_role == AgentRole.SEARCHER

    def test_crew_result_success(self):
        result = CrewResult(
            success=True,
            task_id="task_001",
            result="代码生成成功",
            agent_traces=["supervisor → coder"],
            duration_seconds=5.0,
        )
        assert result.success
        assert "代码生成成功" in str(result.result)

    def test_crew_result_failure(self):
        result = CrewResult(
            success=False,
            task_id="task_002",
            error="无法分配Agent",
        )
        assert not result.success
        assert result.error == "无法分配Agent"

    def test_agent_role_enum_values(self):
        assert AgentRole.SUPERVISOR.value == "supervisor"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.SEARCHER.value == "searcher"
        assert AgentRole.OPS.value == "ops"

    def test_crew_task_status_transitions(self):
        task = CrewTask(task_id="t1", description="测试")
        assert task.status == CrewTaskStatus.PENDING
        task.status = CrewTaskStatus.ASSIGNED
        assert task.status == CrewTaskStatus.ASSIGNED
        task.status = CrewTaskStatus.RUNNING
        assert task.status == CrewTaskStatus.RUNNING
        task.status = CrewTaskStatus.COMPLETED
        assert task.status == CrewTaskStatus.COMPLETED


class TestAgentRegistry:
    def test_register_agent(self):
        from Coder.multi_agent.registry import agent_registry
        config = AgentConfig(
            role=AgentRole.CODER,
            name="reg_test_coder",
            display_name="注册测试",
            system_prompt="test",
            description="test",
            capabilities=[AgentCapability.CODE_GENERATION],
        )
        assert agent_registry.register(config)
        agent = agent_registry.get("reg_test_coder")
        assert agent is not None
        assert agent.config.name == "reg_test_coder"
        agent_registry.unregister("reg_test_coder")

    def test_register_duplicate(self):
        from Coder.multi_agent.registry import agent_registry
        config = AgentConfig(
            role=AgentRole.CODER,
            name="dup_test",
            display_name="重复测试",
            system_prompt="test",
            description="test",
        )
        agent_registry.register(config)
        assert agent_registry.register(config)
        agent_registry.unregister("dup_test")

    def test_get_nonexistent(self):
        from Coder.multi_agent.registry import agent_registry
        assert agent_registry.get("nonexistent_agent") is None

    def test_list_by_role(self):
        from Coder.multi_agent.registry import agent_registry
        config = AgentConfig(
            role=AgentRole.SEARCHER,
            name="role_test_searcher",
            display_name="角色测试",
            system_prompt="test",
            description="test",
        )
        agent_registry.register(config)
        searchers = agent_registry.list_by_role(AgentRole.SEARCHER)
        assert len(searchers) > 0
        agent_registry.unregister("role_test_searcher")

    def test_set_status(self):
        from Coder.multi_agent.registry import agent_registry
        config = AgentConfig(
            role=AgentRole.CODER,
            name="status_test",
            display_name="状态测试",
            system_prompt="test",
            description="test",
        )
        agent_registry.register(config)
        agent_registry.set_status("status_test", AgentStatus.BUSY)
        agent = agent_registry.get("status_test")
        assert agent.status == AgentStatus.BUSY
        agent_registry.unregister("status_test")

    def test_assign_and_release_task(self):
        from Coder.multi_agent.registry import agent_registry
        config = AgentConfig(
            role=AgentRole.CODER,
            name="task_test",
            display_name="任务测试",
            system_prompt="test",
            description="test",
        )
        agent_registry.register(config)
        agent_registry.assign_task("task_test", "task_001")
        agent = agent_registry.get("task_test")
        assert agent.current_task_id == "task_001"
        assert agent.status == AgentStatus.BUSY

        agent_registry.release_task("task_test")
        agent = agent_registry.get("task_test")
        assert agent.current_task_id == ""
        assert agent.status == AgentStatus.IDLE
        agent_registry.unregister("task_test")

    def test_evaluate_and_adjust(self):
        from Coder.multi_agent.registry import agent_registry
        config = AgentConfig(
            role=AgentRole.CODER,
            name="eval_test",
            display_name="评估测试",
            system_prompt="test",
            description="test",
        )
        agent_registry.register(config)
        task = CrewTask(task_id="t1", description="test")
        agent_registry.evaluate_and_adjust("eval_test", task, success=True)
        stats = agent_registry.get_agent_statistics("eval_test")
        assert stats["capacity_score"] > 0.9
        agent_registry.evaluate_and_adjust("eval_test", task, success=False)
        stats = agent_registry.get_agent_statistics("eval_test")
        assert stats["capacity_score"] < 1.0
        agent_registry.unregister("eval_test")

    def test_select_agent_preference(self):
        from Coder.multi_agent.registry import agent_registry
        config1 = AgentConfig(
            role=AgentRole.CODER,
            name="select_test_1",
            display_name="选择测试1",
            system_prompt="test",
            description="test",
            capabilities=[AgentCapability.CODE_GENERATION],
        )
        config2 = AgentConfig(
            role=AgentRole.CODER,
            name="select_test_2",
            display_name="选择测试2",
            system_prompt="test",
            description="test",
            capabilities=[AgentCapability.CODE_GENERATION],
        )
        agent_registry.register(config1)
        agent_registry.register(config2)

        agent_registry.set_status("select_test_1", AgentStatus.BUSY)
        selected = agent_registry.select_agent(
            AgentRole.CODER, exclude_busy=True
        )
        assert selected is not None
        assert selected.config.name == "select_test_2"

        agent_registry.unregister("select_test_1")
        agent_registry.unregister("select_test_2")


class TestCommunicationProtocol:
    def test_send_and_receive(self):
        from Coder.multi_agent.protocol import CommunicationProtocol
        protocol = CommunicationProtocol()
        msg_id = protocol.send(
            sender="supervisor",
            receiver="coder",
            content="请编写代码",
            msg_type=MessageType.TASK_ASSIGN,
            task_id="task_001",
        )
        assert msg_id
        messages = protocol.receive("coder")
        assert len(messages) > 0
        assert messages[0].sender == "supervisor"
        assert messages[0].content == "请编写代码"

    def test_reply(self):
        from Coder.multi_agent.protocol import CommunicationProtocol
        protocol = CommunicationProtocol()
        original_id = protocol.send(
            sender="supervisor",
            receiver="coder",
            content="任务指派",
            task_id="task_001",
        )
        reply_id = protocol.reply(
            original_msg_id=original_id,
            content="任务完成",
        )
        assert reply_id
        supervisor_msgs = protocol.receive("supervisor")
        assert len(supervisor_msgs) > 0
        assert any("任务完成" in m.content for m in supervisor_msgs)

    def test_broadcast(self):
        from Coder.multi_agent.protocol import CommunicationProtocol
        protocol = CommunicationProtocol()
        msg_ids = protocol.broadcast(
            sender="supervisor",
            receivers=["coder", "searcher", "ops"],
            content="团队通知",
            task_id="task_001",
        )
        assert len(msg_ids) == 3
        assert len(protocol.receive("coder")) > 0
        assert len(protocol.receive("searcher")) > 0
        assert len(protocol.receive("ops")) > 0

    def test_thread_history(self):
        from Coder.multi_agent.protocol import CommunicationProtocol
        protocol = CommunicationProtocol()
        protocol.send(
            sender="supervisor", receiver="coder",
            content="消息1", task_id="task_001",
        )
        protocol.send(
            sender="coder", receiver="supervisor",
            content="消息2", task_id="task_001",
        )
        history = protocol.get_thread_history("task_001")
        assert len(history) == 2

    def test_delegate_to_agent(self):
        from Coder.multi_agent.protocol import CommunicationProtocol
        protocol = CommunicationProtocol()
        msg_id = protocol.delegate_to_agent(
            sender="coder",
            target_agent="searcher",
            task_description="搜索资料",
            task_id="task_001",
        )
        messages = protocol.receive("searcher")
        assert any("搜索资料" in m.content for m in messages)


class TestTaskRouter:
    def test_analyze_user_intent_coding(self):
        from Coder.multi_agent.router import task_router
        is_multi, roles, confidence = task_router.analyze_user_intent(
            "帮我写一个Python函数"
        )
        assert AgentRole.CODER in roles

    def test_analyze_user_intent_search(self):
        from Coder.multi_agent.router import task_router
        is_multi, roles, confidence = task_router.analyze_user_intent(
            "什么是机器学习"
        )
        assert AgentRole.SEARCHER in roles

    def test_analyze_user_intent_ops(self):
        from Coder.multi_agent.router import task_router
        is_multi, roles, confidence = task_router.analyze_user_intent(
            "部署一个Python应用到服务器"
        )
        assert AgentRole.OPS in roles

    def test_analyze_user_intent_skill(self):
        from Coder.multi_agent.router import task_router
        is_multi, roles, confidence = task_router.analyze_user_intent(
            "调用skill完成文本反转"
        )
        assert AgentRole.SKILL_EXECUTOR in roles

    def test_decompose_simple_task(self):
        from Coder.multi_agent.router import task_router
        tasks = task_router.decompose_task(
            "帮我写一个排序函数",
            [AgentRole.CODER],
        )
        assert len(tasks) == 1
        assert "排序函数" in tasks[0].description

    def test_decompose_multi_step_task(self):
        from Coder.multi_agent.router import task_router
        tasks = task_router.decompose_task(
            "首先搜索最佳实践，然后编写代码，最后部署",
        )
        assert len(tasks) >= 2

    def test_route_task_force_multi(self):
        from Coder.multi_agent.router import task_router
        tasks, is_multi = task_router.route_task(
            "帮我写代码", force_multi=True
        )
        assert is_multi

    def test_create_task_sets_properties(self):
        from Coder.multi_agent.router import task_router
        task = task_router._create_task("测试任务", [AgentRole.CODER])
        assert task.task_id
        assert task.assigned_roles == [AgentRole.CODER]
        assert task.status == CrewTaskStatus.PENDING


class TestIntegrations:
    def test_build_system_prompt_for_coder(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.CODER)
        assert "编程" in prompt
        assert len(prompt) > 50

    def test_build_system_prompt_for_searcher(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.SEARCHER)
        assert "检索" in prompt or "搜索" in prompt

    def test_build_default_configs_count(self):
        from Coder.multi_agent.integrations import build_default_agent_configs
        configs = build_default_agent_configs()
        assert len(configs) >= 5

    def test_build_default_configs_has_supervisor(self):
        from Coder.multi_agent.integrations import build_default_agent_configs
        configs = build_default_agent_configs()
        supervisors = [c for c in configs if c.role == AgentRole.SUPERVISOR]
        assert len(supervisors) >= 1

    def test_get_skill_tools(self):
        from Coder.multi_agent.integrations import get_skill_tools
        tools = get_skill_tools()
        assert len(tools) >= 2

    def test_get_sop_tools(self):
        from Coder.multi_agent.integrations import get_sop_tools
        tools = get_sop_tools()
        assert len(tools) >= 2


class TestMultiAgentCrew:
    def test_create_crew(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        assert crew.config is not None
        assert crew.registry is not None

    def test_initialize_default_crew(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        count = crew.initialize_default_crew()
        assert count >= 5
        agents = crew.registry.list_all()
        assert len(agents) >= 5
        crew.reset()

    def test_add_coder(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        assert crew.add_coder(name="my_coder")
        agent = crew.registry.get("my_coder")
        assert agent is not None
        assert agent.config.role == AgentRole.CODER
        crew.reset()

    def test_add_searcher(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        assert crew.add_searcher(name="my_searcher")
        agent = crew.registry.get("my_searcher")
        assert agent.config.role == AgentRole.SEARCHER
        crew.reset()

    def test_add_ops(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        assert crew.add_ops(name="my_ops")
        agent = crew.registry.get("my_ops")
        assert agent.config.role == AgentRole.OPS
        crew.reset()

    def test_get_statistics_initial(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        crew.initialize_default_crew()
        stats = crew.get_statistics()
        assert "agents" in stats
        assert stats["total_executions"] == 0
        crew.reset()

    def test_get_history_empty(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        crew = MultiAgentCrew()
        history = crew.get_history()
        assert history == []

    def test_crew_config_defaults(self):
        from Coder.multi_agent.crew import MultiAgentCrew
        from Coder.multi_agent.types import CrewConfig, ProcessType
        config = CrewConfig(process_type=ProcessType.SEQUENTIAL)
        crew = MultiAgentCrew(crew_config=config)
        assert crew.config.process_type == ProcessType.SEQUENTIAL


class TestAgentBuilder:
    def test_create_builder(self):
        from Coder.multi_agent.agent_builder import AgentBuilder
        builder = AgentBuilder()
        assert builder is not None
        assert builder.checkpointer is not None


class TestSupervisorAgent:
    def test_create_supervisor(self):
        from Coder.multi_agent.supervisor import SupervisorAgent
        supervisor = SupervisorAgent()
        assert supervisor is not None
        assert supervisor.protocol is not None

    def test_initialize_default_agents(self):
        from Coder.multi_agent.supervisor import SupervisorAgent
        from Coder.multi_agent.registry import agent_registry
        agent_registry.reset()
        supervisor = SupervisorAgent()
        count = supervisor.initialize_default_agents()
        assert count >= 5
        supervisor.reset()

    def test_execution_log_empty_initial(self):
        from Coder.multi_agent.supervisor import SupervisorAgent
        supervisor = SupervisorAgent()
        log = supervisor.get_execution_log()
        assert log == []

    def test_simple_integration(self):
        from Coder.multi_agent.supervisor import SupervisorAgent
        result = SupervisorAgent._simple_integration([
            {"status": "completed", "description": "任务1", "result": "成功"},
            {"status": "failed", "description": "任务2", "error": "失败原因"},
        ])
        assert "任务1" in result
        assert "任务2" in result
        assert "✅" in result
        assert "❌" in result


class TestModuleExports:
    def test_sop_init_exports(self):
        from Coder.sop import (
            AgentRole,
            AgentConfig,
            MultiAgentCrew,
            ProcessType,
            CrewTask,
            CrewResult,
            AgentRegistry,
            TaskRouter,
            CommunicationProtocol,
            AgentBuilder,
        )
        assert AgentRole is not None
        assert MultiAgentCrew is not None

    def test_multi_agent_init_exports(self):
        from Coder.multi_agent import (
            AgentRole,
            AgentConfig,
            MultiAgentCrew,
            ProcessType,
            CrewTask,
            CrewResult,
            AgentRegistry,
            TaskRouter,
            CommunicationProtocol,
            AgentBuilder,
        )
        assert AgentRole is not None
        assert MultiAgentCrew is not None

    def test_code_agent_multi_agent_import(self):
        from Coder.agent.code_agent import create_multi_agent_crew
        assert create_multi_agent_crew is not None

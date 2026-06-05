"""子 Agent 默认配置，由 AgentConfig 数据类统一驱动。"""
from Coder.multi_agent.types import AgentRole, AgentConfig, AgentCapability

DEFAULT_AGENT_CONFIGS: dict[AgentRole, AgentConfig] = {
    AgentRole.CODER: AgentConfig(
        role=AgentRole.CODER,
        name="coder",
        display_name="编程专家",
        system_prompt=(
            "你是一个编程专家。直接给出高质量、可运行的代码。\n"
            "重要：只需要给出代码本身和简短说明，不要大段分析过程。"
        ),
        description="负责代码生成、调试、重构、算法实现",
        capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.CODE_DEBUGGING],
        tools=["file_tools", "knowledge_toolkit", "docx_tools"],
        timeout_seconds=120.0,
    ),
    AgentRole.SEARCHER: AgentConfig(
        role=AgentRole.SEARCHER,
        name="searcher",
        display_name="搜索专家",
        system_prompt=(
            "你是一个信息检索专家。\n"
            "核心规则：\n"
            "1. 只输出基于事实的简洁回答\n"
            "2. 不要列出信息来源URL或大段引用原文\n"
            "3. 不确定时直接说明，不要编造\n"
            "4. 优先使用搜索工具获取最新信息"
        ),
        description="负责信息检索、文档查询、知识库搜索",
        capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.KNOWLEDGE_RETRIEVAL],
        tools=["web_search_toolkit", "knowledge_toolkit"],
        timeout_seconds=120.0,
    ),
    AgentRole.OPS: AgentConfig(
        role=AgentRole.OPS,
        name="ops",
        display_name="运维专家",
        system_prompt=(
            "你是一个运维专家。直接给出操作命令和配置方案。\n"
            "重要：只输出关键操作步骤和命令，不要大段分析。"
        ),
        description="负责部署、配置、故障排查",
        capabilities=[AgentCapability.SYSTEM_OPERATION, AgentCapability.TROUBLESHOOTING],
        tools=["file_tools"],
        timeout_seconds=120.0,
    ),
    AgentRole.SKILL_EXECUTOR: AgentConfig(
        role=AgentRole.SKILL_EXECUTOR,
        name="skill_executor",
        display_name="技能执行器",
        system_prompt=(
            "你是一个技能执行器。根据需求调用已注册的技能。\n"
            "重要：只输出执行结果，不要多余说明。"
        ),
        description="调用已注册的技能",
        capabilities=[AgentCapability.SKILL_EXECUTION],
        tools=[],  # 技能工具由 AgentBuilder 动态注入
        timeout_seconds=120.0,
    ),
}

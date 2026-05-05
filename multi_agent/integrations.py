import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, tool

from Coder.multi_agent.types import AgentRole, AgentCapability, AgentConfig

logger = logging.getLogger(__name__)

_CODER_SYSTEM_PROMPT = (
    "你是一个专业的编程专家 Agent，拥有10年全栈开发经验。\n"
    "你的职责：\n"
    "1. 编写高质量、可维护的代码\n"
    "2. 代码审查与优化建议\n"
    "3. Bug 分析与修复\n"
    "4. 技术方案设计与架构思考\n\n"
    "回答要求：\n"
    "- 先给出【思考过程】，再给出【代码实现】\n"
    "- 代码需包含必要的错误处理\n"
    "- 如有多个方案，说明优缺点\n"
    "- 生成代码后说明使用方式"
)

_SEARCHER_SYSTEM_PROMPT = (
    "你是一个专业的信息检索与分析 Agent。\n"
    "你的职责：\n"
    "1. 使用搜索工具查找相关信息\n"
    "2. 检索知识库中的文档\n"
    "3. 整理和分析搜索结果\n"
    "4. 提供准确、有来源的回答\n\n"
    "回答要求：\n"
    "- 明确标注信息来源\n"
    "- 区分事实与推测\n"
    "- 不确定时明确说明"
)

_OPS_SYSTEM_PROMPT = (
    "你是一个专业的运维与系统操作 Agent。\n"
    "你的职责：\n"
    "1. 系统部署与配置\n"
    "2. 故障排查与诊断\n"
    "3. 性能监控与优化\n"
    "4. 日志分析与异常检测\n\n"
    "回答要求：\n"
    "- 操作前说明影响范围\n"
    "- 提供回滚方案\n"
    "- 关键操作需确认"
)

_SOP_EXECUTOR_PROMPT = (
    "你是一个专业的 SOP 流程执行 Agent。\n"
    "你的职责：\n"
    "1. 严格按照 SOP 标准操作流程执行\n"
    "2. 每一步执行后汇报状态\n"
    "3. 遇到异常按预设流程处理\n"
    "4. 执行完毕后给出摘要\n\n"
    "回答要求：\n"
    "- 标明当前步骤序号/总数\n"
    "- 每步完成后汇报结果\n"
    "- 失败步骤说明原因和后续计划"
)

_SKILL_EXECUTOR_PROMPT = (
    "你是一个专业的技能执行 Agent。\n"
    "你的职责：\n"
    "1. 根据用户需求匹配合适的技能\n"
    "2. 提取并验证技能所需参数\n"
    "3. 执行技能并返回结果\n"
    "4. 处理技能执行异常\n\n"
    "回答要求：\n"
    "- 先确认使用的技能名称\n"
    "- 列出使用的参数\n"
    "- 执行后返回明确结果"
)

_SUPERVISOR_SYSTEM_PROMPT = (
    "你是一个多智能体系统的 Supervisor，负责协调整个 Agent 团队。\n"
    "你的职责：\n"
    "1. 分析用户请求，判断是否需要用多 Agent 协作\n"
    "2. 将复杂任务分解为子任务\n"
    "3. 将子任务分配给最合适的专业 Agent\n"
    "4. 整合各 Agent 的结果，形成最终回答\n"
    "5. 质量审核，确保输出准确完整\n\n"
    "决策规则：\n"
    "- 纯知识问答 → 直接调用 Searcher Agent\n"
    "- 代码相关 → 直接调用 Coder Agent\n"
    "- 系统运维 → 直接调用 Ops Agent\n"
    "- 多步骤复杂任务 → 分解后并行/顺序执行\n\n"
    "输出格式：\n"
    "1. 【任务分析】：对用户请求的理解和分解策略\n"
    "2. 【子任务分配】：列出各子任务及负责的 Agent\n"
    "3. 【结果整合】：汇总各 Agent 的结果\n"
    "4. 【最终回答】：给出完整准确的回答"
)


def build_system_prompt_for_role(role: AgentRole) -> str:
    prompts = {
        AgentRole.CODER: _CODER_SYSTEM_PROMPT,
        AgentRole.SEARCHER: _SEARCHER_SYSTEM_PROMPT,
        AgentRole.OPS: _OPS_SYSTEM_PROMPT,
        AgentRole.SOP_EXECUTOR: _SOP_EXECUTOR_PROMPT,
        AgentRole.SKILL_EXECUTOR: _SKILL_EXECUTOR_PROMPT,
        AgentRole.SUPERVISOR: _SUPERVISOR_SYSTEM_PROMPT,
        AgentRole.GENERAL: _CODER_SYSTEM_PROMPT,
    }
    return prompts.get(role, _CODER_SYSTEM_PROMPT)


def build_tool_set_for_role(
    role: AgentRole,
    base_tools: List[BaseTool] = None,
) -> List[BaseTool]:
    tools = list(base_tools or [])

    if role in (AgentRole.CODER, AgentRole.GENERAL, AgentRole.SUPERVISOR):
        pass
    elif role == AgentRole.SEARCHER:
        pass
    elif role == AgentRole.OPS:
        pass

    return tools


def resolve_agent_model(agent_config: AgentConfig):
    try:
        from Coder.model import llm as default_llm
    except Exception:
        default_llm = None

    if agent_config.model_name:
        try:
            from langchain_openai import ChatOpenAI
            import os
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
            return ChatOpenAI(
                model=agent_config.model_name,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key=api_key,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens,
                streaming=True,
            )
        except Exception as e:
            logger.warning(
                f"无法创建模型 {agent_config.model_name}: {e}，使用默认LLM"
            )

    if default_llm:
        return default_llm.bind(
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
        )

    raise RuntimeError("没有可用的 LLM 模型")


def build_default_agent_configs() -> List[AgentConfig]:
    configs = [
        AgentConfig(
            role=AgentRole.SUPERVISOR,
            name="supervisor",
            display_name="任务监督者",
            system_prompt=_SUPERVISOR_SYSTEM_PROMPT,
            description="负责任务分解、分配和结果整合的监督Agent",
            capabilities=[
                AgentCapability.TASK_DECOMPOSITION,
                AgentCapability.RESULT_INTEGRATION,
                AgentCapability.COMMUNICATION,
            ],
            priority=10,
        ),
        AgentConfig(
            role=AgentRole.CODER,
            name="coder",
            display_name="编程专家",
            system_prompt=_CODER_SYSTEM_PROMPT,
            description="负责代码生成、审查和调试的编程Agent",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
                AgentCapability.CODE_DEBUGGING,
            ],
            tools=["file_tools", "knowledge_toolkit"],
            priority=1,
        ),
        AgentConfig(
            role=AgentRole.SEARCHER,
            name="searcher",
            display_name="搜索专家",
            system_prompt=_SEARCHER_SYSTEM_PROMPT,
            description="负责信息检索和知识查询的搜索Agent",
            capabilities=[
                AgentCapability.WEB_SEARCH,
                AgentCapability.KNOWLEDGE_RETRIEVAL,
                AgentCapability.DATA_ANALYSIS,
            ],
            tools=["web_search_toolkit", "knowledge_toolkit"],
            priority=2,
        ),
        AgentConfig(
            role=AgentRole.OPS,
            name="ops",
            display_name="运维专家",
            system_prompt=_OPS_SYSTEM_PROMPT,
            description="负责系统部署和故障排查的运维Agent",
            capabilities=[
                AgentCapability.SYSTEM_OPERATION,
                AgentCapability.DEPLOYMENT,
                AgentCapability.TROUBLESHOOTING,
            ],
            tools=["file_tools"],
        ),
        AgentConfig(
            role=AgentRole.SOP_EXECUTOR,
            name="sop_executor",
            display_name="SOP执行器",
            system_prompt=_SOP_EXECUTOR_PROMPT,
            description="负责按标准操作流程执行任务的SOP Agent",
            capabilities=[
                AgentCapability.SOP_EXECUTION,
            ],
            priority=4,
        ),
        AgentConfig(
            role=AgentRole.SKILL_EXECUTOR,
            name="skill_executor",
            display_name="技能执行器",
            system_prompt=_SKILL_EXECUTOR_PROMPT,
            description="负责执行已注册技能的功能Agent",
            capabilities=[
                AgentCapability.SKILL_EXECUTION,
            ],
            priority=5,
        ),
    ]
    return configs


def get_skill_tools() -> List[BaseTool]:
    tools_list = []

    @tool
    def list_available_skills() -> str:
        """列出所有可用的技能"""
        try:
            from Coder.tools.skill_registry import SkillRegistry
            registry = SkillRegistry()
            if not registry._initialized:
                registry.initialize()
            skills = registry.list_all()
            if not skills:
                return "当前没有可用的技能"
            lines = []
            for s in skills:
                lines.append(f"- {s.name}: {s.display_name} ({s.description[:80]})")
            return "\n".join(lines)
        except Exception as e:
            return f"获取技能列表失败: {e}"

    @tool
    def execute_skill_by_name(skill_name: str) -> str:
        """按名称执行指定技能"""
        try:
            from Coder.tools.skill_registry import SkillRegistry
            from Coder.sop.skill_executor import SkillExecutor, ExecutionContext
            registry = SkillRegistry()
            if not registry._initialized:
                registry.initialize()
            executor = SkillExecutor(registry)
            context = ExecutionContext()
            result = executor.execute(
                step={"skill": skill_name, "params": {}, "name": skill_name},
                context=context,
            )
            if result.status.value == "success":
                return f"技能 '{skill_name}' 执行成功: {result.result}"
            else:
                return f"技能 '{skill_name}' 执行失败: {result.error}"
        except Exception as e:
            return f"执行技能失败: {e}"

    tools_list.append(list_available_skills)
    tools_list.append(execute_skill_by_name)
    return tools_list


def get_sop_tools() -> List[BaseTool]:
    tools_list = []

    @tool
    def list_available_sops() -> str:
        """列出所有可用的SOP流程"""
        try:
            from Coder.sop.flow_orchestrator import FlowOrchestrator
            orchestrator = FlowOrchestrator()
            sops = orchestrator.list_sops()
            if not sops:
                return "当前没有可用的SOP"
            return "\n".join(f"- {name}" for name in sops)
        except Exception as e:
            return f"获取SOP列表失败: {e}"

    @tool
    def execute_sop_step(sop_name: str, step_index: int) -> str:
        """执行SOP的指定步骤"""
        try:
            from Coder.sop.flow_orchestrator import FlowOrchestrator
            orchestrator = FlowOrchestrator()
            sop = orchestrator.get_sop(sop_name)
            if not sop:
                return f"未找到SOP: {sop_name}"
            steps = sop.get("steps", [])
            if step_index < 0 or step_index >= len(steps):
                return f"步骤索引超出范围 (0-{len(steps)-1})"
            step = steps[step_index]
            return f"步骤 {step_index + 1}: {step.get('name', '')} - {step.get('description', '')[:200]}"
        except Exception as e:
            return f"执行SOP步骤失败: {e}"

    tools_list.append(list_available_sops)
    tools_list.append(execute_sop_step)
    return tools_list

import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, tool

from Coder.multi_agent.types import AgentRole

logger = logging.getLogger(__name__)

_CODER_SYSTEM_PROMPT = (
    "你是一个编程专家。直接给出高质量、可运行的代码。\n"
    "重要：只需要给出代码本身和简短说明，不要大段分析过程。\n"
    "需要搜索最新技术信息时使用 web_search 工具。"
)

_SEARCHER_SYSTEM_PROMPT = (
    "你是一个信息检索专家。\n"
    "核心规则：\n"
    "1. 只输出基于事实的简洁回答\n"
    "2. 不要列出信息来源URL或大段引用原文\n"
    "3. 不确定时直接说明，不要编造\n"
    "4. 优先使用搜索工具获取最新信息"
)

_OPS_SYSTEM_PROMPT = (
    "你是一个运维专家。直接给出操作命令和配置方案。\n"
    "重要：只输出关键操作步骤和命令，不要大段分析。"
)

_SKILL_EXECUTOR_PROMPT = (
    "你是一个技能执行器。根据需求调用已注册的技能。\n"
    "重要：只输出执行结果，不要多余说明。"
)

def build_system_prompt_for_role(role: AgentRole) -> str:
    prompts = {
        AgentRole.CODER: _CODER_SYSTEM_PROMPT,
        AgentRole.SEARCHER: _SEARCHER_SYSTEM_PROMPT,
        AgentRole.OPS: _OPS_SYSTEM_PROMPT,
        AgentRole.SKILL_EXECUTOR: _SKILL_EXECUTOR_PROMPT,
        AgentRole.GENERAL: _CODER_SYSTEM_PROMPT,
    }
    return prompts.get(role, _CODER_SYSTEM_PROMPT)




def resolve_agent_model(agent_config):
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
            from Coder.tools.skill_executor import SkillExecutor, ExecutionContext
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





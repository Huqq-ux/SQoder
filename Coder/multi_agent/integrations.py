import logging
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool, tool

from Coder.multi_agent.types import AgentRole

logger = logging.getLogger(__name__)


def build_system_prompt_for_role(role: AgentRole) -> str:
    """从 AgentConfig 读取角色的 system_prompt，不硬编码字符串。"""
    from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

    config = DEFAULT_AGENT_CONFIGS.get(role)
    if config is not None:
        return config.system_prompt
    # fallback：未知角色返回通用编程提示
    return "你是一个智能助手。请直接给出高质量的回答。"


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
    def execute_skill_by_name(skill_name: str, params: dict = None) -> str:
        """按名称执行指定技能。params 为技能参数字典，由调用方根据技能需求传入。"""
        try:
            from Coder.tools.skill_registry import SkillRegistry
            from Coder.tools.skill_executor import SkillExecutor, ExecutionContext
            registry = SkillRegistry()
            if not registry._initialized:
                registry.initialize()
            executor = SkillExecutor(registry)
            context = ExecutionContext()
            result = executor.execute(
                step={
                    "skill": skill_name,
                    "params": params or {},
                    "name": skill_name,
                },
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

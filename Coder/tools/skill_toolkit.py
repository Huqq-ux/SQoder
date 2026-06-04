import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_pg_store():
    """延迟获取 PgSkillStore，只在需要时初始化。"""
    from Coder.storage.skill_store import PgSkillStore
    return PgSkillStore()


@tool
async def list_skills() -> str:
    """列出所有可用的用户技能（技能是由用户自定义的可执行代码片段）。

    返回每个技能的名称、分类、描述和参数列表。
    当用户询问"有哪些技能"、"你能做什么"或需要特定功能时使用此工具。
    """
    try:
        store = _get_pg_store()
        metas = await store.list_skills_meta(enabled_only=True)

        from Coder.tools.skill_registry import SkillRegistry
        registry = SkillRegistry()
        if not registry._initialized:
            registry.initialize()

        if not metas:
            return "当前没有注册任何用户技能。可以通过技能管理页面上传新技能。"

        lines = [f"共 {len(metas)} 个技能:\n"]
        for meta in metas:
            params = ", ".join(
                f"{p.get('name', '?')}:{p.get('type', '?')}"
                + ("?" if not p.get('required') else "")
                for p in meta.parameters
            ) if meta.parameters else "无参数"
            lines.append(
                f"**{meta.display_name}** (`{meta.name}`)\n"
                f"  分类: {meta.category}\n"
                f"  描述: {meta.description}\n"
                f"  参数: {params}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"获取技能列表失败: {e}")
        return f"获取技能列表失败: {e}"


@tool
async def execute_skill(skill_name: str, **kwargs) -> str:
    """执行指定的用户技能。

    先调用 list_skills 确认技能名和参数，再调用本工具执行。

    Args:
        skill_name: 技能名称（英文标识符，如 reverse_text_skill）
        **kwargs: 技能所需的参数，参考 list_skills 返回的参数列表
    """
    if not skill_name or not skill_name.strip():
        return "请指定要执行的技能名称。使用 list_skills 查看可用技能。"

    skill_name = skill_name.strip()

    try:
        store = _get_pg_store()
        skill_def = await store.load_skill(skill_name)

        if skill_def is None:
            metas = await store.list_skills_meta(enabled_only=True)
            available = [m.name for m in metas]
            hint = f"\n当前可用技能: {', '.join(available)}" if available else ""
            return f"技能 '{skill_name}' 不存在。{hint}"

        from Coder.tools.skill_compiler import SkillCompiler, SkillCompileError
        try:
            func = SkillCompiler.compile(skill_def)
        except SkillCompileError as e:
            return f"技能 '{skill_def.display_name}' 编译失败: {e}"

        if func is None:
            return f"技能 '{skill_def.display_name}' 编译失败。"

        try:
            result = func(**kwargs)
        except TypeError as e:
            params_desc = ", ".join(
                f"{p['name']}:{p['type']}"
                + (" (必填)" if p.get('required') else "")
                for p in skill_def.parameters
            )
            return (
                f"参数错误: {e}\n"
                f"技能 '{skill_def.display_name}' 的参数: {params_desc}"
            )
        except Exception as e:
            return f"技能执行失败: {e}"

        if result is None:
            return f"技能 '{skill_def.display_name}' 执行完成。"
        return str(result)

    except Exception as e:
        logger.error(f"执行技能失败: {e}")
        return f"执行技能失败: {e}"


skill_toolkit = [list_skills, execute_skill]

__all__ = ["skill_toolkit"]

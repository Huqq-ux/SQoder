import logging
from typing import Optional

from Coder.sop.state_machine import StateMachine, SOPState, StepResult
from Coder.sop.flow_orchestrator import FlowOrchestrator
from Coder.knowledge.retriever import Retriever
from Coder.prompts.sop_execution import SOP_QUERY_TEMPLATE

logger = logging.getLogger(__name__)


class SOPExecutor:
    def __init__(
        self,
        orchestrator: FlowOrchestrator,
        retriever: Optional[Retriever] = None,
    ):
        self.orchestrator = orchestrator
        self.retriever = retriever

    def build_sop_prompt(self, sop_name: str, user_input: str) -> Optional[str]:
        sop = self.orchestrator.get_sop(sop_name)
        if not sop:
            return None

        context = self._retrieve_context(user_input)
        steps_text = self._format_steps(sop.get("steps", []))
        raw_content = sop.get("raw_content", "")

        prompt_parts = [
            f"## SOP: {sop_name}",
            "",
            f"**用户请求**: {user_input}",
            "",
        ]

        if context:
            prompt_parts.extend(["## 参考文档", "", context, ""])

        if steps_text:
            prompt_parts.extend(["## SOP 步骤", "", steps_text, ""])
        elif raw_content:
            prompt_parts.extend(["## SOP 原文", "", raw_content[:2000], ""])

        prompt_parts.extend([
            "## 执行要求",
            "",
            "请严格按照以上SOP步骤执行：",
            "1. 逐步执行每个步骤，使用必要的工具",
            "2. 每步完成后说明执行结果",
            "3. 如果某步骤失败，说明原因并决定是否继续",
            "4. 最终给出执行摘要",
        ])

        return "\n".join(prompt_parts)

    def build_query_prompt(self, user_input: str, context: str) -> str:
        return SOP_QUERY_TEMPLATE.format(
            user_input=user_input,
            context=context,
        )

    def build_list_prompt(self, user_input: str) -> str:
        available_sops = self.orchestrator.list_sops()
        if not available_sops:
            if self._explicitly_mentions_sop(user_input):
                return (
                    f"用户问题: {user_input}\n\n"
                    f"当前知识库中没有可用的SOP文档。请直接回答用户问题，不要编造SOP内容。"
                )
            return user_input

        sop_list = "\n".join(f"- {name}" for name in available_sops)
        return (
            f"## SOP查询\n\n"
            f"用户问题: {user_input}\n\n"
            f"## 可用SOP列表\n\n"
            f"{sop_list}\n\n"
            f"## 回答要求\n\n"
            f"请基于以上SOP列表回答用户问题。如果用户询问有哪些SOP，请列出所有可用SOP并简要说明。"
            f"如果用户询问的SOP不在列表中，明确告知用户当前没有该SOP。"
        )

    def record_step_result(
        self,
        sop_name: str,
        step_index: int,
        step_name: str,
        status: str,
        result: str = "",
        error: str = "",
        tool_calls: Optional[list[dict]] = None,
    ):
        execution = self.orchestrator.state_machine.get_execution(sop_name)
        if not execution:
            return

        step_result = StepResult(
            step_index=step_index,
            step_name=step_name,
            status=status,
            result=result,
            error=error,
            tool_calls=tool_calls or [],
        )

        if status == "failed":
            self.orchestrator.state_machine.set_error(sop_name, error)
        else:
            self.orchestrator.state_machine.advance_step(sop_name, step_result)

    def should_confirm(self, step: dict) -> bool:
        dangerous_keywords = ["删除", "格式化", "清空", "重置", "停止服务", "关闭"]
        desc = step.get("description", "").lower()
        return any(kw in desc for kw in dangerous_keywords)

    def _retrieve_context(self, user_input: str) -> str:
        if not self.retriever or not self.retriever.is_available():
            return ""
        try:
            return self.retriever.retrieve_with_context(user_input, k=3)
        except Exception as e:
            logger.warning(f"RAG检索失败: {e}")
            return ""

    @staticmethod
    def _format_steps(steps: list[dict]) -> str:
        if not steps:
            return ""
        lines = []
        for step in steps:
            idx = step.get("index", 0)
            name = step.get("name", f"步骤{idx + 1}")
            desc = step.get("description", "")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    @staticmethod
    def _explicitly_mentions_sop(text: str) -> bool:
        text_lower = text.lower()
        return "sop" in text_lower or "流程" in text_lower or "步骤" in text_lower

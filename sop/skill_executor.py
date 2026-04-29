import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from Coder.tools.skill_registry import SkillRegistry, RegisteredSkill
from Coder.tools.skill_compiler import SkillCompileError

logger = logging.getLogger(__name__)


class SkillExecStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    FALLBACK = "fallback"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"


@dataclass
class SkillExecResult:
    status: SkillExecStatus
    skill_name: str = ""
    result: Any = None
    error: str = ""
    error_detail: str = ""
    duration_ms: float = 0.0
    retry_count: int = 0
    fallback_used: bool = False
    fallback_skill: str = ""
    context_snapshot: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExecutionContext:
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[SkillExecResult] = field(default_factory=list)
    step_index: int = 0
    sop_name: str = ""
    max_retries: int = 2
    timeout_seconds: float = 30.0
    allow_fallback: bool = True


class SkillExecutor:

    _VARIABLE_PATTERN = None

    def __init__(self, registry: SkillRegistry = None):
        self.registry = registry or SkillRegistry()
        if not self.registry._initialized:
            self.registry.initialize()

    def execute(
        self,
        step: dict,
        context: ExecutionContext,
    ) -> SkillExecResult:
        skill_name = step.get("skill", "")
        skill_params = step.get("params", {})
        step_name = step.get("name", "未命名步骤")

        if not skill_name:
            context.history.append(SkillExecResult(
                status=SkillExecStatus.SKIPPED,
                skill_name="",
            ))
            return context.history[-1]

        registered = self.registry.get(skill_name)
        if registered is None:
            registered = self._resolve_skill(
                step_name, step.get("description", "")
            )

        start = time.time()

        if registered is None:
            result = SkillExecResult(
                status=SkillExecStatus.NOT_FOUND,
                skill_name=skill_name,
                error=f"未找到技能: {skill_name}",
                duration_ms=(time.time() - start) * 1000,
            )
            result = self._handle_fallback(result, step, context)
            context.history.append(result)
            return result

        resolved_params = self._resolve_params(skill_params, context)
        result = self._execute_with_retry(
            registered, resolved_params, skill_name, context
        )
        result.duration_ms = (time.time() - start) * 1000
        result.context_snapshot = dict(context.variables)

        if result.status == SkillExecStatus.SUCCESS:
            context.variables[
                f"step_{context.step_index}_result"
            ] = result.result
            context.variables[step_name] = result.result

        if result.status in (
            SkillExecStatus.FAILED,
            SkillExecStatus.TIMEOUT,
            SkillExecStatus.NOT_FOUND,
        ):
            result = self._handle_fallback(result, step, context)

        context.history.append(result)
        return result

    def _resolve_skill(
        self, step_name: str, step_description: str
    ) -> Optional[RegisteredSkill]:
        candidates = self.registry.match_for_step(step_name, step_description)
        if candidates:
            logger.info(
                f"自动匹配技能: {step_name} -> {candidates[0].name}"
            )
            return candidates[0]
        return None

    def _resolve_params(
        self,
        params: dict,
        context: ExecutionContext,
    ) -> dict:
        if self._VARIABLE_PATTERN is None:
            import re
            self.__class__._VARIABLE_PATTERN = re.compile(
                r'\$\{(\w+(?:\.\w+)?)\}'
            )

        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                def replace_var(match):
                    var_name = match.group(1)
                    if var_name in context.variables:
                        return str(context.variables[var_name])
                    return match.group(0)
                resolved[key] = self._VARIABLE_PATTERN.sub(
                    replace_var, value
                )
            else:
                resolved[key] = value
        return resolved

    def _execute_with_retry(
        self,
        skill: RegisteredSkill,
        params: dict,
        skill_name: str,
        context: ExecutionContext,
    ) -> SkillExecResult:
        last_error = ""
        last_error_detail = ""

        for attempt in range(context.max_retries + 1):
            try:
                result_value = self._call_with_timeout(
                    skill.func,
                    params,
                    context.timeout_seconds,
                )
                return SkillExecResult(
                    status=SkillExecStatus.SUCCESS,
                    skill_name=skill_name,
                    result=result_value,
                    retry_count=attempt,
                )
            except TimeoutError:
                last_error = f"技能执行超时 ({context.timeout_seconds}s)"
                last_error_detail = traceback.format_exc()
                logger.warning(
                    f"技能超时 {skill_name} (尝试 {attempt + 1})"
                )
            except Exception as e:
                last_error = str(e)
                last_error_detail = traceback.format_exc()
                logger.warning(
                    f"技能执行失败 {skill_name} (尝试 {attempt + 1}): {e}"
                )

            if attempt < context.max_retries:
                time.sleep(0.5 * (attempt + 1))

        status = SkillExecStatus.TIMEOUT if "超时" in last_error else SkillExecStatus.FAILED
        return SkillExecResult(
            status=status,
            skill_name=skill_name,
            error=last_error,
            error_detail=last_error_detail,
            retry_count=context.max_retries,
        )

    def _call_with_timeout(
        self,
        func: Callable,
        params: dict,
        timeout: float,
    ) -> Any:
        import threading

        result_container = {}
        error_container = {}

        def target():
            try:
                result_container["value"] = func(**params)
            except Exception as e:
                error_container["error"] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"执行超时 ({timeout}s)")

        if "error" in error_container:
            raise error_container["error"]

        return result_container.get("value")

    def _handle_fallback(
        self,
        result: SkillExecResult,
        step: dict,
        context: ExecutionContext,
    ) -> SkillExecResult:
        if not context.allow_fallback:
            return result

        fallback_skill = step.get("fallback_skill", "")
        if fallback_skill:
            registered = self.registry.get(fallback_skill)
            if registered:
                logger.info(
                    f"回退到备用技能: {result.skill_name} -> {fallback_skill}"
                )
                fallback_params = self._resolve_params(
                    step.get("fallback_params", {}), context
                )
                try:
                    fb_result = registered.func(**fallback_params)
                    return SkillExecResult(
                        status=SkillExecStatus.FALLBACK,
                        skill_name=result.skill_name,
                        result=fb_result,
                        error=result.error,
                        error_detail=result.error_detail,
                        retry_count=result.retry_count,
                        fallback_used=True,
                        fallback_skill=fallback_skill,
                        duration_ms=result.duration_ms,
                    )
                except Exception as e:
                    logger.warning(f"备用技能也失败了: {fallback_skill}: {e}")

        on_failure = step.get("on_failure", "stop")
        if on_failure == "skip":
            return SkillExecResult(
                status=SkillExecStatus.SKIPPED,
                skill_name=result.skill_name,
                error=result.error,
                error_detail=result.error_detail,
                retry_count=result.retry_count,
                duration_ms=result.duration_ms,
            )

        return result

    def get_execution_summary(self, context: ExecutionContext) -> dict:
        total = len(context.history)
        succeeded = sum(
            1 for r in context.history
            if r.status in (SkillExecStatus.SUCCESS, SkillExecStatus.FALLBACK)
        )
        failed = sum(
            1 for r in context.history
            if r.status == SkillExecStatus.FAILED
        )
        skipped = sum(
            1 for r in context.history
            if r.status == SkillExecStatus.SKIPPED
        )
        fallbacks = sum(
            1 for r in context.history
            if r.fallback_used
        )
        total_duration = sum(r.duration_ms for r in context.history)

        return {
            "total_steps": total,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "fallbacks_used": fallbacks,
            "total_duration_ms": total_duration,
            "progress": succeeded / total if total > 0 else 0,
            "last_error": (
                context.history[-1].error
                if context.history and context.history[-1].error
                else ""
            ),
        }

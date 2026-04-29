import json
import logging
import os
import re
from typing import Optional, List
from datetime import datetime

from Coder.sop.intent_classifier import IntentType, IntentResult, classify_intent
from Coder.sop.state_machine import StateMachine, SOPState

logger = logging.getLogger(__name__)

_STEP_PATTERN = re.compile(
    r"(?:步骤\s*(\d+)|(\d+)[\.、])\s*[：:]\s*(.+?)(?=(?:步骤\s*\d+|\d+[\.、])\s*[：:]|\Z)",
    re.DOTALL,
)

_SKILL_BINDING_RE = re.compile(
    r'@skill\(([\w_]+)\)',
)

_SKILL_REF_RE = re.compile(
    r"使用技能[：:]\s*([\w_]+)",
)

_STEP_SKILL_LINE_RE = re.compile(
    r"(?:步骤\s*(\d+)|(\d+)[\.、])\s*"
    r"(?:\[技能[：:]\s*([\w_]+)\])?\s*[：:]\s*(.+)",
    re.MULTILINE,
)

_SUPPORTED_EXTENSIONS = (".json", ".md", ".txt")


class FlowOrchestrator:
    def __init__(self, sop_dir: Optional[str] = None):
        if sop_dir is None:
            sop_dir = os.path.join(
                os.path.dirname(__file__), "..", "knowledge", "sop_docs"
            )
        self.sop_dir = os.path.normpath(sop_dir)
        os.makedirs(self.sop_dir, exist_ok=True)
        self.state_machine = StateMachine()
        self._sop_cache: dict[str, dict] = {}
        self._cache_mtimes: dict[str, float] = {}
        self._file_index: Optional[dict[str, str]] = None

    def _ensure_file_index(self):
        if self._file_index is not None:
            return
        self._file_index = {}
        if not os.path.exists(self.sop_dir):
            return
        for filename in os.listdir(self.sop_dir):
            name, ext = os.path.splitext(filename)
            if ext.lower() in _SUPPORTED_EXTENSIONS:
                self._file_index[name.lower()] = os.path.join(
                    self.sop_dir, filename
                )

    def _invalidate_file_index(self):
        self._file_index = None

    def route(self, user_input: str) -> IntentResult:
        return classify_intent(user_input)

    def get_sop(self, sop_name: str) -> Optional[dict]:
        cached = self._sop_cache.get(sop_name)
        if cached:
            cached_mtime = self._cache_mtimes.get(sop_name)
            current_mtime = self._get_sop_mtime(sop_name)
            if (
                cached_mtime is not None
                and current_mtime is not None
                and cached_mtime >= current_mtime
            ):
                return cached
            if cached_mtime is not None and current_mtime is None:
                del self._sop_cache[sop_name]
                del self._cache_mtimes[sop_name]
                return None

        sop = self._load_sop_from_file(sop_name)
        if sop:
            self._sop_cache[sop_name] = sop
            self._cache_mtimes[sop_name] = (
                self._get_sop_mtime(sop_name) or 0.0
            )
        return sop

    def _get_sop_mtime(self, sop_name: str) -> Optional[float]:
        for ext in _SUPPORTED_EXTENSIONS:
            path = os.path.join(self.sop_dir, f"{sop_name}{ext}")
            if os.path.exists(path):
                return os.path.getmtime(path)
        return None

    def _load_sop_from_file(self, sop_name: str) -> Optional[dict]:
        for ext in _SUPPORTED_EXTENSIONS:
            path = os.path.join(self.sop_dir, f"{sop_name}{ext}")
            if os.path.exists(path):
                return self._read_sop_file(path, sop_name)

        self._ensure_file_index()
        lower_name = sop_name.lower()
        matched_path = self._file_index.get(lower_name)
        if matched_path:
            return self._read_sop_file(matched_path, sop_name)

        for idx_name, idx_path in self._file_index.items():
            if lower_name in idx_name:
                return self._read_sop_file(idx_path, sop_name)

        return None

    def _read_sop_file(self, path: str, sop_name: str) -> Optional[dict]:
        try:
            if path.endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._normalize_sop_steps(data, sop_name)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return self._parse_text_sop(content, sop_name)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"加载SOP文件失败 {path}: {e}")
            return None

    def _normalize_sop_steps(self, data: dict, sop_name: str) -> dict:
        steps = data.get("steps", [])
        for i, step in enumerate(steps):
            if "index" not in step:
                step["index"] = i
            if "skill" not in step:
                step["skill"] = ""
            if "fallback_skill" not in step:
                step["fallback_skill"] = ""
            if "on_failure" not in step:
                step["on_failure"] = "stop"
            if "condition" not in step:
                step["condition"] = ""
        data.setdefault("name", sop_name)
        data.setdefault("source", "json")
        return data

    def _parse_text_sop(self, content: str, name: str) -> dict:
        steps = self._parse_skill_bound_steps(content)

        if not steps:
            steps = self._parse_legacy_steps(content)

        return {
            "name": name,
            "description": content[:200],
            "steps": steps,
            "source": "text",
            "raw_content": content,
        }

    def _parse_skill_bound_steps(self, content: str) -> list:
        steps = []
        for match in _STEP_SKILL_LINE_RE.finditer(content):
            step_num = match.group(1) or match.group(2)
            skill_name = match.group(3) or ""
            step_desc = match.group(4).strip()

            step = {
                "index": int(step_num) - 1,
                "name": f"步骤{step_num}",
                "description": step_desc[:200],
                "skill": skill_name,
                "fallback_skill": "",
                "on_failure": "stop",
            }
            steps.append(step)
        return steps

    def _parse_legacy_steps(self, content: str) -> list:
        steps = []
        for match in _STEP_PATTERN.finditer(content):
            step_num = match.group(1) or match.group(2)
            step_desc = match.group(3).strip()

            skill_name = ""
            skill_ref = _SKILL_REF_RE.search(step_desc)
            if skill_ref:
                skill_name = skill_ref.group(1)

            for binding_match in _SKILL_BINDING_RE.finditer(step_desc):
                skill_name = binding_match.group(1)

            steps.append({
                "index": int(step_num) - 1,
                "name": f"步骤{step_num}",
                "description": step_desc[:200],
                "skill": skill_name,
                "fallback_skill": "",
                "on_failure": "stop",
            })

        if not steps:
            lines = [
                l.strip() for l in content.split("\n") if l.strip()
            ]
            for i, line in enumerate(lines):
                if line.startswith(
                    ("#", "-", "*", "1.", "2.", "3.", "4.", "5.")
                ):
                    clean = line.lstrip("#- *").strip()
                    if clean:
                        steps.append({
                            "index": i,
                            "name": f"步骤{i + 1}",
                            "description": clean[:200],
                            "skill": "",
                            "fallback_skill": "",
                            "on_failure": "stop",
                        })

        return steps

    def get_adaptive_next_steps(
        self,
        sop_name: str,
        current_step: int,
        execution_result: dict,
    ) -> List[dict]:
        sop = self.get_sop(sop_name)
        if not sop:
            return []

        steps = sop.get("steps", [])
        if current_step >= len(steps) - 1:
            return []

        next_index = current_step + 1
        remaining_steps = steps[next_index:]

        if not execution_result.get("success", True):
            failed_on = execution_result.get("step", "")
            on_failure_steps = [
                s for s in remaining_steps
                if s.get("on_failure", "stop") == "execute"
                or s.get("condition", "").startswith("on_failure")
            ]
            if on_failure_steps:
                logger.info(
                    f"自适应流程: 检测到失败，切换到失败恢复步骤"
                )
                return on_failure_steps

        on_success_steps = [
            s for s in remaining_steps
            if not s.get("condition", "").startswith("on_failure")
        ]
        return on_success_steps or remaining_steps

    def get_skill_bound_steps(self, sop_name: str) -> List[dict]:
        sop = self.get_sop(sop_name)
        if not sop:
            return []
        return [
            s for s in sop.get("steps", [])
            if s.get("skill", "")
        ]

    def list_sops(self) -> list[str]:
        self._ensure_file_index()
        return sorted(set(
            os.path.splitext(os.path.basename(p))[0]
            for p in self._file_index.values()
        ))

    def save_sop(self, sop_name: str, sop_data: dict) -> str:
        sop_data = self._normalize_sop_steps(sop_data, sop_name)
        path = os.path.join(self.sop_dir, f"{sop_name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sop_data, f, ensure_ascii=False, indent=2)

        self._sop_cache.pop(sop_name, None)
        self._cache_mtimes.pop(sop_name, None)
        self._invalidate_file_index()

        logger.info(f"保存SOP: {sop_name}")
        return path

    def delete_sop(self, sop_name: str) -> bool:
        deleted = False
        for ext in _SUPPORTED_EXTENSIONS:
            path = os.path.join(self.sop_dir, f"{sop_name}{ext}")
            if os.path.exists(path):
                os.remove(path)
                deleted = True

        self._sop_cache.pop(sop_name, None)
        self._cache_mtimes.pop(sop_name, None)
        self._invalidate_file_index()

        return deleted

    def start_execution(self, sop_name: str) -> Optional[dict]:
        sop = self.get_sop(sop_name)
        if not sop:
            return None

        steps = sop.get("steps", [])
        execution = self.state_machine.create_execution(
            sop_name, len(steps)
        )
        self.state_machine.transition(sop_name, SOPState.RUNNING)

        skill_steps = self.get_skill_bound_steps(sop_name)

        return {
            "sop_name": sop_name,
            "total_steps": len(steps),
            "skill_steps": len(skill_steps),
            "current_step": 0,
            "state": execution.state.value,
        }

    def get_execution_status(self, sop_name: str) -> Optional[dict]:
        execution = self.state_machine.get_execution(sop_name)
        if not execution:
            return None

        return {
            "sop_name": sop_name,
            "state": execution.state.value,
            "current_step": execution.current_step,
            "total_steps": execution.total_steps,
            "progress": self.state_machine.get_progress(sop_name),
            "step_results": [
                {
                    "step_index": r.step_index,
                    "step_name": r.step_name,
                    "status": r.status,
                    "result": r.result[:200] if r.result else "",
                    "error": r.error,
                }
                for r in execution.step_results
            ],
            "error": execution.error,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
        }

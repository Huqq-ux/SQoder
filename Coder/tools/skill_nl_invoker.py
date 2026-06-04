import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from Coder.tools.skill_registry import SkillRegistry
from Coder.tools.skill_store import SkillMeta

logger = logging.getLogger(__name__)


class InvokeStage(Enum):
    DETECTING = "detecting"
    COLLECTING_PARAMS = "collecting_params"
    CONFIRMING = "confirming"
    EXECUTING = "executing"
    DONE = "done"


@dataclass
class SkillInvocationState:
    skill_name: str = ""
    skill_display: str = ""
    matched_params: Dict[str, Any] = field(default_factory=dict)
    missing_params: List[str] = field(default_factory=list)
    stage: InvokeStage = InvokeStage.DETECTING
    needs_confirmation: bool = False
    result: Any = None
    error: str = ""

    def reset(self):
        self.skill_name = ""
        self.skill_display = ""
        self.matched_params.clear()
        self.missing_params.clear()
        self.stage = InvokeStage.DETECTING
        self.needs_confirmation = False
        self.result = None
        self.error = ""


_DANGEROUS_KEYWORDS = [
    "删除", "格式化", "清空", "重置", "停止", "关闭",
    "卸载", "移除", "覆盖", "重写", "覆盖写入",
    "drop", "delete", "remove", "format",
]


_SKILL_CALL_PATTERNS = [
    re.compile(r"(?:使用|调用|用|执行|运行)\s*(?:技能|功能)?\s*[：:]*\s*(.+?)(?:[，,。！!]|$)", re.DOTALL),
    re.compile(r"帮(?:我|助)\s*(.+?)(?:[，,。！!]|$)", re.DOTALL),
    re.compile(r"(?:能不能|可以|能|请)\s*(?:帮我)?\s*(.+?)(?:[？?吗]|$)", re.DOTALL),
]


_CHINESE_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")


def _is_cjk_char(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
    )

_PARAM_PATTERNS = [
    re.compile(r"""[''"](.+?)['""]\s*[：:=]\s*['""](.+?)['""]"""),
    re.compile(r"""[''"](.+?)['""]\s*[:：=]\s*['""](.+?)['""]"""),
    re.compile(r'(?:参数|输入|内容|文本|文件|路径|名称)\s*[：:=]\s*["\'](.+?)["\']'),
    re.compile(r'(?:参数|输入|内容|文本|文件|路径|名称)\s*[：:=]\s*(.+?)(?:[，,。！!\s]|$)'),
    re.compile(r'["\'](.+?)["\']'),
    re.compile(r'[：:=]\s*(.+?)(?:[，,。！!\s]|$)'),
]


class SkillNLInvoker:

    def __init__(self, registry: SkillRegistry = None):
        self.registry = registry or SkillRegistry()
        if not self.registry._initialized:
            self.registry.initialize()
        self._state = SkillInvocationState()

    @property
    def state(self) -> SkillInvocationState:
        return self._state

    def reset(self):
        self._state.reset()
        logger.info("SkillNLInvoker 状态已重置")

    def detect_skill_call(
        self, user_input: str
    ) -> Tuple[bool, Optional[SkillMeta], float]:
        if not user_input or not user_input.strip():
            return False, None, 0.0

        metas = self.registry.list_all()
        if not metas:
            return False, None, 0.0

        user_lower = user_input.lower()
        best_meta = None
        best_score = 0.0

        user_mentions_skill = bool(
            re.search(r"(?:技能|skill|功能调用)", user_lower)
        )

        for meta in metas:
            score = 0.0

            if meta.name.lower() in user_lower:
                score += 50
            if meta.display_name.lower() in user_lower:
                score += 40

            name_parts = re.split(r"[_\-\s]+", meta.name.lower())
            for part in name_parts:
                if len(part) >= 2 and part in user_lower:
                    score += 8

            display_chars = list(meta.display_name)
            for i in range(len(display_chars) - 1):
                bigram = "".join(display_chars[i : i + 2])
                if len(bigram) >= 2 and bigram in user_lower:
                    score += 4
            for ch in display_chars:
                if _is_cjk_char(ch) and ch in user_lower:
                    score += 1

            if meta.description:
                desc_parts = re.split(r"[\s，,。.]+", meta.description.lower())
                for dp in desc_parts:
                    if len(dp) >= 2 and dp in user_lower:
                        score += 2

            for tag in meta.tags:
                if tag.lower() in user_lower:
                    score += 6

            if meta.category:
                for cat_chunk in self._chunk_chinese(meta.category):
                    if cat_chunk in user_lower:
                        score += 3
                        break

            action_words = self._extract_action_words(meta)
            for aw in action_words:
                if aw in user_lower:
                    score += 5

            if user_mentions_skill:
                score += 3

            if score > best_score:
                best_score = score
                best_meta = meta

        threshold = 10

        if best_score >= threshold:
            logger.info(
                f"检测到技能调用意图: {best_meta.name} (score={best_score})"
            )
            return True, best_meta, best_score

        return False, None, 0.0

    @staticmethod
    def _chunk_chinese(text: str) -> list:
        results = []
        chars = list(text)
        for i in range(len(chars) - 1):
            results.append("".join(chars[i : i + 2]))
        for ch in chars:
            results.append(ch)
        return results

    @staticmethod
    def _extract_action_words(meta: SkillMeta) -> list:
        words = set()
        combined = meta.display_name + " " + meta.description
        for m in re.finditer(r"[\u4e00-\u9fff]{1,3}(?:文本|数据|文件|输入|输出|代码|字符串|数字|列表|字典|图像)", combined):
            words.add(m.group())
        for m in re.finditer(r"(?:反转|翻转|颠倒|排序|过滤|搜索|查找|替换|格式化|压缩|解压|加密|解密|编码|解码|转换|翻译|分析|统计|计算|合并|拆分|提取|清洗|验证|检查|生成|创建|删除|移动|复制|重命名|上传|下载)", combined):
            words.add(m.group())
        return list(words)

    def extract_params(
        self,
        user_input: str,
        skill_meta: SkillMeta,
    ) -> Tuple[Dict[str, Any], List[str]]:
        extracted: Dict[str, Any] = {}
        missing: List[str] = []

        if not skill_meta.parameters:
            return extracted, missing

        remaining = user_input

        for param_def in skill_meta.parameters:
            param_name = param_def.get("name", "")
            param_type = param_def.get("type", "str")
            param_required = param_def.get("required", False)
            param_desc = param_def.get("description", "")

            value = None

            if param_name:
                patterns = [
                    re.compile(
                        rf'{param_name}\s*[：:=]\s*(.+?)(?:[，,。！!\s]|$)'
                    ),
                    re.compile(
                        rf'(?:{param_name})\s*(?:是|为|=)\s*(.+?)(?:[，,。！!\s]|$)'
                    ),
                ]
                for pat in patterns:
                    m = pat.search(user_input)
                    if m:
                        value = m.group(1).strip().strip("\"'")
                        remaining = remaining.replace(m.group(0), "")
                        break

            if not value:
                for p_def in _PARAM_PATTERNS:
                    matches = list(p_def.finditer(user_input))
                    if not matches:
                        continue
                    last_match = matches[-1]
                    groups = last_match.groups()
                    if len(groups) == 2 and groups[0] == param_name:
                        value = groups[1]
                        remaining = remaining.replace(last_match.group(0), "")
                        break
                    if len(groups) == 1 and not extracted:
                        value = groups[0]
                        remaining = remaining.replace(last_match.group(0), "")
                        break

            if value:
                if param_type == "int":
                    try:
                        value = int(re.sub(r'[^\d\-]', '', str(value)))
                    except ValueError:
                        value = 0
                elif param_type == "float":
                    try:
                        value = float(str(value))
                    except ValueError:
                        value = 0.0
                extracted[param_name] = value
            elif param_required:
                missing.append(param_name)

        if missing:
            stripped = self._strip_noise(remaining, skill_meta)
            if stripped:
                positional = stripped.split()
                if positional:
                    for mp in list(missing):
                        if positional:
                            extracted[mp] = positional[0]
                            missing.remove(mp)
                            positional = positional[1:]

        return extracted, missing

    def _strip_noise(self, text: str, skill_meta: SkillMeta) -> str:
        result = text

        prefixes = sorted([
            "帮我", "请帮我", "请你", "帮忙",
            "能不能", "可以", "能", "请",
            "用技能", "调用技能", "使用技能", "执行技能", "运行技能",
        ], key=len, reverse=True)
        for p in prefixes:
            if result.startswith(p):
                result = result[len(p):]
                break

        result = result.strip("，,。.！! ")

        return result

    def build_missing_param_prompt(
        self,
        skill_meta: SkillMeta,
        missing_params: List[str],
    ) -> str:
        parts = [
            f"📋 要执行 **{skill_meta.display_name}**，还需要以下信息：",
            "",
        ]

        for mp in missing_params:
            for p in skill_meta.parameters:
                if p.get("name") == mp:
                    ptype = p.get("type", "str")
                    desc = p.get("description", mp)
                    parts.append(f"- **{mp}** ({ptype}): {desc}")

        parts.append("")
        parts.append("请提供这些参数的取值，例如：")
        example_parts = []
        for mp in missing_params:
            example_parts.append(f"{mp}=<值>")
        parts.append("  " + "，".join(example_parts))

        return "\n".join(parts)

    def needs_confirmation(self, skill_meta: SkillMeta) -> bool:
        combined = (
            skill_meta.display_name
            + " "
            + skill_meta.description
            + " "
            + " ".join(skill_meta.tags)
        )
        combined_lower = combined.lower()
        for kw in _DANGEROUS_KEYWORDS:
            if kw in combined_lower:
                return True
        return False

    def build_confirmation_prompt(
        self,
        skill_meta: SkillMeta,
        params: Dict[str, Any],
    ) -> str:
        parts = [
            f"⚠️ 确认执行 **{skill_meta.display_name}**",
            "",
            f"描述: {skill_meta.description or '(无)'}",
            "",
        ]

        if params:
            parts.append("参数:")
            for k, v in params.items():
                parts.append(f"  - {k} = `{v}`")
            parts.append("")

        parts.append("此操作可能涉及敏感操作，确定执行吗？")
        parts.append("- 回复 **确定** / **是** / **执行** 来确认")
        parts.append("- 回复 **取消** / **否** 来放弃")

        return "\n".join(parts)

import re
from enum import Enum
from dataclasses import dataclass


class IntentType(Enum):
    QUERY_SOP = "query_sop"
    EXECUTE_SOP = "execute_sop"
    GENERAL_CHAT = "general_chat"
    MODIFY_SOP = "modify_sop"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    sop_name: str = ""
    raw_input: str = ""


_EXECUTE_KEYWORDS = [
    "执行", "运行", "部署", "安装", "启动", "停止", "重启",
    "按照", "根据", "依照", "遵循", "按SOP",
]

_QUERY_KEYWORDS = [
    "查询", "查看", "什么是", "如何", "流程", "步骤",
    "SOP", "规范", "标准", "操作指南", "手册", "文档",
    "有没有", "是否存在", "怎么操作", "怎么做",
]

_MODIFY_KEYWORDS = [
    "修改SOP", "更新SOP", "新增SOP", "删除SOP", "编辑SOP",
    "添加步骤", "删除步骤", "修改步骤",
]

_MODIFY_ACTION_KEYWORDS = ["修改", "删除", "更新"]

_GENERAL_CHAT_KEYWORDS = [
    "你是谁", "你叫什么", "你是什么", "智能体是谁", "助手是谁",
    "介绍一下你自己", "描述一下你自己",
]

_SOP_NAME_PATTERNS = [
    re.compile(
        r"(?:执行|运行|查看|查询|按照|根据|依照)\s*[《【]?(.+?)[》】]?\s*(?:的)?(?:sop|流程|步骤|规范)"
    ),
    re.compile(
        r"(.+?)(?:的)?(?:部署|安装|启动|配置|检查|排查)(?:sop|流程|步骤)"
    ),
    re.compile(
        r"(?:sop|流程|步骤|规范)[：:]\s*(.+?)(?:的|$)"
    ),
    re.compile(
        r"(.+?)(?:应用|服务|项目|系统)?(?:的)?(?:部署|安装|启动|配置|检查|排查)"
    ),
]

_SOP_ACTION_KEYWORDS = ["部署", "安装", "启动", "配置", "检查", "排查", "故障"]
_STRIP_CHARS_RE = re.compile(r"[的如何是有没请问]")


def classify_intent(user_input: str) -> IntentResult:
    text = user_input.strip().lower()

    modify_score = sum(1 for kw in _MODIFY_KEYWORDS if kw.lower() in text)
    if modify_score > 0:
        sop_name = _extract_sop_name(text)
        return IntentResult(
            intent=IntentType.MODIFY_SOP,
            confidence=min(modify_score / 2.0, 1.0),
            sop_name=sop_name,
            raw_input=user_input,
        )

    execute_score = sum(1 for kw in _EXECUTE_KEYWORDS if kw.lower() in text)
    query_score = sum(1 for kw in _QUERY_KEYWORDS if kw.lower() in text)

    general_score = sum(1 for kw in _GENERAL_CHAT_KEYWORDS if kw in text)
    if general_score > 0 and execute_score == 0 and query_score == 0:
        return IntentResult(
            intent=IntentType.GENERAL_CHAT,
            confidence=min(general_score / 2.0, 1.0),
            raw_input=user_input,
        )

    max_score = max(execute_score, query_score)
    if max_score == 0:
        return IntentResult(
            intent=IntentType.GENERAL_CHAT,
            confidence=0.3,
            raw_input=user_input,
        )

    if execute_score >= query_score:
        best_intent = IntentType.EXECUTE_SOP
        confidence = min(execute_score / 5.0, 1.0)
    else:
        best_intent = IntentType.QUERY_SOP
        confidence = min(query_score / 5.0, 1.0)

    sop_name = _extract_sop_name(text)

    return IntentResult(
        intent=best_intent,
        confidence=max(confidence, 0.2),
        sop_name=sop_name,
        raw_input=user_input,
    )


def _extract_sop_name(text: str) -> str:
    for pattern in _SOP_NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            if name and len(name) <= 20:
                return name

    for kw in _SOP_ACTION_KEYWORDS:
        if kw in text:
            prefix = text.split(kw)[0].strip()
            if prefix and len(prefix) <= 15:
                clean = _STRIP_CHARS_RE.sub("", prefix).strip()
                if clean:
                    return clean + kw

    return ""

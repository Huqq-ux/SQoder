import re
import logging
from typing import Optional

from Coder.browser.browser_config import BROWSER_CONFIG, QUERY_TYPE_CONFIG

logger = logging.getLogger(__name__)

_NOISE_PATTERNS = [
    re.compile(r"cookie|隐私|广告|订阅|登录|注册|下载APP|关注|分享|举报", re.IGNORECASE),
    re.compile(r"copyright|all rights reserved|版权所有", re.IGNORECASE),
    re.compile(r"javascript.*?;|window\..*?;|document\..*?;", re.IGNORECASE),
]

_CONTENT_CLEAN_RE = re.compile(r"\s+")


def extract_relevant_content(raw_content: str, query_type: str, keywords: list = None) -> str:
    if not raw_content:
        return ""

    lines = raw_content.split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_noise = False
        for pattern in _NOISE_PATTERNS:
            if pattern.search(line):
                is_noise = True
                break
        if is_noise:
            continue

        if len(line) < 3:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def verify_content(content: str, query_type: str, location: str = None,
                   target_date: str = None) -> dict:
    if not content:
        return {"valid": False, "confidence": 0, "reason": "内容为空"}

    confidence = 1
    reasons = []

    type_config = QUERY_TYPE_CONFIG.get(query_type, {})
    type_keywords = {
        "weather": ["天气", "气温", "温度", "晴", "阴", "雨", "雪", "风", "度",
                     "高温", "低温", "最高", "最低", "weather", "temp", "degree"],
        "news": ["报道", "消息", "记者", "发布", "声明", "表示", "据悉", "新闻",
                 "news", "report", "said", "announced"],
    }

    kw_list = type_keywords.get(query_type, [])
    matched_kw = [kw for kw in kw_list if kw in content]
    if matched_kw:
        confidence += min(len(matched_kw), 3)
    else:
        confidence -= 1
        reasons.append("内容中未找到相关类型关键词")

    if location:
        if location in content:
            confidence += 2
        else:
            confidence -= 2
            reasons.append(f"内容中未找到地点 '{location}'")

    if target_date:
        year = target_date[:4]
        month = target_date[5:7].lstrip("0")
        day = target_date[8:].lstrip("0")

        date_found = False
        for date_str in [target_date, f"{month}月{day}日", f"{month}/{day}",
                         f"{month}-{day}", f"{year}年{month}月{day}日"]:
            if date_str in content:
                date_found = True
                break

        if date_found:
            confidence += 2
        else:
            confidence -= 1
            reasons.append(f"内容中未找到日期 '{target_date}'")

    confidence = max(0, min(confidence, 5))

    valid = confidence >= 2
    if not valid:
        reasons.insert(0, "可信度不足")

    return {
        "valid": valid,
        "confidence": confidence,
        "reason": "; ".join(reasons) if reasons else "验证通过",
    }


def format_response(query: str, query_type: str, results: list,
                    verification: dict = None) -> str:
    if not results:
        return "未能从网页中检索到相关信息。请尝试更换查询词或稍后再试。"

    parts = []

    if verification and not verification["valid"]:
        parts.append(f"[注意: 信息可信度较低 - {verification['reason']}]")
        parts.append("")

    if query_type == "weather":
        parts.append(_format_weather(query, results))
    elif query_type == "news":
        parts.append(_format_news(query, results))
    else:
        parts.append(_format_general(query, results))

    source_info = []
    for r in results[:3]:
        source = r.get("source", r.get("title", "未知来源"))
        url = r.get("link", r.get("url", ""))
        if url:
            source_info.append(f"  - {source}: {url}")
        else:
            source_info.append(f"  - {source}")

    if source_info:
        parts.append("")
        parts.append("信息来源:")
        parts.extend(source_info)

    return "\n".join(parts)


def _format_weather(query: str, results: list) -> str:
    parts = [f"关于「{query}」的天气信息：", ""]

    for r in results[:3]:
        content = r.get("content", r.get("snippet", ""))
        source = r.get("source", "未知来源")
        if content:
            cleaned = extract_relevant_content(content, "weather")
            if cleaned:
                parts.append(f"[{source}]")
                parts.append(cleaned[:500])
                parts.append("")

    return "\n".join(parts)


def _format_news(query: str, results: list) -> str:
    parts = [f"关于「{query}」的最新消息：", ""]

    for i, r in enumerate(results[:5]):
        title = r.get("title", "")
        snippet = r.get("content", r.get("snippet", ""))
        source = r.get("source", "未知来源")

        if title:
            parts.append(f"{i + 1}. {title}")
        if snippet:
            cleaned = extract_relevant_content(snippet, "news")
            if cleaned:
                parts.append(f"   {cleaned[:200]}")
        parts.append("")

    return "\n".join(parts)


def _format_general(query: str, results: list) -> str:
    parts = [f"关于「{query}」的搜索结果：", ""]

    for i, r in enumerate(results[:5]):
        title = r.get("title", "")
        snippet = r.get("content", r.get("snippet", ""))
        source = r.get("source", "未知来源")

        if title:
            parts.append(f"{i + 1}. {title}")
        if snippet:
            cleaned = extract_relevant_content(snippet, "general")
            if cleaned:
                parts.append(f"   {cleaned[:300]}")
        parts.append("")

    return "\n".join(parts)

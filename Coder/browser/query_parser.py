import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta

from Coder.browser.browser_config import SEARCH_CONFIG, QUERY_TYPE_CONFIG

logger = logging.getLogger(__name__)

_LOCATION_RE = re.compile(
    r"([\u4e00-\u9fff]{1,3}(?:省|市|区|县|镇|州)|"
    r"[\u4e00-\u9fff]{1,4}(?:省|市|区|县))"
    r"|((?:北京|上海|天津|重庆|深圳|广州|长沙|湘潭|杭州|成都|武汉|南京|"
    r"苏州|郑州|青岛|大连|厦门|昆明|哈尔滨|西安|济南|福州|合肥|南昌|"
    r"贵阳|南宁|海口|三亚|石家庄|太原|沈阳|长春|兰州|银川|西宁|"
    r"呼和浩特|乌鲁木齐|拉萨|香港|澳门|台北))"
)

_DATE_PATTERNS = [
    (re.compile(r"今天|今日|现在|当前|目前"), 0),
    (re.compile(r"明天|明日|第二天"), 1),
    (re.compile(r"后天"), 2),
    (re.compile(r"大后天"), 3),
    (re.compile(r"昨天|昨日"), -1),
    (re.compile(r"前天"), -2),
    (re.compile(r"本周|这周"), "this_week"),
    (re.compile(r"下周|下星期"), "next_week"),
    (re.compile(r"(\d{1,2})月(\d{1,2})[日号]"), "absolute"),
    (re.compile(r"最近|近期|这几天"), "recent"),
]


@dataclass
class ParsedQuery:
    raw_query: str
    query_type: str = "general"
    location: Optional[str] = None
    date_offset: Optional[int] = None
    date_label: Optional[str] = None
    target_date: Optional[str] = None
    keywords: list = field(default_factory=list)
    is_time_sensitive: bool = False
    search_terms: str = ""


def _detect_query_type(query: str) -> str:
    weather_kw = SEARCH_CONFIG["weather_keywords"]
    news_kw = SEARCH_CONFIG["news_keywords"]

    for kw in weather_kw:
        if kw in query:
            return "weather"

    for kw in news_kw:
        if kw in query:
            return "news"

    return "general"


def _extract_location(query: str) -> Optional[str]:
    m = _LOCATION_RE.search(query)
    if m:
        return m.group(1) or m.group(2)
    return None


def _extract_date(query: str):
    for pattern, offset in _DATE_PATTERNS:
        m = pattern.search(query)
        if not m:
            continue

        if offset == "absolute":
            month = int(m.group(1))
            day = int(m.group(2))
            now = datetime.now()
            try:
                target = datetime(now.year, month, day)
                if target < now - timedelta(days=30):
                    target = datetime(now.year + 1, month, day)
                return (now - target).days * -1, m.group(0)
            except ValueError:
                return None, m.group(0)

        if isinstance(offset, int):
            return offset, m.group(0)

        return None, m.group(0)

    return None, None


def _check_time_sensitive(query: str) -> bool:
    time_kw = SEARCH_CONFIG["time_keywords"]
    for kw in time_kw:
        if kw in query:
            return True
    return False


def _build_search_terms(parsed: ParsedQuery) -> str:
    parts = []

    if parsed.location:
        parts.append(parsed.location)

    if parsed.query_type == "weather":
        parts.append("天气")
    elif parsed.query_type == "news":
        parts.append("最新")

    if parsed.date_label:
        parts.append(parsed.date_label)

    for kw in parsed.keywords:
        if kw not in parts:
            parts.append(kw)

    if not parts:
        parts.append(parsed.raw_query)

    return " ".join(parts)


def parse_query(query: str) -> ParsedQuery:
    if not query or not query.strip():
        return ParsedQuery(raw_query=query or "", query_type="general")

    query = query.strip()
    query_type = _detect_query_type(query)
    location = _extract_location(query)
    date_offset, date_label = _extract_date(query)
    is_time_sensitive = _check_time_sensitive(query)

    cleaned = query
    for pattern, _ in _DATE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    location_m = _LOCATION_RE.search(cleaned)
    if location_m:
        cleaned = cleaned.replace(location_m.group(0), "", 1)

    type_keywords = SEARCH_CONFIG.get("weather_keywords", []) + SEARCH_CONFIG.get("news_keywords", [])
    keywords = []
    for kw in type_keywords:
        if kw in cleaned:
            cleaned = cleaned.replace(kw, "", 1)
            if kw not in keywords:
                keywords.append(kw)

    remaining = cleaned.strip()
    if remaining and remaining not in keywords:
        keywords.append(remaining)

    target_date = None
    if isinstance(date_offset, int):
        target_date = (datetime.now() + timedelta(days=date_offset)).strftime("%Y-%m-%d")

    parsed = ParsedQuery(
        raw_query=query,
        query_type=query_type,
        location=location,
        date_offset=date_offset,
        date_label=date_label,
        target_date=target_date,
        keywords=keywords,
        is_time_sensitive=is_time_sensitive,
    )

    parsed.search_terms = _build_search_terms(parsed)

    logger.info(
        f"查询解析: type={query_type}, location={location}, "
        f"date_offset={date_offset}, target_date={target_date}, "
        f"search_terms={parsed.search_terms}"
    )

    return parsed

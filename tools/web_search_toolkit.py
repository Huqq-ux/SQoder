import time
import json
import logging
import threading
from datetime import datetime

from langchain_core.tools import tool

from Coder.browser.query_parser import parse_query
from Coder.browser.search_strategy import (
    search_engine, fetch_direct_site, fetch_page_content, _close_browser,
)
from Coder.browser.content_extractor import (
    verify_content, format_response,
)
from Coder.browser.browser_config import BROWSER_CONFIG

logger = logging.getLogger(__name__)

_search_log_lock = threading.Lock()
_search_log_path = "logs/web_search_queries.jsonl"


def _log_search(event: str, query: str, result_count: int = 0,
                latency_ms: float = 0.0, error: str = ""):
    import os
    log_dir = os.path.dirname(_search_log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "query": query[:100],
        "result_count": result_count,
        "latency_ms": round(latency_ms, 2),
        "error": error,
    }
    with _search_log_lock:
        try:
            with open(_search_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _do_web_search(query: str, query_type_hint: str = "auto") -> str:
    start = time.monotonic()

    if not query or not query.strip():
        return "查询不能为空。"

    query = query.strip()
    if len(query) > 500:
        query = query[:500]

    try:
        parsed = parse_query(query)

        if query_type_hint != "auto" and query_type_hint in ("weather", "news", "general"):
            parsed.query_type = query_type_hint

        all_results = []

        if parsed.query_type in ("weather",):
            direct = fetch_direct_site(parsed)
            if direct and direct.get("content"):
                all_results.append(direct)

        if not all_results:
            search_results = search_engine(parsed)
            for sr in search_results:
                if sr.get("snippet") and len(sr["snippet"]) > 20:
                    all_results.append({
                        "source": sr.get("title", "未知来源"),
                        "link": sr.get("link", ""),
                        "content": sr["snippet"],
                    })

            top_links = [
                sr for sr in search_results
                if sr.get("link") and sr.get("link").startswith("http")
            ][:2]

            for sr in top_links:
                retry_count = BROWSER_CONFIG["retry_count"]
                for attempt in range(retry_count + 1):
                    page_content = fetch_page_content(sr["link"])
                    if page_content and page_content.get("content"):
                        all_results.append(page_content)
                        break
                    if attempt < retry_count:
                        time.sleep(BROWSER_CONFIG["retry_delay"])

        if not all_results:
            latency = (time.monotonic() - start) * 1000
            _log_search("search", query, 0, latency)
            return f"未找到与 '{query[:50]}' 相关的实时信息。"

        verification = None
        if parsed.query_type in ("weather", "news"):
            best_content = all_results[0].get("content", "")
            verification = verify_content(
                best_content, parsed.query_type,
                parsed.location, parsed.target_date,
            )

        response = format_response(query, parsed.query_type, all_results, verification)

        latency = (time.monotonic() - start) * 1000
        _log_search("search", query, len(all_results), latency)

        return response

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_search("search", query, 0, latency, type(e).__name__)
        logger.error(f"网页搜索异常: {type(e).__name__}: {e}")
        return f"搜索失败: {type(e).__name__}"


@tool
def web_search(query: str) -> str:
    """通过浏览器搜索实时信息。适用于时效性强的查询，如天气、新闻、最新动态等。
    会自动识别查询类型（天气/新闻/通用），选择合适的搜索引擎和信息来源。

    Args:
        query: 搜索查询，如"湘潭明天天气"、"最新AI新闻"
    """
    return _do_web_search(query, "auto")


@tool
def web_search_weather(query: str) -> str:
    """专门搜索天气信息。自动识别地点和日期，从天气网站获取实时数据。

    Args:
        query: 天气查询，如"湘潭明天天气"、"北京今天气温"
    """
    return _do_web_search(query, "weather")


@tool
def web_search_news(query: str) -> str:
    """专门搜索最新新闻资讯。从搜索引擎获取最新报道。

    Args:
        query: 新闻查询，如"AI最新进展"、"今日科技新闻"
    """
    return _do_web_search(query, "news")


@tool
def web_fetch_page(url: str) -> str:
    """直接访问指定URL并提取页面内容。用于获取特定网页的信息。

    Args:
        url: 要访问的网页URL，必须是完整的http或https地址
    """
    start = time.monotonic()

    if not url or not url.strip():
        return "URL不能为空。"

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return "URL必须以 http:// 或 https:// 开头。"

    if len(url) > 2000:
        return "URL过长。"

    try:
        result = fetch_page_content(url)
        latency = (time.monotonic() - start) * 1000

        if result and result.get("content"):
            _log_search("fetch", url, 1, latency)
            content = result["content"]
            if len(content) > 8000:
                content = content[:8000]
            return f"来源: {result['source']}\nURL: {result['url']}\n\n{content}"
        else:
            _log_search("fetch", url, 0, latency, "no_content")
            return f"无法从 {url} 提取有效内容。"

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_search("fetch", url, 0, latency, type(e).__name__)
        logger.error(f"页面获取异常: {type(e).__name__}: {e}")
        return f"页面获取失败: {type(e).__name__}"


web_search_toolkit = [web_search, web_search_weather, web_search_news, web_fetch_page]

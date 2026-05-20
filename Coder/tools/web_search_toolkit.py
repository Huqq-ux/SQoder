import time
import json
import logging
import threading
from datetime import datetime

from langchain_core.tools import tool

from Coder.browser.query_parser import parse_query
from Coder.browser.search_strategy import (
    search_engine, fetch_direct_site, fetch_page_content,
)
from Coder.browser.content_extractor import (
    verify_content, format_response,
)

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

        search_results = search_engine(parsed)
        has_rich_snippets = False
        for sr in search_results:
            snippet = sr.get("snippet", "")
            title = sr.get("title", "")
            link = sr.get("link", "")
            if title:
                all_results.append({
                    "source": title,
                    "link": link,
                    "content": snippet if snippet else f"(来自 {title})",
                })
                if snippet and len(snippet) > 80:
                    has_rich_snippets = True

        if not has_rich_snippets:
            top_links = [
                sr for sr in search_results
                if sr.get("link") and sr.get("link").startswith("http")
            ][:2]

            page_deadline = time.monotonic() + 10.0
            for sr in top_links:
                if time.monotonic() > page_deadline:
                    break
                page_content = fetch_page_content(sr["link"])
                if page_content and page_content.get("content"):
                    all_results.append(page_content)
                    break

        if not all_results:
            latency = (time.monotonic() - start) * 1000
            _log_search("search", query, 0, latency)
            return (
                f"搜索完成：所有搜索引擎均未返回与 '{query[:50]}' 相关的结果。\n\n"
                f"请基于你已有的知识直接回答用户问题，不要再重复搜索。\n"
                f"如果确实需要实时信息，请告知用户当前搜索服务暂不可用。"
            )

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
        return f"搜索失败: {type(e).__name__}: {str(e)[:100]}"


@tool
def web_search(query: str) -> str:
    """搜索实时信息。返回标题、摘要、链接。

    Args:
        query: 搜索关键词，建议包含地点和时间
    """
    return _do_web_search(query, "auto")


@tool
def web_search_weather(query: str) -> str:
    """搜索指定地点和日期的天气信息。

    Args:
        query: 如「长沙明天天气」「北京气温」
    """
    return _do_web_search(query, "weather")


@tool
def web_search_news(query: str) -> str:
    """搜索最新新闻资讯。

    Args:
        query: 如「AI最新进展」「今日科技新闻」
    """
    return _do_web_search(query, "news")


@tool
def web_fetch_page(url: str) -> str:
    """获取网页详情内容。可能失败，失败后直接用搜索摘要回答，不重试。

    Args:
        url: 完整 HTTP/HTTPS 地址
    """
    start = time.monotonic()

    if not url or not url.strip():
        return "URL不能为空。"

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return "URL必须以 http:// 或 https:// 开头。"

    if len(url) > 2000:
        return "URL过长。"

    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    _blocked_hosts = [
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254", "metadata.google.internal",
    ]
    if hostname.lower() in _blocked_hosts:
        return "不允许访问内部地址。"
    if hostname.startswith("10.") or hostname.startswith("192.168."):
        return "不允许访问私有网络地址。"
    if hostname.startswith("172."):
        parts = hostname.split(".")
        if len(parts) >= 2:
            try:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return "不允许访问私有网络地址。"
            except ValueError:
                pass

    try:
        result = fetch_page_content(url)
        latency = (time.monotonic() - start) * 1000

        if result and result.get("content"):
            _log_search("fetch", url, 1, latency)
            content = result["content"]
            if len(content) > 8000:
                content = content[:8000]
            return (
                f"## 页面内容\n\n"
                f"**来源:** {result['source']}\n"
                f"**URL:** {result['url']}\n\n"
                f"{content}"
            )
        else:
            _log_search("fetch", url, 0, latency, "no_content")
            return f"无法从 {url} 提取有效内容。请确认页面可正常访问。"

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_search("fetch", url, 0, latency, type(e).__name__)
        logger.error(f"页面获取异常: {type(e).__name__}: {e}")
        return f"页面获取失败: {type(e).__name__}: {str(e)[:100]}"


web_search_toolkit = [web_search, web_search_weather, web_search_news, web_fetch_page]

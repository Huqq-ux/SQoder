import logging
import time
import functools
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import quote_plus, urlparse

from Coder.browser.browser_config import (
    BROWSER_CONFIG, SEARCH_CONFIG, QUERY_TYPE_CONFIG,
)
from Coder.browser.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 共享 httpx 客户端（连接池复用）
# ---------------------------------------------------------------------------
_http_client = None
_http_lock = threading.Lock()


def _get_http_client():
    global _http_client
    if _http_client is None:
        with _http_lock:
            if _http_client is None:
                import httpx
                _http_client = httpx.Client(
                    timeout=15.0,
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    headers={
                        "User-Agent": BROWSER_CONFIG["user_agent"],
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    },
                )
    return _http_client


# ---------------------------------------------------------------------------
# SSRF 防护
# ---------------------------------------------------------------------------
def _is_url_allowed(url: str) -> bool:
    if not url:
        return False
    scheme = url.split("://")[0].lower() if "://" in url else ""
    if scheme and scheme not in BROWSER_CONFIG["allowed_schemes"]:
        return False

    # 优先使用 LangChain 内置 SSRF 防护
    try:
        from langchain_core._security import validate_safe_url
        validate_safe_url(url)
        return True
    except ImportError:
        pass
    except Exception:
        return False

    # 仅限 HTTPS
    if scheme == "http":
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in ("www.weather.com.cn", "weather.com.cn"):
            return False

    # 兜底：主机名黑名单
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    _blocked_hosts = [
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254", "metadata.google.internal",
    ]
    if hostname in _blocked_hosts:
        return False
    if hostname.startswith("10.") or hostname.startswith("192.168."):
        return False
    if hostname.startswith("172."):
        parts = hostname.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return False
            except ValueError:
                pass
    return True


# ---------------------------------------------------------------------------
# 内容选择器
# ---------------------------------------------------------------------------
_DEFAULT_CONTENT_SELECTORS = [
    "article", "main", "[role='main']",
    ".content", "#content", ".article-content", ".post-content",
    ".entry-content", ".main-content", ".page-content",
    "section", ".container", ".wrapper",
    "[data-testid='article-body']", ".story-body",
]


# ---------------------------------------------------------------------------
# 请求重试 + 退避
# ---------------------------------------------------------------------------
def _http_get(url: str, headers: dict = None) -> Optional[str]:
    """带重试的 HTTP GET，429/503 指数退避。"""
    client = _get_http_client()
    req_headers = {}
    if headers:
        req_headers.update(headers)
    max_retries = BROWSER_CONFIG.get("retry_count", 2)
    base_delay = BROWSER_CONFIG.get("retry_delay", 1.5)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.get(url, headers=req_headers)
            if resp.status_code in (429, 503):
                delay = base_delay * (2 ** attempt)
                logger.debug(f"HTTP {resp.status_code}, 第 {attempt+1} 次重试, 等待 {delay:.1f}s")
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.debug(f"请求失败 {type(e).__name__}, 第 {attempt+1} 次重试, 等待 {delay:.1f}s")
                time.sleep(delay)

    logger.warning(f"HTTP 请求最终失败 [{url[:60]}]: {type(last_error).__name__}: {last_error}")
    return None


# ---------------------------------------------------------------------------
# 熔断器
# ---------------------------------------------------------------------------
_circuit_state: dict[str, int] = {}
_circuit_lock = threading.Lock()
_CIRCUIT_THRESHOLD = 3


def _circuit_ok(engine: str) -> bool:
    with _circuit_lock:
        return _circuit_state.get(engine, 0) < _CIRCUIT_THRESHOLD


def _circuit_fail(engine: str):
    with _circuit_lock:
        _circuit_state[engine] = _circuit_state.get(engine, 0) + 1


def _circuit_reset(engine: str):
    with _circuit_lock:
        _circuit_state[engine] = 0


# ---------------------------------------------------------------------------
# 搜索缓存
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, list]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 300  # 5 分钟


def _cached_search(key: str) -> Optional[list]:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.time() - entry[0] < _CACHE_TTL:
            return entry[1]
    return None


def _cache_store(key: str, results: list):
    with _cache_lock:
        _cache[key] = (time.time(), results)
        if len(_cache) > 200:
            oldest = min(_cache.items(), key=lambda x: x[1][0])
            del _cache[oldest[0]]


# ---------------------------------------------------------------------------
# 搜索引擎实现
# ---------------------------------------------------------------------------
def _http_search_bing(search_terms: str, max_results: int = 5) -> list:
    if not _circuit_ok("bing"):
        return []

    encoded = quote_plus(search_terms)
    url = f"https://www.bing.com/search?q={encoded}&setlang=zh-Hans&cc=us"

    html = _http_get(url)
    if html is None:
        _circuit_fail("bing")
        return []
    _circuit_reset("bing")

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return []

    results = []
    for selector in ("#b_results > li.b_algo", ".b_algo", "li.b_algo"):
        items = soup.select(selector)
        if items:
            break

    for item in (items if items else []):
        if len(results) >= max_results:
            break
        title_el = item.select_one("h2 a")
        snippet_el = item.select_one(".b_caption p, .b_lineclamp2, .b_algoSlug, p")
        title = title_el.get_text(strip=True) if title_el else ""
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        link = title_el.get("href", "") if title_el else ""
        if title:
            results.append({"title": title, "snippet": snippet, "link": link})

    return results


def _http_search_baidu(search_terms: str, max_results: int = 5) -> list:
    if not _circuit_ok("baidu"):
        return []

    encoded = quote_plus(search_terms)
    url = f"https://www.baidu.com/s?wd={encoded}&rn={max_results}"

    html = _http_get(url)
    if html is None:
        _circuit_fail("baidu")
        return []
    _circuit_reset("baidu")

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return []

    results = []
    for item in soup.select(".result.c-container, .c-container, div[tpl]"):
        if len(results) >= max_results:
            break
        title_el = item.select_one("h3 a, .t a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        link = title_el.get("href", "")
        if not title:
            continue

        snippet = ""
        for sel in (".c-abstract", ".c-span-last", ".content-right_8Zs40",
                     "span.content-right_8Zs40", ".c-color-text", "p"):
            snippet_el = item.select_one(sel)
            if snippet_el:
                snippet = snippet_el.get_text(strip=True)
                if snippet:
                    break

        results.append({"title": title, "snippet": snippet, "link": link})

    return results


def _http_search_duckduckgo(search_terms: str, max_results: int = 5) -> list:
    if not _circuit_ok("duckduckgo"):
        return []

    encoded = quote_plus(search_terms)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    html = _http_get(url)
    if html is None:
        _circuit_fail("duckduckgo")
        return []
    _circuit_reset("duckduckgo")

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return []

    results = []
    for item in soup.select(".result"):
        if len(results) >= max_results:
            break
        title_el = item.select_one(".result__a")
        snippet_el = item.select_one(".result__snippet")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        link = title_el.get("href", "")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if title:
            results.append({"title": title, "snippet": snippet, "link": link})

    return results


def _ddgs_search(search_terms: str, max_results: int = 5) -> list:
    if not _circuit_ok("ddgs"):
        return []

    try:
        from ddgs import DDGS
    except ImportError:
        return []

    try:
        raw = list(DDGS().text(search_terms, max_results=max_results))
    except Exception as e:
        logger.warning(f"DDGS 搜索失败: {type(e).__name__}: {e}")
        _circuit_fail("ddgs")
        return []
    _circuit_reset("ddgs")

    results = []
    for r in raw:
        results.append({
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "link": r.get("href", ""),
        })

    return results


# ---------------------------------------------------------------------------
# 并行搜索编排
# ---------------------------------------------------------------------------
_SEARCH_FUNCTIONS = [
    ("ddgs", _ddgs_search),
    ("baidu", _http_search_baidu),
    ("duckduckgo", _http_search_duckduckgo),
    ("bing", _http_search_bing),
]


def _parallel_search(search_terms: str, max_results: int = 5) -> list:
    """并行调用所有搜索引擎，合并去重结果。"""
    cache_key = f"{search_terms}:{max_results}"
    cached = _cached_search(cache_key)
    if cached is not None:
        logger.info(f"搜索缓存命中: '{search_terms[:30]}...'")
        return cached

    all_results = []
    seen_links = set()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fn, search_terms, max_results): name
            for name, fn in _SEARCH_FUNCTIONS
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result()
                for r in results:
                    link = r.get("link", "")
                    if link and link not in seen_links:
                        seen_links.add(link)
                        all_results.append(r)
                    elif not link:
                        all_results.append(r)
                    if len(all_results) >= max_results * 2:
                        break
            except Exception as e:
                logger.warning(f"搜索引擎 {name} 异常: {type(e).__name__}: {e}")

    # 去重后截断
    final = all_results[:max_results]

    _cache_store(cache_key, final)
    logger.info(f"并行搜索: '{search_terms[:30]}...' → {len(final)} 条结果")
    return final


def search_engine(parsed: ParsedQuery) -> list:
    max_results = SEARCH_CONFIG["max_results"]
    search_terms = parsed.search_terms

    results = _parallel_search(search_terms, max_results)

    if not results and search_terms != parsed.raw_query:
        logger.info(f"搜索无结果，尝试原始查询 '{parsed.raw_query}'")
        results = _parallel_search(parsed.raw_query, max_results)

    logger.info(f"搜索完成: '{search_terms[:20]}...' → {len(results)} 条结果")
    return results


# ---------------------------------------------------------------------------
# 页面获取
# ---------------------------------------------------------------------------
def _http_fetch_page_content(url: str, selectors: list = None) -> Optional[dict]:
    if not _is_url_allowed(url):
        return None

    html = _http_get(url)
    if html is None:
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return None

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    if selectors is None:
        selectors = _DEFAULT_CONTENT_SELECTORS

    content_parts = []
    for sel in list(selectors) + ["body"]:
        elements = soup.select(sel)
        for el in elements[:3]:
            text = el.get_text(separator="\n", strip=True)
            if text and len(text) > 30:
                content_parts.append(text)
        if content_parts:
            break

    if content_parts:
        full_content = "\n".join(content_parts)
        max_len = BROWSER_CONFIG["max_content_length"]
        if len(full_content) > max_len:
            full_content = full_content[:max_len]
        return {"source": title or url, "url": url, "content": full_content}
    return None


def fetch_page_content(url: str, selectors: list = None) -> Optional[dict]:
    result = _http_fetch_page_content(url, selectors)
    if result:
        logger.info(f"页面获取成功: {url}, 内容长度 {len(result['content'])}")
    else:
        logger.warning(f"页面获取失败: {url}")
    return result


# ---------------------------------------------------------------------------
# 直连站点（天气等）
# ---------------------------------------------------------------------------
def _http_fetch_direct_site(url: str, selectors: list = None) -> Optional[dict]:
    # 天气站点升级到 HTTPS
    url = url.replace("http://www.weather.com.cn", "https://www.weather.com.cn")

    html = _http_get(url)
    if html is None:
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return None

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    content_parts = []
    for sel in (selectors or []):
        elements = soup.select(sel)
        for el in elements[:5]:
            text = el.get_text(strip=True)
            if text and len(text) > 5:
                content_parts.append(text)

    if not content_parts:
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            for line in text.split("\n")[:30]:
                line = line.strip()
                if len(line) > 10:
                    content_parts.append(line)

    if content_parts:
        return {"source": title or url, "url": url, "content": "\n".join(content_parts[:10])}
    return None


def fetch_direct_site(parsed: ParsedQuery) -> Optional[dict]:
    query_type = parsed.query_type
    type_config = QUERY_TYPE_CONFIG.get(query_type, {})
    direct_sites = type_config.get("direct_sites", [])
    if not direct_sites or not parsed.location:
        return None

    content_selectors = type_config.get("content_selectors", [])

    for site in direct_sites:
        city_codes = site.get("city_codes", {})
        city_code = city_codes.get(parsed.location)
        if not city_code:
            continue
        url = site["url_template"].format(city_code=city_code)
        # 升级天气站点到 HTTPS
        url = url.replace("http://", "https://")

        result = _http_fetch_direct_site(url, content_selectors)
        if result:
            return result

    return None

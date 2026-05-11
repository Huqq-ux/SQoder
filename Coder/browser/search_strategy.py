import logging
from typing import Optional
from urllib.parse import quote_plus

from Coder.browser.browser_config import (
    BROWSER_CONFIG, SEARCH_CONFIG, QUERY_TYPE_CONFIG,
)
from Coder.browser.query_parser import ParsedQuery

logger = logging.getLogger(__name__)


def _is_url_allowed(url: str) -> bool:
    if not url:
        return False
    scheme = url.split("://")[0].lower() if "://" in url else ""
    if scheme and scheme not in BROWSER_CONFIG["allowed_schemes"]:
        return False
    for blocked in BROWSER_CONFIG["blocked_domains"]:
        if blocked in url:
            return False
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    _blocked_hosts = [
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254", "metadata.google.internal",
    ]
    if hostname.lower() in _blocked_hosts:
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


_DEFAULT_CONTENT_SELECTORS = [
    "article", "main", "[role='main']",
    ".content", "#content", ".article-content", ".post-content",
    ".entry-content", ".main-content", ".page-content",
    "section", ".container", ".wrapper",
    "[data-testid='article-body']", ".story-body",
]


def _http_search_bing(search_terms: str, max_results: int = 5) -> list:
    try:
        import httpx
    except ImportError:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    encoded = quote_plus(search_terms)
    url = f"https://www.bing.com/search?q={encoded}&setlang=zh-Hans&cc=us"

    headers = {
        "User-Agent": BROWSER_CONFIG["user_agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for selector in ("#b_results > li.b_algo", ".b_algo", "li.b_algo"):
        items = soup.select(selector)
        if items:
            break

    for item in items if items else []:
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
    try:
        import httpx
    except ImportError:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    encoded = quote_plus(search_terms)
    url = f"https://www.baidu.com/s?wd={encoded}&rn={max_results}"

    headers = {
        "User-Agent": BROWSER_CONFIG["user_agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
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
    try:
        import httpx
    except ImportError:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    encoded = quote_plus(search_terms)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    headers = {
        "User-Agent": BROWSER_CONFIG["user_agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
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
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    try:
        raw = list(DDGS().text(search_terms, max_results=max_results))
    except Exception:
        return []

    results = []
    for r in raw:
        results.append({
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "link": r.get("href", ""),
        })

    logger.info(f"DDGS 搜索: '{search_terms[:20]}...' 返回 {len(results)} 条结果")
    return results


def _http_search(search_terms: str, max_results: int = 5) -> list:
    all_results = []
    seen_links = set()

    for search_fn in (_http_search_baidu, _http_search_duckduckgo, _http_search_bing):
        try:
            results = search_fn(search_terms, max_results)
        except Exception:
            results = []
        for r in results:
            link = r.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                all_results.append(r)
            elif not link:
                all_results.append(r)
            if len(all_results) >= max_results:
                break
        if len(all_results) >= max_results:
            break

    logger.info(f"HTTP 搜索: '{search_terms[:20]}...' 返回 {len(all_results)} 条结果")
    return all_results


def search_engine(parsed: ParsedQuery) -> list:
    max_results = SEARCH_CONFIG["max_results"]
    search_terms = parsed.search_terms

    results = _ddgs_search(search_terms, max_results)

    if not results:
        results = _http_search(search_terms, max_results)

    if not results and search_terms != parsed.raw_query:
        logger.info(
            f"搜索无结果，尝试原始查询 '{parsed.raw_query}'"
        )
        results = _ddgs_search(parsed.raw_query, max_results)
        if not results:
            results = _http_search(parsed.raw_query, max_results)

    logger.info(f"搜索完成: '{search_terms[:20]}...' → {len(results)} 条结果")
    return results


def _http_fetch_page_content(url: str, selectors: list = None) -> Optional[dict]:
    try:
        import httpx
    except ImportError:
        return None
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    headers = {
        "User-Agent": BROWSER_CONFIG["user_agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    if selectors is None:
        selectors = _DEFAULT_CONTENT_SELECTORS

    content_parts = []
    selectors_to_try = list(selectors)
    selectors_to_try.append("body")

    for sel in selectors_to_try:
        elements = soup.select(sel)
        for el in elements[:3]:
            text = el.get_text(separator="\n", strip=True)
            if text and len(text) > 30:
                content_parts.append(text)
        if content_parts:
            break

    if content_parts:
        full_content = "\n".join(content_parts)
        if len(full_content) > BROWSER_CONFIG["max_content_length"]:
            full_content = full_content[:BROWSER_CONFIG["max_content_length"]]
        return {
            "source": title or url,
            "url": url,
            "content": full_content,
        }
    return None


def fetch_page_content(url: str, selectors: list = None) -> Optional[dict]:
    if not _is_url_allowed(url):
        return None

    result = _http_fetch_page_content(url, selectors)
    if result:
        logger.info(f"页面获取成功: {url}, 内容长度 {len(result['content'])}")
    else:
        logger.warning(f"页面获取失败: {url}")
    return result


def _http_fetch_direct_site(url: str, selectors: list = None) -> Optional[dict]:
    try:
        import httpx
    except ImportError:
        return None
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    headers = {
        "User-Agent": BROWSER_CONFIG["user_agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
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
        return {
            "source": title or url,
            "url": url,
            "content": "\n".join(content_parts[:10]),
        }
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

        result = _http_fetch_direct_site(url, content_selectors)
        if result:
            return result

    return None

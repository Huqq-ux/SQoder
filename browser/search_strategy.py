import re
import time
import logging
import threading
from typing import Optional
from urllib.parse import quote_plus

from Coder.browser.browser_config import (
    BROWSER_CONFIG, SEARCH_CONFIG, QUERY_TYPE_CONFIG, get_browser_options,
)
from Coder.browser.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

_browser_lock = threading.Lock()
_browser_instance = None


def _get_browser():
    global _browser_instance
    if _browser_instance is not None:
        try:
            _browser_instance.latest_tab.url
            return _browser_instance
        except Exception:
            _browser_instance = None

    from DrissionPage import ChromiumPage

    opts = get_browser_options()
    _browser_instance = ChromiumPage(addr_or_opts=opts)
    return _browser_instance


def _close_browser():
    global _browser_instance
    if _browser_instance is not None:
        try:
            _browser_instance.quit()
        except Exception:
            pass
        _browser_instance = None


def _is_url_allowed(url: str) -> bool:
    if not url:
        return False

    scheme = url.split("://")[0].lower() if "://" in url else ""
    if scheme and scheme not in BROWSER_CONFIG["allowed_schemes"]:
        return False

    for blocked in BROWSER_CONFIG["blocked_domains"]:
        if blocked in url:
            return False

    return True


def _safe_navigate(page, url: str, timeout: int = None) -> bool:
    if not _is_url_allowed(url):
        logger.warning(f"URL被阻止: {url}")
        return False

    timeout = timeout or BROWSER_CONFIG["load_timeout"]

    try:
        page.get(url)
        page.wait.doc_loaded(timeout=timeout)
        return True
    except Exception as e:
        logger.warning(f"页面加载失败: {url} - {type(e).__name__}")
        return False


def search_engine(parsed: ParsedQuery) -> list:
    query_type = parsed.query_type
    type_config = QUERY_TYPE_CONFIG.get(query_type, QUERY_TYPE_CONFIG["general"])
    engines = type_config.get("priority_engines", [SEARCH_CONFIG["default_engine"]])
    max_results = SEARCH_CONFIG["max_results"]

    for engine_name in engines:
        engine = SEARCH_CONFIG["engines"].get(engine_name)
        if not engine:
            continue

        results = _do_search(engine, parsed.search_terms, max_results)
        if results:
            return results

    fallback = SEARCH_CONFIG["engines"].get(SEARCH_CONFIG["default_engine"])
    if fallback:
        return _do_search(fallback, parsed.search_terms, max_results)

    return []


def _do_search(engine: dict, search_terms: str, max_results: int) -> list:
    encoded = quote_plus(search_terms)
    url = engine["url_template"].format(query=encoded)

    with _browser_lock:
        try:
            page = _get_browser()
        except Exception as e:
            logger.error(f"浏览器启动失败: {type(e).__name__}")
            return []

        if not _safe_navigate(page, url):
            return []

        time.sleep(1.0)

        results = []
        try:
            items = page.eles(f"css:{engine['result_selector']}")
            for item in items[:max_results * 2]:
                if len(results) >= max_results:
                    break

                try:
                    title_el = item.ele(f"css:{engine['title_selector']}")
                    snippet_el = item.ele(f"css:{engine['snippet_selector']}")
                    link_el = item.ele(f"css:{engine['link_selector']}")

                    title = title_el.text.strip() if title_el else ""
                    snippet = snippet_el.text.strip() if snippet_el else ""
                    link = link_el.attr("href") if link_el else ""

                    if not title:
                        continue

                    if link and not link.startswith("http"):
                        if link.startswith("/"):
                            base = page.url.split("/")[0] + "//" + page.url.split("/")[2]
                            link = base + link

                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "link": link,
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"搜索结果解析失败: {type(e).__name__}")

    return results


def fetch_direct_site(parsed: ParsedQuery) -> Optional[dict]:
    query_type = parsed.query_type
    type_config = QUERY_TYPE_CONFIG.get(query_type, {})
    direct_sites = type_config.get("direct_sites", [])

    if not direct_sites or not parsed.location:
        return None

    for site in direct_sites:
        city_codes = site.get("city_codes", {})
        city_code = city_codes.get(parsed.location)

        if not city_code:
            continue

        url = site["url_template"].format(city_code=city_code)

        with _browser_lock:
            try:
                page = _get_browser()
            except Exception:
                return None

            if not _safe_navigate(page, url):
                continue

            time.sleep(1.0)

            content_selectors = type_config.get("content_selectors", [])
            content_parts = []

            for sel in content_selectors:
                try:
                    elements = page.eles(f"css:{sel}")
                    for el in elements[:5]:
                        text = el.text.strip()
                        if text and len(text) > 5:
                            content_parts.append(text)
                except Exception:
                    continue

            if content_parts:
                return {
                    "source": site["name"],
                    "url": url,
                    "content": "\n".join(content_parts[:10]),
                }

    return None


def fetch_page_content(url: str, selectors: list = None) -> Optional[dict]:
    if not _is_url_allowed(url):
        return None

    if selectors is None:
        selectors = ["article", "main", ".content", "#content", ".article-content"]

    with _browser_lock:
        try:
            page = _get_browser()
        except Exception:
            return None

        if not _safe_navigate(page, url):
            return None

        time.sleep(0.8)

        content_parts = []
        for sel in selectors:
            try:
                elements = page.eles(f"css:{sel}")
                for el in elements[:3]:
                    text = el.text.strip()
                    if text and len(text) > 20:
                        content_parts.append(text)
            except Exception:
                continue

        if not content_parts:
            try:
                body = page.ele("tag:body")
                if body:
                    text = body.text.strip()
                    if text:
                        content_parts.append(text[:BROWSER_CONFIG["max_content_length"]])
            except Exception:
                pass

        title = ""
        try:
            title_el = page.ele("tag:title")
            title = title_el.text.strip() if title_el else ""
        except Exception:
            pass

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

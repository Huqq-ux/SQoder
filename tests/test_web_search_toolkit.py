import sys
import os

_project_root = os.path.join(os.path.dirname(__file__), "..", "..")
_project_root = os.path.normpath(_project_root)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def test_query_parser_basic():
    from Coder.browser.query_parser import parse_query

    p = parse_query("湘潭明天天气")
    assert p.query_type == "weather", f"Expected weather, got {p.query_type}"
    assert p.location == "湘潭", f"Expected 湘潭, got {p.location}"
    assert p.date_offset == 1, f"Expected 1, got {p.date_offset}"
    assert p.is_time_sensitive, "Should be time sensitive"
    print("PASS: query_parser basic weather query")


def test_query_parser_news():
    from Coder.browser.query_parser import parse_query

    p = parse_query("最新AI新闻")
    assert p.query_type == "news", f"Expected news, got {p.query_type}"
    assert p.is_time_sensitive, "Should be time sensitive"
    print("PASS: query_parser news query")


def test_query_parser_general():
    from Coder.browser.query_parser import parse_query

    p = parse_query("Python装饰器用法")
    assert p.query_type == "general", f"Expected general, got {p.query_type}"
    assert not p.is_time_sensitive, "Should not be time sensitive"
    print("PASS: query_parser general query")


def test_query_parser_date_extraction():
    from Coder.browser.query_parser import parse_query

    p1 = parse_query("北京今天天气")
    assert p1.date_offset == 0, f"Expected 0, got {p1.date_offset}"

    p2 = parse_query("上海后天天气")
    assert p2.date_offset == 2, f"Expected 2, got {p2.date_offset}"

    p3 = parse_query("广州昨天新闻")
    assert p3.date_offset == -1, f"Expected -1, got {p3.date_offset}"
    print("PASS: query_parser date extraction")


def test_query_parser_location():
    from Coder.browser.query_parser import parse_query

    p1 = parse_query("长沙市明天天气")
    assert p1.location is not None, "Should detect location"

    p2 = parse_query("浙江省今日新闻")
    assert p2.location is not None, "Should detect province"

    p3 = parse_query("今天天气怎么样")
    assert p3.location is None, "No location in query"
    print("PASS: query_parser location extraction")


def test_query_parser_empty():
    from Coder.browser.query_parser import parse_query

    p1 = parse_query("")
    assert p1.query_type == "general"

    p2 = parse_query(None)
    assert p2.query_type == "general"
    print("PASS: query_parser empty/None input")


def test_query_parser_search_terms():
    from Coder.browser.query_parser import parse_query

    p = parse_query("湘潭明天天气")
    assert "湘潭" in p.search_terms, f"Missing location in search_terms: {p.search_terms}"
    assert "天气" in p.search_terms, f"Missing weather keyword: {p.search_terms}"
    print("PASS: query_parser search_terms generation")


def test_content_extractor_verify():
    from Coder.browser.content_extractor import verify_content

    v1 = verify_content("湘潭明天天气晴，最高温度32度", "weather", "湘潭", None)
    assert v1["valid"], f"Should be valid: {v1}"
    assert v1["confidence"] >= 2, f"Confidence too low: {v1['confidence']}"

    v2 = verify_content("这是一段无关内容", "weather", "湘潭", None)
    assert not v2["valid"], f"Should be invalid: {v2}"

    v3 = verify_content("", "weather")
    assert not v3["valid"], "Empty content should be invalid"
    print("PASS: content_extractor verify_content")


def test_content_extractor_format():
    from Coder.browser.content_extractor import format_response

    results = [
        {"source": "测试来源", "content": "湘潭明天晴，25-32度", "link": "https://example.com"}
    ]
    resp = format_response("湘潭明天天气", "weather", results)
    assert "湘潭" in resp, f"Missing location in response"
    assert "晴" in resp or "度" in resp, f"Missing weather info in response"
    print("PASS: content_extractor format_response")


def test_content_extractor_format_empty():
    from Coder.browser.content_extractor import format_response

    resp = format_response("测试查询", "general", [])
    assert "未找到" in resp or "未能" in resp, f"Expected no results message: {resp}"
    print("PASS: content_extractor format_response empty")


def test_content_extractor_noise_filter():
    from Coder.browser.content_extractor import extract_relevant_content

    noisy = "这是正文内容\ncookie设置\n隐私政策\n广告推荐\n更多有用信息\n版权所有"
    cleaned = extract_relevant_content(noisy, "general")
    assert "cookie" not in cleaned.lower(), "Should filter cookie noise"
    assert "隐私" not in cleaned, "Should filter privacy noise"
    assert "正文" in cleaned, "Should keep real content"
    assert "有用" in cleaned, "Should keep useful content"
    print("PASS: content_extractor noise filtering")


def test_browser_config():
    from Coder.browser.browser_config import BROWSER_CONFIG, SEARCH_CONFIG, QUERY_TYPE_CONFIG

    assert BROWSER_CONFIG["headless"] is True
    assert BROWSER_CONFIG["page_timeout"] > 0
    assert "bing" in SEARCH_CONFIG["engines"]
    assert "baidu" in SEARCH_CONFIG["engines"]
    assert "weather" in QUERY_TYPE_CONFIG
    assert "news" in QUERY_TYPE_CONFIG
    assert "general" in QUERY_TYPE_CONFIG
    print("PASS: browser_config structure")


def test_browser_config_options():
    from Coder.browser.browser_config import get_browser_options

    opts = get_browser_options()
    assert opts is not None
    print("PASS: browser_config get_browser_options")


def test_web_search_toolkit_structure():
    from Coder.tools.web_search_toolkit import web_search_toolkit

    assert len(web_search_toolkit) == 4, f"Expected 4 tools, got {len(web_search_toolkit)}"

    tool_names = [t.name for t in web_search_toolkit]
    assert "web_search" in tool_names, f"Missing web_search in {tool_names}"
    assert "web_search_weather" in tool_names, f"Missing web_search_weather in {tool_names}"
    assert "web_search_news" in tool_names, f"Missing web_search_news in {tool_names}"
    assert "web_fetch_page" in tool_names, f"Missing web_fetch_page in {tool_names}"

    for t in web_search_toolkit:
        assert t.description, f"Tool {t.name} has no description"
    print("PASS: web_search_toolkit structure and descriptions")


def test_web_search_toolkit_empty_input():
    from Coder.tools.web_search_toolkit import web_search, web_fetch_page

    r1 = web_search.invoke({"query": ""})
    assert "不能为空" in r1, f"Expected empty error: {r1}"

    r2 = web_fetch_page.invoke({"url": ""})
    assert "不能为空" in r2, f"Expected empty error: {r2}"

    r3 = web_fetch_page.invoke({"url": "not-a-url"})
    assert "http" in r3, f"Expected URL format error: {r3}"
    print("PASS: web_search_toolkit input validation")


def test_search_strategy_url_check():
    from Coder.browser.search_strategy import _is_url_allowed

    assert _is_url_allowed("https://www.bing.com/search?q=test")
    assert _is_url_allowed("http://example.com")
    assert not _is_url_allowed("ftp://example.com")
    assert not _is_url_allowed("https://facebook.com/page")
    assert not _is_url_allowed("")
    print("PASS: search_strategy URL validation")


if __name__ == "__main__":
    tests = [
        test_query_parser_basic,
        test_query_parser_news,
        test_query_parser_general,
        test_query_parser_date_extraction,
        test_query_parser_location,
        test_query_parser_empty,
        test_query_parser_search_terms,
        test_content_extractor_verify,
        test_content_extractor_format,
        test_content_extractor_format_empty,
        test_content_extractor_noise_filter,
        test_browser_config,
        test_browser_config_options,
        test_web_search_toolkit_structure,
        test_web_search_toolkit_empty_input,
        test_search_strategy_url_check,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {t.__name__} - {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED!")

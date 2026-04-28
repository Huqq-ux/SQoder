import os
import logging

logger = logging.getLogger(__name__)

BROWSER_CONFIG = {
    "headless": True,
    "browser_path": "",
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
    ),
    "page_timeout": 15,
    "load_timeout": 20,
    "retry_count": 2,
    "retry_delay": 1.5,
    "request_delay": (0.5, 1.5),
    "max_content_length": 50000,
    "respect_robots_txt": True,
    "blocked_domains": [
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "linkedin.com",
    ],
    "allowed_schemes": ["http", "https"],
}

SEARCH_CONFIG = {
    "default_engine": "bing",
    "engines": {
        "bing": {
            "url_template": "https://www.bing.com/search?q={query}&setlang=zh-Hans",
            "result_selector": "#b_results > li.b_algo",
            "title_selector": "h2 a",
            "snippet_selector": ".b_caption p, .b_lineclamp2",
            "link_selector": "h2 a",
        },
        "baidu": {
            "url_template": "https://www.baidu.com/s?wd={query}",
            "result_selector": ".result.c-container, .c-container",
            "title_selector": "h3 a",
            "snippet_selector": ".c-abstract, .content-right_8Zs40",
            "link_selector": "h3 a",
        },
    },
    "max_results": 5,
    "weather_keywords": [
        "天气", "气温", "温度", "下雨", "下雪", "刮风",
        "weather", "forecast", "rain", "snow",
    ],
    "news_keywords": [
        "新闻", "最新", "今日", "最近", "热点", "时事",
        "news", "latest", "today", "recent", "breaking",
    ],
    "time_keywords": [
        "今天", "明天", "后天", "昨天", "本周", "下周",
        "现在", "当前", "实时", "最新",
        "today", "tomorrow", "yesterday", "now", "current",
    ],
}

QUERY_TYPE_CONFIG = {
    "weather": {
        "priority_engines": ["bing", "baidu"],
        "direct_sites": [
            {
                "name": "中国天气网",
                "url_template": "http://www.weather.com.cn/weather1d/{city_code}.shtml",
                "city_codes": {
                    "北京": "101010100", "上海": "101020100", "广州": "101280101",
                    "深圳": "101280601", "长沙": "101250101", "湘潭": "101250201",
                    "杭州": "101210101", "成都": "101270101", "武汉": "101200101",
                    "南京": "101190101", "重庆": "101040100", "天津": "101030100",
                    "西安": "101110101", "苏州": "101190401", "郑州": "101180101",
                    "青岛": "101120201", "大连": "101070201", "厦门": "101230201",
                    "昆明": "101290101", "哈尔滨": "101050101",
                },
            },
        ],
        "content_selectors": [".t", ".wea", ".tem", ".win"],
    },
    "news": {
        "priority_engines": ["bing", "baidu"],
        "direct_sites": [],
        "content_selectors": ["article", ".article-content", ".news-content"],
    },
    "general": {
        "priority_engines": ["bing", "baidu"],
        "direct_sites": [],
        "content_selectors": ["article", "main", ".content", "#content"],
    },
}


def get_browser_options():
    from DrissionPage import ChromiumOptions

    opts = ChromiumOptions()

    if BROWSER_CONFIG["headless"]:
        opts.headless()

    if BROWSER_CONFIG["browser_path"]:
        opts.set_browser_path(BROWSER_CONFIG["browser_path"])
    else:
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for p in edge_paths:
            if os.path.isfile(p):
                opts.set_browser_path(p)
                break

    opts.set_user_agent(BROWSER_CONFIG["user_agent"])
    opts.set_timeouts(
        page_load=BROWSER_CONFIG["load_timeout"],
    )
    opts.set_argument("--disable-gpu")
    opts.set_argument("--disable-dev-shm-usage")
    opts.set_argument("--no-sandbox")
    opts.set_argument("--disable-extensions")
    opts.set_argument("--disable-images")
    opts.set_argument("--lang=zh-CN")

    return opts

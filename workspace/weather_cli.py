#!/usr/bin/env python3
"""
天气查询命令行工具
──────────────────────────────────────────
数据来源: wttr.in（免费、无需 API Key）

用法:
  python weather_cli.py 北京              # 简洁模式
  python weather_cli.py Tokyo --detail    # 详细模式
  python weather_cli.py "New York" -d     # 多词城市用引号
  python weather_cli.py 上海 --lang en    # 英文描述
"""

import argparse
import json
import sys
from typing import Optional

import requests

# ============================================================
# 配置常量
# ============================================================
BASE_URL = "https://wttr.in"
TIMEOUT = 10  # 请求超时（秒）
USER_AGENT = "WeatherCLI/1.0"

# 天气状况中英文映射（wttr.in 原文 → 中文 + emoji）
WEATHER_CODE_MAP: dict[str, str] = {
    "Sunny":                 "☀️ 晴天",
    "Clear":                 "🌙 晴朗",
    "Partly cloudy":         "⛅ 多云",
    "Cloudy":                "☁️ 阴天",
    "Overcast":              "☁️ 阴天",
    "Mist":                  "🌫️ 薄雾",
    "Fog":                   "🌫️ 大雾",
    "Freezing fog":          "🌫️ 冻雾",
    "Light rain":            "🌦️ 小雨",
    "Moderate rain":         "🌧️ 中雨",
    "Heavy rain":            "🌧️ 大雨",
    "Light drizzle":         "🌦️ 毛毛雨",
    "Patchy rain possible":  "🌦️ 局部可能有雨",
    "Patchy light rain":     "🌦️ 局部小雨",
    "Light snow":            "🌨️ 小雪",
    "Moderate snow":         "🌨️ 中雪",
    "Heavy snow":            "❄️ 大雪",
    "Blizzard":              "❄️ 暴风雪",
    "Thunderstorm":          "⛈️ 雷暴",
    "Haze":                  "🌫️ 霾",
}


# ============================================================
# 核心逻辑
# ============================================================

def translate_weather(desc: str, lang: str = "zh") -> str:
    """英文天气描述 → 中文 + emoji；未知描述返回原文。"""
    if lang != "zh":
        return desc
    return WEATHER_CODE_MAP.get(desc, desc)


def fetch_weather(city: str) -> Optional[dict]:
    """
    调用 wttr.in API 获取天气 JSON。

    Args:
        city: 城市名，中英文均可，如 "北京"、"Tokyo"、"New York"

    Returns:
        解析后的 dict；失败返回 None（错误信息已打印到 stderr）
    """
    url = f"{BASE_URL}/{city}"
    params = {"format": "j1"}

    try:
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（{TIMEOUT} 秒），请检查网络后重试。", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError:
        print("❌ 网络连接失败，请检查网络。", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}", file=sys.stderr)
        return None

    # HTTP 状态码检查
    if resp.status_code == 404:
        print(f"❌ 未找到城市「{city}」，请检查拼写。", file=sys.stderr)
        return None
    if not resp.ok:
        print(f"❌ HTTP {resp.status_code} 错误，请稍后重试。", file=sys.stderr)
        return None

    # JSON 解析
    try:
        return resp.json()
    except json.JSONDecodeError:
        print("❌ 服务器返回数据格式异常，请稍后重试。", file=sys.stderr)
        return None


def parse_current_weather(data: dict) -> dict:
    """从 wttr.in 原始 JSON 中提取当前天气关键字段。"""
    current = data.get("current_condition", [{}])[0]
    return {
        "temp_c":          current.get("temp_C", "N/A"),
        "temp_f":          current.get("temp_F", "N/A"),
        "feels_like_c":    current.get("FeelsLikeC", "N/A"),
        "humidity":        current.get("humidity", "N/A"),
        "wind_speed_kmph": current.get("windspeedKmph", "N/A"),
        "wind_dir":        current.get("winddir16Point", "N/A"),
        "weather_desc":    current.get("weatherDesc", [{}])[0].get("value", "N/A"),
        "visibility_km":   current.get("visibility", "N/A"),
        "pressure_mb":     current.get("pressure", "N/A"),
        "uv_index":        current.get("uvIndex", "N/A"),
        "observation_time": current.get("observation_time", "N/A"),
    }


# ============================================================
# 输出格式化
# ============================================================

def print_simple(weather: dict, city: str, lang: str) -> None:
    """简洁模式：仅温度 + 天气 + 湿度。"""
    desc = translate_weather(weather["weather_desc"], lang)
    print()
    print(f"  📍 {city}")
    print(f"  🌡️  温度: {weather['temp_c']}°C  （体感 {weather['feels_like_c']}°C）")
    print(f"  🌤️  天气: {desc}")
    print(f"  💧 湿度: {weather['humidity']}%")
    print()


def print_detail(weather: dict, city: str, data: dict, lang: str) -> None:
    """详细模式：包含风速、能见度、气压、UV 等。"""
    desc = translate_weather(weather["weather_desc"], lang)

    nearest = data.get("nearest_area", [{}])[0]
    country = nearest.get("country", [{}])[0].get("value", "")
    region  = nearest.get("region",  [{}])[0].get("value", "")

    print()
    print("  ╔" + "═" * 46 + "╗")
    print(f"  ║  📍 {city}  ({region}, {country})")
    print(f"  ║  🕐 观测: {weather['observation_time']}")
    print("  ╠" + "═" * 46 + "╣")
    print(f"  ║  🌡️  温度:     {weather['temp_c']}°C / {weather['temp_f']}°F")
    print(f"  ║  🤔 体感:     {weather['feels_like_c']}°C")
    print(f"  ║  🌤️  天气:     {desc}")
    print(f"  ║  💧 湿度:     {weather['humidity']}%")
    print(f"  ║  🌬️  风速:     {weather['wind_speed_kmph']} km/h  {weather['wind_dir']}")
    print(f"  ║  👁️  能见度:   {weather['visibility_km']} km")
    print(f"  ║  📊 气压:     {weather['pressure_mb']} mb")
    print(f"  ║  ☀️  UV 指数:  {weather['uv_index']}")
    print("  ╚" + "═" * 46 + "╝")
    print()


# ============================================================
# 入口
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="🌤️  天气查询命令行工具  (数据来源: wttr.in — 免费免注册)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python weather_cli.py 北京              简洁模式
  python weather_cli.py Tokyo --detail    详细模式
  python weather_cli.py "New York" -d     多词城市名
  python weather_cli.py 上海 --lang en    英文天气描述
        """,
    )
    parser.add_argument(
        "city", nargs="+",
        help="城市名称，中英文均可（如 北京、Tokyo、'New York'）",
    )
    parser.add_argument(
        "-d", "--detail", action="store_true",
        help="详细模式（默认简洁模式）",
    )
    parser.add_argument(
        "--lang", choices=["zh", "en"], default="zh",
        help="天气描述语言（默认 zh）",
    )
    parser.add_argument(
        "--version", action="version", version="weather_cli 1.0.0",
    )

    args = parser.parse_args()
    city = " ".join(args.city)

    print(f"🔍 正在查询「{city}」…")

    data = fetch_weather(city)
    if data is None:
        sys.exit(1)

    weather = parse_current_weather(data)

    if args.detail:
        print_detail(weather, city, data, args.lang)
    else:
        print_simple(weather, city, args.lang)


if __name__ == "__main__":
    main()

"""时间工具 —— 获取当前准确时间。"""
from datetime import datetime
from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取当前准确的日期和时间。当用户询问"今天几号"、"现在几点"、"当前日期"等问题时必须调用此工具。"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return (
        f"当前时间: {now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]} "
        f"{now.strftime('%H:%M:%S')}"
    )


@tool
def get_current_year() -> str:
    """获取当前年份。当需要确认今年是哪一年时调用此工具。"""
    return f"当前年份: {datetime.now().year}年"


time_toolkit = [get_current_time, get_current_year]

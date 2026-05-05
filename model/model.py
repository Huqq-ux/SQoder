import os

from langchain_openai import ChatOpenAI

_api_key = os.environ.get("DEEPSEEK_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "环境变量 DEEPSEEK_API_KEY 未设置。"
        "请先设置: set DEEPSEEK_API_KEY=your_api_key"
    )

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    api_key=_api_key,
    streaming=True,
)

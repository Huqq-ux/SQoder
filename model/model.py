import os

from langchain_openai import ChatOpenAI

_api_key = os.environ.get("DASHSCOPE_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "环境变量 DASHSCOPE_API_KEY 未设置。"
        "请先设置: set DASHSCOPE_API_KEY=your_api_key"
    )

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=_api_key,
    streaming=True,
)
import asyncio
import logging
from datetime import datetime
from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain_core.messages import HumanMessage, AIMessageChunk, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from Coder.model import llm
from Coder.tools.file_tools import file_management_toolkit
from Coder.tools.knowledge_toolkit import knowledge_toolkit
from Coder.tools.web_search_toolkit import web_search_toolkit
from Coder.tools.skill_toolkit import skill_toolkit
from Coder.tools.docx_tools import create_docx, read_docx
from Coder.tools.time_tools import time_toolkit

docx_toolkit = [create_docx, read_docx]

logger = logging.getLogger(__name__)

COLOR_THINK = "\033[36m"
COLOR_TOOL = "\033[33m"
COLOR_RESULT = "\033[32m"
COLOR_RESET = "\033[0m"

SYSTEM_PROMPT = (
    "你是 Qbot，一个通用 AI 智能助手，可以帮你搜索信息、查询知识库、执行自定义技能、操作文件等。\n\n"
    "## 可用工具\n"
    "- web_search: 搜索实时信息\n"
    "- web_search_weather: 搜索天气（含地点和日期识别）\n"
    "- web_search_news: 搜索新闻\n"
    "- web_fetch_page: 获取网页详情（不稳定，失败不重试）\n"
    "- knowledge_search: 在知识库中搜索课程教材、课件内容。这是回答课程相关问题的首选工具\n"
    "- knowledge_keyword_search / knowledge_context_search: 关键词搜索和上下文感知搜索\n"
    "- knowledge_list_files: 列出知识库中已有的文档\n"
    "- file_read / file_write / file_list: 文件系统操作（工作目录，非知识库）\n"
    "- get_current_time: 获取当前准确日期和时间\n"
    "- get_current_year: 获取当前年份\n"
    "- create_docx: 生成 Word 文档（支持标题、段落、表格）\n"
    "- read_docx: 读取 Word 文档内容\n"
    "- list_skills: 列出所有用户自定义技能\n"
    "- execute_skill: 执行指定的用户技能\n"
    "- 以服务名开头的 MCP 工具（如 sequential_thinking__sequentialthinking、memory__create_entities）：\n"
    "  - sequential_thinking__*: 将复杂问题分解为多步推理\n"
    "  - memory__*: 知识图谱持久化记忆（实体→关系→观察）\n\n"
    "## 核心规则\n"
    "0. 涉及日期、时间、年份的问题，必须先调用 get_current_time 获取准确时间，严禁凭记忆猜测\n"
    "1. **知识库优先**：用户询问课程内容（章节、知识点、概念、公式等）时，必须先调用 knowledge_search 搜索知识库，不要凭记忆回答，也不要先用 file 工具\n"
    "2. **搜索上限**：knowledge_search 最多 3 次，web_search 最多 2 次。达到上限立即停止，基于已有信息直接回答\n"
    "3. 回答中禁止描述工具调用过程和内部推理\n"
    "4. 命名实体不翻译\n"
    "5. 工具调用总数不能超过 15 次，超过会被强制终止\n"
    "6. 用户提到具体操作需求时，先调用 list_skills 查看是否有匹配的技能，有则用 execute_skill 执行。execute_skill 的 skill_name 用技能英文名，其余参数按 list_skills 返回的参数列表填写\n\n"
    "## 搜索规则（重要）\n"
    "如果搜索返回「所有搜索引擎均未返回结果」或类似消息，说明当前搜索服务不可用。\n"
    "此时必须停止搜索，直接告知用户「当前搜索服务暂不可用」，并基于你已有的知识回答问题。\n"
    "严禁在搜索失败后反复更换关键词重试——这会导致无限循环。\n\n"
    "## 回答风格\n"
    "简洁直接。\n"
    "复杂问题，按需组织结构。\n\n"
    f"当前日期: {datetime.now().strftime('%Y年%m月%d日 %A')}"
)


async def create_code_agent(thread_id: str = "1", mcp_manager=None):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from Coder.storage.db import DatabaseManager
    memory = AsyncPostgresSaver(DatabaseManager.pool())

    if mcp_manager is None:
        mcp_tools = []
    else:
        mcp_tools = mcp_manager.get_all_tools()
    tools = file_management_toolkit + knowledge_toolkit + web_search_toolkit + skill_toolkit + docx_toolkit + time_toolkit + mcp_tools

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory,
        middleware=[
            SummarizationMiddleware(
                model=llm,
                trigger=("messages", 40),
                keep=("messages", 20),
            ),
        ],
        debug=False,
    )
    config = RunnableConfig(
        configurable={"thread_id": thread_id},
        recursion_limit=30,
    )

    return agent, config


async def stream_agent_response(agent, config, user_input: str, system_prefix: str = ""):
    messages = []
    if system_prefix:
        messages.append(SystemMessage(content=system_prefix))
    messages.append(HumanMessage(content=user_input))
    input_data = {"messages": messages}
    tool_calls_accumulator = {}
    yielded_tool_calls = set()
    tool_call_count = 0
    MAX_TOOL_CALLS = 15

    async for chunk in agent.astream(
            input=input_data,
            config=config,
            stream_mode="messages",
    ):
        if not isinstance(chunk, tuple) or len(chunk) != 2:
            continue

        msg_chunk, metadata = chunk

        if isinstance(msg_chunk, AIMessageChunk):
            reasoning = msg_chunk.additional_kwargs.get("reasoning_content", "")
            if reasoning:
                pass

            for tc in msg_chunk.tool_call_chunks:
                tc_id = tc.get("id") or tc.get("name", "unknown")
                if tc_id not in tool_calls_accumulator:
                    tool_calls_accumulator[tc_id] = {"name": "", "args": ""}
                if tc.get("name"):
                    tool_calls_accumulator[tc_id]["name"] = tc["name"]
                if tc.get("args"):
                    tool_calls_accumulator[tc_id]["args"] += tc["args"]

            for tc_id, tc_data in tool_calls_accumulator.items():
                if tc_id not in yielded_tool_calls and tc_data["name"]:
                    tool_call_count += 1
                    if tool_call_count > MAX_TOOL_CALLS:
                        yield {
                            "type": "content",
                            "content": (
                                f"\n\n⚠️ 已达最大工具调用次数 ({MAX_TOOL_CALLS})，"
                                f"请基于已有信息直接回答用户问题。\n\n"
                            ),
                        }
                        return
                    yield {
                        "type": "tool_call",
                        "name": tc_data["name"],
                        "args": tc_data["args"],
                    }
                    yielded_tool_calls.add(tc_id)

            if msg_chunk.content:
                yield {"type": "content", "content": msg_chunk.content}

        elif isinstance(msg_chunk, ToolMessage):
            tool_name = msg_chunk.name or ""
            content = str(msg_chunk.content)[:50]
            yield {"type": "tool_result", "name": tool_name, "content": content}


async def run_agent():
    agent, config = await create_code_agent(thread_id="2")

    while True:
        try:
            user_input = input("用户: ")
            if user_input.lower() in ("exit", "quit"):
                break
            print("助手:", flush=True)

            async for event in stream_agent_response(agent, config, user_input):
                event_type = event["type"]

                if event_type == "thinking":
                    print(f"{COLOR_THINK}[思考] {event['content']}{COLOR_RESET}", end="", flush=True)
                elif event_type == "tool_call":
                    args_str = f" | 参数: {event['args']}" if event['args'] else ""
                    print(f"\n{COLOR_TOOL}[工具调用] {event['name']}{args_str}{COLOR_RESET}", end="", flush=True)
                elif event_type == "tool_result":
                    print(f"\n{COLOR_RESULT}[工具结果-{event['name']}] {event['content']}{COLOR_RESET}", end="", flush=True)
                elif event_type == "content":
                    print(f"{COLOR_RESET}{event['content']}", end="", flush=True)
            print()
        except KeyboardInterrupt:
            print("\n程序已中断")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    asyncio.run(run_agent())

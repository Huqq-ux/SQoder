import asyncio
import logging
from typing import Optional
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessageChunk, ToolMessage
from langchain_core.runnables import RunnableConfig
from Coder.model import llm
from Coder.tools.file_tools import file_management_toolkit
from Coder.tools.knowledge_toolkit import knowledge_toolkit
from Coder.tools.web_search_toolkit import web_search_toolkit
from Coder.tools.file_saver import FileSaver
from Coder.sop.intent_classifier import classify_intent, IntentType
from Coder.sop.flow_orchestrator import FlowOrchestrator
from Coder.sop.executor import SOPExecutor
from Coder.sop.checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)

COLOR_THINK = "\033[36m"
COLOR_TOOL = "\033[33m"
COLOR_RESULT = "\033[32m"
COLOR_RESET = "\033[0m"

SYSTEM_PROMPT = (
    "你是一个专业的编程助手，具备SOP执行能力。在回答问题时，请遵循以下格式：\n"
    "1. 【思考过程】：分析问题、设计思路和决策依据\n"
    "2. 【工具调用】：如需使用工具，说明工具名称、参数和预期结果\n"
    "3. 【回答】：给出最终答案\n"
    "当用户请求涉及SOP执行时，严格按照SOP步骤操作。\n"
    "请确保回答结构清晰、逻辑严谨。"
)


async def _init_mcp_tools(timeout: float = 15.0):
    try:
        from Coder.tools.powershell_tools import get_powershell_stdio_tools
        client, tools = await asyncio.wait_for(
            get_powershell_stdio_tools(), timeout=timeout
        )
        return client, tools
    except asyncio.TimeoutError:
        logger.warning(f"MCP工具初始化超时（{timeout}秒），跳过PowerShell工具")
        return None, []
    except Exception as e:
        logger.warning(f"MCP工具初始化失败: {e}，跳过PowerShell工具")
        return None, []


async def _auto_index_sop_docs(vector_store, timeout: float = 30.0):
    import os as _os
    import concurrent.futures

    sop_dir = _os.path.join(
        _os.path.dirname(__file__), "..", "knowledge", "sop_docs"
    )
    sop_dir = _os.path.normpath(sop_dir)
    if not _os.path.isdir(sop_dir):
        logger.warning(f"SOP文档目录不存在: {sop_dir}")
        return 0

    def _do_index():
        from Coder.knowledge.document_loader import DocumentLoader
        from Coder.knowledge.text_splitter import SOPTextSplitter

        loader = DocumentLoader()
        splitter = SOPTextSplitter()
        total_chunks = 0

        for filename in _os.listdir(sop_dir):
            ext = _os.path.splitext(filename)[1].lower()
            if ext not in (".md", ".txt", ".pdf", ".docx"):
                continue
            filepath = _os.path.join(sop_dir, filename)
            try:
                doc = loader.load(filepath)
                chunks = splitter.split_documents([doc])
                vector_store.add_documents(chunks)
                total_chunks += len(chunks)
                logger.info(f"自动导入: {filename} -> {len(chunks)} 个文档块")
            except Exception as e:
                logger.warning(f"导入 {filename} 失败: {e}")

        return total_chunks

    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            total = await asyncio.wait_for(
                loop.run_in_executor(pool, _do_index),
                timeout=timeout,
            )
        if total > 0:
            logger.info(f"SOP文档自动导入完成，共 {total} 个文档块")
        else:
            logger.warning("未导入任何SOP文档")
        return total
    except asyncio.TimeoutError:
        logger.warning(f"SOP文档自动导入超时（{timeout}秒），已取消")
        return 0
    except Exception as e:
        logger.warning(f"SOP文档自动导入失败: {e}")
        return 0


async def create_code_agent(thread_id: str = "1"):
    memory = FileSaver()

    client, power_shell_tools = await _init_mcp_tools(timeout=15.0)
    tools = file_management_toolkit + knowledge_toolkit + web_search_toolkit + power_shell_tools

    orchestrator = FlowOrchestrator()
    checkpoint_mgr = CheckpointManager()

    retriever = None
    executor = None
    try:
        from Coder.knowledge.retriever import Retriever
        retriever = Retriever()

        if not retriever.is_available():
            logger.info("向量库为空，尝试自动导入SOP文档...")
            try:
                await _auto_index_sop_docs(retriever.vector_store, timeout=30.0)
            except Exception as idx_err:
                logger.warning(f"自动导入SOP文档失败: {idx_err}")

        executor = SOPExecutor(orchestrator, retriever)
        logger.info("知识库和SOP执行器初始化成功")
    except Exception as e:
        logger.warning(f"知识库初始化失败（不影响基本功能）: {e}")

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory,
        debug=False,
    )
    config = RunnableConfig(configurable={"thread_id": thread_id})

    sop_context = {
        "retriever": retriever,
        "orchestrator": orchestrator,
        "executor": executor,
        "checkpoint_mgr": checkpoint_mgr,
    }

    return agent, config, client, sop_context


def _build_enhanced_input(user_input: str, sop_context: dict) -> str:
    intent = classify_intent(user_input)
    retriever = sop_context.get("retriever")
    executor = sop_context.get("executor")
    orchestrator = sop_context.get("orchestrator")

    text_lower = user_input.lower()
    explicitly_mentions_sop = "sop" in text_lower or "流程" in text_lower or "步骤" in text_lower

    if intent.intent == IntentType.GENERAL_CHAT and not explicitly_mentions_sop:
        return user_input

    if intent.intent == IntentType.SKILL_INVOKE:
        return user_input

    context, has_relevant_docs = _retrieve_relevant_docs(retriever, user_input)

    sop_name = intent.sop_name
    if not sop_name and orchestrator:
        sop_name = _fuzzy_match_sop(user_input, orchestrator)

    if sop_name and executor:
        sop_prompt = executor.build_sop_prompt(sop_name, user_input)
        if sop_prompt:
            return sop_prompt

    if sop_name and not executor and orchestrator:
        return _build_sop_prompt_fallback(sop_name, user_input, orchestrator)

    if intent.intent == IntentType.QUERY_SOP or explicitly_mentions_sop:
        return _handle_query_intent(user_input, executor, orchestrator, has_relevant_docs, context, explicitly_mentions_sop)

    if intent.intent == IntentType.EXECUTE_SOP and not sop_name:
        return _handle_execute_without_sop(user_input, has_relevant_docs, context)

    if has_relevant_docs and context:
        return (
            f"参考文档：\n{context}\n\n"
            f"用户问题：{user_input}\n\n"
            f"请基于以上参考文档回答用户问题。"
        )

    return user_input


def _retrieve_relevant_docs(retriever, user_input: str) -> tuple[str, bool]:
    if not retriever or not retriever.is_available():
        return "", False

    try:
        docs = retriever.retrieve(user_input, k=3)
        if not docs:
            return "", False

        relevant_docs = [
            d for d in docs
            if d.metadata.get("relevance_score", float("inf")) <= retriever.score_threshold
        ]

        if not relevant_docs:
            return "", False

        context = retriever.retrieve_with_context(user_input, k=3)
        return context, True
    except Exception as e:
        logger.warning(f"RAG检索失败: {e}")
        return "", False


def _build_sop_prompt_fallback(sop_name: str, user_input: str, orchestrator) -> str:
    sop = orchestrator.get_sop(sop_name)
    if not sop:
        return user_input

    steps_text = SOPExecutor._format_steps(sop.get("steps", []))
    raw = sop.get("raw_content", "")

    parts = [
        f"## SOP: {sop_name}",
        "",
        f"**用户请求**: {user_input}",
        "",
    ]
    if steps_text:
        parts.extend(["## SOP 步骤", "", steps_text, ""])
    elif raw:
        parts.extend(["## SOP 原文", "", raw[:2000], ""])
    parts.extend([
        "## 执行要求", "",
        "请严格按照以上SOP步骤执行：",
        "1. 逐步执行每个步骤",
        "2. 每步完成后说明执行结果",
        "3. 如果某步骤失败，说明原因并决定是否继续",
        "4. 最终给出执行摘要",
    ])
    return "\n".join(parts)


def _handle_query_intent(
    user_input: str,
    executor: Optional[SOPExecutor],
    orchestrator,
    has_relevant_docs: bool,
    context: str,
    explicitly_mentions_sop: bool,
) -> str:
    if has_relevant_docs and context and executor:
        return executor.build_query_prompt(user_input, context)

    if executor:
        return executor.build_list_prompt(user_input)

    if orchestrator:
        available_sops = orchestrator.list_sops()
        if available_sops:
            sop_list = "\n".join(f"- {name}" for name in available_sops)
            return (
                f"## SOP查询\n\n"
                f"用户问题: {user_input}\n\n"
                f"## 可用SOP列表\n\n"
                f"{sop_list}\n\n"
                f"## 回答要求\n\n"
                f"请基于以上SOP列表回答用户问题。如果用户询问有哪些SOP，请列出所有可用SOP并简要说明。"
                f"如果用户询问的SOP不在列表中，明确告知用户当前没有该SOP。"
            )

    if explicitly_mentions_sop:
        return (
            f"用户问题: {user_input}\n\n"
            f"当前知识库中没有可用的SOP文档。请直接回答用户问题，不要编造SOP内容。"
        )
    return user_input


def _handle_execute_without_sop(user_input: str, has_relevant_docs: bool, context: str) -> str:
    if has_relevant_docs and context:
        return (
            f"## SOP 执行请求\n\n"
            f"用户请求: {user_input}\n\n"
            f"## 参考文档\n\n{context}\n\n"
            f"## 执行要求\n\n"
            f"请基于以上参考文档中的流程步骤执行操作，逐步完成并给出执行摘要。"
        )
    return user_input


def _fuzzy_match_sop(user_input: str, orchestrator) -> str:
    available_sops = orchestrator.list_sops()
    if not available_sops:
        return ""

    text = user_input.lower()
    best_match = ""
    best_score = 0

    for sop_name in available_sops:
        sop_name_lower = sop_name.lower()
        score = 0
        for char in sop_name_lower:
            if char in text:
                score += 1
        keywords = sop_name_lower.replace("应用", " ").replace("服务", " ").split()
        for kw in keywords:
            if kw in text:
                score += 3

        if score > best_score:
            best_score = score
            best_match = sop_name

    if best_score >= 2:
        return best_match
    return ""


async def stream_agent_response(agent, config, user_input: str, sop_context: dict = None):
    if sop_context:
        enhanced_input = _build_enhanced_input(user_input, sop_context)
    else:
        enhanced_input = user_input

    input_data = {"messages": [HumanMessage(content=enhanced_input)]}
    tool_calls_accumulator = {}
    yielded_tool_calls = set()

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
                yield {"type": "thinking", "content": reasoning}

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
                    yield {
                        "type": "tool_call",
                        "name": tc_data["name"],
                        "args": tc_data["args"],
                    }
                    yielded_tool_calls.add(tc_id)

            if msg_chunk.content:
                yield {"type": "content", "content": msg_chunk.content}

        elif isinstance(msg_chunk, ToolMessage):
            tool_name = msg_chunk.name or "工具"
            content = str(msg_chunk.content)[:500]
            yield {"type": "tool_result", "name": tool_name, "content": content}


async def run_agent():
    agent, config, _, sop_context = await create_code_agent(thread_id="2")

    while True:
        try:
            user_input = input("用户: ")
            if user_input.lower() in ("exit", "quit"):
                break
            print("助手:", flush=True)

            async for event in stream_agent_response(agent, config, user_input, sop_context):
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

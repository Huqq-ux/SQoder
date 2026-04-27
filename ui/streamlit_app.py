import sys
import os
import re
import asyncio
import html
import time
import logging
import threading
import traceback
import uuid
import warnings

warnings.filterwarnings("ignore")

_logger = logging.getLogger(__name__)

_SAFE_FILENAME_RE = re.compile(r'^[\w\-\.]+$')
_MAX_UPLOAD_SIZE_MB = 50
_ALLOWED_UPLOAD_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}

_project_root = os.path.join(os.path.dirname(__file__), "..", "..")
_project_root = os.path.normpath(_project_root)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

logging.basicConfig(level=logging.WARNING)

st.set_page_config(page_title="AI 编程助手", page_icon="🤖", layout="wide")

if "agent" not in st.session_state:
    st.session_state.agent = None
    st.session_state.config = None
    st.session_state.messages = []
    st.session_state.agent_ready = False
    st.session_state.mcp_client = None
    st.session_state.event_loop = None
    st.session_state.sop_context = None
    st.session_state.init_error = None
    st.session_state.init_log = []
    st.session_state.thread_id = "streamlit"
    st.session_state.stop_event = threading.Event()
    st.session_state.is_generating = False
    st.session_state.confirm_new_session = False


def _get_event_loop():
    if st.session_state.event_loop is None or st.session_state.event_loop.is_closed():
        st.session_state.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(st.session_state.event_loop)
    return st.session_state.event_loop


def run_async(coro):
    loop = _get_event_loop()
    return loop.run_until_complete(coro)


def _escape(text):
    return html.escape(str(text))


def _merge_parts(parts):
    merged = []
    for part in parts:
        if not merged:
            merged.append(dict(part))
            continue
        last = merged[-1]
        if part["type"] == "content" and last["type"] == "content":
            last["content"] += part.get("content", "")
        elif part["type"] == "thinking" and last["type"] == "thinking":
            last["content"] += part.get("content", "")
        else:
            merged.append(dict(part))
    return merged


def render_assistant_message(parts):
    merged = _merge_parts(parts)
    for part in merged:
        ptype = part["type"]
        if ptype == "thinking":
            st.markdown(
                f'<details><summary>💭 思考过程</summary>'
                f'<pre style="white-space:pre-wrap;font-size:0.85em;color:#6b7280;">'
                f'{_escape(part["content"])}</pre></details>',
                unsafe_allow_html=True,
            )
        elif ptype == "tool_call":
            args_display = f'  \n📋 参数: `{_escape(part["args"])}`' if part.get("args") else ""
            st.markdown(f"🔧 **调用工具**: `{_escape(part['name'])}`{args_display}")
        elif ptype == "tool_result":
            st.markdown(
                f'<details><summary>📤 工具结果 - {_escape(part["name"])}</summary>'
                f'<pre style="white-space:pre-wrap;font-size:0.85em;">'
                f'{_escape(part["content"])}</pre></details>',
                unsafe_allow_html=True,
            )
        elif ptype == "content":
            st.markdown(part["content"])


def build_display(parts):
    merged = _merge_parts(parts)
    buf = []
    for part in merged:
        ptype = part["type"]
        if ptype == "thinking":
            buf.append(
                f'<details><summary>💭 思考过程</summary>'
                f'<pre style="white-space:pre-wrap;font-size:0.85em;color:#6b7280;">'
                f'{_escape(part["content"])}</pre></details>'
            )
        elif ptype == "tool_call":
            args_display = f'  \n📋 参数: `{_escape(part["args"])}`' if part.get("args") else ""
            buf.append(f"🔧 **调用工具**: `{_escape(part['name'])}`{args_display}")
        elif ptype == "tool_result":
            buf.append(
                f'<details><summary>📤 工具结果 - {_escape(part["name"])}</summary>'
                f'<pre style="white-space:pre-wrap;font-size:0.85em;">'
                f'{_escape(part["content"])}</pre></details>'
            )
        elif ptype == "content":
            buf.append(part["content"])
    return "\n".join(buf)


def _render_knowledge_page():
    st.header("📚 知识库管理")

    tab_upload, tab_list, tab_search = st.tabs(["上传文档", "文档列表", "检索测试"])

    with tab_upload:
        st.subheader("上传文档到知识库")
        uploaded_files = st.file_uploader(
            "选择文件",
            type=["txt", "md", "pdf", "docx"],
            accept_multiple_files=True,
            key="kb_upload",
        )

        if uploaded_files and st.button("导入到知识库", key="btn_import"):
            sop_dir = os.path.join(
                os.path.dirname(__file__), "..", "knowledge", "sop_docs"
            )
            sop_dir = os.path.normpath(sop_dir)
            os.makedirs(sop_dir, exist_ok=True)

            from Coder.knowledge.document_loader import DocumentLoader
            from Coder.knowledge.text_splitter import SOPTextSplitter
            from Coder.knowledge.vector_store import VectorStore

            loader = DocumentLoader()
            splitter = SOPTextSplitter()
            vector_store = VectorStore()

            total_chunks = 0
            for uploaded_file in uploaded_files:
                raw_name = uploaded_file.name
                safe_name = os.path.basename(raw_name)
                if not _SAFE_FILENAME_RE.match(safe_name):
                    st.error(f"❌ {raw_name}: 文件名包含非法字符")
                    continue

                suffix = os.path.splitext(safe_name)[1].lower()
                if suffix not in _ALLOWED_UPLOAD_SUFFIXES:
                    st.error(f"❌ {safe_name}: 不支持的文件类型 {suffix}")
                    continue

                file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
                if file_size_mb > _MAX_UPLOAD_SIZE_MB:
                    st.error(f"❌ {safe_name}: 文件过大 ({file_size_mb:.1f}MB)")
                    continue

                save_path = os.path.normpath(os.path.join(sop_dir, safe_name))
                if not save_path.startswith(sop_dir):
                    st.error(f"❌ {safe_name}: 文件路径异常")
                    continue

                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with st.spinner(f"处理 {safe_name}..."):
                    try:
                        doc = loader.load(save_path)
                        chunks = splitter.split_documents([doc])
                        vector_store.add_documents(chunks)
                        total_chunks += len(chunks)
                        st.success(f"✅ {safe_name}: {len(chunks)} 个文档块")
                    except Exception as e:
                        st.error(f"❌ {safe_name}: {type(e).__name__}")

            st.info(f"共导入 {len(uploaded_files)} 个文件，{total_chunks} 个文档块")

    with tab_list:
        st.subheader("已上传的文档")
        sop_dir = os.path.join(
            os.path.dirname(__file__), "..", "knowledge", "sop_docs"
        )
        sop_dir = os.path.normpath(sop_dir)
        if os.path.exists(sop_dir):
            files = [
                f
                for f in os.listdir(sop_dir)
                if os.path.splitext(f)[1].lower() in (".txt", ".md", ".pdf", ".docx", ".json")
                and _SAFE_FILENAME_RE.match(f)
            ]
            if files:
                for f in sorted(files):
                    path = os.path.normpath(os.path.join(sop_dir, f))
                    if not path.startswith(sop_dir):
                        continue
                    size = os.path.getsize(path)
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.text(f)
                    col2.text(f"{size / 1024:.1f} KB")
                    if col3.button("删除", key=f"del_{f}"):
                        os.remove(path)
                        st.rerun()
            else:
                st.info("暂无文档，请先上传")
        else:
            st.info("暂无文档，请先上传")

        from Coder.knowledge.vector_store import VectorStore
        vector_store = VectorStore()
        doc_count = vector_store.get_document_count()
        st.metric("向量库文档块数", doc_count)

    with tab_search:
        st.subheader("检索测试")
        query = st.text_input("输入查询", key="kb_search_query")
        if query and st.button("检索", key="btn_search"):
            from Coder.knowledge.retriever import Retriever

            retriever = Retriever()
            if retriever.is_available():
                docs = retriever.retrieve(query, k=3)
                for i, doc in enumerate(docs):
                    score = doc.metadata.get("relevance_score", "N/A")
                    source = doc.metadata.get("filename", "未知")
                    section = doc.metadata.get("section", "")
                    st.markdown(
                        f"**结果 {i + 1}** | 来源: {source} | 章节: {section} | 相关度: {score}"
                    )
                    st.code(doc.page_content[:500], language="markdown")
                    st.divider()
            else:
                st.warning("知识库为空，请先上传文档")


def _render_sop_page():
    st.header("📋 SOP 管理")

    if st.session_state.sop_context is None:
        st.warning("智能体未初始化")
        return

    orchestrator = st.session_state.sop_context.get("orchestrator")
    executor = st.session_state.sop_context.get("executor")
    checkpoint_mgr = st.session_state.sop_context.get("checkpoint_mgr")

    if orchestrator is None:
        st.warning("SOP编排器未初始化")
        return

    tab_list, tab_create, tab_exec, tab_history = st.tabs(
        ["SOP 列表", "创建 SOP", "执行 SOP", "执行历史"]
    )

    with tab_list:
        sops = orchestrator.list_sops()
        if sops:
            for sop_name in sops:
                sop = orchestrator.get_sop(sop_name)
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    steps_count = len(sop.get("steps", [])) if sop else 0
                    st.markdown(f"**{sop_name}** ({steps_count} 个步骤)")
                with col2:
                    if sop and sop.get("description"):
                        st.caption(sop["description"][:100])
                with col3:
                    if st.button("删除", key=f"sop_del_{sop_name}"):
                        orchestrator.delete_sop(sop_name)
                        st.rerun()
        else:
            st.info("暂无SOP，请创建或上传文档")

    with tab_create:
        st.subheader("创建新 SOP")
        sop_name = st.text_input("SOP 名称", key="sop_create_name")
        sop_desc = st.text_area("SOP 描述", key="sop_create_desc", height=80)

        steps_text = st.text_area(
            "步骤列表（每行一个步骤，格式：步骤名称: 步骤描述）",
            key="sop_create_steps",
            height=200,
            value="步骤1: 检查环境\n步骤2: 准备资源\n步骤3: 执行操作\n步骤4: 验证结果",
        )

        if st.button("创建 SOP", key="btn_create_sop") and sop_name:
            steps = []
            for i, line in enumerate(steps_text.strip().split("\n")):
                line = line.strip()
                if not line:
                    continue
                if ":" in line or "：" in line:
                    sep = ":" if ":" in line else "："
                    parts = line.split(sep, 1)
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""
                else:
                    name = f"步骤{i + 1}"
                    desc = line

                steps.append({
                    "index": i,
                    "name": name,
                    "description": desc,
                })

            sop_data = {
                "name": sop_name,
                "description": sop_desc,
                "steps": steps,
            }

            from Coder.sop.validator import SOPValidator

            validator = SOPValidator()
            validation = validator.validate_sop_structure(sop_data)

            if validation["valid"]:
                orchestrator.save_sop(sop_name, sop_data)
                st.success(f"SOP '{sop_name}' 创建成功！共 {len(steps)} 个步骤")
            else:
                for issue in validation["issues"]:
                    st.error(f"❌ {issue}")

    with tab_exec:
        st.subheader("执行 SOP")
        sops = orchestrator.list_sops()
        if sops:
            selected_sop = st.selectbox("选择 SOP", sops, key="sop_exec_select")
            if selected_sop:
                sop = orchestrator.get_sop(selected_sop)
                if sop and sop.get("steps"):
                    st.markdown("### 步骤预览")
                    for step in sop["steps"]:
                        st.markdown(
                            f"- **{step.get('name', '')}**: {step.get('description', '')[:100]}"
                        )

                    if st.button("开始执行", key="btn_exec_sop"):
                        result = orchestrator.start_execution(selected_sop)
                        if result:
                            st.success(
                                f"SOP '{selected_sop}' 开始执行，共 {result['total_steps']} 个步骤"
                            )
                            st.info("请切换到对话页面，输入执行指令与智能体交互")
                        else:
                            st.error("启动执行失败")
        else:
            st.info("暂无可执行的SOP")

    with tab_history:
        st.subheader("执行历史")
        if checkpoint_mgr:
            checkpoints = checkpoint_mgr.list_checkpoints()
            if checkpoints:
                for cp in checkpoints:
                    with st.expander(
                        f"{cp['sop_name']} - {cp.get('saved_at', '未知时间')}"
                    ):
                        st.json(cp)
            else:
                st.info("暂无执行历史")
        else:
            st.info("检查点管理器未初始化")


def _render_chat_page():
    st.title("🤖 AI 编程助手")

    if st.session_state.sop_context:
        retriever = st.session_state.sop_context.get("retriever")
        kb_status = "[OK] 已连接" if retriever and retriever.is_available() else "[--] 未配置"
        orchestrator = st.session_state.sop_context.get("orchestrator")
        sop_count = len(orchestrator.list_sops()) if orchestrator else 0
        st.caption(f"知识库: {kb_status} | SOP: {sop_count} 个 | 会话: {st.session_state.thread_id[:8]}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                parts = msg.get("parts", [])
                if parts:
                    render_assistant_message(parts)
                else:
                    st.markdown(msg.get("content", ""))
            else:
                st.markdown(msg["content"])

    if st.session_state.is_generating:
        st.info("⏹ 智能体正在生成回答...")

    # 输入区域布局：输入框 + 停止按钮
    input_container = st.container()
    with input_container:
        if st.session_state.is_generating:
            col1, col2 = st.columns([5, 1])
            with col1:
                prompt = st.chat_input("输入你的问题...", disabled=True)
            with col2:
                if st.button("⏹ 停止", type="primary", use_container_width=True):
                    st.session_state.stop_event.set()
                    st.session_state.is_generating = False
                    _logger.info("用户点击了停止回答按钮")
                    st.toast("已停止回答", icon="⏹")
                    st.rerun()
        else:
            prompt = st.chat_input("输入你的问题...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_parts = []
            placeholder = st.empty()
            throttle = {"last_update": 0}
            UPDATE_INTERVAL = 0.1

            st.session_state.stop_event.clear()
            st.session_state.is_generating = True

            async def process_stream():
                from Coder.agent.code_agent import stream_agent_response
                async for event in stream_agent_response(
                    st.session_state.agent,
                    st.session_state.config,
                    prompt,
                    st.session_state.sop_context,
                ):
                    if st.session_state.stop_event.is_set():
                        response_parts.append({
                            "type": "content",
                            "content": "\n\n[回答已停止]",
                        })
                        _logger.info("用户停止了智能体回答")
                        break

                    response_parts.append(event)

                    now = time.time()
                    if now - throttle["last_update"] >= UPDATE_INTERVAL:
                        placeholder.markdown(
                            build_display(response_parts), unsafe_allow_html=True
                        )
                        throttle["last_update"] = now

                placeholder.markdown(
                    build_display(response_parts), unsafe_allow_html=True
                )

            try:
                run_async(process_stream())
            except Exception as e:
                _logger.error(f"智能体响应异常: {type(e).__name__}: {e}")
                st.error(f"发生错误: {type(e).__name__}")
                response_parts.append({"type": "content", "content": f"发生错误: {type(e).__name__}"})
            finally:
                st.session_state.is_generating = False
                st.session_state.stop_event.clear()

            merged_parts = _merge_parts(response_parts)

            content_text = ""
            for p in merged_parts:
                if p["type"] == "content":
                    content_text += p.get("content", "")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "parts": merged_parts,
                    "content": content_text,
                }
            )


page = st.sidebar.radio(
    "导航",
    ["💬 对话", "📚 知识库", "📋 SOP 管理"],
    key="nav_page",
)

with st.sidebar:
    st.divider()

    if st.session_state.confirm_new_session:
        st.warning("确认开启新会话？当前对话历史将被清除。")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认", type="primary", use_container_width=True):
                old_thread = st.session_state.thread_id
                st.session_state.messages = []
                st.session_state.thread_id = f"session_{uuid.uuid4().hex[:12]}"
                st.session_state.stop_event.clear()
                st.session_state.is_generating = False
                st.session_state.confirm_new_session = False

                if st.session_state.agent_ready:
                    from langchain_core.runnables import RunnableConfig
                    st.session_state.config = RunnableConfig(
                        configurable={"thread_id": st.session_state.thread_id}
                    )

                _logger.info(f"新会话已创建: {st.session_state.thread_id} (旧: {old_thread})")
                st.toast("新会话已创建", icon="🔄")
                st.rerun()
        with col2:
            if st.button("取消", use_container_width=True):
                st.session_state.confirm_new_session = False
                st.rerun()
    else:
        if st.button("🔄 开启新会话", use_container_width=True):
            st.session_state.confirm_new_session = True
            st.rerun()

    st.divider()
    st.caption("基于 LangGraph + Qwen3.6-plus + RAG")
    st.caption("支持 SOP 执行 | 文件操作 | Shell 命令")

if not st.session_state.agent_ready:
    init_status = st.empty()
    init_progress = st.empty()
    init_status.info("🔄 正在初始化智能体，请稍候...")

    log_file = os.path.join(_project_root, "streamlit_init.log")

    try:
        with open(log_file, "w", encoding="utf-8") as lf:
            lf.write("=== Streamlit Init Start ===\n")
            lf.flush()

            from Coder.agent.code_agent import create_code_agent

            lf.write("Step 1: import OK\n")
            lf.flush()

            init_progress.info("🔄 步骤 1/3: 加载模型和基础工具...")
            init_status.empty()

            import concurrent.futures

            def _create_agent_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(create_code_agent("streamlit"))
                finally:
                    loop.close()

            INIT_TIMEOUT = 60

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_create_agent_sync)
                try:
                    agent, config, client, sop_context = future.result(timeout=INIT_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    lf.write(f"TIMEOUT after {INIT_TIMEOUT}s\n")
                    lf.flush()
                    future.cancel()
                    raise TimeoutError(f"初始化超时（{INIT_TIMEOUT}秒），请检查网络连接或模型缓存")

            lf.write("Step 2: agent created OK\n")
            lf.flush()

            st.session_state.agent = agent
            st.session_state.config = config
            st.session_state.mcp_client = client
            st.session_state.agent_ready = True
            st.session_state.sop_context = sop_context
            st.session_state.thread_id = config.get("configurable", {}).get("thread_id", st.session_state.thread_id)

            lf.write("Step 3: session state updated\n")
            lf.flush()

            init_progress.success("✅ 智能体初始化成功！")
            time.sleep(0.5)
            st.rerun()

    except TimeoutError as te:
        try:
            with open(log_file, "a", encoding="utf-8") as lf:
                lf.write(f"TIMEOUT: {te}\n")
                lf.flush()
        except:
            pass
        init_progress.error(f"❌ {te}")
        with st.expander("排查建议"):
            st.markdown(
                "1. **模型未缓存**：首次运行需要下载嵌入模型 `BAAI/bge-small-zh-v1.5`（约100MB），请确保网络通畅\n"
                "2. **网络不通**：如果无法访问 HuggingFace，请设置镜像：\n"
                "   ```bash\n"
                "   set HF_ENDPOINT=https://hf-mirror.com\n"
                "   ```\n"
                "3. **手动下载模型**：运行以下命令预先缓存模型：\n"
                "   ```bash\n"
                "   python -c \"from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')\"\n"
                "   ```\n"
                "4. **跳过知识库**：如果不需要知识库功能，可以在初始化时忽略此错误"
            )
        if st.button("重新初始化"):
            st.session_state.init_error = None
            st.rerun()
        st.stop()

    except Exception as e:
        error_msg = str(e)
        try:
            with open(log_file, "a", encoding="utf-8") as lf:
                lf.write(f"ERROR: {error_msg}\n")
                import traceback
                lf.write(traceback.format_exc())
                lf.flush()
        except:
            pass

        init_progress.error(f"❌ 初始化智能体失败: {error_msg}")
        with st.expander("查看详细错误信息"):
            st.code(traceback.format_exc())
        if st.button("重新初始化"):
            st.session_state.init_error = None
            st.rerun()
        st.stop()

if page == "💬 对话":
    _render_chat_page()
elif page == "📚 知识库":
    _render_knowledge_page()
elif page == "📋 SOP 管理":
    _render_sop_page()

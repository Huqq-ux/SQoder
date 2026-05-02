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
from Coder.tools.file_saver import FileSaver

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
    st.session_state.thread_id = None
    st.session_state.stop_event = threading.Event()
    st.session_state.is_generating = False
    st.session_state.confirm_new_session = False
    st.session_state.session_manager = None
    st.session_state.session_list_cache = None
    st.session_state.switching_session = False
    st.session_state.deleting_session = None
    st.session_state.skill_invoke_state = None
    st.session_state.skill_invoker = None


def _get_session_manager():
    if st.session_state.session_manager is None:
        from Coder.tools.session_manager import SessionManager
        st.session_state.session_manager = SessionManager()
    return st.session_state.session_manager


def _ensure_session():
    if st.session_state.thread_id is None:
        mgr = _get_session_manager()
        sessions = mgr.list_sessions()
        if sessions:
            latest = sessions[0]
            st.session_state.thread_id = latest["session_id"]
            st.session_state.messages = []
        else:
            session = mgr.create_session()
            st.session_state.thread_id = session["session_id"]
            st.session_state.messages = []
            if st.session_state.agent_ready:
                from langchain_core.runnables import RunnableConfig
                st.session_state.config = RunnableConfig(
                    configurable={"thread_id": st.session_state.thread_id}
                )


def _switch_to_session(target_id: str):
    mgr = _get_session_manager()
    current_id = st.session_state.thread_id

    if current_id and current_id != target_id:
        mgr.update_session_from_messages(current_id, st.session_state.messages)

    st.session_state.thread_id = target_id

    if st.session_state.agent_ready:
        checkpointer = None
        try:
            from Coder.tools.file_saver import FileSaver
            checkpointer = FileSaver()
        except Exception:
            pass

        if checkpointer:
            restored = mgr.get_session_messages_from_checkpoint(target_id, checkpointer)
            if restored:
                st.session_state.messages = restored
            else:
                st.session_state.messages = []
        else:
            st.session_state.messages = []

        from langchain_core.runnables import RunnableConfig
        st.session_state.config = RunnableConfig(
            configurable={"thread_id": target_id}
        )
    else:
        st.session_state.messages = []

    st.session_state.stop_event.clear()
    st.session_state.is_generating = False
    st.session_state.session_list_cache = None
    _logger.info(f"切换到会话: {target_id}")


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


def _render_skill_page():
    st.header("🔧 Skill 管理")

    from Coder.tools.skill_store import SkillStore
    store = SkillStore()

    tab_upload, tab_list, tab_detail = st.tabs([
        "上传 Skill", "已安装 Skills", "Skill 详情"
    ])

    with tab_upload:
        _render_skill_upload_tab(store)
    with tab_list:
        _render_skill_list_tab(store)
    with tab_detail:
        _render_skill_detail_tab(store)


def _render_skill_upload_tab(store):
    st.subheader("📤 上传 Skill Markdown 文件")
    st.caption("仅支持 `.md` 格式，文件名需包含 `skill` 关键词，大小不超过 5MB")

    uploaded_file = st.file_uploader(
        "选择 Skill 文件",
        type=["md"],
        accept_multiple_files=False,
        key="skill_upload",
        help="选择包含 Skill 定义的 Markdown 文件",
    )

    if uploaded_file is None:
        return

    raw_name = uploaded_file.name

    if not raw_name.lower().endswith(".md"):
        st.error("❌ 仅支持 .md 格式的文件")
        st.stop()

    name_no_ext = os.path.splitext(raw_name)[0].lower()
    if "skill" not in name_no_ext:
        st.error(f"❌ 文件名需包含 'skill' 关键词（当前: `{raw_name}`）")
        st.info("示例文件名: `my_skill.md`, `code_review_skill.md`")
        st.stop()

    file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
    if file_size_mb > 5:
        st.error(f"❌ 文件过大 ({file_size_mb:.1f}MB)，最大允许 5MB")
        st.stop()

    status_container = st.empty()
    progress_bar = st.progress(0, text="⏳ 正在读取文件...")

    try:
        content = uploaded_file.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        progress_bar.empty()
        status_container.error("❌ 文件编码错误，请使用 UTF-8 编码")
        st.stop()

    progress_bar.progress(20, text="📖 正在解析 Skill 定义...")

    from Coder.tools.skill_parser import SkillParser

    name_hint = os.path.splitext(raw_name)[0]
    skill_def = SkillParser.parse_markdown(content, name_hint=name_hint)
    if skill_def is None:
        progress_bar.empty()
        status_container.error("❌ 解析失败：无法从文件中提取有效的 Skill 定义")
        with st.expander("📄 文件内容预览"):
            st.code(content[:2000], language="markdown")
        st.stop()

    progress_bar.progress(40, text="🔍 正在验证代码...")

    from Coder.tools.skill_compiler import SkillCompiler

    code_ok = True
    code_msg = ""
    if skill_def.code:
        valid, msg = SkillCompiler.validate(skill_def.code)
        code_ok = valid
        code_msg = msg

    progress_bar.progress(60, text="💾 正在保存 Skill...")

    is_overwrite = store.exists(skill_def.name)

    if not store.save_skill(skill_def):
        progress_bar.empty()
        status_container.error("❌ 保存 Skill 失败，请检查文件格式")
        return

    progress_bar.progress(80, text="🔄 正在注册 Skill...")

    from Coder.tools.skill_registry import SkillRegistry
    registry = SkillRegistry()
    if registry._initialized:
        registry.reload_skill(skill_def.name)

    progress_bar.progress(100, text="✅ 上传完成！")
    time.sleep(0.5)
    progress_bar.empty()

    if is_overwrite:
        status_container.success(
            f"✅ Skill `{skill_def.display_name}` 已覆盖更新！"
        )
    else:
        status_container.success(
            f"✅ Skill `{skill_def.display_name}` 已成功安装！"
        )

    st.markdown("---")
    st.subheader("📋 解析预览")

    col1, col2, col3 = st.columns(3)
    col1.metric("名称", skill_def.name)
    col2.metric("分类", skill_def.category)
    col3.metric("版本", skill_def.version or "1.0.0")

    st.markdown(f"**描述**: {skill_def.description or '(无)'}")

    if skill_def.tags:
        tags_html = " ".join(f"`{t}`" for t in skill_def.tags)
        st.markdown(f"**标签**: {tags_html}")

    if skill_def.parameters:
        st.markdown("**参数定义**:")
        param_data = []
        for p in skill_def.parameters:
            param_data.append({
                "参数名": p.get("name", ""),
                "类型": p.get("type", "str"),
                "必填": "✅" if p.get("required") else "❌",
                "说明": p.get("description", ""),
            })
        st.dataframe(param_data, use_container_width=True, hide_index=True)

    if skill_def.code:
        with st.expander("🐍 代码实现", expanded=False):
            if code_ok:
                st.code(skill_def.code, language="python")
            else:
                st.warning(f"⚠️ 代码验证未通过: {code_msg}")
                st.code(skill_def.code, language="python")
    elif not skill_def.code:
        st.info("ℹ️ 此 Skill 不包含代码实现")

    st.divider()
    st.caption(
        f"文件: {raw_name} | "
        f"大小: {file_size_mb:.1f}KB | "
        f"创建时间: {skill_def.created_at}"
    )


def _render_skill_list_tab(store):
    st.subheader("📦 已安装的 Skills")

    if st.button("🔄 刷新列表", key="btn_refresh_skills"):
        pass

    skills_path = os.path.join(os.path.dirname(__file__), "..", "skills")
    skills_path = os.path.normpath(skills_path)

    skill_files = (
        [f for f in os.listdir(skills_path) if f.endswith(".json")]
        if os.path.exists(skills_path)
        else []
    )

    if not skill_files:
        st.info("暂无已安装的 Skill，请先上传")
        return

    from Coder.tools.skill_registry import SkillRegistry
    registry = SkillRegistry()
    if not registry._initialized:
        registry.initialize()

    for sf in sorted(skill_files):
        skill_name = sf[:-5]
        meta = registry.get_meta(skill_name)
        if meta is None:
            meta = store.load_skill_meta(skill_name)

        if meta:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            col1.markdown(f"**{meta.display_name}**")
            col1.caption(f"`{meta.name}`")

            enabled_text = f"📂 {meta.category}"
            if not meta.enabled:
                enabled_text += " *(已禁用)*"
            col2.markdown(enabled_text)

            is_compiled = registry._initialized and meta.name in registry._skills
            if is_compiled:
                col3.success("已编译")
            else:
                col3.info("元数据")

            comp_col, del_col = st.columns([1, 1])
            with comp_col:
                btn_label = "禁用" if meta.enabled else "启用"
                if st.button(btn_label, key=f"toggle_skill_{skill_name}"):
                    store.toggle_skill(skill_name, not meta.enabled)
                    if registry._initialized:
                        registry.reload_skill(skill_name)
                    st.rerun()

            with del_col:
                if st.button("🗑", key=f"del_skill_{skill_name}",
                             help=f"删除 {meta.display_name}"):
                    if st.session_state.get("confirm_del_skill") == skill_name:
                        store.delete_skill(skill_name)
                        registry.unregister(skill_name)
                        st.session_state["confirm_del_skill"] = None
                        st.toast(f"已删除 {meta.display_name}", icon="🗑")
                        st.rerun()
                    else:
                        st.session_state["confirm_del_skill"] = skill_name
                        st.warning(
                            f"⚠️ 再次点击确认删除 `{meta.display_name}`"
                        )
                        st.rerun()

            if meta.tags:
                tags_text = " ".join(f"`{t}`" for t in meta.tags)
                st.caption(tags_text)

            if meta.description:
                st.caption(meta.description)

            st.divider()


def _render_skill_detail_tab(store):
    st.subheader("🔍 Skill 详情查看")

    skills_path = os.path.join(os.path.dirname(__file__), "..", "skills")
    skills_path = os.path.normpath(skills_path)

    if not os.path.exists(skills_path):
        st.info("暂无已安装的 Skill，请先上传")
        return

    skill_files = [f for f in os.listdir(skills_path) if f.endswith(".json")]
    if not skill_files:
        st.info("暂无已安装的 Skill，请先上传")
        return

    skill_names = sorted(f[:-5] for f in skill_files)
    display_names = []
    name_map = {}

    for sn in skill_names:
        meta = store.load_skill_meta(sn)
        label = f"{meta.display_name} ({sn})" if meta else sn
        display_names.append(label)
        name_map[label] = sn

    selected_label = st.selectbox(
        "选择要查看的 Skill",
        display_names,
        key="skill_detail_select",
    )

    if not selected_label:
        return

    selected_name = name_map[selected_label]
    skill_def = store.load_skill(selected_name)

    if not skill_def:
        st.warning(f"无法加载 Skill: {selected_name}")
        return

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("内部名称", skill_def.name)
    col_b.metric("分类", skill_def.category)
    col_c.metric("版本", skill_def.version or "1.0.0")

    st.markdown(f"**显示名称**: {skill_def.display_name}")
    st.markdown(f"**描述**: {skill_def.description or '(无)'}")
    status = "✅ 启用" if skill_def.enabled else "⛔ 已禁用"
    st.markdown(f"**状态**: {status}")
    if skill_def.author:
        st.markdown(f"**作者**: {skill_def.author}")
    if skill_def.tags:
        st.markdown(
            "**标签**: " + " ".join(f"`{t}`" for t in skill_def.tags)
        )

    if skill_def.parameters:
        st.markdown("**参数定义**:")
        param_data = []
        for p in skill_def.parameters:
            param_data.append({
                "参数名": p.get("name", ""),
                "类型": p.get("type", "str"),
                "必填": "✅" if p.get("required") else "❌",
                "说明": p.get("description", ""),
            })
        st.dataframe(param_data, use_container_width=True, hide_index=True)

    if skill_def.code:
        with st.expander("🐍 代码实现", expanded=False):
            st.code(skill_def.code, language="python")

    st.divider()
    st.caption(
        f"创建: {skill_def.created_at} | "
        f"更新: {skill_def.updated_at}"
    )

    col_json, _ = st.columns(2)
    with col_json:
        full_path = os.path.join(skills_path, f"{selected_name}.json")
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                with st.expander("📄 原始 JSON", expanded=False):
                    st.json(f.read())


def _get_skill_invoker():
    if st.session_state.skill_invoker is None:
        from Coder.sop.skill_nl_invoker import SkillNLInvoker
        st.session_state.skill_invoker = SkillNLInvoker()
    return st.session_state.skill_invoker


def _handle_skill_invoke(user_input: str) -> tuple:
    from Coder.sop.skill_nl_invoker import InvokeStage, SkillInvocationState

    invoker = _get_skill_invoker()
    state = st.session_state.skill_invoke_state

    if state is not None and state.stage == InvokeStage.COLLECTING_PARAMS:
        new_params, still_missing = invoker.extract_params(
            user_input, invoker.registry.get_meta(state.skill_name)
        )
        state.matched_params.update(new_params)
        for mp in list(state.missing_params):
            if mp in new_params:
                state.missing_params.remove(mp)

        if state.missing_params:
            prompt = invoker.build_missing_param_prompt(
                invoker.registry.get_meta(state.skill_name),
                state.missing_params,
            )
            return "skill_collecting", prompt, state

        if state.needs_confirmation:
            state.stage = InvokeStage.CONFIRMING
            skill_meta = invoker.registry.get_meta(state.skill_name)
            prompt = invoker.build_confirmation_prompt(
                skill_meta, state.matched_params
            )
            return "skill_confirming", prompt, state
        else:
            return _execute_skill(state)

    if state is not None and state.stage == InvokeStage.CONFIRMING:
        user_lower = user_input.strip().lower()
        confirm_words = ["确定", "是", "执行", "确认", "yes", "ok", "y", "好"]
        cancel_words = ["取消", "否", "不", "no", "n", "取消执行"]

        is_confirm = any(w in user_lower for w in confirm_words)
        is_cancel = any(w in user_lower for w in cancel_words)

        if is_cancel and not is_confirm:
            invoker.reset()
            st.session_state.skill_invoke_state = None
            return "skill_cancelled", "⚠️ 已取消技能执行。", None

        if is_confirm:
            return _execute_skill(state)

        return "skill_confirming", (
            "⚠️ 请明确回复：**确定** / **是** 来确认执行，或 **取消** / **否** 来放弃。"
        ), state

    found, skill_meta, score = invoker.detect_skill_call(user_input)
    if not found:
        from Coder.sop.intent_classifier import classify_intent, IntentType

        intent = classify_intent(user_input)
        if intent.intent == IntentType.SKILL_INVOKE:
            all_metas = invoker.registry.list_all()
            if all_metas:
                parts = [
                    "🤔 检测到您想使用 Skill，但没有精确匹配到具体技能。",
                    "",
                    "当前可用的 Skill：",
                ]
                for m in all_metas:
                    parts.append(f"- **{m.display_name}** (`{m.name}`): {m.description[:50]}")
                parts.append("")
                parts.append("请指定具体的 Skill 名称，例如：`帮我反转文本 hello`")
                return "skill_collecting", "\n".join(parts), None
        return None, None, None

    params, missing = invoker.extract_params(user_input, skill_meta)
    needs_confirm = invoker.needs_confirmation(skill_meta)

    new_state = SkillInvocationState(
        skill_name=skill_meta.name,
        skill_display=skill_meta.display_name,
        matched_params=params,
        missing_params=missing,
        stage=InvokeStage.COLLECTING_PARAMS,
        needs_confirmation=needs_confirm,
    )

    if missing:
        st.session_state.skill_invoke_state = new_state
        prompt = invoker.build_missing_param_prompt(skill_meta, missing)
        return "skill_collecting", prompt, new_state

    if needs_confirm:
        new_state.stage = InvokeStage.CONFIRMING
        st.session_state.skill_invoke_state = new_state
        prompt = invoker.build_confirmation_prompt(skill_meta, params)
        return "skill_confirming", prompt, new_state

    new_state.stage = InvokeStage.EXECUTING
    return _execute_skill(new_state)


def _execute_skill(state):
    from Coder.sop.skill_nl_invoker import SkillNLInvoker

    invoker = _get_skill_invoker()
    registry = invoker.registry

    try:
        registered = registry.get(state.skill_name)
        if registered is None:
            invoker.reset()
            st.session_state.skill_invoke_state = None
            return "skill_error", f"❌ 技能 `{state.skill_display}` 未找到或编译失败。", None

        result = registered.func(**state.matched_params)

        summary_parts = [
            f"✅ **{state.skill_display}** 执行成功",
            "",
        ]
        if state.matched_params:
            summary_parts.append("**参数**:")
            for k, v in state.matched_params.items():
                summary_parts.append(f"  - {k}: `{v}`")
            summary_parts.append("")
        summary_parts.append("**结果**:")
        summary_parts.append(f"```\n{result}\n```")

        invoker.reset()
        st.session_state.skill_invoke_state = None
        return "skill_done", "\n".join(summary_parts), None

    except Exception as e:
        invoker.reset()
        st.session_state.skill_invoke_state = None
        return "skill_error", f"❌ 技能执行失败: {type(e).__name__}: {e}", None


def _render_chat_page():
    _ensure_session()

    st.title("🤖 AI 编程助手")

    if st.session_state.sop_context:
        retriever = st.session_state.sop_context.get("retriever")
        kb_status = "[OK] 已连接" if retriever and retriever.is_available() else "[--] 未配置"
        orchestrator = st.session_state.sop_context.get("orchestrator")
        sop_count = len(orchestrator.list_sops()) if orchestrator else 0
        st.caption(f"知识库: {kb_status} | SOP: {sop_count} 个 | 会话: {st.session_state.thread_id[:8] if st.session_state.thread_id else 'N/A'}")

    if st.session_state.is_generating:
        col_info, col_stop = st.columns([5, 1])
        with col_info:
            st.info("智能体正在生成回答...")
        with col_stop:
            if st.button("停止", type="primary", use_container_width=True, key="btn_stop_chat"):
                st.session_state.stop_event.set()
                st.session_state.is_generating = False
                _logger.info("用户点击了停止回答按钮")
                st.toast("已停止回答")
                st.rerun()

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

    if prompt := st.chat_input("输入你的问题..."):
        if st.session_state.is_generating:
            st.session_state.is_generating = False
            st.session_state.stop_event.clear()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            skill_status, skill_response, skill_state = _handle_skill_invoke(prompt)

            if skill_status in ("skill_collecting", "skill_confirming"):
                st.markdown(skill_response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": skill_response,
                })
                st.rerun()

            elif skill_status in ("skill_done", "skill_error", "skill_cancelled"):
                st.markdown(skill_response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": skill_response,
                })

            else:
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

                if st.session_state.thread_id:
                    mgr = _get_session_manager()
                    mgr.update_session_from_messages(
                        st.session_state.thread_id, st.session_state.messages
                    )
                    st.session_state.session_list_cache = None


page = st.sidebar.radio(
    "导航",
    ["💬 对话", "📚 知识库", "📋 SOP 管理", "🔧 Skill 管理"],
    key="nav_page",
)

with st.sidebar:
    st.divider()

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.markdown("**💬 历史会话**")
    with col_btn:
        if st.button("➕", key="btn_new_session", help="新建会话", use_container_width=True):
            mgr = _get_session_manager()
            if st.session_state.thread_id:
                mgr.update_session_from_messages(
                    st.session_state.thread_id, st.session_state.messages
                )
            new_sess = mgr.create_session()
            _switch_to_session(new_sess["session_id"])
            st.toast("新会话已创建", icon="✨")
            st.rerun()

    mgr = _get_session_manager()
    if st.session_state.session_list_cache is None:
        st.session_state.session_list_cache = mgr.list_sessions()
    sessions = st.session_state.session_list_cache

    if sessions:
        for sess in sessions:
            sid = sess["session_id"]
            is_active = sid == st.session_state.thread_id
            title = sess.get("title", "新会话")
            if len(title) > 18:
                title = title[:18] + "..."

            if is_active:
                label = f"▶ {title}"
            else:
                label = f"  {title}"

            col_switch, col_del = st.columns([5, 1])
            with col_switch:
                if st.button(
                    label,
                    key=f"sess_{sid}",
                    use_container_width=True,
                    disabled=is_active,
                ):
                    _switch_to_session(sid)
                    st.rerun()
            with col_del:
                if st.button("", key=f"del_sess_{sid}", icon="🗑", help=f"删除「{title}」"):
                    st.session_state.deleting_session = sid
    else:
        st.caption("暂无历史会话，点击上方按钮新建")

    if st.session_state.deleting_session:
        del_sid = st.session_state.deleting_session
        st.warning("确认删除此会话？此操作不可撤销。")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认删除", type="primary", key="btn_confirm_del"):
                mgr.delete_session(del_sid)
                st.session_state.deleting_session = None
                st.session_state.session_list_cache = None
                if st.session_state.thread_id == del_sid:
                    remaining = mgr.list_sessions()
                    if remaining:
                        _switch_to_session(remaining[0]["session_id"])
                    else:
                        new_sess = mgr.create_session()
                        _switch_to_session(new_sess["session_id"])
                st.toast("会话已删除", icon="🗑")
                st.rerun()
        with col2:
            if st.button("取消", key="btn_cancel_del"):
                st.session_state.deleting_session = None
                st.rerun()

    st.divider()
    st.caption("基于 LangGraph + deepseek-v4-pro + RAG")
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

            _ensure_session()
            init_thread_id = st.session_state.thread_id

            import concurrent.futures

            def _create_agent_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(create_code_agent(init_thread_id))
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

            mgr = _get_session_manager()
            mgr.migrate_legacy_session("streamlit")

            restored = mgr.get_session_messages_from_checkpoint(
                st.session_state.thread_id, FileSaver()
            )
            if restored:
                st.session_state.messages = restored

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
elif page == "🔧 Skill 管理":
    _render_skill_page()

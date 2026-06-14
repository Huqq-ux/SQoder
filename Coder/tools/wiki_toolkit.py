import logging
from contextvars import ContextVar
from typing import Optional

from langchain_core.tools import tool

from Coder.knowledge.wiki_manager import WikiManager
from Coder.tools.knowledge_toolkit import _current_course_id

logger = logging.getLogger(__name__)


def _resolve_course_id(explicit_id: str = "") -> str:
    """解析 course_id：优先用显式传入的，否则从上下文变量取。"""
    if explicit_id and explicit_id.strip():
        return explicit_id.strip()
    ctx_id = _current_course_id.get()
    return ctx_id or ""


@tool
def wiki_ingest(course_id: str = "") -> str:
    """从课程知识库的原始课件文件自动构建/更新百科页面。
    读取已在知识库中的课件内容，按章节结构拆分为概念页，创建交叉引用。
    适用于首次构建百科、课件更新后同步百科。
    注意：此操作可能耗时较长，每次调用最多处理100个章节。

    Args:
        course_id: 课程ID（可选，不提供则使用当前对话上下文中的课程）
    """
    cid = _resolve_course_id(course_id)
    if not cid:
        return "未指定课程ID。请提供 course_id 参数或在课程对话中使用。"

    WikiManager.init_wiki(cid)

    # 获取文档列表（模拟——实际应访问文件系统）
    import os
    docs_dir = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "knowledge", "docs"
    ))
    if not os.path.isdir(docs_dir):
        return "知识库文档目录不存在。请先在知识库中上传课件文件。"

    # 查找此课程相关的文档
    index_dir = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "knowledge", "index", cid
    ))

    # 尝试从向量存储获取文档列表
    from Coder.knowledge.vector_store import VectorStore
    store = VectorStore(store_path=index_dir)
    if not store.has_local_index():
        # 检查全局索引
        global_index = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "knowledge", "index"
        ))
        store = VectorStore(store_path=global_index)
        if not store.has_local_index():
            return (
                "知识库向量索引为空。请先在知识库管理页面上传课件文件，"
                "然后再调用 wiki_ingest 构建百科。\n"
                "步骤：知识库管理 → 选择课程 → 上传 PDF/PPTX 等课件 → "
                "返回此处再次调用 wiki_ingest。"
            )

    doc_count = store.get_document_count()
    if doc_count == 0:
        return "知识库中暂无文档，请先上传课件。"

    # 从 docs/ 目录枚举文件
    from Coder.knowledge.document_loader import DocumentLoader
    from Coder.knowledge.chapter_splitter import ChapterSplitter

    files = []
    for f in os.listdir(docs_dir):
        ext = os.path.splitext(f)[1].lower()
        if ext in (".txt", ".md", ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".epub"):
            fpath = os.path.normpath(os.path.join(docs_dir, f))
            if os.path.isfile(fpath):
                files.append(fpath)

    if not files:
        return "知识库文档目录为空，请先上传课件文件。"

    pages_created = 0
    pages_updated = 0
    errors = []

    loader = DocumentLoader()
    splitter = ChapterSplitter()

    for fpath in files:
        filename = os.path.basename(fpath)
        try:
            doc = loader.load(fpath)
            content = doc.get("content", "")
            if not content or not content.strip():
                continue

            chunks = splitter.split_text(content, source_file=filename)

            for chunk in chunks:
                section = chunk.metadata.get("section", "").strip()
                if not section:
                    continue
                section_clean = section.lstrip("#").strip()
                if not section_clean or len(section_clean) < 2:
                    continue

                existing_path = WikiManager.resolve_link(cid, section_clean)
                body = chunk.page_content

                if existing_path:
                    existing = WikiManager.read_page(cid, existing_path)
                    old_body = existing["body"] if existing else ""
                    new_body = old_body + "\n\n## 补充（来源: " + filename + "）\n\n" + body
                    fm = existing["frontmatter"] if existing else {}
                    fm["source"] = (fm.get("source", "") + ", " + filename).strip(", ")
                    WikiManager.write_page(
                        cid, existing_path,
                        _make_content(fm, new_body),
                        summary=f"更新自 {filename}",
                    )
                    pages_updated += 1
                else:
                    page_filename = section_clean[:60]
                    import re as _re
                    safe = _re.sub(r'[<>:"/\\|?*]', '', page_filename).strip()
                    if not safe:
                        safe = "untitled"
                    rel_path = f"concepts/{safe}.md"
                    WikiManager.write_page(
                        cid, rel_path,
                        _make_content(
                            {"title": section_clean, "source": filename},
                            body,
                        ),
                        summary=section_clean[:80],
                    )
                    pages_created += 1

                if pages_created + pages_updated >= 100:
                    break

        except Exception as e:
            errors.append(f"{filename}: {str(e)[:80]}")

        if pages_created + pages_updated >= 100:
            break

    summary_parts = [f"百科构建完成：新建 {pages_created} 个页面，更新 {pages_updated} 个页面。"]
    if errors:
        summary_parts.append(f"错误 ({len(errors)}): " + "; ".join(errors[:5]))
    if pages_created + pages_updated > 0:
        summary_parts.append(
            f"你可以用 wiki_read_index 查看目录，用 wiki_recall 查询具体概念。"
        )

    return "\n".join(summary_parts)


@tool
def wiki_recall(query: str, course_id: str = "", max_depth: int = 3) -> str:
    """从课程百科中查询知识。先从 index.md 找到入口，再沿 [[链接]] 导航相关页面，
    返回完整的上下文信息。区别于 knowledge_search 的语义碎片检索，
    wiki_recall 提供结构化、可导航的完整知识页面。

    适用于：总结某章节、理解概念关系、获取知识点完整上下文。

    Args:
        query: 查询关键词或自然语言描述
        course_id: 课程ID（可选）
        max_depth: 链接追踪深度，默认3层。1=只返回匹配页面，2=含直接引用页面，3=含间接引用
    """
    cid = _resolve_course_id(course_id)
    if not cid:
        return "未指定课程ID。"

    WikiManager.init_wiki(cid)

    # Step 1: 搜索匹配的页面
    results = WikiManager.search_pages(cid, query, max_results=10)
    if not results:
        # 也尝试从 index 中查找
        index_content = WikiManager.read_index(cid)
        if query.lower() in index_content.lower():
            return (
                f"百科索引中找到相关条目，但页面详情未加载。\n\n"
                f"## 索引中匹配的内容\n{index_content[:2000]}\n\n"
                f"请使用 wiki_read_index 查看完整目录。"
            )
        return (
            f"百科中未找到与「{query}」相关的页面。\n"
            f"可能原因：1. 百科尚未构建，请先调用 wiki_ingest；"
            f"2. 该概念在课件中未被自动提取，可调用 wiki_write 手动创建。"
        )

    # Step 2: BFS 追踪链接
    visited = set()
    collected = []

    # 首先加入匹配页面
    queue = []
    for r in results:
        path = r["path"]
        if path not in visited:
            visited.add(path)
            page = WikiManager.read_page(cid, path)
            if page:
                collected.append(page)
                links = WikiManager.extract_links(page["body"])
                for link_title in links:
                    resolved = WikiManager.resolve_link(cid, link_title)
                    if resolved:
                        queue.append(resolved)

    # BFS 最多 max_depth-1 层（因为匹配页面是第1层）
    for _ in range(max_depth - 1):
        if not queue:
            break
        next_queue = []
        for path in queue:
            if path in visited:
                continue
            visited.add(path)
            page = WikiManager.read_page(cid, path)
            if page:
                collected.append(page)
                links = WikiManager.extract_links(page["body"])
                for link_title in links:
                    resolved = WikiManager.resolve_link(cid, link_title)
                    if resolved:
                        next_queue.append(resolved)
        queue = next_queue

    if not collected:
        return f"未能读取匹配页面内容。请确认百科已正确构建。"

    # Step 3: 格式化输出
    parts = [f"百科查询结果（'{query}'，共 {len(collected)} 个相关页面）：\n"]
    for i, page in enumerate(collected):
        title = page["frontmatter"].get("title", os.path.basename(page["path"]))
        source = page["frontmatter"].get("source", "未知来源")
        body = page["body"]
        if len(body) > 1500:
            body = body[:1500] + "\n\n... (内容较长，已截断。使用 wiki_recall 指定更具体的关键词获取完整内容)"
        parts.append(
            f"### [{i + 1}] {title}\n"
            f"来源: {source}\n"
            f"页面: {page['path']}\n\n"
            f"{body}\n"
        )

    return "\n---\n\n".join(parts)


@tool
def wiki_write(page_path: str, content: str, course_id: str = "",
               summary: str = "") -> str:
    """创建或更新百科页面。页面会自动加入 index.md 目录。
    页面内容应使用 Markdown 格式，可包含 [[页面名]] 交叉链接。
    适合手动补充或修正知识点内容。

    Args:
        page_path: 页面相对路径，如 "concepts/矩阵乘法.md" 或 "queries/常见问题.md"
        content: 页面完整 Markdown 内容，建议包含 YAML frontmatter
        course_id: 课程ID（可选）
        summary: 单行摘要，用于 index.md 目录
    """
    cid = _resolve_course_id(course_id)
    if not cid:
        return "未指定课程ID。"

    WikiManager.init_wiki(cid)

    # 清理路径
    page_path = page_path.strip()
    if not page_path.endswith(".md"):
        page_path += ".md"

    try:
        result = WikiManager.write_page(cid, page_path, content, summary=summary)
        return (
            f"页面已{result['status']}: {result['path']}\n"
            f"反向链接更新: {result['backlinks_updated']} 处\n"
            f"你可以用 wiki_read_index 查看更新后的目录。"
        )
    except ValueError as e:
        return f"写入失败: {e}"
    except Exception as e:
        logger.error(f"wiki_write 异常: {e}")
        return f"写入失败: {e}"


@tool
def wiki_lint(course_id: str = "") -> str:
    """百科健康检查。检测：断链（指向不存在页面的链接）、
    孤立页面（没有被任何页面引用的页面）、frontmatter 格式问题。

    Args:
        course_id: 课程ID（可选）
    """
    cid = _resolve_course_id(course_id)
    if not cid:
        return "未指定课程ID。"

    WikiManager.init_wiki(cid)

    broken = WikiManager.check_broken_links(cid)
    orphans = WikiManager.find_orphan_pages(cid)
    fm_issues = WikiManager.check_frontmatter(cid)
    total = len(WikiManager.list_pages(cid))

    parts = [f"百科健康检查（共 {total} 个页面）：\n"]

    if broken:
        parts.append(f"## 断链 ({len(broken)} 处)")
        by_source = {}
        for b in broken:
            by_source.setdefault(b["source"], []).append(b["target"])
        for src, targets in list(by_source.items())[:10]:
            parts.append(f"- {src} → 断链目标: {', '.join(targets[:5])}")
        if len(by_source) > 10:
            parts.append(f"  ... 还有 {len(by_source) - 10} 个页面有断链")
        parts.append("")
    else:
        parts.append("断链: 无 ✓")

    if orphans:
        parts.append(f"## 孤立页面 ({len(orphans)} 个)")
        for o in orphans[:15]:
            parts.append(f"- {o}")
        if len(orphans) > 15:
            parts.append(f"  ... 还有 {len(orphans) - 15} 个孤立页面")
        parts.append("")
    else:
        parts.append("孤立页面: 无 ✓")

    if fm_issues:
        parts.append(f"## Frontmatter 问题 ({len(fm_issues)} 处)")
        for fi in fm_issues[:10]:
            parts.append(f"- {fi}")
        parts.append("")
    else:
        parts.append("Frontmatter: 全部正常 ✓")

    parts.append(f"\n整体健康度: {'优秀' if not broken and not orphans else '需修复'}")

    return "\n".join(parts)


@tool
def wiki_search(query: str, course_id: str = "") -> str:
    """在百科所有页面中进行全文关键词搜索。返回匹配页面和上下文片段。
    相比 wiki_recall，本工具更轻量，适合快速查找特定关键词的位置。

    Args:
        query: 搜索关键词
        course_id: 课程ID（可选）
    """
    cid = _resolve_course_id(course_id)
    if not cid:
        return "未指定课程ID。"

    WikiManager.init_wiki(cid)
    results = WikiManager.search_pages(cid, query, max_results=15)

    if not results:
        return f"百科中未找到包含「{query}」的页面。"

    parts = [f"搜索「{query}」- 共 {len(results)} 条结果：\n"]
    for i, r in enumerate(results):
        title = r.get("title", os.path.basename(r["path"]))
        parts.append(
            f"[{i + 1}] **{title}** ({r['path']})\n"
            f"> {r['snippet']}\n"
        )

    return "\n".join(parts)


@tool
def wiki_read_index(course_id: str = "") -> str:
    """读取百科主目录索引，了解百科包含哪些概念和问题页面。
    这是浏览百科的首要入口。返回完整的 index.md 内容，
    包含 [[链接]] 格式的目录。

    Args:
        course_id: 课程ID（可选）
    """
    cid = _resolve_course_id(course_id)
    if not cid:
        return "未指定课程ID。"

    WikiManager.init_wiki(cid)
    content = WikiManager.read_index(cid)

    pages = WikiManager.list_pages(cid)
    if not pages:
        return (
            f"{content}\n\n---\n"
            f"百科当前无页面。请先使用 wiki_ingest 从课件构建百科。"
        )

    return content


import os as _os

wiki_toolkit = [
    wiki_ingest,
    wiki_recall,
    wiki_write,
    wiki_lint,
    wiki_search,
    wiki_read_index,
]

__all__ = ["wiki_toolkit", "wiki_ingest", "wiki_recall", "wiki_write",
           "wiki_lint", "wiki_search", "wiki_read_index"]


def _make_content(frontmatter: dict, body: str) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    fm = {"created": now, "updated": now}
    fm.update(frontmatter)
    lines = [f"{k}: {v}" for k, v in fm.items() if v]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body

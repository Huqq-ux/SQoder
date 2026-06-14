import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from Coder.knowledge.wiki_manager import WikiManager
from Coder.server.schemas import (
    WikiPageResponse, WikiPageSummary, WikiSearchRequest,
    WikiIngestResponse, WikiLintResult, WikiLintEntry,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_course(identifier: str) -> Optional[dict]:
    from Coder.storage.course_manager import CourseManager
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    return course


@router.get("/{course_id}/pages")
async def list_pages(request: Request, course_id: str):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    cid = course["id"]
    pages = WikiManager.list_pages(cid)
    return {"pages": pages, "course_id": cid}


@router.get("/{course_id}/pages/{path:path}")
async def get_page(request: Request, course_id: str, path: str):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    cid = course["id"]
    page = WikiManager.read_page(cid, path)
    if page is None:
        raise HTTPException(status_code=404, detail=f"页面不存在: {path}")
    backlinks = WikiManager.get_backlinks(cid, path)
    return WikiPageResponse(
        path=page["path"],
        frontmatter=page["frontmatter"],
        body=page["body"],
        backlinks=backlinks,
    )


@router.get("/{course_id}/index")
async def get_index(request: Request, course_id: str):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    content = WikiManager.read_index(course["id"])
    return {"content": content}


@router.get("/{course_id}/schema")
async def get_schema(request: Request, course_id: str):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    content = WikiManager.get_schema(course["id"])
    return {"content": content}


@router.get("/{course_id}/log")
async def get_log(request: Request, course_id: str, n: int = Query(default=100, ge=10, le=500)):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    entries = WikiManager.read_log(course["id"], lines=n)
    return {"entries": entries}


@router.post("/{course_id}/search")
async def search_pages(request: Request, course_id: str, body: WikiSearchRequest):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    results = WikiManager.search_pages(course["id"], body.query)
    return {"results": results}


@router.post("/{course_id}/ingest")
async def ingest_wiki(request: Request, course_id: str):
    """从课程知识库文档自动构建 Wiki 页面。"""
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    cid = course["id"]

    # 初始化 wiki 目录
    WikiManager.init_wiki(cid)

    # 获取课程文件列表
    from Coder.storage.course_manager import CourseManager
    files = await CourseManager.list_files(cid)
    if not files:
        files = await CourseManager.list_global_files()
        if not files:
            return WikiIngestResponse(
                status="no_files",
                errors=["该课程没有已上传的课件。请先在知识库中上传课件文件。"],
            )

    pages_created = 0
    pages_updated = 0
    errors = []

    for f in files:
        filename = f.get("filename", "")
        try:
            # 读取文档内容
            from Coder.knowledge.document_loader import DocumentLoader
            import os
            docs_dir = os.path.normpath(os.path.join(
                os.path.dirname(__file__), "..", "..", "knowledge", "docs"
            ))
            file_path = os.path.normpath(os.path.join(docs_dir, filename))
            if not os.path.isfile(file_path):
                errors.append(f"文件不存在: {filename}")
                continue

            loader = DocumentLoader()
            doc = loader.load(file_path)
            content = doc.get("content", "")
            if not content or not content.strip():
                errors.append(f"文件内容为空: {filename}")
                continue

            # 按章节拆分
            from Coder.knowledge.chapter_splitter import ChapterSplitter
            splitter = ChapterSplitter()
            chunks = splitter.split_text(content, source_file=filename)
            # 为每个章节创建/更新概念页面
            for chunk in chunks:
                section = chunk.metadata.get("section", "").strip()
                if not section:
                    continue
                sections_seen.add(section)
                # 清理标题
                section_clean = section.lstrip("#").strip()
                if not section_clean:
                    continue

                # 检查是否已有此概念的页面
                existing_path = WikiManager.resolve_link(cid, section_clean)
                if existing_path:
                    # 更新已有页面（追加内容）
                    existing = WikiManager.read_page(cid, existing_path)
                    new_body = (existing["body"] + "\n\n---\n\n## 补充（来源: " +
                                filename + "）\n\n" + chunk.page_content) if existing else chunk.page_content
                    WikiManager.write_page(
                        cid, existing_path, body_to_content(
                            existing["frontmatter"] if existing else {},
                            new_body, section_clean, filename
                        ),
                        summary=f"更新自 {filename}",
                    )
                    pages_updated += 1
                else:
                    # 新建页面
                    page_filename = _safe_filename(section_clean)
                    rel_path = f"concepts/{page_filename}"
                    WikiManager.write_page(
                        cid, rel_path, body_to_content(
                            {"title": section_clean, "source": filename},
                            chunk.page_content, section_clean, filename
                        ),
                        summary=section_clean,
                    )
                    pages_created += 1

                # 限制 ingest 规模，防止超长处理
                if pages_created + pages_updated >= 100:
                    break

        except Exception as e:
            logger.error(f"Ingest 文件失败 {filename}: {e}")
            errors.append(f"{filename}: {str(e)[:100]}")

    return WikiIngestResponse(
        status="completed",
        pages_created=pages_created,
        pages_updated=pages_updated,
        errors=errors,
    )


@router.post("/{course_id}/lint")
async def lint_wiki(request: Request, course_id: str):
    course = await _resolve_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    cid = course["id"]

    WikiManager.init_wiki(cid)

    broken_links = WikiManager.check_broken_links(cid)
    orphans = WikiManager.find_orphan_pages(cid)
    fm_issues = WikiManager.check_frontmatter(cid)
    total_pages = len(WikiManager.list_pages(cid))

    if not broken_links and not orphans and not fm_issues:
        health = "good"
    elif len(broken_links) > 5 or len(orphans) > 3:
        health = "error"
    else:
        health = "warning"

    return WikiLintResult(
        broken_links=[WikiLintEntry(source=e["source"], target=e["target"]) for e in broken_links],
        orphans=orphans,
        frontmatter_issues=fm_issues,
        total_pages=total_pages,
        health=health,
    )


def _safe_filename(name: str) -> str:
    import re
    safe = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    if not safe:
        safe = "untitled"
    return safe + ".md"


def body_to_content(frontmatter: dict, body: str, title: str, source: str) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    fm = {
        "title": title,
        "source": source,
        "tags": "",
        "created": frontmatter.get("created", now),
        "updated": now,
    }
    fm.update({k: v for k, v in frontmatter.items() if k not in fm})
    lines = [f"{k}: {v}" for k, v in fm.items() if v]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body

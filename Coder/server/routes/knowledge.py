import os
import logging
import re
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from Coder.server.schemas import KnowledgeSearchRequest

logger = logging.getLogger(__name__)
router = APIRouter()

_SAFE_FILENAME_RE = re.compile(r'^[\w\-\.]+$')
_ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".epub"}

_INDEX_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "index")


def _get_course_store(course_id: str):
    """Get a VectorStore for a specific course."""
    from Coder.knowledge.vector_store import VectorStore
    store_path = os.path.join(_INDEX_BASE, course_id)
    return VectorStore(store_path=store_path)


def _get_global_store():
    """Get the global (legacy) VectorStore."""
    from Coder.knowledge.vector_store import VectorStore
    return VectorStore()


def _resolve_course(identifier: str) -> dict | None:
    """Resolve a course identifier (slug or UUID) to a course dict."""
    from Coder.storage.course_manager import CourseManager
    import asyncio
    course = asyncio.get_event_loop().run_until_complete(CourseManager.get_course(identifier))
    if not course:
        course = asyncio.get_event_loop().run_until_complete(CourseManager.get_course_by_slug(identifier))
    return course


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    course_id: str = Query(default=""),
):
    """Upload documents. If course_id is provided, index into that course's vector store."""
    docs_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "knowledge", "docs"
    )
    docs_dir = os.path.normpath(docs_dir)
    os.makedirs(docs_dir, exist_ok=True)

    from Coder.knowledge.document_loader import DocumentLoader
    from Coder.knowledge.text_splitter import StructuredTextSplitter
    from Coder.knowledge.vector_store import VectorStore
    from Coder.storage.course_manager import CourseManager

    loader = DocumentLoader()
    splitter = StructuredTextSplitter()

    results = []
    for file in files:
        safe_name = os.path.basename(file.filename or "unknown")
        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in _ALLOWED_SUFFIXES:
            results.append({"filename": safe_name, "chunks": 0, "status": f"unsupported format: {ext}"})
            continue

        content = await file.read()
        filepath = os.path.join(docs_dir, safe_name)
        with open(filepath, "wb") as f:
            f.write(content)

        try:
            doc = loader.load(filepath)
            chunks = splitter.split_documents([doc])

            if course_id:
                # Use course-scoped vector store
                course = _resolve_course(course_id)
                if not course:
                    results.append({"filename": safe_name, "chunks": 0, "status": "课程不存在"})
                    continue
                store = _get_course_store(course["id"])
                store.add_documents(chunks)
                # Register file
                async def _reg():
                    await CourseManager.register_file(
                        course["id"], safe_name, ext, len(content), len(chunks),
                        os.path.join(_INDEX_BASE, course["id"]),
                    )
                import asyncio
                asyncio.get_event_loop().run_until_complete(_reg())
            else:
                # Use global (legacy) vector store
                store = _get_global_store()
                store.add_documents(chunks)

            results.append({"filename": safe_name, "chunks": len(chunks), "status": "imported"})
        except Exception as e:
            logger.error(f"Upload failed for {safe_name}: {e}")
            results.append({"filename": safe_name, "chunks": 0, "status": f"error: {e}"})

    return {"results": results}


@router.post("/search")
async def search_knowledge(req: KnowledgeSearchRequest, course_id: str = Query(default="")):
    from Coder.knowledge.retriever import Retriever
    from Coder.knowledge.vector_store import VectorStore

    if course_id:
        course = _resolve_course(course_id)
        if not course:
            return {"results": [], "available": False}
        store = _get_course_store(course["id"])
    else:
        store = _get_global_store()

    if not store.is_available():
        return {"results": [], "available": False}

    docs = store.similarity_search(req.query, k=req.k)
    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content[:500],
            "metadata": {
                "filename": doc.metadata.get("filename", ""),
                "section": doc.metadata.get("section", ""),
                "relevance_score": doc.metadata.get("relevance_score", 0),
            },
        })
    return {"results": results, "available": True}


@router.get("/documents")
async def list_knowledge_documents(course_id: str = Query(default="")):
    """List uploaded documents, optionally filtered by course."""
    if course_id:
        course = _resolve_course(course_id)
        if not course:
            return {"documents": []}
        from Coder.storage.course_manager import CourseManager
        import asyncio
        docs = asyncio.get_event_loop().run_until_complete(CourseManager.list_files(course["id"]))
        return {"documents": [{
            "id": d["id"],
            "filename": d["filename"],
            "file_type": d["file_type"],
            "size": d["file_size"],
            "chunks": d["chunk_count"],
            "course_slug": course.get("slug", ""),
            "course_name": course.get("name", ""),
            "status": "indexed",
        } for d in docs]}

    # Global: return all files from all courses + global docs
    from Coder.storage.course_manager import CourseManager
    import asyncio
    courses = asyncio.get_event_loop().run_until_complete(CourseManager.list_courses())
    all_docs = []
    for c in courses:
        try:
            docs = asyncio.get_event_loop().run_until_complete(CourseManager.list_files(c["id"]))
            for d in docs:
                all_docs.append({
                    "id": d["id"],
                    "filename": d["filename"],
                    "file_type": d["file_type"],
                    "size": d["file_size"],
                    "chunks": d["chunk_count"],
                    "course_slug": c.get("slug", ""),
                    "course_name": c.get("name", ""),
                    "status": "indexed",
                })
        except Exception:
            pass
    return {"documents": all_docs}


@router.get("/preview-docx")
async def preview_docx(path: str = ""):
    """预览 Word 文档内容。path 为文件名或相对于 workspace 的路径。"""
    import os as _os
    from fastapi import HTTPException

    workspace = _os.path.join(_os.path.dirname(__file__), "..", "..", "workspace")
    workspace = _os.path.normpath(_os.path.abspath(workspace))

    filename = _os.path.basename(path)
    if not filename.endswith(".docx"):
        filename += ".docx"
    filepath = _os.path.normpath(_os.path.join(workspace, filename))

    # 安全校验：必须在 workspace 内
    if not filepath.startswith(workspace):
        raise HTTPException(status_code=403, detail="路径不在 workspace 内")

    if not _os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(filepath)
        content = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name if para.style else ""
            if style.startswith("Heading"):
                content.append({"type": "heading", "text": text, "level": 1 if "1" in style else 2})
            else:
                content.append({"type": "paragraph", "text": text})

        tables = []
        for table in doc.tables:
            rows = []
            for row in table.rows:
                rows.append([cell.text.strip() for cell in row.cells])
            tables.append(rows)

        return {"filename": filename, "content": content, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文档失败: {e}")


def _resolve_docx_path(path: str) -> str:
    """解析 docx 文件的安全路径，返回绝对路径。"""
    import os as _os

    workspace = _os.path.join(_os.path.dirname(__file__), "..", "..", "workspace")
    workspace = _os.path.normpath(_os.path.abspath(workspace))

    filename = _os.path.basename(path)
    if not filename.endswith(".docx"):
        filename += ".docx"
    filepath = _os.path.normpath(_os.path.join(workspace, filename))

    if not filepath.startswith(workspace):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="路径不在 workspace 内")
    return filepath


@router.get("/docx-raw")
async def docx_raw(path: str = ""):
    """返回原始 .docx 文件二进制数据，供前端 mammoth.js 渲染。"""
    import os as _os
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    filepath = _resolve_docx_path(path)
    if not _os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"文件不存在: {_os.path.basename(filepath)}")
    return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.post("/eval")
async def evaluate_rag(query: str = "", k: int = 5):
    """RAG 质量评估端点。评估检索结果的忠实度、相关性、上下文召回率和精度。
    需要 ragas 库：pip install ragas（当前 Windows 环境因依赖编译问题待解决）。
    """
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
        from langchain_core.documents import Document

        from Coder.tools.knowledge_toolkit import _get_retriever
        retriever = _get_retriever()
        if not retriever or not retriever.is_available():
            return {"status": "unavailable", "message": "知识库未初始化"}

        docs = retriever.retrieve(query, k=k)

        return {
            "status": "ok",
            "query": query,
            "retrieved_count": len(docs),
            "message": "RAGAS 评估就绪。完整评估需提供 ground_truth 参照。",
        }
    except ImportError:
        return {
            "status": "not_configured",
            "message": "ragas 库未安装（依赖 scikit-network 需 MSVC 编译）。安装后可使用 faithfulness/answer_relevancy/context_recall/context_precision 四项指标评估。",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

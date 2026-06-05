import os
import logging
import re
from fastapi import APIRouter, UploadFile, File
from Coder.server.schemas import KnowledgeSearchRequest

logger = logging.getLogger(__name__)
router = APIRouter()

_SAFE_FILENAME_RE = re.compile(r'^[\w\-\.]+$')
_ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    docs_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "knowledge", "docs"
    )
    docs_dir = os.path.normpath(docs_dir)
    os.makedirs(docs_dir, exist_ok=True)

    from Coder.knowledge.document_loader import DocumentLoader
    from Coder.knowledge.text_splitter import StructuredTextSplitter
    from Coder.knowledge.vector_store import VectorStore

    loader = DocumentLoader()
    splitter = StructuredTextSplitter()
    vector_store = VectorStore()

    results = []
    for file in files:
        safe_name = os.path.basename(file.filename or "unknown")
        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in _ALLOWED_SUFFIXES:
            results.append({
                "filename": safe_name,
                "chunks": 0,
                "status": f"unsupported format: {ext}",
            })
            continue

        content = await file.read()
        filepath = os.path.join(docs_dir, safe_name)
        with open(filepath, "wb") as f:
            f.write(content)

        try:
            doc = loader.load(filepath)
            chunks = splitter.split_documents([doc])
            vector_store.add_documents(chunks)
            results.append({
                "filename": safe_name,
                "chunks": len(chunks),
                "status": "imported",
            })
        except Exception as e:
            results.append({
                "filename": safe_name,
                "chunks": 0,
                "status": f"error: {e}",
            })

    return {"results": results}


@router.post("/search")
async def search_knowledge(req: KnowledgeSearchRequest):
    from Coder.knowledge.retriever import Retriever
    retriever = Retriever()

    if not retriever.is_available():
        return {"results": [], "available": False}

    docs = retriever.retrieve(req.query, k=req.k)
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

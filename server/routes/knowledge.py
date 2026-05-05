import os
import logging
import re
from fastapi import APIRouter, UploadFile, File, Request
from Coder.server.schemas import KnowledgeSearchRequest

logger = logging.getLogger(__name__)
router = APIRouter()

_SAFE_FILENAME_RE = re.compile(r'^[\w\-\.]+$')
_ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    sop_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "knowledge", "sop_docs"
    )
    sop_dir = os.path.normpath(sop_dir)
    os.makedirs(sop_dir, exist_ok=True)

    from Coder.knowledge.document_loader import DocumentLoader
    from Coder.knowledge.text_splitter import SOPTextSplitter
    from Coder.knowledge.vector_store import VectorStore

    loader = DocumentLoader()
    splitter = SOPTextSplitter()
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
        filepath = os.path.join(sop_dir, safe_name)
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


@router.get("/status")
async def knowledge_status():
    from Coder.knowledge.retriever import Retriever
    retriever = Retriever()
    return {"available": retriever.is_available()}

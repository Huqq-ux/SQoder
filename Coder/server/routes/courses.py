import logging
import uuid as _uuid
from fastapi import APIRouter, HTTPException, Query

from Coder.storage.course_manager import CourseManager
from Coder.storage.db import DatabaseManager
from Coder.server.schemas import (
    CourseCreate, CourseUpdate,
    NoteCreate, WrongAnswerCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/courses", response_model=dict)
async def create_course(body: CourseCreate):
    course_id = await CourseManager.create_course(
        name=body.name,
        description=body.description,
        semester=body.semester,
    )
    course = await CourseManager.get_course(course_id)
    return {"status": "created", "course_id": course_id, "slug": course["slug"] if course else ""}


@router.get("/courses")
async def list_courses(limit: int = 50):
    courses = await CourseManager.list_courses(limit=limit)
    return {"courses": courses}


@router.get("/courses/{identifier}")
async def get_course(identifier: str):
    # Try slug first, then UUID
    course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        course = await CourseManager.get_course(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"course": course}


@router.put("/courses/{identifier}")
async def update_course(identifier: str, body: CourseUpdate):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    await CourseManager.update_course(
        course["id"],
        name=body.name,
        description=body.description,
        semester=body.semester,
    )
    return {"status": "updated"}


@router.delete("/courses/{identifier}")
async def delete_course(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    await CourseManager.delete_course(course["id"])
    return {"status": "deleted"}


@router.get("/courses/{identifier}/knowledge-points")
async def list_knowledge_points(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    points = await CourseManager.get_knowledge_points(course["id"])
    return {"knowledge_points": points}


@router.get("/courses/{identifier}/files")
async def list_course_files(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    files = await CourseManager.list_files(course["id"])
    return {"files": files}


@router.get("/courses/{identifier}/progress")
async def get_learning_progress(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    progress = await CourseManager.get_progress(course["id"])
    return progress


@router.post("/courses/{identifier}/progress")
async def update_learning_progress(identifier: str, body: dict):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    await CourseManager.update_progress(
        course["id"],
        kp_id=body.get("kp_id", ""),
        status=body.get("status", "learning"),
        mastery_score=body.get("mastery_score", 0.0),
    )
    return {"status": "updated"}


@router.get("/courses/{identifier}/notes")
async def list_notes(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    notes = await CourseManager.list_notes(course["id"])
    return {"notes": notes}


@router.post("/courses/{identifier}/notes")
async def create_note(identifier: str, body: NoteCreate):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    note_id = await CourseManager.create_note(
        course["id"],
        title=body.title,
        content=body.content,
        kp_id=body.kp_id,
    )
    return {"status": "created", "note_id": note_id}


@router.get("/courses/{identifier}/wrong-answers")
async def list_wrong_answers(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    answers = await CourseManager.list_wrong_answers(course["id"])
    return {"wrong_answers": answers}


@router.post("/courses/{identifier}/wrong-answers")
async def add_wrong_answer(identifier: str, body: WrongAnswerCreate):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    answer_id = await CourseManager.add_wrong_answer(
        course["id"],
        question=body.question,
        user_answer=body.user_answer,
        correct_answer=body.correct_answer,
        kp_id=body.kp_id,
    )
    return {"status": "created", "answer_id": answer_id}


@router.get("/courses/{identifier}/knowledge-graph")
async def get_knowledge_graph(
    identifier: str,
    source_file: str = Query(default=""),
):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    from Coder.storage.course_manager import CourseManager as CM
    points = await CM.get_knowledge_points(course["id"])

    # Collect unique source files for the tab bar
    sources = sorted({p["source_file"] for p in points if p.get("source_file")})

    # Filter by source file
    if source_file:
        points = [p for p in points if p.get("source_file") == source_file]

    # Get mastery status for all points
    if points:
        kp_uuids = [_uuid.UUID(p["id"]) for p in points]
        placeholders = ",".join(["%s"] * len(kp_uuids))
        progress_rows = await DatabaseManager.fetch(
            f"SELECT kp_id, status FROM learning_progress WHERE kp_id IN ({placeholders})",
            *kp_uuids,
        )
        mastery_map = {str(r["kp_id"]): r["status"] for r in progress_rows}
    else:
        mastery_map = {}

    nodes = [
        {
            "id": p["id"],
            "name": p["name"],
            "section": p["section"],
            "source_file": p.get("source_file", ""),
            "mastery": mastery_map.get(p["id"], "unlearned"),
        }
        for p in points
    ]

    # Edges: semantic similarity via embeddings
    edges = _build_semantic_edges(points)

    return {"nodes": nodes, "edges": edges, "sources": sources}


def _get_embedding_model():
    """Lazy-load the shared embedding model (bge-small-zh-v1.5)."""
    import os as _os
    from langchain_huggingface import HuggingFaceEmbeddings

    local_dir = _os.path.normpath(
        _os.path.join(_os.path.dirname(__file__), "..", "..", "..",
                      ".cache", "bge-small-zh-v1.5")
    )
    if _os.path.isdir(local_dir):
        return HuggingFaceEmbeddings(model_name=local_dir)
    return HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")


def _cosine_similarity(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_semantic_edges(points: list[dict], top_k: int = 3,
                          min_similarity: float = 0.40,
                          max_edges_per_node: int = 5) -> list[dict]:
    """Connect each knowledge point to its top-K most similar neighbors.

    Uses cosine similarity on embedding vectors.  Falls back to sequential
    edges within sections if the embedding model is unavailable.
    """
    n = len(points)
    if n < 2:
        return []

    names = [p["name"] for p in points]
    ids = [p["id"] for p in points]

    try:
        model = _get_embedding_model()
        vectors = model.embed_documents(names)
    except Exception:
        edges = []
        for i in range(n - 1):
            edges.append({"source": points[i]["id"], "target": points[i + 1]["id"], "type": "related"})
        return edges

    # For each node, find its top-K most similar neighbors
    node_degree: dict[int, int] = {i: 0 for i in range(n)}
    edges: list[dict] = []

    for i in range(n):
        sims: list[tuple[float, int]] = []
        for j in range(n):
            if i == j:
                continue
            sims.append((_cosine_similarity(vectors[i], vectors[j]), j))
        sims.sort(key=lambda x: x[0], reverse=True)

        added = 0
        for sim, j in sims:
            if added >= top_k or sim < min_similarity:
                break
            if node_degree[i] >= max_edges_per_node or node_degree[j] >= max_edges_per_node:
                continue
            # Avoid duplicate (i,j) or (j,i)
            if j < i:
                continue
            edges.append({"source": ids[i], "target": ids[j], "type": "semantic"})
            node_degree[i] += 1
            node_degree[j] += 1
            added += 1

    return edges

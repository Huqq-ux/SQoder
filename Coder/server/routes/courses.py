import logging
from fastapi import APIRouter, HTTPException

from Coder.storage.course_manager import CourseManager
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


@router.delete("/courses/by-index/{index}")
async def delete_course_by_index(index: int):
    """Delete a course by its position in the list (1-based, for courses with empty slugs)"""
    courses = await CourseManager.list_courses()
    if index < 1 or index > len(courses):
        raise HTTPException(status_code=404, detail="课程不存在")
    await CourseManager.delete_course(courses[index - 1]["id"])
    return {"status": "deleted"}


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
async def get_knowledge_graph(identifier: str):
    course = await CourseManager.get_course(identifier)
    if not course:
        course = await CourseManager.get_course_by_slug(identifier)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    from Coder.storage.course_manager import CourseManager as CM
    points = await CM.get_knowledge_points(course["id"])

    nodes = [{"id": p["id"], "name": p["name"], "section": p["section"]} for p in points]

    # Edges: co-occurrence within same section + sequential
    edges = []
    by_section: dict[str, list] = {}
    for p in points:
        by_section.setdefault(p["section"] or "通用", []).append(p)

    for section_pts in by_section.values():
        for i in range(len(section_pts)):
            for j in range(i + 1, min(i + 3, len(section_pts))):
                edges.append({
                    "source": section_pts[i]["id"],
                    "target": section_pts[j]["id"],
                    "type": "related",
                })

    return {"nodes": nodes, "edges": edges}

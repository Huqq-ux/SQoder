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
    return {"status": "created", "course_id": course_id}


@router.get("/courses")
async def list_courses(limit: int = 50):
    courses = await CourseManager.list_courses(limit=limit)
    return {"courses": courses}


@router.get("/courses/{course_id}")
async def get_course(course_id: str):
    course = await CourseManager.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"course": course}


@router.put("/courses/{course_id}")
async def update_course(course_id: str, body: CourseUpdate):
    await CourseManager.update_course(
        course_id,
        name=body.name,
        description=body.description,
        semester=body.semester,
    )
    return {"status": "updated"}


@router.delete("/courses/{course_id}")
async def delete_course(course_id: str):
    await CourseManager.delete_course(course_id)
    return {"status": "deleted"}


@router.get("/courses/{course_id}/knowledge-points")
async def list_knowledge_points(course_id: str):
    points = await CourseManager.get_knowledge_points(course_id)
    return {"knowledge_points": points}


@router.get("/courses/{course_id}/files")
async def list_course_files(course_id: str):
    files = await CourseManager.list_files(course_id)
    return {"files": files}


@router.get("/courses/{course_id}/progress")
async def get_learning_progress(course_id: str):
    return {"course_id": course_id, "progress": [], "overall_mastery": 0.0}

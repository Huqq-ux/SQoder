import logging
from typing import Optional

from Coder.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class CourseManager:

    @classmethod
    async def create_course(cls, name: str, description: str = "",
                            semester: str = "") -> str:
        row = await DatabaseManager.fetchrow(
            """INSERT INTO courses (name, description, semester)
               VALUES (%s, %s, %s)
               RETURNING id""",
            name, description, semester,
        )
        course_id = str(row["id"])
        logger.info(f"课程已创建: {name} ({course_id})")
        return course_id

    @classmethod
    async def get_course(cls, course_id: str) -> Optional[dict]:
        row = await DatabaseManager.fetchrow(
            "SELECT * FROM courses WHERE id = %s", course_id
        )
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"] or "",
            "semester": row["semester"] or "",
            "created_at": str(row["created_at"]) if row.get("created_at") else "",
            "updated_at": str(row["updated_at"]) if row.get("updated_at") else "",
        }

    @classmethod
    async def list_courses(cls, limit: int = 50) -> list[dict]:
        rows = await DatabaseManager.fetch(
            "SELECT * FROM courses ORDER BY updated_at DESC LIMIT %s", limit
        )
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "description": r["description"] or "",
                "semester": r["semester"] or "",
                "created_at": str(r["created_at"]) if r.get("created_at") else "",
                "updated_at": str(r["updated_at"]) if r.get("updated_at") else "",
            }
            for r in rows
        ]

    @classmethod
    async def update_course(cls, course_id: str, name: str = None,
                            description: str = None, semester: str = None):
        fields = []
        params = []
        if name is not None:
            fields.append("name = %s")
            params.append(name)
        if description is not None:
            fields.append("description = %s")
            params.append(description)
        if semester is not None:
            fields.append("semester = %s")
            params.append(semester)
        if not fields:
            return
        fields.append("updated_at = NOW()")
        params.append(course_id)
        sql = f"UPDATE courses SET {', '.join(fields)} WHERE id = %s"
        await DatabaseManager.execute(sql, *params)

    @classmethod
    async def delete_course(cls, course_id: str):
        await DatabaseManager.execute(
            "DELETE FROM courses WHERE id = %s", course_id
        )
        logger.info(f"课程已删除: {course_id}")

    @classmethod
    async def add_knowledge_point(cls, course_id: str, name: str,
                                  section: str = "", chunk_content: str = "",
                                  source_file: str = "",
                                  source_page: int = 0) -> str:
        row = await DatabaseManager.fetchrow(
            """INSERT INTO knowledge_points
               (course_id, name, section, chunk_content, source_file, source_page)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            course_id, name, section, chunk_content, source_file, source_page,
        )
        return str(row["id"])

    @classmethod
    async def get_knowledge_points(cls, course_id: str) -> list[dict]:
        rows = await DatabaseManager.fetch(
            "SELECT * FROM knowledge_points WHERE course_id = %s ORDER BY section, name",
            course_id,
        )
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "section": r["section"] or "",
                "chunk_content": r["chunk_content"] or "",
                "source_file": r["source_file"] or "",
                "source_page": r["source_page"] or 0,
            }
            for r in rows
        ]

    @classmethod
    async def register_file(cls, course_id: str, filename: str,
                            file_type: str, file_size: int = 0,
                            chunk_count: int = 0,
                            index_path: str = "") -> str:
        row = await DatabaseManager.fetchrow(
            """INSERT INTO course_files
               (course_id, filename, file_type, file_size, chunk_count, index_path)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            course_id, filename, file_type, file_size, chunk_count, index_path,
        )
        return str(row["id"])

    @classmethod
    async def list_files(cls, course_id: str) -> list[dict]:
        rows = await DatabaseManager.fetch(
            "SELECT * FROM course_files WHERE course_id = %s ORDER BY uploaded_at DESC",
            course_id,
        )
        return [
            {
                "id": str(r["id"]),
                "filename": r["filename"],
                "file_type": r["file_type"],
                "file_size": r["file_size"],
                "chunk_count": r["chunk_count"],
                "index_path": r["index_path"],
                "uploaded_at": str(r["uploaded_at"]) if r.get("uploaded_at") else "",
            }
            for r in rows
        ]

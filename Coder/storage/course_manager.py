import re
import logging
from typing import Optional

from Coder.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


def _make_slug(name: str) -> str:
    import hashlib
    slug = re.sub(r'[^a-z0-9-]', '', name.lower().strip())
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    if slug:
        return slug[:64]
    return "course-" + hashlib.md5(name.encode()).hexdigest()[:8]


class CourseManager:

    @classmethod
    async def create_course(cls, name: str, description: str = "",
                            semester: str = "") -> str:
        base_slug = _make_slug(name)
        slug = base_slug
        n = 1
        while True:
            existing = await DatabaseManager.fetchrow(
                "SELECT id FROM courses WHERE slug = %s", slug
            )
            if existing is None:
                break
            n += 1
            slug = f"{base_slug}-{n}"

        row = await DatabaseManager.fetchrow(
            """INSERT INTO courses (slug, name, description, semester)
               VALUES (%s, %s, %s, %s)
               RETURNING id, slug""",
            slug, name, description, semester,
        )
        course_id = str(row["id"])
        logger.info(f"课程已创建: {name} ({course_id}, slug={slug})")
        return course_id

    @classmethod
    def _row_to_dict(cls, row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "slug": row.get("slug", ""),
            "name": row["name"],
            "description": row["description"] or "",
            "semester": row["semester"] or "",
            "created_at": str(row["created_at"]) if row.get("created_at") else "",
            "updated_at": str(row["updated_at"]) if row.get("updated_at") else "",
        }

    @classmethod
    async def get_course(cls, course_id: str) -> Optional[dict]:
        import uuid
        try:
            uuid.UUID(course_id)
        except (ValueError, AttributeError):
            return None
        row = await DatabaseManager.fetchrow(
            "SELECT * FROM courses WHERE id = %s", course_id
        )
        if row is None:
            return None
        return cls._row_to_dict(row)

    @classmethod
    async def get_course_by_slug(cls, slug: str) -> Optional[dict]:
        row = await DatabaseManager.fetchrow(
            "SELECT * FROM courses WHERE slug = %s", slug
        )
        if row is None:
            return None
        return cls._row_to_dict(row)

    @classmethod
    async def list_courses(cls, limit: int = 50) -> list[dict]:
        rows = await DatabaseManager.fetch(
            "SELECT * FROM courses ORDER BY updated_at DESC LIMIT %s", limit
        )
        return [cls._row_to_dict(r) for r in rows]

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

    # ── Learning Progress ──

    @classmethod
    async def update_progress(cls, course_id: str, kp_id: str,
                              status: str = "learning",
                              mastery_score: float = 0.0):
        await DatabaseManager.execute(
            """INSERT INTO learning_progress (course_id, kp_id, status,
               mastery_score, interaction_count, last_reviewed, updated_at)
               VALUES (%s, %s, %s, %s, 1, NOW(), NOW())
               ON CONFLICT (course_id, kp_id) DO UPDATE SET
               status = EXCLUDED.status,
               mastery_score = GREATEST(learning_progress.mastery_score, EXCLUDED.mastery_score),
               interaction_count = learning_progress.interaction_count + 1,
               last_reviewed = NOW(),
               updated_at = NOW()""",
            course_id, kp_id, status, mastery_score,
        )

    @classmethod
    async def get_progress(cls, course_id: str) -> dict:
        rows = await DatabaseManager.fetch(
            """SELECT lp.*, kp.name as kp_name, kp.section
               FROM learning_progress lp
               JOIN knowledge_points kp ON lp.kp_id = kp.id
               WHERE lp.course_id = %s
               ORDER BY lp.updated_at DESC""",
            course_id,
        )
        total_kp = await DatabaseManager.fetchrow(
            "SELECT COUNT(*) as cnt FROM knowledge_points WHERE course_id = %s",
            course_id,
        )
        total = total_kp["cnt"] if total_kp else 0

        items = [
            {
                "kp_id": str(r["kp_id"]),
                "kp_name": r.get("kp_name", ""),
                "section": r.get("section", ""),
                "status": r["status"],
                "mastery_score": float(r["mastery_score"]),
                "interaction_count": r["interaction_count"],
            }
            for r in rows
        ]

        mastered = sum(1 for i in items if i["status"] == "mastered")
        overall = (mastered / total * 100) if total > 0 else 0.0

        return {
            "course_id": course_id,
            "total_points": total,
            "tracked_points": len(items),
            "mastered_points": mastered,
            "overall_mastery": round(overall, 1),
            "items": items,
        }

    # ── Notes ──

    @classmethod
    async def create_note(cls, course_id: str, title: str, content: str,
                          kp_id: str = None) -> str:
        row = await DatabaseManager.fetchrow(
            """INSERT INTO notes (course_id, kp_id, title, content)
               VALUES (%s, %s, %s, %s)
               RETURNING id""",
            course_id, kp_id, title, content,
        )
        return str(row["id"])

    @classmethod
    async def list_notes(cls, course_id: str) -> list[dict]:
        rows = await DatabaseManager.fetch(
            "SELECT * FROM notes WHERE course_id = %s ORDER BY created_at DESC",
            course_id,
        )
        return [
            {
                "id": str(r["id"]),
                "title": r["title"] or "",
                "content": r["content"] or "",
                "created_at": str(r["created_at"]) if r.get("created_at") else "",
            }
            for r in rows
        ]

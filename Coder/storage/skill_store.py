import re
import logging
from datetime import datetime
from typing import Optional, List

from psycopg.types.json import Jsonb

from Coder.storage.db import DatabaseManager
from Coder.tools.skill_store import SkillDefinition, SkillMeta

logger = logging.getLogger(__name__)

_SKILL_NAME_RE = re.compile(r'^[a-zA-Z_][\w\-]*$')


class PgSkillStore:
    async def save_skill(self, skill: SkillDefinition) -> bool:
        name = skill.name
        if not _SKILL_NAME_RE.match(name):
            logger.warning(f"无效的技能名称: {name}")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not skill.created_at:
            skill.created_at = now
        skill.updated_at = now

        await DatabaseManager.execute(
            "INSERT INTO skills (name, display_name, description, category, "
            "parameters, tags, code, version, author, source, enabled, "
            "created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (name) DO UPDATE SET "
            "display_name=%s, description=%s, category=%s, parameters=%s, "
            "tags=%s, code=%s, version=%s, author=%s, source=%s, enabled=%s, "
            "updated_at=%s",
            skill.name,
            skill.display_name,
            skill.description,
            skill.category,
            Jsonb(skill.parameters),
            Jsonb(skill.tags),
            skill.code,
            skill.version,
            skill.author,
            skill.source,
            skill.enabled,
            skill.created_at,
            skill.updated_at,
            skill.display_name,
            skill.description,
            skill.category,
            Jsonb(skill.parameters),
            Jsonb(skill.tags),
            skill.code,
            skill.version,
            skill.author,
            skill.source,
            skill.enabled,
            skill.updated_at,
        )
        logger.info(f"技能已保存: {name}")
        return True

    async def load_skill(self, name: str) -> Optional[SkillDefinition]:
        if not _SKILL_NAME_RE.match(name):
            return None

        row = await DatabaseManager.fetchrow(
            "SELECT * FROM skills WHERE name = %s", name
        )

        if not row:
            return None

        return SkillDefinition(
            name=row["name"],
            display_name=row["display_name"],
            description=row["description"],
            category=row["category"],
            parameters=row["parameters"] or [],
            tags=row["tags"] or [],
            code=row["code"],
            version=row["version"],
            author=row["author"],
            source=row["source"],
            enabled=row["enabled"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def load_skill_meta(self, name: str) -> Optional[SkillMeta]:
        skill = await self.load_skill(name)
        if skill is None:
            return None
        return skill.to_meta()

    async def list_skills_meta(
        self,
        category: str = None,
        enabled_only: bool = True
    ) -> List[SkillMeta]:
        sql, args = self._build_list_query(category, enabled_only)
        rows = await DatabaseManager.fetch(sql, *args)

        return [
            SkillMeta(
                name=row["name"],
                display_name=row["display_name"],
                description=row["description"],
                category=row["category"],
                parameters=row["parameters"] or [],
                tags=row["tags"] or [],
                version=row["version"],
                source=row["source"],
                enabled=row["enabled"],
                author=row["author"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def list_skills(
        self,
        category: str = None,
        enabled_only: bool = True
    ) -> List[SkillDefinition]:
        sql, args = self._build_list_query(category, enabled_only)
        rows = await DatabaseManager.fetch(sql, *args)

        return [
            SkillDefinition(
                name=row["name"],
                display_name=row["display_name"],
                description=row["description"],
                category=row["category"],
                parameters=row["parameters"] or [],
                tags=row["tags"] or [],
                code=row["code"],
                version=row["version"],
                author=row["author"],
                source=row["source"],
                enabled=row["enabled"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def _build_list_query(self, category: str, enabled_only: bool):
        conditions = []
        args = []

        if enabled_only:
            conditions.append("enabled = TRUE")
        if category:
            conditions.append("category = %s")
            args.append(category)

        sql = "SELECT * FROM skills"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY category, display_name"
        return sql, args

    async def delete_skill(self, name: str) -> bool:
        result = await DatabaseManager.execute(
            "DELETE FROM skills WHERE name = %s", name
        )
        deleted = result != "DELETE 0"
        if deleted:
            logger.info(f"技能已删除: {name}")
        return deleted

    async def toggle_skill(self, name: str, enabled: bool) -> bool:
        result = await DatabaseManager.execute(
            "UPDATE skills SET enabled = %s WHERE name = %s",
            enabled, name,
        )
        updated = result != "UPDATE 0"
        if updated:
            logger.info(f"技能状态已更新: {name} -> enabled={enabled}")
        return updated

    async def exists(self, name: str) -> bool:
        row = await DatabaseManager.fetchrow(
            "SELECT 1 FROM skills WHERE name = %s", name
        )
        return row is not None

    async def get_categories(self) -> List[str]:
        rows = await DatabaseManager.fetch(
            "SELECT DISTINCT category FROM skills ORDER BY category"
        )
        return [row["category"] for row in rows]

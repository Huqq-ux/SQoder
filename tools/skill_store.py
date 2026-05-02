import os
import json
import logging
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

_SKILL_NAME_RE = None


def _get_skill_name_re():
    global _SKILL_NAME_RE
    if _SKILL_NAME_RE is None:
        import re
        _SKILL_NAME_RE = re.compile(r'^[a-zA-Z_][\w\-]*$')
    return _SKILL_NAME_RE


@dataclass
class SkillMeta:
    name: str
    display_name: str
    description: str
    category: str
    parameters: List[dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    source: str = "user"
    enabled: bool = True
    author: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class SkillDefinition:
    name: str
    display_name: str
    description: str
    category: str
    parameters: List[dict] = field(default_factory=list)
    code: str = ""
    enabled: bool = True
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_meta(self) -> SkillMeta:
        return SkillMeta(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            category=self.category,
            parameters=self.parameters,
            tags=self.tags,
            version=self.version,
            source="user",
            enabled=self.enabled,
            author=self.author,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "SkillDefinition":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        for list_field in ("parameters", "tags"):
            if list_field in filtered and not isinstance(filtered[list_field], list):
                filtered[list_field] = []
        filtered.setdefault("parameters", [])
        filtered.setdefault("tags", [])
        return cls(**filtered)


class SkillStore:

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(__file__), "..", "skills"
            )
            base_path = os.path.normpath(base_path)
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save_skill(self, skill: SkillDefinition) -> bool:
        name = skill.name
        if not _get_skill_name_re().match(name):
            logger.warning(f"无效的技能名称: {name}")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not skill.created_at:
            skill.created_at = now
        skill.updated_at = now

        path = os.path.join(self.base_path, f"{name}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"技能已保存: {name}")
            return True
        except OSError as e:
            logger.error(f"保存技能失败 {name}: {e}")
            return False

    def load_skill(self, name: str) -> Optional[SkillDefinition]:
        if not _get_skill_name_re().match(name):
            return None
        path = os.path.join(self.base_path, f"{name}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SkillDefinition.from_dict(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"加载技能失败 {name}: {e}")
            return None

    def load_skill_meta(self, name: str) -> Optional[SkillMeta]:
        if not _get_skill_name_re().match(name):
            return None
        path = os.path.join(self.base_path, f"{name}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SkillMeta(
                name=data.get("name", name),
                display_name=data.get("display_name", name),
                description=data.get("description", ""),
                category=data.get("category", ""),
                parameters=data.get("parameters", []),
                tags=data.get("tags", []),
                version=data.get("version", "1.0.0"),
                source="user",
                enabled=data.get("enabled", True),
                author=data.get("author", ""),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"加载技能元数据失败 {name}: {e}")
            return None

    def list_skills_meta(
        self,
        category: str = None,
        enabled_only: bool = True
    ) -> List[SkillMeta]:
        metas = []
        if not os.path.exists(self.base_path):
            return metas

        for filename in os.listdir(self.base_path):
            if not filename.endswith(".json"):
                continue
            name = filename[:-5]
            meta = self.load_skill_meta(name)
            if meta is None:
                continue
            if enabled_only and not meta.enabled:
                continue
            if category and meta.category != category:
                continue
            metas.append(meta)

        metas.sort(key=lambda s: (s.category, s.display_name))
        return metas

    def list_skills(
        self,
        category: str = None,
        enabled_only: bool = True
    ) -> List[SkillDefinition]:
        skills = []
        if not os.path.exists(self.base_path):
            return skills

        for filename in os.listdir(self.base_path):
            if not filename.endswith(".json"):
                continue
            name = filename[:-5]
            skill = self.load_skill(name)
            if skill is None:
                continue
            if enabled_only and not skill.enabled:
                continue
            if category and skill.category != category:
                continue
            skills.append(skill)

        skills.sort(key=lambda s: (s.category, s.display_name))
        return skills

    def delete_skill(self, name: str) -> bool:
        path = os.path.join(self.base_path, f"{name}.json")
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            logger.info(f"技能已删除: {name}")
            return True
        except OSError as e:
            logger.error(f"删除技能失败 {name}: {e}")
            return False

    def toggle_skill(self, name: str, enabled: bool) -> bool:
        skill = self.load_skill(name)
        if skill is None:
            return False
        skill.enabled = enabled
        return self.save_skill(skill)

    def exists(self, name: str) -> bool:
        return os.path.exists(os.path.join(self.base_path, f"{name}.json"))

    def get_categories(self) -> List[str]:
        cats = set()
        for skill in self.list_skills(enabled_only=False):
            cats.add(skill.category)
        return sorted(cats)

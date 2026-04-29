import re
import logging
from typing import Optional
from Coder.tools.skill_store import SkillDefinition

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r'^##\s+(.+)$', re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r'```(\w*)\s*\n(.+?)\s*```', re.DOTALL)
_TITLE_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)
_PARAM_HEADER_RE = re.compile(
    r'^\|\s*参数名\s*\|\s*类型\s*\|'
)
_PARAM_ROW_RE = re.compile(
    r'^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(是|否)\s*\|\s*(.+?)\s*\|$'
)
_TAG_RE = re.compile(r'`([^`]+)`')


class SkillParser:

    @staticmethod
    def parse_markdown(content: str) -> Optional[SkillDefinition]:
        if not content or not content.strip():
            logger.warning("技能文档内容为空")
            return None

        title = SkillParser._extract_title(content)
        if not title:
            logger.warning("技能文档缺少标题")
            return None

        sections = SkillParser._extract_sections(content)

        description = sections.get("描述", sections.get("说明", ""))
        category = sections.get("分类", "其他")
        code = SkillParser._extract_code(content)
        params = SkillParser._extract_params(content)
        tags = SkillParser._extract_tags(sections.get("标签", ""))

        name = SkillParser._generate_name(title)

        return SkillDefinition(
            name=name,
            display_name=title,
            description=description.strip(),
            category=category.strip(),
            parameters=params,
            code=code,
            tags=tags,
        )

    @staticmethod
    def parse_json(data: dict) -> Optional[SkillDefinition]:
        required = ["name", "display_name"]
        for field in required:
            if field not in data:
                logger.warning(f"技能JSON缺少必要字段: {field}")
                return None

        return SkillDefinition.from_dict(data)

    @staticmethod
    def parse(content: str, fmt: str = "auto") -> Optional[SkillDefinition]:
        if fmt == "json":
            import json
            try:
                return SkillParser.parse_json(json.loads(content))
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                return None

        return SkillParser.parse_markdown(content)

    @staticmethod
    def _extract_title(content: str) -> str:
        match = _TITLE_RE.search(content)
        if match:
            return match.group(1).strip()
        first_line = content.strip().split("\n")[0].strip()
        return first_line.lstrip("#").strip() if first_line else ""

    @staticmethod
    def _extract_sections(content: str) -> dict:
        sections = {}
        matches = list(_SECTION_RE.finditer(content))
        for i, match in enumerate(matches):
            header = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()
            sections[header] = body
        return sections

    @staticmethod
    def _extract_code(content: str) -> str:
        matches = _CODE_BLOCK_RE.findall(content)
        for lang, code in matches:
            if lang.lower() in ("python", "py", ""):
                return code.strip()
        if matches:
            return matches[0][1].strip()
        return ""

    @staticmethod
    def _extract_params(content: str) -> list:
        params = []
        in_table = False
        for line in content.split("\n"):
            line = line.strip()
            if _PARAM_HEADER_RE.match(line):
                in_table = True
                continue
            if in_table:
                match = _PARAM_ROW_RE.match(line)
                if match:
                    params.append({
                        "name": match.group(1).strip(),
                        "type": match.group(2).strip(),
                        "required": match.group(3).strip() == "是",
                        "description": match.group(4).strip(),
                    })
                elif not line.startswith("|"):
                    in_table = False
        return params

    @staticmethod
    def _extract_tags(tag_section: str) -> list:
        if not tag_section:
            return []
        tags = _TAG_RE.findall(tag_section)
        if not tags:
            tags = [
                t.strip()
                for t in tag_section.replace(",", " ").split()
                if t.strip()
            ]
        return list(dict.fromkeys(tags))

    @staticmethod
    def _generate_name(display_name: str) -> str:
        name = display_name.strip().lower()
        name = re.sub(r'[\s\-]+', '_', name)
        name = re.sub(r'[^\w]', '', name)
        if not name:
            name = "unnamed_skill"
        if name[0].isdigit():
            name = "skill_" + name
        return name

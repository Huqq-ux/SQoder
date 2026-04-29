import logging
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field

from Coder.tools.skill_store import SkillStore, SkillDefinition
from Coder.tools.skill_compiler import SkillCompiler, SkillCompileError

logger = logging.getLogger(__name__)


@dataclass
class RegisteredSkill:
    name: str
    display_name: str
    description: str
    category: str
    func: Callable
    parameters: List[dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    source: str = "user"


class SkillRegistry:
    _instance: Optional["SkillRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: Dict[str, RegisteredSkill] = {}
            cls._instance._store = SkillStore()
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, auto_load: bool = True):
        if self._initialized:
            return
        self._register_builtin_skills()
        if auto_load:
            self._load_user_skills()
        self._initialized = True
        logger.info(
            f"SkillRegistry 初始化完成: "
            f"{len(self._skills)} 个技能已注册"
        )

    def register(self, skill: RegisteredSkill):
        self._skills[skill.name] = skill
        logger.info(f"技能已注册: {skill.name}")

    def unregister(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            logger.info(f"技能已注销: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[RegisteredSkill]:
        return self._skills.get(name)

    def get_by_category(self, category: str) -> List[RegisteredSkill]:
        return [
            s for s in self._skills.values()
            if s.category == category
        ]

    def list_all(self) -> List[RegisteredSkill]:
        return sorted(
            self._skills.values(),
            key=lambda s: (s.category, s.display_name)
        )

    def get_categories(self) -> List[str]:
        return sorted(set(
            s.category for s in self._skills.values()
        ))

    def search(self, query: str) -> List[RegisteredSkill]:
        query_lower = query.lower()
        query_tokens = self._tokenize(query_lower)

        results = []
        for skill in self._skills.values():
            score = 0

            if query_lower in skill.name.lower():
                score += 10
            if query_lower in skill.display_name.lower():
                score += 8
            if query_lower in skill.description.lower():
                score += 3

            name_tokens = self._tokenize(skill.display_name.lower())
            desc_tokens = self._tokenize(skill.description.lower())

            for qt in query_tokens:
                if len(qt) < 2:
                    continue
                if any(qt in nt for nt in name_tokens):
                    score += 4
                if any(qt in dt for dt in desc_tokens):
                    score += 2
                for tag in skill.tags:
                    if qt in tag.lower():
                        score += 3

            if score > 0:
                results.append((score, skill))

        results.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in results]

    @staticmethod
    def _tokenize(text: str) -> list:
        tokens = []
        current = ""
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(ch)
            elif ch.isalnum() or ch in "_-":
                current += ch
            else:
                if current:
                    tokens.append(current)
                    current = ""
        if current:
            tokens.append(current)

        bigrams = []
        for i in range(len(tokens) - 1):
            if (
                '\u4e00' <= tokens[i] <= '\u9fff'
                and '\u4e00' <= tokens[i + 1] <= '\u9fff'
            ):
                bigrams.append(tokens[i] + tokens[i + 1])

        all_tokens = tokens + bigrams
        if not all_tokens:
            all_tokens = [text]
        return all_tokens

    def match_for_step(
        self,
        step_name: str,
        step_description: str,
        min_score: int = 1
    ) -> List[RegisteredSkill]:
        combined = f"{step_name} {step_description}"
        results = self.search(combined)
        if results:
            return results
        return self.search(combined)[:3]

    def load_skill_from_store(self, name: str) -> Optional[RegisteredSkill]:
        if name in self._skills:
            return self._skills[name]

        skill_def = self._store.load_skill(name)
        if skill_def is None:
            return None

        return self._compile_and_register(skill_def)

    def reload_skill(self, name: str) -> Optional[RegisteredSkill]:
        self._skills.pop(name, None)
        return self.load_skill_from_store(name)

    def reload_all(self) -> int:
        self._skills = {
            k: v for k, v in self._skills.items()
            if v.source == "builtin"
        }
        return self._load_user_skills()

    def _compile_and_register(
        self, skill_def: SkillDefinition
    ) -> Optional[RegisteredSkill]:
        try:
            func = SkillCompiler.compile(skill_def)
            if func is None:
                return None
        except SkillCompileError as e:
            logger.warning(f"编译技能失败 {skill_def.name}: {e}")
            return None

        registered = RegisteredSkill(
            name=skill_def.name,
            display_name=skill_def.display_name,
            description=skill_def.description,
            category=skill_def.category,
            func=func,
            parameters=skill_def.parameters,
            tags=skill_def.tags,
            version=skill_def.version,
            source="user",
        )
        self._skills[skill_def.name] = registered
        logger.info(f"用户技能已加载: {skill_def.name}")
        return registered

    def _load_user_skills(self) -> int:
        loaded = 0
        for skill_def in self._store.list_skills(enabled_only=True):
            if skill_def.name in self._skills:
                continue
            if self._compile_and_register(skill_def):
                loaded += 1
        return loaded

    def _register_builtin_skills(self):
        builtins = self._collect_builtin_skills()

        for name, info in builtins.items():
            self._skills[name] = RegisteredSkill(
                name=name,
                display_name=info.get("display_name", name),
                description=info.get("description", ""),
                category=info.get("category", "builtin"),
                func=info["func"],
                parameters=info.get("parameters", []),
                tags=info.get("tags", []),
                source="builtin",
            )

    def _collect_builtin_skills(self) -> dict:
        skills = {}

        try:
            from Coder.tools.knowledge_toolkit import (
                list_directory,
                search_knowledge,
                add_to_knowledge,
                get_knowledge_content,
            )
            skills.update({
                "knowledge_search": {
                    "display_name": "知识库搜索",
                    "description": "在知识库中语义搜索文档",
                    "category": "知识库",
                    "func": search_knowledge,
                    "parameters": [
                        {
                            "name": "query",
                            "type": "str",
                            "required": True,
                            "description": "搜索查询"
                        },
                        {
                            "name": "top_k",
                            "type": "int",
                            "required": False,
                            "description": "返回结果数量"
                        },
                    ],
                    "tags": ["搜索", "检索", "查询", "知识库"],
                },
                "knowledge_list": {
                    "display_name": "知识库目录",
                    "description": "列出知识库中的文件",
                    "category": "知识库",
                    "func": list_directory,
                    "parameters": [],
                    "tags": ["列表", "目录", "文件"],
                },
                "knowledge_add": {
                    "display_name": "添加到知识库",
                    "description": "将内容添加到知识库",
                    "category": "知识库",
                    "func": add_to_knowledge,
                    "parameters": [
                        {
                            "name": "filename",
                            "type": "str",
                            "required": True,
                            "description": "文件名"
                        },
                        {
                            "name": "content",
                            "type": "str",
                            "required": True,
                            "description": "文件内容"
                        },
                    ],
                    "tags": ["添加", "上传", "知识库"],
                },
                "knowledge_content": {
                    "display_name": "获取知识内容",
                    "description": "获取知识库文件的完整内容",
                    "category": "知识库",
                    "func": get_knowledge_content,
                    "parameters": [
                        {
                            "name": "filename",
                            "type": "str",
                            "required": True,
                            "description": "文件名"
                        },
                    ],
                    "tags": ["内容", "读取", "查看"],
                },
            })
        except ImportError as e:
            logger.debug(f"知识库技能注册跳过: {e}")

        try:
            from Coder.tools.file_tools import read_file, write_file, list_files
            skills.update({
                "file_read": {
                    "display_name": "读取文件",
                    "description": "读取指定文件的内容",
                    "category": "文件操作",
                    "func": read_file,
                    "parameters": [
                        {
                            "name": "path",
                            "type": "str",
                            "required": True,
                            "description": "文件路径"
                        },
                    ],
                    "tags": ["文件", "读取", "查看"],
                },
                "file_write": {
                    "display_name": "写入文件",
                    "description": "将内容写入文件",
                    "category": "文件操作",
                    "func": write_file,
                    "parameters": [
                        {
                            "name": "path",
                            "type": "str",
                            "required": True,
                            "description": "文件路径"
                        },
                        {
                            "name": "content",
                            "type": "str",
                            "required": True,
                            "description": "写入内容"
                        },
                    ],
                    "tags": ["文件", "写入", "保存"],
                },
                "file_list": {
                    "display_name": "列出文件",
                    "description": "列出目录中的文件",
                    "category": "文件操作",
                    "func": list_files,
                    "parameters": [
                        {
                            "name": "path",
                            "type": "str",
                            "required": False,
                            "description": "目录路径"
                        },
                    ],
                    "tags": ["文件", "目录", "列表"],
                },
            })
        except ImportError as e:
            logger.debug(f"文件操作技能注册跳过: {e}")

        try:
            from Coder.tools.web_search_toolkit import (
                web_search,
                search_weather,
                search_news,
                fetch_page,
            )
            skills.update({
                "web_search": {
                    "display_name": "网页搜索",
                    "description": "在互联网上搜索信息",
                    "category": "搜索",
                    "func": web_search,
                    "parameters": [
                        {
                            "name": "query",
                            "type": "str",
                            "required": True,
                            "description": "搜索查询"
                        },
                    ],
                    "tags": ["搜索", "网页", "联网"],
                },
                "weather_search": {
                    "display_name": "天气搜索",
                    "description": "搜索指定地点的天气信息",
                    "category": "搜索",
                    "func": search_weather,
                    "parameters": [
                        {
                            "name": "location",
                            "type": "str",
                            "required": True,
                            "description": "地点名称"
                        },
                    ],
                    "tags": ["天气", "搜索"],
                },
                "news_search": {
                    "display_name": "新闻搜索",
                    "description": "搜索最新新闻",
                    "category": "搜索",
                    "func": search_news,
                    "parameters": [
                        {
                            "name": "query",
                            "type": "str",
                            "required": True,
                            "description": "新闻关键词"
                        },
                    ],
                    "tags": ["新闻", "搜索", "资讯"],
                },
                "fetch_page": {
                    "display_name": "获取网页",
                    "description": "获取指定网页的内容",
                    "category": "搜索",
                    "func": fetch_page,
                    "parameters": [
                        {
                            "name": "url",
                            "type": "str",
                            "required": True,
                            "description": "网页URL"
                        },
                    ],
                    "tags": ["网页", "抓取", "内容"],
                },
            })
        except ImportError as e:
            logger.debug(f"搜索技能注册跳过: {e}")

        return skills

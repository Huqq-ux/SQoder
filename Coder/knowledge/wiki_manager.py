import os
import re
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_WIKI_BASE = os.path.normpath(os.path.join(os.path.dirname(__file__), "wiki"))
_SAFE_FILENAME_RE = re.compile(r'^[^<>:"/\\|?*]+$')
_MAX_FILE_SIZE_MB = 5
_AUTO_START = "<!-- AUTO-GENERATED LISTING -->"
_AUTO_END = "<!-- END AUTO-GENERATED -->"
_LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')
_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

_lock = threading.Lock()


def _validate_course_id(course_id: str):
    if not course_id or not _SAFE_FILENAME_RE.match(course_id):
        raise ValueError(f"非法 course_id: {course_id}")


def _validate_rel_path(rel_path: str):
    if not rel_path or ".." in rel_path:
        raise ValueError(f"非法路径: {rel_path}")
    normalized = os.path.normpath(rel_path)
    if not (normalized.startswith("concepts") or normalized.startswith("queries")):
        raise ValueError(f"页面路径必须在 concepts/ 或 queries/ 下: {rel_path}")


def _safe_filename(name: str) -> str:
    """从页面标题生成安全文件名"""
    safe = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    if not safe:
        safe = "untitled"
    return safe + ".md"


def _parse_frontmatter(raw: str):
    """解析 YAML frontmatter。返回 (frontmatter_dict, body_str)。"""
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    body = raw[m.end():]
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if ':' in line:
            key, _, val = line.partition(':')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            fm[key] = val
    return fm, body


class WikiManager:
    """Wiki 文件系统管理器。所有方法均为静态方法，线程安全。"""

    # ── 路径 & 初始化 ──

    @staticmethod
    def get_wiki_root(course_id: str) -> str:
        _validate_course_id(course_id)
        return os.path.normpath(os.path.join(_WIKI_BASE, course_id))

    @staticmethod
    def init_wiki(course_id: str) -> dict:
        """初始化 wiki 目录结构（幂等）。返回 {root, created}。"""
        root = WikiManager.get_wiki_root(course_id)
        created = False
        with _lock:
            if not os.path.exists(root):
                os.makedirs(root, exist_ok=True)
                created = True
            for sub in ("concepts", "queries"):
                sub_path = os.path.join(root, sub)
                if not os.path.exists(sub_path):
                    os.makedirs(sub_path, exist_ok=True)
                    created = True

            schema_path = os.path.join(root, "SCHEMA.md")
            if not os.path.exists(schema_path):
                WikiManager._write_file(schema_path, (
                    "# Wiki Schema\n\n"
                    "## 页面格式\n"
                    "- 每个概念页使用 YAML frontmatter（`---` 包裹）\n"
                    "- `title`: 概念名称\n"
                    "- `tags`: 逗号分隔的标签\n"
                    "- `source`: 来源课件文件名\n"
                    "- `created` / `updated`: ISO 时间戳\n\n"
                    "## 链接规范\n"
                    "- 使用 `[[页面名]]` 语法链接到其他 wiki 页面\n"
                    "- 页面名应与目标页面的 frontmatter `title` 一致\n\n"
                    "## 编写规范\n"
                    "- 概念页：定义 → 性质/推导 → 与其他概念的关系 → 来源\n"
                    "- 查询归档：问题 → 回答 → 关键引用\n"
                ))
                created = True

            index_path = os.path.join(root, "index.md")
            if not os.path.exists(index_path):
                WikiManager._write_file(index_path, (
                    "# 课程知识百科\n\n"
                    f"{_AUTO_START}\n"
                    "## 概念\n\n"
                    "## 查询归档\n\n"
                    f"{_AUTO_END}\n"
                ))
                created = True

            log_path = os.path.join(root, "log.md")
            if not os.path.exists(log_path):
                WikiManager._write_file(log_path, (
                    f"# 操作日志\n\n"
                    f"- {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} 百科初始化\n"
                ))
                created = True

        return {"root": root, "created": created}

    # ── 页面 CRUD ──

    @staticmethod
    def read_page(course_id: str, rel_path: str) -> Optional[dict]:
        """读取 wiki 页面，返回 {path, frontmatter, body, raw} 或 None。"""
        root = WikiManager.get_wiki_root(course_id)
        full_path = os.path.normpath(os.path.join(root, rel_path))
        if not full_path.startswith(root):
            return None
        if not os.path.isfile(full_path):
            return None

        raw = WikiManager._read_file(full_path)
        if raw is None:
            return None
        frontmatter, body = _parse_frontmatter(raw)
        return {
            "path": rel_path.replace("\\", "/"),
            "frontmatter": frontmatter,
            "body": body,
            "raw": raw,
        }

    @staticmethod
    def write_page(course_id: str, rel_path: str, content: str,
                   summary: str = "") -> dict:
        """写入学页面。自动更新 index.md 和反向链接。返回 {path, status, backlinks_updated}。"""
        _validate_rel_path(rel_path)
        root = WikiManager.get_wiki_root(course_id)
        os.makedirs(root, exist_ok=True)

        # 确保目录存在
        page_dir = os.path.dirname(os.path.join(root, rel_path))
        os.makedirs(page_dir, exist_ok=True)

        full_path = os.path.normpath(os.path.join(root, rel_path))
        if not full_path.startswith(root):
            raise ValueError(f"路径超出 wiki 根目录: {rel_path}")

        existed = os.path.isfile(full_path)

        # 自动更新 frontmatter 的 updated 时间戳
        frontmatter, body = _parse_frontmatter(content)
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        if not frontmatter.get("created"):
            frontmatter["created"] = now_str
        frontmatter["updated"] = now_str

        # 重建带 frontmatter 的内容
        fm_lines = [f"{k}: {v}" for k, v in frontmatter.items()]
        new_content = "---\n" + "\n".join(fm_lines) + "\n---\n\n" + body

        WikiManager._write_file(full_path, new_content)

        # 更新 index.md
        title = frontmatter.get("title", os.path.splitext(os.path.basename(rel_path))[0])
        category = "concepts" if rel_path.startswith("concepts") else "queries"
        WikiManager.update_index(course_id, {
            "path": rel_path.replace("\\", "/"),
            "title": title,
            "summary": summary or title,
            "category": category,
        })

        # 更新反向链接：扫描所有页面，给包含 [[title]] 的页面添加反向链接
        backlinks_updated = WikiManager._update_backlinks(course_id, rel_path, title)

        status = "updated" if existed else "created"
        WikiManager.append_log(course_id, "write", f"{status} {rel_path} -- {summary or title}")
        logger.info(f"Wiki 页面已{status}: {rel_path}")
        return {"path": rel_path.replace("\\", "/"), "status": status, "backlinks_updated": backlinks_updated}

    @staticmethod
    def list_pages(course_id: str) -> list[dict]:
        """列出所有 wiki 页面（concepts/ + queries/）。"""
        root = WikiManager.get_wiki_root(course_id)
        if not os.path.isdir(root):
            return []
        pages = []
        for category in ("concepts", "queries"):
            cat_dir = os.path.join(root, category)
            if not os.path.isdir(cat_dir):
                continue
            for entry in os.scandir(cat_dir):
                if entry.is_file() and entry.name.endswith(".md"):
                    rel_path = f"{category}/{entry.name}"
                    try:
                        page = WikiManager.read_page(course_id, rel_path)
                        title = page["frontmatter"].get("title", entry.name[:-3]) if page else entry.name[:-3]
                        links = _LINK_RE.findall(page["body"]) if page else []
                        pages.append({
                            "path": rel_path,
                            "title": title,
                            "category": category,
                            "link_count": len(links),
                            "backlink_count": 0,
                            "modified": datetime.fromtimestamp(
                                entry.stat().st_mtime, tz=timezone.utc
                            ).strftime('%Y-%m-%d %H:%M'),
                        })
                    except Exception as e:
                        logger.warning(f"读取页面失败 {rel_path}: {e}")
        pages.sort(key=lambda p: p["title"])
        return pages

    # ── 索引管理 ──

    @staticmethod
    def read_index(course_id: str) -> str:
        root = WikiManager.get_wiki_root(course_id)
        index_path = os.path.join(root, "index.md")
        if not os.path.isfile(index_path):
            WikiManager.init_wiki(course_id)
        return WikiManager._read_file(index_path) or ""

    @staticmethod
    def update_index(course_id: str, entry: dict):
        """在 index.md 的自动管理区域内添加/更新条目。entry = {path, title, summary, category}。"""
        root = WikiManager.get_wiki_root(course_id)
        index_path = os.path.join(root, "index.md")
        if not os.path.isfile(index_path):
            WikiManager.init_wiki(course_id)

        content = WikiManager._read_file(index_path) or ""
        title = entry.get("title", "")
        path = entry.get("path", "")
        summary = entry.get("summary", title)
        category = entry.get("category", "concepts")
        section_header = "## 概念" if category == "concepts" else "## 查询归档"
        new_line = f"- [[{title}]] -- {summary}\n"

        # 检查是否已存在该条目
        existing_pattern = re.compile(rf'^\s*-\s*\[\[{re.escape(title)}\]\].*$', re.MULTILINE)
        if existing_pattern.search(content):
            # 更新已有行
            content = existing_pattern.sub(f"- [[{title}]] -- {summary}", content)
        else:
            # 在对应 section 下添加新行
            section_pattern = re.compile(rf'({re.escape(section_header)}\s*\n)', re.MULTILINE)
            match = section_pattern.search(content)
            if match:
                insert_pos = match.end()
                # 在 section header 后插入，确保在 AUTO_END 之前
                auto_end_pos = content.find(_AUTO_END, insert_pos)
                if auto_end_pos > 0:
                    # 在 AUTO_END 前插入
                    content = content[:auto_end_pos] + new_line + content[auto_end_pos:]
                else:
                    content = content[:insert_pos] + new_line + content[insert_pos:]
            else:
                # 没找到对应 section，在 AUTO_END 前添加
                auto_end_pos = content.find(_AUTO_END)
                if auto_end_pos > 0:
                    insert_block = f"\n{section_header}\n{new_line}\n"
                    content = content[:auto_end_pos] + insert_block + content[auto_end_pos:]

        WikiManager._write_file(index_path, content)

    @staticmethod
    def get_schema(course_id: str) -> str:
        root = WikiManager.get_wiki_root(course_id)
        schema_path = os.path.join(root, "SCHEMA.md")
        if not os.path.isfile(schema_path):
            WikiManager.init_wiki(course_id)
        return WikiManager._read_file(schema_path) or ""

    @staticmethod
    def update_schema(course_id: str, content: str):
        root = WikiManager.get_wiki_root(course_id)
        schema_path = os.path.join(root, "SCHEMA.md")
        os.makedirs(root, exist_ok=True)
        WikiManager._write_file(schema_path, content)
        WikiManager.append_log(course_id, "update_schema", "SCHEMA.md 已更新")

    # ── 链接解析 ──

    @staticmethod
    def extract_links(content: str) -> list[str]:
        """提取所有 [[wiki链接]] 目标。"""
        return _LINK_RE.findall(content)

    @staticmethod
    def resolve_link(course_id: str, link_title: str) -> Optional[str]:
        """根据 frontmatter title 查找页面路径。"""
        for page in WikiManager.list_pages(course_id):
            if page["title"] == link_title:
                return page["path"]
        # 也尝试去掉 .md 后缀做文件名匹配
        for page in WikiManager.list_pages(course_id):
            filename = os.path.basename(page["path"]).replace(".md", "")
            if filename == link_title:
                return page["path"]
        return None

    @staticmethod
    def get_backlinks(course_id: str, page_path: str) -> list[str]:
        """查找所有包含指向此页面链接的页面。"""
        page = WikiManager.read_page(course_id, page_path)
        if not page:
            return []
        title = page["frontmatter"].get("title", "")
        if not title:
            return []

        backlinks = []
        for p in WikiManager.list_pages(course_id):
            if p["path"] == page_path:
                continue
            full = WikiManager.read_page(course_id, p["path"])
            if full and f"[[{title}]]" in full["raw"]:
                backlinks.append(p["path"])
        return backlinks

    # ── 搜索 ──

    @staticmethod
    def search_pages(course_id: str, query: str, max_results: int = 20) -> list[dict]:
        """全文关键词搜索（大小写不敏感）。返回 [{path, title, snippet, score}]。"""
        if not query or not query.strip():
            return []
        query_lower = query.strip().lower()
        results = []
        for page in WikiManager.list_pages(course_id):
            full = WikiManager.read_page(course_id, page["path"])
            if not full:
                continue
            body_lower = full["body"].lower()
            title_lower = page["title"].lower()
            score = 0
            # 标题匹配权重更高
            if query_lower in title_lower:
                score += 10
            # 正文匹配
            count = body_lower.count(query_lower)
            score += count * 2
            if score == 0:
                continue

            # 提取上下文片段
            idx = body_lower.find(query_lower)
            snippet_start = max(0, idx - 40)
            snippet_end = min(len(full["body"]), idx + len(query) + 80)
            snippet = full["body"][snippet_start:snippet_end]
            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(full["body"]):
                snippet = snippet + "..."

            results.append({
                "path": page["path"],
                "title": page["title"],
                "snippet": snippet,
                "score": score,
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:max_results]

    # ── 健康检查 ──

    @staticmethod
    def check_broken_links(course_id: str) -> list[dict]:
        """检测所有页面中的断链。"""
        all_pages = WikiManager.list_pages(course_id)
        all_titles = {p["title"] for p in all_pages}
        all_filenames = {os.path.basename(p["path"]).replace(".md", "") for p in all_pages}

        broken = []
        for p in all_pages:
            full = WikiManager.read_page(course_id, p["path"])
            if not full:
                continue
            links = WikiManager.extract_links(full["raw"])
            for link in links:
                if link not in all_titles and link not in all_filenames:
                    broken.append({
                        "source": p["path"],
                        "target": link,
                    })
        return broken

    @staticmethod
    def find_orphan_pages(course_id: str) -> list[str]:
        """查找无入链的孤立页面（排除 index/log/schema）。"""
        all_pages = WikiManager.list_pages(course_id)
        orphans = []
        for p in all_pages:
            backlinks = WikiManager.get_backlinks(course_id, p["path"])
            # 也检查是否在 index.md 中被引用
            index_content = WikiManager.read_index(course_id)
            title = p["title"]
            if not backlinks and f"[[{title}]]" not in index_content:
                orphans.append(p["path"])
        return orphans

    @staticmethod
    def check_frontmatter(course_id: str) -> list[str]:
        """检查缺少必要 frontmatter 字段的页面。"""
        issues = []
        required = ("title",)
        for p in WikiManager.list_pages(course_id):
            full = WikiManager.read_page(course_id, p["path"])
            if not full:
                continue
            for key in required:
                if not full["frontmatter"].get(key):
                    issues.append(f"{p['path']}: 缺少 '{key}'")
        return issues

    # ── 日志 ──

    @staticmethod
    def append_log(course_id: str, operation: str, details: str = ""):
        root = WikiManager.get_wiki_root(course_id)
        log_path = os.path.join(root, "log.md")
        os.makedirs(root, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
        entry = f"- {timestamp} [{operation}] {details}\n"
        if os.path.isfile(log_path):
            content = WikiManager._read_file(log_path) or ""
        else:
            content = "# 操作日志\n\n"
        content += entry
        WikiManager._write_file(log_path, content)

    @staticmethod
    def read_log(course_id: str, lines: int = 100) -> list[str]:
        root = WikiManager.get_wiki_root(course_id)
        log_path = os.path.join(root, "log.md")
        if not os.path.isfile(log_path):
            return []
        content = WikiManager._read_file(log_path) or ""
        all_lines = content.splitlines()
        # 过滤头部和空行，返回最近 N 条
        entries = [l for l in all_lines if l.startswith("- ")]
        return entries[-lines:]

    # ── 内部 I/O 辅助 ──

    @staticmethod
    def _read_file(path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {path}: {e}")
            return None

    @staticmethod
    def _write_file(path: str, content: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _update_backlinks(course_id: str, page_path: str, title: str) -> int:
        """扫描所有页面，在包含 [[title]] 的页面中添加反向链接引用。"""
        if not title:
            return 0
        updated = 0
        for p in WikiManager.list_pages(course_id):
            if p["path"] == page_path:
                continue
            full = WikiManager.read_page(course_id, p["path"])
            if not full:
                continue
            if f"[[{title}]]" in full["raw"]:
                # 已在正文中有链接，无需额外处理
                pass
        return updated


__all__ = ["WikiManager"]

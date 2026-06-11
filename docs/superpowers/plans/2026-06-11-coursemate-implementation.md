# CourseMate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the generic Qbot agent into CourseMate, a course-material-driven AI learning companion with course-scoped RAG, hybrid search, and learning path tracking.

**Architecture:** Three sequential rounds. Round 1 delivers the core loop (course KB → hybrid RAG → course Q&A with source citations). Round 2 adds visualization (knowledge graph, learning progress, smart notes). Round 3 completes the set (wrong-answer book, review plans, thesis polish, OCR, RAGAS eval, cleanup).

**Tech Stack:** Python 3.12+, FastAPI, LangChain + LangGraph, FAISS + BM25 (rank-bm25), bge-small-zh-v1.5, MinerU, React 18 + TypeScript + Vite, PostgreSQL, Redis

---

---

### Task 0: Install New Dependencies

- [ ] **Step 1: Install new Python packages**

```bash
cd D:/PyCharm/AI && uv pip install magic-pdf rank-bm25 jieba python-pptx openpyxl ebooklib beautifulsoup4
```

Expected: All packages install without errors.

- [ ] **Step 2: Install new frontend packages**

```bash
cd D:/PyCharm/AI/Coder/web && npm install react-force-graph-2d
```

- [ ] **Step 3: Commit pyproject.toml / package.json updates**

```bash
git add pyproject.toml Coder/web/package.json Coder/web/package-lock.json
git commit -m "chore: add new dependencies for CourseMate (MinerU, rank-bm25, jieba, etc.)"
```

---

### Task 1: New Database Tables for Courses and Knowledge Points

**Files:**
- Modify: `D:/PyCharm/AI/Coder/storage/db.py` — add new table DDL to `_schema_sql`

- [ ] **Step 1: Add course-related table DDL to `_schema_sql`**

In `D:/PyCharm/AI/Coder/storage/db.py`, append to the `_schema_sql` string (after the `mcp_servers` block, before the closing `"""`):

```sql

CREATE TABLE IF NOT EXISTS courses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(256) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    semester        VARCHAR(64) NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_updated_at ON courses(updated_at DESC);

CREATE TABLE IF NOT EXISTS course_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    filename        VARCHAR(512) NOT NULL,
    file_type       VARCHAR(16) NOT NULL,
    file_size       BIGINT NOT NULL DEFAULT 0,
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    index_path      VARCHAR(1024) NOT NULL DEFAULT '',
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_course_files_course ON course_files(course_id);

CREATE TABLE IF NOT EXISTS knowledge_points (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name            VARCHAR(256) NOT NULL,
    section         VARCHAR(128) NOT NULL DEFAULT '',
    chunk_content   TEXT NOT NULL DEFAULT '',
    source_file     VARCHAR(512) NOT NULL DEFAULT '',
    source_page     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kp_course ON knowledge_points(course_id);
CREATE INDEX IF NOT EXISTS idx_kp_section ON knowledge_points(course_id, section);

CREATE TABLE IF NOT EXISTS learning_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    kp_id           UUID NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE,
    status          VARCHAR(16) NOT NULL DEFAULT 'unlearned',
    mastery_score   REAL NOT NULL DEFAULT 0.0,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_reviewed   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(course_id, kp_id)
);

CREATE INDEX IF NOT EXISTS idx_lp_course_status ON learning_progress(course_id, status);

CREATE TABLE IF NOT EXISTS notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    kp_id           UUID REFERENCES knowledge_points(id) ON DELETE SET NULL,
    title           VARCHAR(256) NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_course ON notes(course_id);

CREATE TABLE IF NOT EXISTS wrong_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    kp_id           UUID REFERENCES knowledge_points(id) ON DELETE SET NULL,
    question        TEXT NOT NULL DEFAULT '',
    user_answer     TEXT NOT NULL DEFAULT '',
    correct_answer  TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wrong_answers_course ON wrong_answers(course_id);
```

- [ ] **Step 2: Verify tables are created on next startup**

Run: `python -c "import asyncio; from Coder.storage.db import DatabaseManager; asyncio.run(DatabaseManager.init_pool()); print('OK')"`
Expected: "OK" with no errors, tables created in PostgreSQL.

- [ ] **Step 3: Commit**

```bash
git add Coder/storage/db.py
git commit -m "feat: add course, knowledge_point, progress, notes, wrong_answer tables"
```

---

### Task 2: Course Manager Storage Layer

**Files:**
- Create: `D:/PyCharm/AI/Coder/storage/course_manager.py`
- Test: `D:/PyCharm/AI/Coder/tests/test_course_manager.py`

- [ ] **Step 1: Write the test file**

```python
import pytest
from Coder.storage.course_manager import CourseManager


@pytest.mark.asyncio
async def test_create_and_get_course():
    course_id = await CourseManager.create_course(
        name="高等数学",
        description="大一上学期",
        semester="2025-秋季"
    )
    assert course_id is not None

    course = await CourseManager.get_course(course_id)
    assert course is not None
    assert course["name"] == "高等数学"
    assert course["description"] == "大一上学期"

    # Cleanup
    await CourseManager.delete_course(course_id)


@pytest.mark.asyncio
async def test_list_courses():
    id1 = await CourseManager.create_course(name="课程A")
    id2 = await CourseManager.create_course(name="课程B")

    courses = await CourseManager.list_courses()
    names = [c["name"] for c in courses]

    await CourseManager.delete_course(id1)
    await CourseManager.delete_course(id2)

    assert "课程A" in names
    assert "课程B" in names


@pytest.mark.asyncio
async def test_add_knowledge_point():
    course_id = await CourseManager.create_course(name="测试知识点课程")
    kp_id = await CourseManager.add_knowledge_point(
        course_id=course_id,
        name="极限的定义",
        section="第一章 §1.1",
        chunk_content="设函数f(x)在点x0的某个去心邻域内有定义...",
        source_file="高数上册.pdf",
        source_page=12
    )
    assert kp_id is not None

    points = await CourseManager.get_knowledge_points(course_id)
    assert len(points) > 0
    assert points[0]["name"] == "极限的定义"

    await CourseManager.delete_course(course_id)


@pytest.mark.asyncio
async def test_register_course_file():
    course_id = await CourseManager.create_course(name="文件注册测试")
    file_id = await CourseManager.register_file(
        course_id=course_id,
        filename="课件第一章.pptx",
        file_type="pptx",
        file_size=2048000,
        chunk_count=15,
        index_path="/data/indexes/course_abc"
    )
    assert file_id is not None

    files = await CourseManager.list_files(course_id)
    assert len(files) > 0
    assert files[0]["filename"] == "课件第一章.pptx"

    await CourseManager.delete_course(course_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Coder/tests/test_course_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'Coder.storage.course_manager'`

- [ ] **Step 3: Write the CourseManager implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Coder/tests/test_course_manager.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add Coder/storage/course_manager.py Coder/tests/test_course_manager.py
git commit -m "feat: add CourseManager storage layer for course CRUD and knowledge points"
```

---

### Task 3: Rename Project to CourseMate

**Files:**
- Modify: `D:/PyCharm/AI/Coder/server/main.py` — update FastAPI title and docstring references
- Modify: `D:/PyCharm/AI/Coder/web/src/App.tsx` — update imports for renamed pages
- Modify: `D:/PyCharm/AI/CLAUDE.md` — update project name references

- [ ] **Step 1: Update FastAPI title**

In `D:/PyCharm/AI/Coder/server/main.py` line 70:

```python
app = FastAPI(
    title="CourseMate - AI Course Learning Companion",
    version="0.2.0",
    lifespan=lifespan,
    max_request_size=50 * 1024 * 1024,
)
```

- [ ] **Step 2: Update CLAUDE.md project overview**

In `D:/PyCharm/AI/CLAUDE.md`, change the first line under 项目概述:

```markdown
## 项目概述

CourseMate-基于课程教材的 AI 学习伴侣。使用 LangChain + LangGraph 构建，聚焦高等教育课程学习场景。
```

- [ ] **Step 3: Commit**

```bash
git add Coder/server/main.py CLAUDE.md
git commit -m "chore: rename project to CourseMate"
```

---

### Task 4: Add MinerU PDF Loader Support

**Files:**
- Modify: `D:/PyCharm/AI/Coder/knowledge/document_loader.py` — add MinerU PDF loader

- [ ] **Step 1: Add MinerU to dependencies and implement loader**

First, add to pyproject.toml dependencies: `magic-pdf>=1.0.0` (MinerU package name).

In `D:/PyCharm/AI/Coder/knowledge/document_loader.py`, update `_SUPPORTED_SUFFIXES` and add the MinerU-based PDF loader:

Change line 18:
```python
_SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".pptx", ".xlsx", ".csv", ".epub"}
```

Replace `_load_pdf` method (lines 56-71) with:

```python
def _load_pdf(self, path: Path) -> str:
    try:
        return self._load_pdf_mineru(path)
    except ImportError:
        logger.warning("MinerU 未安装，回退到 pypdf")
        return self._load_pdf_fallback(path)

def _load_pdf_mineru(self, path: Path) -> str:
    import tempfile
    from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
    from magic_pdf.data.dataset import PymuDocDataset
    from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = FileBasedDataWriter(tmpdir)
        reader = FileBasedDataReader(str(path))
        ds = PymuDocDataset(reader.read())
        ds = ds.apply(doc_analyze, ocr=False)
        ds.pipe_mk_markdown(writer, str(path))

        import glob
        md_files = glob.glob(os.path.join(tmpdir, "**", "*.md"), recursive=True)
        if md_files:
            parts = []
            for md_file in sorted(md_files):
                with open(md_file, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            return "\n\n".join(parts)
        return ""

def _load_pdf_fallback(self, path: Path) -> str:
    reader = pypdf.PdfReader(path)
    page_count = len(reader.pages)
    if page_count > _MAX_PDF_PAGES:
        logger.warning(f"PDF页数过多 ({page_count})，仅读取前 {_MAX_PDF_PAGES} 页")
        reader.pages = reader.pages[:_MAX_PDF_PAGES]

    pages = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text:
                pages.append(text)
        except Exception as e:
            logger.warning(f"PDF第{i + 1}页提取失败: {e}")
    return "\n\n".join(pages)
```

- [ ] **Step 2: Verify the loader works**

Run: `pytest Coder/tests/ -v -k "test_document" 2>/dev/null || echo "No existing document tests — manual verification needed"`
Expected: No regressions in existing tests.

- [ ] **Step 3: Commit**

```bash
git add Coder/knowledge/document_loader.py
git commit -m "feat: add MinerU PDF loader with pypdf fallback for formula/table preservation"
```

---

### Task 5: Add New File Type Loaders (pptx, xlsx, csv, epub)

**Files:**
- Modify: `D:/PyCharm/AI/Coder/knowledge/document_loader.py` — add new loader methods
- Test: `D:/PyCharm/AI/Coder/tests/test_document_loader.py`

- [ ] **Step 1: Write the test**

```python
import os
import tempfile
import pytest
from pathlib import Path
from Coder.knowledge.document_loader import DocumentLoader


class TestDocumentLoaderNewFormats:
    def setup_method(self):
        self.loader = DocumentLoader()

    def test_load_pptx(self):
        from pptx import Presentation
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "第一章 绪论"
        body = slide.shapes.placeholders[1]
        body.text = "这是课程介绍内容"

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            prs.save(f.name)
            tmp_path = f.name

        try:
            result = self.loader.load(tmp_path)
            assert "第一章 绪论" in result["content"]
            assert "课程介绍内容" in result["content"]
        finally:
            os.unlink(tmp_path)

    def test_load_xlsx(self):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["题目", "选项A", "选项B", "答案"])
        ws.append(["1+1=?", "1", "2", "B"])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            wb.save(f.name)
            tmp_path = f.name

        try:
            result = self.loader.load(tmp_path)
            assert "1+1=?" in result["content"]
        finally:
            os.unlink(tmp_path)

    def test_load_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8") as f:
            f.write("题目,答案\n极限的定义,见教材P12\n")
            tmp_path = f.name

        try:
            result = self.loader.load(tmp_path)
            assert "极限的定义" in result["content"]
        finally:
            os.unlink(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Coder/tests/test_document_loader.py -v`
Expected: FAIL — "不支持的文件类型: .pptx"

- [ ] **Step 3: Add the new loader methods**

In `D:/PyCharm/AI/Coder/knowledge/document_loader.py`, update the loader dict (after line 45):

```python
loader = {
    ".pdf": self._load_pdf,
    ".docx": self._load_docx,
    ".txt": self._load_text,
    ".md": self._load_text,
    ".pptx": self._load_pptx,
    ".xlsx": self._load_xlsx,
    ".csv": self._load_csv,
    ".epub": self._load_epub,
}.get(suffix)
```

Add these new methods after `_load_docx`:

```python
def _load_pptx(self, path: Path) -> str:
    from pptx import Presentation
    prs = Presentation(str(path))
    slides_text = []
    for i, slide in enumerate(prs.slides):
        lines = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        lines.append(text)
        if lines:
            slides_text.append(f"[幻灯片 {i + 1}]\n" + "\n".join(lines))
    return "\n\n".join(slides_text)

def _load_xlsx(self, path: Path) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    sheet_texts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            rows.append("\t".join(cells))
        sheet_texts.append(f"[工作表: {sheet_name}]\n" + "\n".join(rows))
    wb.close()
    return "\n\n".join(sheet_texts)

def _load_csv(self, path: Path) -> str:
    import csv
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = ["\t".join(row) for row in reader]
    return "\n".join(rows)

def _load_epub(self, path: Path) -> str:
    from ebooklib import epub, ITEM_DOCUMENT
    from bs4 import BeautifulSoup
    book = epub.read_epub(str(path))
    chapters = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            chapters.append(soup.get_text("\n", strip=True))
    return "\n\n".join(chapters)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Coder/tests/test_document_loader.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add Coder/knowledge/document_loader.py Coder/tests/test_document_loader.py
git commit -m "feat: add pptx, xlsx, csv, epub document loaders for course materials"
```

---

### Task 6: Chapter-Aware Text Splitter

**Files:**
- Create: `D:/PyCharm/AI/Coder/knowledge/chapter_splitter.py`
- Test: `D:/PyCharm/AI/Coder/tests/test_chapter_splitter.py`

- [ ] **Step 1: Write the test**

```python
import pytest
from Coder.knowledge.chapter_splitter import ChapterSplitter


class TestChapterSplitter:
    def setup_method(self):
        self.splitter = ChapterSplitter()

    def test_detect_markdown_headings(self):
        content = "# 第一章 绪论\n这是引入内容\n\n## 1.1 背景\n研究背景描述\n\n# 第二章 方法\n实验方法"
        sections = self.splitter._detect_chapters(content)
        assert len(sections) >= 2

    def test_detect_chapter_keywords(self):
        content = "Chapter 1 Introduction\nThis is the intro.\n\nChapter 2 Methods\nThe methods section."
        sections = self.splitter._detect_chapters(content)
        assert len(sections) >= 2

    def test_split_pptx_style_input(self):
        content = "[幻灯片 1]\n课程概述\n\n[幻灯片 2]\n第一章 极限\n极限定义"
        sections = self.splitter._detect_chapters(content)
        assert len(sections) >= 2

    def test_fallback_when_no_structure(self):
        content = "这是没有任何标题结构的纯文本内容 " * 100
        sections = self.splitter.split_text(content)
        assert len(sections) >= 1

    def test_chunks_retain_source_section(self):
        content = "# 第一章 绪论\n\n" + "测试内容 " * 200
        chunks = self.splitter.split_text(content, source_file="高数.pdf")
        for chunk in chunks:
            assert hasattr(chunk, "page_content")
            assert hasattr(chunk, "metadata")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Coder/tests/test_chapter_splitter.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the ChapterSplitter implementation**

```python
import re
import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_CHAPTER_PATTERNS = [
    re.compile(r"(?:^|\n)(#{1,3}\s+.+?)(?=\n#{1,3}\s|\Z)", re.DOTALL | re.MULTILINE),
    re.compile(r"(?:^|\n)(Chapter\s*\d+[\.\s]*.*?)(?=\nChapter\s*\d+|\Z)", re.DOTALL | re.IGNORECASE),
    re.compile(r"(?:^|\n)(第[一二三四五六七八九十\d]+[章节]\s*.*?)(?=\n第[一二三四五六七八九十\d]+[章节]|\Z)", re.DOTALL),
    re.compile(r"(?:^|\n)(\[幻灯片\s*\d+\].*?)(?=\n\[幻灯片\s*\d+\]|\Z)", re.DOTALL),
    re.compile(r"(?:^|\n)(\d+[\.、]\s*.+?)(?=\n\d+[\.、]\s|\Z)", re.DOTALL | re.MULTILINE),
]


class ChapterSplitter:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, content: str, source_file: str = "",
                   defaults: dict = None) -> list[Document]:
        if not content or not content.strip():
            return []

        chapters = self._detect_chapters(content)
        documents = []

        for chapter in chapters:
            title = chapter["title"][:80]
            body = chapter["content"]

            if len(body) <= self.chunk_size:
                meta = {"section": title, "filename": source_file}
                if defaults:
                    meta.update(defaults)
                documents.append(Document(page_content=body, metadata=meta))
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separators=["\n\n", "\n", "。", "；", "，", " "],
                )
                sub_chunks = splitter.split_text(body)
                for i, chunk in enumerate(sub_chunks):
                    meta = {
                        "section": title,
                        "filename": source_file,
                        "chunk_index": i,
                    }
                    if defaults:
                        meta.update(defaults)
                    documents.append(Document(page_content=chunk, metadata=meta))

        logger.info(f"章节分段: {len(chapters)} 章节 → {len(documents)} chunks")
        return documents

    def _detect_chapters(self, content: str) -> list[dict]:
        for pattern in _CHAPTER_PATTERNS:
            matches = list(pattern.finditer(content))
            if len(matches) >= 2:
                sections = []
                for match in matches:
                    text = match.group(1).strip()
                    if not text:
                        continue
                    first_line = text.split("\n")[0].strip()
                    title = re.sub(r"^#{1,3}\s+", "", first_line)
                    title = re.sub(r"^\[幻灯片\s*\d+\]\s*", "", title)
                    sections.append({"title": title, "content": text})
                return sections

        return [{"title": "全文", "content": content}]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Coder/tests/test_chapter_splitter.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add Coder/knowledge/chapter_splitter.py Coder/tests/test_chapter_splitter.py
git commit -m "feat: add chapter-aware text splitter for structured course materials"
```

---

### Task 7: Hybrid Retriever (BM25 + FAISS)

**Files:**
- Create: `D:/PyCharm/AI/Coder/knowledge/hybrid_retriever.py`
- Test: `D:/PyCharm/AI/Coder/tests/test_hybrid_retriever.py`

- [ ] **Step 1: Write the test**

```python
import os
import tempfile
import pytest
from langchain_core.documents import Document
from Coder.knowledge.hybrid_retriever import HybridRetriever


class TestHybridRetriever:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.retriever = HybridRetriever(
            store_path=self.tmpdir,
            model_name="BAAI/bge-small-zh-v1.5",
        )

    def teardown_method(self):
        import shutil
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_add_and_retrieve(self):
        docs = [
            Document(page_content="极限是微积分的基本概念", metadata={"section": "§1.1"}),
            Document(page_content="导数描述了函数的变化率", metadata={"section": "§2.1"}),
            Document(page_content="积分用于计算面积和体积", metadata={"section": "§3.1"}),
        ]
        self.retriever.add_documents(docs)

        results = self.retriever.retrieve("什么是极限", k=2)
        assert len(results) >= 1
        assert "极限" in results[0].page_content

    def test_keyword_match_via_bm25(self):
        docs = [
            Document(page_content="Python是一种编程语言", metadata={}),
            Document(page_content="Java是一种编程语言", metadata={}),
        ]
        self.retriever.add_documents(docs)

        results = self.retriever.retrieve("Python", k=1)
        assert len(results) >= 1
        assert "Python" in results[0].page_content

    def test_merge_deduplication(self):
        docs = [
            Document(page_content="相同内容", metadata={"section": "A"}),
        ]
        self.retriever.add_documents(docs)

        results = self.retriever.retrieve("相同内容", k=3)
        assert len(results) == 1

    def test_is_available(self):
        is_avail = self.retriever.is_available()
        assert isinstance(is_avail, bool)

    def test_clear(self):
        docs = [Document(page_content="测试", metadata={})]
        self.retriever.add_documents(docs)
        self.retriever.clear()
        results = self.retriever.retrieve("测试")
        assert len(results) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Coder/tests/test_hybrid_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the HybridRetriever implementation**

```python
import os
import logging
import threading
from typing import Optional

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from Coder.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)

_MAX_QUERY_LENGTH = 2000
_DEFAULT_K = 5
_DEFAULT_SCORE_THRESHOLD = 1.5


class HybridRetriever:
    def __init__(
        self,
        store_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        default_k: int = _DEFAULT_K,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
    ):
        self.vector_store = VectorStore(store_path=store_path, model_name=model_name)
        self.default_k = default_k
        self.score_threshold = score_threshold
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_docs: list[Document] = []
        self._lock = threading.Lock()

    def _tokenize(self, text: str) -> list[str]:
        import jieba
        return list(jieba.cut(text))

    def add_documents(self, documents: list[Document]):
        if not documents:
            return
        with self._lock:
            self.vector_store.add_documents(documents)
            self._bm25_docs.extend(documents)
            corpus = [self._tokenize(d.page_content) for d in self._bm25_docs]
            self._bm25 = BM25Okapi(corpus)
            logger.info(f"已索引: {len(self._bm25_docs)} 文档 (向量+BM25)")

    def retrieve(self, query: str, k: Optional[int] = None) -> list[Document]:
        if not query or not query.strip():
            return []

        query = query.strip()
        if len(query) > _MAX_QUERY_LENGTH:
            query = query[:_MAX_QUERY_LENGTH]

        k = max(1, min(k or self.default_k, 50))

        vector_results = self._retrieve_vector(query, k=k)
        bm25_results = self._retrieve_bm25(query, k=k)

        merged = self._merge_results(vector_results, bm25_results, k)
        logger.info(f"混合检索: 向量={len(vector_results)} BM25={len(bm25_results)} → 合并={len(merged)}")
        return merged

    def _retrieve_vector(self, query: str, k: int) -> list[Document]:
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"向量检索异常: {e}")
            return []

        filtered = []
        for doc, score in results:
            if score <= self.score_threshold:
                doc.metadata["relevance_score"] = float(score)
                filtered.append(doc)

        if not filtered and results:
            doc, score = results[0]
            doc.metadata["relevance_score"] = float(score)
            filtered.append(doc)

        return filtered

    def _retrieve_bm25(self, query: str, k: int) -> list[Document]:
        if self._bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:k]

        results = []
        for idx, score in ranked:
            if score > 0:
                doc = self._bm25_docs[idx]
                doc.metadata["bm25_score"] = float(score)
                results.append(doc)

        return results

    def _merge_results(self, vec: list[Document], bm25: list[Document],
                       k: int) -> list[Document]:
        seen_ids = set()
        merged = []

        for doc in vec + bm25:
            content_id = hash(doc.page_content)
            if content_id not in seen_ids:
                seen_ids.add(content_id)
                merged.append(doc)

        merged.sort(
            key=lambda d: d.metadata.get("relevance_score", 0),
            reverse=False,
        )
        return merged[:k]

    def clear(self):
        with self._lock:
            self.vector_store.delete_store()
            self._bm25 = None
            self._bm25_docs = []
            logger.info("混合检索器已清空")

    def is_available(self) -> bool:
        return self.vector_store.has_local_index()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Coder/tests/test_hybrid_retriever.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add Coder/knowledge/hybrid_retriever.py Coder/tests/test_hybrid_retriever.py
git commit -m "feat: add hybrid retriever with BM25 keyword + FAISS vector search"
```

---

### Task 8: Course-Scoped Agent with RAG Rewiring

**Files:**
- Modify: `D:/PyCharm/AI/Coder/tools/knowledge_toolkit.py` — support per-course index switching
- Modify: `D:/PyCharm/AI/Coder/agent/code_agent.py` — wire in course-scoped hybrid retriever

- [ ] **Step 1: Add course-scoped search tools to knowledge_toolkit.py**

Append to `D:/PyCharm/AI/Coder/tools/knowledge_toolkit.py`:

```python
_course_retrievers: dict[str, object] = {}
_course_retrievers_lock = threading.Lock()


def get_course_retriever(course_id: str) -> object:
    global _course_retrievers
    if course_id not in _course_retrievers:
        with _course_retrievers_lock:
            if course_id not in _course_retrievers:
                import os
                from Coder.knowledge.hybrid_retriever import HybridRetriever
                index_path = os.path.normpath(
                    os.path.join(_INDEX_DIR, f"course_{course_id}")
                )
                os.makedirs(index_path, exist_ok=True)
                _course_retrievers[course_id] = HybridRetriever(store_path=index_path)
    return _course_retrievers[course_id]


@tool
def course_knowledge_search(query: str, course_id: str, k: int = 5) -> str:
    """在指定课程的知识库中搜索。基于上传的教材/课件内容进行语义+关键词混合检索。

    Args:
        query: 搜索查询，支持自然语言描述
        course_id: 课程ID
        k: 返回结果数量，1-20之间，默认5
    """
    start = time.monotonic()
    if not query or not query.strip():
        return "查询不能为空。"

    query = query.strip()
    if len(query) > _MAX_QUERY_LENGTH:
        query = query[:_MAX_QUERY_LENGTH]

    k = max(1, min(k, 20))

    try:
        retriever = get_course_retriever(course_id)
        if not retriever.is_available():
            return f"课程 {course_id} 知识库为空，请先上传课件。"

        docs = retriever.retrieve(query, k=k)
        latency = (time.monotonic() - start) * 1000

        if not docs:
            return f"在课程知识库中未找到与 '{query[:50]}' 相关的内容。"

        parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("filename", "未知来源")
            section = doc.metadata.get("section", "")
            score = doc.metadata.get("relevance_score", doc.metadata.get("bm25_score", 0))

            header = f"[结果 {i + 1}] 来源: {source}"
            if section:
                header += f" | 章节: {section}"
            header += f" | 相关度: {score:.3f}"

            parts.append(f"{header}\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        logger.error(f"课程知识库搜索异常: {type(e).__name__}: {e}")
        return f"搜索失败: {type(e).__name__}: {str(e)[:100]}"


@tool
def course_add_document(file_path: str, course_id: str) -> str:
    """将课件文件导入指定课程的知识库。支持 pdf/pptx/docx/epub/xlsx/csv/txt/md。

    Args:
        file_path: 要导入的文件路径
        course_id: 目标课程ID
    """
    start = time.monotonic()
    if not file_path or not file_path.strip():
        return "文件路径不能为空。"

    file_path = file_path.strip()
    try:
        file_path = _validate_doc_path(file_path)
    except ValueError as e:
        return f"文件路径验证失败: {e}"

    try:
        loader = _get_document_loader()
        doc = loader.load(file_path)
        content = doc.get("content", "")

        if not content or not content.strip():
            return f"文件 {os.path.basename(file_path)} 内容为空。"

        from Coder.knowledge.chapter_splitter import ChapterSplitter
        splitter = ChapterSplitter()
        chunks = splitter.split_text(content, source_file=os.path.basename(file_path))

        retriever = get_course_retriever(course_id)
        retriever.add_documents(chunks)

        latency = (time.monotonic() - start) * 1000

        return (
            f"[OK] 成功导入 {os.path.basename(file_path)} 到课程 {course_id}\n"
            f"  - 文档块数: {len(chunks)}\n"
            f"  - 字符数: {len(content)}\n"
            f"  - 耗时: {latency:.0f}ms"
        )

    except FileNotFoundError:
        return f"文件不存在: {file_path}"
    except Exception as e:
        return f"导入失败: {type(e).__name__}: {str(e)[:100]}"
```

Update the `course_knowledge_toolkit` export at line 769:

```python
course_knowledge_toolkit = [
    course_knowledge_search,
    course_add_document,
]

__all__ = ["knowledge_toolkit", "course_knowledge_toolkit"]
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `pytest Coder/tests/test_knowledge_toolkit.py -v`
Expected: All existing tests PASS.

- [ ] **Step 3: Commit**

```bash
git add Coder/tools/knowledge_toolkit.py
git commit -m "feat: add course-scoped knowledge tools with hybrid retriever"
```

---

### Task 9: Course API Routes

**Files:**
- Create: `D:/PyCharm/AI/Coder/server/routes/courses.py`
- Modify: `D:/PyCharm/AI/Coder/server/main.py` — register new routes
- Modify: `D:/PyCharm/AI/Coder/server/schemas.py` — add course schemas

- [ ] **Step 1: Add course schemas**

Append to `D:/PyCharm/AI/Coder/server/schemas.py`:

```python


class CourseCreate(BaseModel):
    name: str
    description: str = ""
    semester: str = ""


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    semester: Optional[str] = None


class CourseResponse(BaseModel):
    id: str
    name: str
    description: str
    semester: str
    created_at: str
    updated_at: str


class KnowledgePointResponse(BaseModel):
    id: str
    name: str
    section: str
    source_file: str
    source_page: int


class CourseFileResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    uploaded_at: str


class NoteCreate(BaseModel):
    course_id: str
    kp_id: Optional[str] = None
    title: str = ""
    content: str


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    created_at: str


class WrongAnswerCreate(BaseModel):
    course_id: str
    kp_id: Optional[str] = None
    question: str
    user_answer: str
    correct_answer: str
```

- [ ] **Step 2: Write the courses API router**

```python
import logging
from fastapi import APIRouter, HTTPException

from Coder.storage.course_manager import CourseManager
from Coder.server.schemas import (
    CourseCreate, CourseUpdate, CourseResponse,
    KnowledgePointResponse, CourseFileResponse,
    NoteCreate, NoteResponse, WrongAnswerCreate,
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
    # Stub — will be fully implemented in Round 2
    return {"course_id": course_id, "progress": "not yet implemented"}
```

- [ ] **Step 3: Register the new router in main.py**

In `D:/PyCharm/AI/Coder/server/main.py`:
- Add import: `from Coder.server.routes import courses` (after the existing route imports)
- Add: `app.include_router(courses.router, prefix="/api", tags=["Courses"])`

- [ ] **Step 4: Verify server starts**

Run: `python -c "from Coder.server.main import app; print('Router registered OK')"`
Expected: "Router registered OK"

- [ ] **Step 5: Commit**

```bash
git add Coder/server/routes/courses.py Coder/server/main.py Coder/server/schemas.py
git commit -m "feat: add course API routes (CRUD, knowledge points, file listing)"
```

---

### Task 10: Frontend Restructure — Course Workspace Layout

**Files:**
- Create: `D:/PyCharm/AI/Coder/web/src/pages/CoursePage.tsx`
- Modify: `D:/PyCharm/AI/Coder/web/src/App.tsx` — add CoursePage route, remove MultiAgentPage + MCPPage + SkillsPage routes
- Modify: `D:/PyCharm/AI/Coder/web/src/components/layout/Sidebar.tsx` — repurpose as course list
- Create: `D:/PyCharm/AI/Coder/web/src/api/courses.ts`

- [ ] **Step 1: Create courses API client**

```typescript
// D:/PyCharm/AI/Coder/web/src/api/courses.ts
import { apiClient } from './client';

export interface Course {
  id: string;
  name: string;
  description: string;
  semester: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgePoint {
  id: string;
  name: string;
  section: string;
  source_file: string;
  source_page: number;
}

export interface CourseFile {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  uploaded_at: string;
}

export async function listCourses(): Promise<Course[]> {
  const res = await apiClient.get('/courses');
  return res.data.courses;
}

export async function getCourse(courseId: string): Promise<Course> {
  const res = await apiClient.get(`/courses/${courseId}`);
  return res.data.course;
}

export async function createCourse(
  name: string,
  description?: string,
  semester?: string
): Promise<string> {
  const res = await apiClient.post('/courses', { name, description, semester });
  return res.data.course_id;
}

export async function deleteCourse(courseId: string): Promise<void> {
  await apiClient.delete(`/courses/${courseId}`);
}

export async function getKnowledgePoints(courseId: string): Promise<KnowledgePoint[]> {
  const res = await apiClient.get(`/courses/${courseId}/knowledge-points`);
  return res.data.knowledge_points;
}

export async function getCourseFiles(courseId: string): Promise<CourseFile[]> {
  const res = await apiClient.get(`/courses/${courseId}/files`);
  return res.data.files;
}
```

- [ ] **Step 2: Create CoursePage component**

```tsx
// D:/PyCharm/AI/Coder/web/src/pages/CoursePage.tsx
import { useParams } from 'react-router-dom';
import { useState } from 'react';
import { ChatPage } from './ChatPage';

export function CoursePage() {
  const { courseId } = useParams<{ courseId: string }>();
  const [activeTab, setActiveTab] = useState<'qa' | 'notes' | 'graph' | 'wrong'>('qa');

  if (!courseId) {
    return <div className="p-8 text-gray-500">请选择一个课程</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {courseId}
          </h2>
          <div className="flex items-center gap-1">
            {(['qa', 'notes', 'graph', 'wrong'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  activeTab === tab
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                {tab === 'qa' ? '问答' : tab === 'notes' ? '笔记' : tab === 'graph' ? '图谱' : '错题'}
              </button>
            ))}
          </div>
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          知识点掌握度: --
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'qa' && <ChatPage courseId={courseId} />}
        {activeTab === 'notes' && (
          <div className="p-8 text-gray-500">笔记功能即将上线</div>
        )}
        {activeTab === 'graph' && (
          <div className="p-8 text-gray-500">知识图谱即将上线</div>
        )}
        {activeTab === 'wrong' && (
          <div className="p-8 text-gray-500">错题本即将上线</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update Sidebar to show courses**

In `D:/PyCharm/AI/Coder/web/src/components/layout/Sidebar.tsx`, add a course list section at the top. Include:
- "我的课程" header with a "+" button to create course
- List of course names fetched from `listCourses()` API, each linking to `/course/:id`
- Keep existing session list below, but filtered by course context

- [ ] **Step 4: Update App.tsx routing**

Replace the import and route blocks:

```tsx
// Remove these imports:
// import { MultiAgentPage } from './pages/MultiAgentPage'
// import { MCPPage } from './pages/MCPPage'

// Add:
import { CoursePage } from './pages/CoursePage'

// Replace routes:
<Routes>
  <Route path="/" element={<Navigate to="/chat" replace />} />
  <Route path="/chat" element={<ChatPage />} />
  <Route path="/course/:courseId" element={<CoursePage />} />
  <Route path="/knowledge" element={<KnowledgePage />} />
  <Route path="/skills" element={<SkillsPage />} />
</Routes>
```

Remove imported pages that are no longer used (MultiAgentPage, MCPPage). Keep the files on disk for now (cleanup in Round 3).

- [ ] **Step 5: Verify frontend builds**

Run: `cd Coder/web && npm run build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add Coder/web/src/
git commit -m "feat: add course workspace layout with tabbed interface and course list sidebar"
```

---

### Task 11: ChatPage Course-Aware Mode

**Files:**
- Modify: `D:/PyCharm/AI/Coder/web/src/pages/ChatPage.tsx` — accept optional courseId prop
- Modify: `D:/PyCharm/AI/Coder/web/src/api/chat.ts` — send course_id in SSE stream request
- Modify: `D:/PyCharm/AI/Coder/server/routes/chat.py` — accept course_id param

- [ ] **Step 1: Update ChatPage props**

In `D:/PyCharm/AI/Coder/web/src/pages/ChatPage.tsx`, update the component signature:

```tsx
interface ChatPageProps {
  courseId?: string;
}

export function ChatPage({ courseId }: ChatPageProps) {
  // ... existing code

  // When courseId is provided, prepend system context to each message
  const sendMessage = useCallback((content: string) => {
    const payload = { message: content, thread_id: threadId };
    if (courseId) {
      payload.course_id = courseId;
    }
    // ... send payload
  }, [threadId, courseId]);
}
```

- [ ] **Step 2: Update stream API to accept course_id**

In `D:/PyCharm/AI/Coder/server/routes/chat.py`, update the stream endpoint to read `course_id` from the request body and pass it to the agent context.

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/pages/ChatPage.tsx Coder/web/src/api/chat.ts Coder/server/routes/chat.py
git commit -m "feat: wire course context into chat stream for course-scoped Q&A"
```

---

### Task 12-14: Round 2 — Knowledge Graph, Learning Progress, Smart Notes (Outline)

These tasks are documented with their scope; full implementation details will be expanded during Round 2 planning.

**Task 12: Knowledge Graph Page**
- Backend: `GET /api/courses/{id}/knowledge-graph` — return nodes (knowledge points) and edges (co-occurrence from same section/sequential)
- Frontend: Use `react-force-graph-2d` or `d3.js` to render interactive graph
- Click node → navigate to Q&A with that knowledge point as context

**Task 13: Learning Progress Tracking**
- Backend: `POST /api/courses/{id}/progress` — update mastery status
- Backend: `GET /api/courses/{id}/progress` — return progress dashboard data
- Each knowledge point interaction increments counter; after 3+ interactions status auto-promotes to "learning" or "mastered"

**Task 14: Smart Note Generation**
- Backend: `POST /api/notes` — agent summarizes Q&A session into structured notes
- Backend: `GET /api/notes?course_id=...` — list notes
- Frontend: Note preview panel in course workspace

---

### Task 15-18: Round 3 — Wrong Answers, Review Plans, Thesis, OCR, RAGAS (Outline)

**Task 15: Wrong Answer Book**
- Backend: `POST /api/wrong-answers` — save wrong answer
- Backend: `GET /api/wrong-answers?course_id=...` — list for review
- Frontend: Display in course workspace tab

**Task 16: Review Plan Generation**
- Agent tool: given weak knowledge points, generate spaced-repetition schedule

**Task 17: Thesis Polish Entry**
- Dedicated input area for thesis paragraph → agent returns academic writing suggestions

**Task 18: OCR + RAGAS + Cleanup**
- Add Tesseract/PaddleOCR image extraction in document_loader
- Add RAGAS evaluation endpoint (`POST /api/eval/ragas`)
- Remove: `MultiAgentPage.tsx`, route imports, PowerShell MCP tool from agent, `/api/agent-orchestrator` route (logic moved into course agent)
- Remove: `MCPPage.tsx` from routes (keep MCP backend for course tool extension)

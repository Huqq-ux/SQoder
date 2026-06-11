import re
import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_CHAPTER_PATTERNS = [
    re.compile(
        r"(?:^|\n)(#{1,3}\s+.+?)(?=\n#{1,3}\s|\Z)",
        re.DOTALL | re.MULTILINE,
    ),
    re.compile(
        r"(?:^|\n)(Chapter\s*\d+[\.\s]*.*?)(?=\nChapter\s*\d+|\Z)",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|\n)(第[一二三四五六七八九十\d]+[章节]\s*.*?)(?=\n第[一二三四五六七八九十\d]+[章节]|\Z)",
        re.DOTALL,
    ),
    re.compile(
        r"(?:^|\n)(\[幻灯片\s*\d+\].*?)(?=\n\[幻灯片\s*\d+\]|\Z)",
        re.DOTALL,
    ),
    re.compile(
        r"(?:^|\n)(\d+[\.、]\s*.+?)(?=\n\d+[\.、]\s|\Z)",
        re.DOTALL | re.MULTILINE,
    ),
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

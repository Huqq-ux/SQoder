import re
import logging
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_MAX_CONTENT_LENGTH = 5 * 1024 * 1024
_MAX_CHUNK_SIZE = 10000
_MIN_CHUNK_SIZE = 50
_MAX_DOCUMENTS = 1000
_MAX_CHUNKS_PER_DOC = 500


class SOPTextSplitter:
    _HEADING_PATTERN = re.compile(
        r"(?:^|\n)(#{1,3}\s+.+?)(?=\n#{1,3}\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    _STEP_PATTERN = re.compile(
        r"(?:^|\n)(步骤\s*\d+[：:]\s*.+?)(?=\n步骤\s*\d+[：:]|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    _NUMBERED_PATTERN = re.compile(
        r"(?:^|\n)(\d+[\.、]\s*.+?)(?=\n\d+[\.、]\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[list[str]] = None,
    ):
        if separators is None:
            separators = ["\n\n## ", "\n\n### ", "\n\n", "\n", "。", "；", "，", " "]

        self.chunk_size = max(_MIN_CHUNK_SIZE, min(chunk_size, _MAX_CHUNK_SIZE))
        self.chunk_overlap = min(chunk_overlap, self.chunk_size // 2)
        self.separators = separators

    def split_documents(self, documents: list[dict]) -> list[Document]:
        if not documents:
            return []

        if len(documents) > _MAX_DOCUMENTS:
            logger.warning(f"文档数量过多 ({len(documents)})，仅处理前 {_MAX_DOCUMENTS} 个")
            documents = documents[:_MAX_DOCUMENTS]

        all_chunks = []

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            if not content or not content.strip():
                continue

            if len(content) > _MAX_CONTENT_LENGTH:
                logger.warning(f"文档内容过长 ({len(content)} 字符)，已截断")
                content = content[:_MAX_CONTENT_LENGTH]

            sections = self._split_by_sop_structure(content)

            if not sections:
                sections = [{"content": content, "section": "全文"}]

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )

            doc_chunks = 0
            for section in sections:
                if doc_chunks >= _MAX_CHUNKS_PER_DOC:
                    logger.warning(f"单文档分块数超过限制 ({_MAX_CHUNKS_PER_DOC})")
                    break

                section_content = section["content"]
                section_title = section["section"]

                if len(section_content) <= self.chunk_size:
                    chunk_meta = {**metadata, "section": section_title}
                    all_chunks.append(Document(
                        page_content=section_content,
                        metadata=chunk_meta,
                    ))
                    doc_chunks += 1
                else:
                    chunks = splitter.split_text(section_content)
                    for i, chunk in enumerate(chunks):
                        if doc_chunks >= _MAX_CHUNKS_PER_DOC:
                            break
                        chunk_meta = {
                            **metadata,
                            "section": section_title,
                            "chunk_index": i,
                        }
                        all_chunks.append(Document(
                            page_content=chunk,
                            metadata=chunk_meta,
                        ))
                        doc_chunks += 1

        return all_chunks

    def _split_by_sop_structure(self, content: str) -> list[dict]:
        sections = []

        patterns = [
            (self._HEADING_PATTERN, "heading"),
            (self._STEP_PATTERN, "step"),
            (self._NUMBERED_PATTERN, "numbered"),
        ]

        for pattern, ptype in patterns:
            matches = list(pattern.finditer(content))
            if matches:
                for match in matches:
                    text = match.group(1).strip()
                    if not text:
                        continue
                    first_line = text.split("\n")[0].strip()
                    title = re.sub(r"^#{1,3}\s+", "", first_line)
                    title = re.sub(r"^步骤\s*\d+[：:]\s*", "", title)
                    title = re.sub(r"^\d+[\.、]\s*", "", title)
                    sections.append({"content": text, "section": title[:50]})
                break

        return sections

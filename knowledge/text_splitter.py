import re
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class SOPTextSplitter:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[list[str]] = None,
    ):
        if separators is None:
            separators = ["\n\n## ", "\n\n### ", "\n\n", "\n", "。", "；", "，", " "]

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators

    def split_documents(self, documents: list[dict]) -> list[Document]:
        all_chunks = []

        for doc in documents:
            content = doc["content"]
            metadata = doc.get("metadata", {})

            sections = self._split_by_sop_structure(content)

            if not sections:
                sections = [{"content": content, "section": "全文"}]

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )

            for section in sections:
                section_content = section["content"]
                section_title = section["section"]

                if len(section_content) <= self.chunk_size:
                    chunk_meta = {**metadata, "section": section_title}
                    all_chunks.append(Document(
                        page_content=section_content,
                        metadata=chunk_meta,
                    ))
                else:
                    chunks = splitter.split_text(section_content)
                    for i, chunk in enumerate(chunks):
                        chunk_meta = {
                            **metadata,
                            "section": section_title,
                            "chunk_index": i,
                        }
                        all_chunks.append(Document(
                            page_content=chunk,
                            metadata=chunk_meta,
                        ))

        return all_chunks

    def _split_by_sop_structure(self, content: str) -> list[dict]:
        sections = []

        patterns = [
            (r"(?:^|\n)(#{1,3}\s+.+?)(?=\n#{1,3}\s|\Z)", "heading"),
            (r"(?:^|\n)(步骤\s*\d+[：:]\s*.+?)(?=\n步骤\s*\d+[：:]|\Z)", "step"),
            (r"(?:^|\n)(\d+[\.、]\s*.+?)(?=\n\d+[\.、]\s|\Z)", "numbered"),
        ]

        for pattern, ptype in patterns:
            matches = list(re.finditer(pattern, content, re.DOTALL | re.MULTILINE))
            if matches:
                for match in matches:
                    text = match.group(1).strip()
                    first_line = text.split("\n")[0].strip()
                    title = re.sub(r"^#{1,3}\s+", "", first_line)
                    title = re.sub(r"^步骤\s*\d+[：:]\s*", "", title)
                    title = re.sub(r"^\d+[\.、]\s*", "", title)
                    sections.append({"content": text, "section": title[:50]})
                break

        return sections

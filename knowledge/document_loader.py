import os
import json
import logging
from pathlib import Path
from typing import Optional

import pypdf
import docx

logger = logging.getLogger(__name__)


class DocumentLoader:
    def load(self, file_path: str) -> dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        loaders = {
            ".pdf": self._load_pdf,
            ".docx": self._load_docx,
            ".txt": self._load_text,
            ".md": self._load_text,
        }

        loader = loaders.get(suffix)
        if not loader:
            raise ValueError(f"不支持的文件类型: {suffix}")

        content = loader(path)
        metadata = self._extract_metadata(path, content)

        return {"content": content, "metadata": metadata}

    def _load_pdf(self, path: Path) -> str:
        reader = pypdf.PdfReader(path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    def _load_docx(self, path: Path) -> str:
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _load_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def _extract_metadata(self, path: Path, content: str) -> dict:
        stat = path.stat()
        metadata = {
            "source": str(path),
            "filename": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "char_count": len(content),
        }

        version = self._parse_version(path.name)
        if version:
            metadata["version"] = version

        title = self._parse_title(content)
        if title:
            metadata["title"] = title

        return metadata

    def _parse_version(self, filename: str) -> Optional[str]:
        import re
        match = re.search(r"v(\d+[\.\d]*)", filename, re.IGNORECASE)
        return match.group(1) if match else None

    def _parse_title(self, content: str) -> Optional[str]:
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line and len(line) < 100:
                return line
        return None

    def load_directory(self, dir_path: str, suffixes: Optional[list[str]] = None) -> list[dict]:
        if suffixes is None:
            suffixes = [".pdf", ".docx", ".txt", ".md"]

        path = Path(dir_path)
        if not path.is_dir():
            raise ValueError(f"目录不存在: {dir_path}")

        documents = []
        for file_path in sorted(path.rglob("*")):
            if file_path.suffix.lower() in suffixes and file_path.name != "__init__.py":
                try:
                    doc = self.load(str(file_path))
                    documents.append(doc)
                    logger.info(f"加载文档: {file_path.name}")
                except Exception as e:
                    logger.error(f"加载文档失败 {file_path}: {e}")

        return documents

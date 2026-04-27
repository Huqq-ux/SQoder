import os
import re
import logging
from pathlib import Path
from typing import Optional

import pypdf
import docx

logger = logging.getLogger(__name__)

_ALLOWED_BASE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_MAX_FILE_SIZE_MB = 50
_MAX_PDF_PAGES = 500
_MAX_DIRECTORY_DEPTH = 5
_SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


def _validate_file_path(file_path: str) -> Path:
    path = Path(file_path).resolve()
    if not str(path).startswith(_ALLOWED_BASE):
        raise ValueError(f"文件路径超出允许范围: {file_path}")
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > _MAX_FILE_SIZE_MB:
        raise ValueError(f"文件过大 ({size_mb:.1f}MB)，超过限制 ({_MAX_FILE_SIZE_MB}MB)")
    return path


class DocumentLoader:
    def load(self, file_path: str) -> dict:
        path = _validate_file_path(file_path)

        suffix = path.suffix.lower()
        if suffix not in _SUPPORTED_SUFFIXES:
            raise ValueError(f"不支持的文件类型: {suffix}")

        loader = {
            ".pdf": self._load_pdf,
            ".docx": self._load_docx,
            ".txt": self._load_text,
            ".md": self._load_text,
        }.get(suffix)

        if not loader:
            raise ValueError(f"不支持的文件类型: {suffix}")

        content = loader(path)
        metadata = self._extract_metadata(path, content)

        return {"content": content, "metadata": metadata}

    def _load_pdf(self, path: Path) -> str:
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

    def _load_docx(self, path: Path) -> str:
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _load_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="gbk")

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
            suffixes = list(_SUPPORTED_SUFFIXES)

        path = Path(dir_path).resolve()
        if not str(path).startswith(_ALLOWED_BASE):
            raise ValueError(f"目录路径超出允许范围: {dir_path}")
        if not path.is_dir():
            raise ValueError(f"目录不存在: {dir_path}")

        documents = []
        for file_path in sorted(path.rglob("*")):
            try:
                rel = file_path.relative_to(path)
                if len(rel.parts) > _MAX_DIRECTORY_DEPTH:
                    continue
            except ValueError:
                continue

            if file_path.suffix.lower() in suffixes and file_path.name != "__init__.py":
                try:
                    doc = self.load(str(file_path))
                    documents.append(doc)
                    logger.info(f"加载文档: {file_path.name}")
                except Exception as e:
                    logger.error(f"加载文档失败 {file_path}: {e}")

        return documents

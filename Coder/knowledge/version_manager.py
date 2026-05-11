import os
import re
import json
import logging
import difflib
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

_ALLOWED_BASE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "knowledge", "versions")
)
_MAX_VERSIONS_PER_FILE = 100
_MAX_CONTENT_LENGTH = 10 * 1024 * 1024
_SAFE_FILENAME_RE = re.compile(r'^[\w\-\.]+$')


def _sanitize_filename(filename: str) -> str:
    basename = os.path.basename(filename)
    basename = basename.replace("/", "_").replace("\\", "_")
    basename = basename.replace("..", "_")
    if not _SAFE_FILENAME_RE.match(basename):
        raise ValueError(f"文件名包含非法字符: {filename}")
    return basename


def _validate_path(base_path: str, target_path: str) -> str:
    normalized = os.path.normpath(os.path.abspath(target_path))
    if not normalized.startswith(os.path.normpath(os.path.abspath(base_path))):
        raise ValueError(f"路径超出允许范围: {target_path}")
    return normalized


class VersionManager:
    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            base_path = _ALLOWED_BASE
        self.base_path = os.path.normpath(os.path.abspath(base_path))
        os.makedirs(self.base_path, exist_ok=True)

    def _get_meta_path(self, filename: str) -> str:
        safe_name = _sanitize_filename(filename)
        meta_path = os.path.join(self.base_path, f"{safe_name}.meta.json")
        return _validate_path(self.base_path, meta_path)

    def _get_version_dir(self, filename: str) -> str:
        safe_name = _sanitize_filename(filename)
        version_dir = os.path.join(self.base_path, safe_name)
        return _validate_path(self.base_path, version_dir)

    def save_version(self, filename: str, content: str, version: Optional[str] = None) -> dict:
        if len(content) > _MAX_CONTENT_LENGTH:
            raise ValueError(f"内容超过最大长度限制 ({_MAX_CONTENT_LENGTH} 字节)")

        meta_path = self._get_meta_path(filename)
        version_dir = self._get_version_dir(filename)

        existing = self._load_meta(meta_path)
        current_version = existing.get("current_version", "0")

        if version is None:
            parts = current_version.split(".")
            try:
                parts[-1] = str(int(parts[-1]) + 1)
            except ValueError:
                parts[-1] = str(int(datetime.now().timestamp()))
            version = ".".join(parts)

        versions = existing.get("versions", [])
        if len(versions) >= _MAX_VERSIONS_PER_FILE:
            oldest = versions.pop(0)
            old_path = oldest.get("file_path", "")
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        os.makedirs(version_dir, exist_ok=True)

        version_file = os.path.join(version_dir, f"v{version}.txt")
        version_file = _validate_path(version_dir, version_file)

        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)

        versions.append({
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "file_path": version_file,
            "char_count": len(content),
        })

        meta = {
            "filename": filename,
            "current_version": version,
            "versions": versions,
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"保存版本: {filename} v{version}")
        return meta

    def get_current(self, filename: str) -> Optional[str]:
        meta_path = self._get_meta_path(filename)
        meta = self._load_meta(meta_path)
        if not meta or not meta.get("versions"):
            return None

        current_version = meta["current_version"]
        for v in meta["versions"]:
            if v["version"] == current_version:
                path = v["file_path"]
                try:
                    _validate_path(self.base_path, path)
                except ValueError:
                    logger.error(f"版本文件路径异常: {path}")
                    return None
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
        return None

    def get_version(self, filename: str, version: str) -> Optional[str]:
        if not _SAFE_FILENAME_RE.match(version):
            raise ValueError(f"版本号包含非法字符: {version}")

        meta_path = self._get_meta_path(filename)
        meta = self._load_meta(meta_path)
        if not meta:
            return None

        for v in meta.get("versions", []):
            if v["version"] == version:
                path = v["file_path"]
                try:
                    _validate_path(self.base_path, path)
                except ValueError:
                    logger.error(f"版本文件路径异常: {path}")
                    return None
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
        return None

    def list_versions(self, filename: str) -> list[dict]:
        meta_path = self._get_meta_path(filename)
        meta = self._load_meta(meta_path)
        if not meta:
            return []
        return meta.get("versions", [])

    def diff_versions(self, filename: str, v1: str, v2: str) -> str:
        if not _SAFE_FILENAME_RE.match(v1) or not _SAFE_FILENAME_RE.match(v2):
            raise ValueError("版本号包含非法字符")

        content1 = self.get_version(filename, v1)
        content2 = self.get_version(filename, v2)
        if content1 is None or content2 is None:
            return "无法获取指定版本的内容"

        diff = difflib.unified_diff(
            content1.splitlines(keepends=True),
            content2.splitlines(keepends=True),
            fromfile=f"v{v1}",
            tofile=f"v{v2}",
        )
        return "".join(diff)

    def _load_meta(self, meta_path: str) -> dict:
        if not os.path.exists(meta_path):
            return {}
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"加载元数据失败: {e}")
            return {}

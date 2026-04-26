import os
import json
import logging
import difflib
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VersionManager:
    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(__file__), "..", "knowledge", "versions"
            )
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _get_meta_path(self, filename: str) -> str:
        safe_name = filename.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_path, f"{safe_name}.meta.json")

    def save_version(self, filename: str, content: str, version: Optional[str] = None) -> dict:
        meta_path = self._get_meta_path(filename)

        existing = self._load_meta(meta_path)
        current_version = existing.get("current_version", "0")

        if version is None:
            parts = current_version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            version = ".".join(parts)

        version_dir = os.path.join(self.base_path, filename.replace("/", "_").replace("\\", "_"))
        os.makedirs(version_dir, exist_ok=True)

        version_file = os.path.join(version_dir, f"v{version}.txt")
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)

        versions = existing.get("versions", [])
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
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
        return None

    def get_version(self, filename: str, version: str) -> Optional[str]:
        meta_path = self._get_meta_path(filename)
        meta = self._load_meta(meta_path)
        if not meta:
            return None

        for v in meta.get("versions", []):
            if v["version"] == version:
                path = v["file_path"]
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
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

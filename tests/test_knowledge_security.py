import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from Coder.knowledge.version_manager import (
    VersionManager,
    _sanitize_filename,
    _validate_path,
    _SAFE_FILENAME_RE,
)
from Coder.knowledge.document_loader import (
    DocumentLoader,
    _validate_file_path,
    _ALLOWED_BASE as DOC_ALLOWED_BASE,
    _MAX_FILE_SIZE_MB,
)
from Coder.knowledge.text_splitter import SOPTextSplitter


class TestSanitizeFilename(unittest.TestCase):
    def test_normal_filename(self):
        self.assertEqual(_sanitize_filename("test.md"), "test.md")

    def test_path_traversal(self):
        result = _sanitize_filename("../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_backslash_traversal(self):
        result = _sanitize_filename("..\\..\\windows\\system32")
        self.assertNotIn("..", result)
        self.assertNotIn("\\", result)

    def test_special_chars(self):
        with self.assertRaises(ValueError):
            _sanitize_filename("file;rm -rf /")

    def test_empty_after_sanitize(self):
        with self.assertRaises(ValueError):
            _sanitize_filename("///")


class TestValidatePath(unittest.TestCase):
    def test_valid_path(self):
        base = tempfile.gettempdir()
        result = _validate_path(base, os.path.join(base, "sub", "file.txt"))
        self.assertTrue(result.startswith(os.path.normpath(base)))

    def test_traversal_attack(self):
        base = tempfile.gettempdir()
        with self.assertRaises(ValueError):
            _validate_path(base, os.path.join(base, "..", "..", "etc", "passwd"))


class TestVersionManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = VersionManager(base_path=self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_get_current(self):
        meta = self.manager.save_version("test.txt", "hello world")
        self.assertEqual(meta["current_version"], "1")

        content = self.manager.get_current("test.txt")
        self.assertEqual(content, "hello world")

    def test_version_increment(self):
        self.manager.save_version("doc.md", "v1")
        self.manager.save_version("doc.md", "v2")
        self.manager.save_version("doc.md", "v3")

        content = self.manager.get_current("doc.md")
        self.assertEqual(content, "v3")

    def test_get_specific_version(self):
        self.manager.save_version("doc.md", "v1")
        self.manager.save_version("doc.md", "v2")

        content = self.manager.get_version("doc.md", "1")
        self.assertEqual(content, "v1")

    def test_list_versions(self):
        self.manager.save_version("doc.md", "v1")
        self.manager.save_version("doc.md", "v2")

        versions = self.manager.list_versions("doc.md")
        self.assertEqual(len(versions), 2)

    def test_diff_versions(self):
        self.manager.save_version("doc.md", "line1\nline2\n")
        self.manager.save_version("doc.md", "line1\nline2_modified\n")

        diff = self.manager.diff_versions("doc.md", "1", "2")
        self.assertIn("line2_modified", diff)

    def test_path_traversal_filename(self):
        with self.assertRaises(ValueError):
            self.manager.save_version("../../etc/passwd", "malicious")

    def test_invalid_version_string(self):
        with self.assertRaises(ValueError):
            self.manager.get_version("test.txt", "../../etc/passwd")

    def test_max_content_length(self):
        from Coder.knowledge.version_manager import _MAX_CONTENT_LENGTH
        with self.assertRaises(ValueError):
            self.manager.save_version("big.txt", "x" * (_MAX_CONTENT_LENGTH + 1))

    def test_nonexistent_file(self):
        content = self.manager.get_current("nonexistent.txt")
        self.assertIsNone(content)

    def test_corrupted_meta(self):
        meta_path = self.manager._get_meta_path("corrupt.txt")
        with open(meta_path, "w") as f:
            f.write("{invalid json")
        result = self.manager._load_meta(meta_path)
        self.assertEqual(result, {})


class TestDocumentLoaderSecurity(unittest.TestCase):
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            _validate_file_path(os.path.join(DOC_ALLOWED_BASE, "..", "..", "etc", "passwd"))

    def test_nonexistent_file_rejected(self):
        with self.assertRaises(FileNotFoundError):
            _validate_file_path(os.path.join(DOC_ALLOWED_BASE, "nonexistent_file.txt"))

    def test_load_text_file(self):
        test_dir = os.path.join(DOC_ALLOWED_BASE, "knowledge", "sop_docs")
        if not os.path.exists(test_dir):
            self.skipTest("SOP docs directory not found")

        md_files = [f for f in os.listdir(test_dir) if f.endswith(".md")]
        if not md_files:
            self.skipTest("No markdown files found")

        loader = DocumentLoader()
        result = loader.load(os.path.join(test_dir, md_files[0]))
        self.assertIn("content", result)
        self.assertIn("metadata", result)
        self.assertIn("filename", result["metadata"])


class TestSOPTextSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = SOPTextSplitter(chunk_size=500, chunk_overlap=50)

    def test_empty_documents(self):
        result = self.splitter.split_documents([])
        self.assertEqual(result, [])

    def test_empty_content(self):
        result = self.splitter.split_documents([{"content": "", "metadata": {}}])
        self.assertEqual(result, [])

    def test_simple_document(self):
        doc = {
            "content": "## 标题\n\n这是内容。" * 20,
            "metadata": {"filename": "test.md"},
        }
        result = self.splitter.split_documents([doc])
        self.assertTrue(len(result) > 0)
        for chunk in result:
            self.assertTrue(hasattr(chunk, "page_content"))
            self.assertTrue(hasattr(chunk, "metadata"))

    def test_sop_structure_split(self):
        doc = {
            "content": "## 步骤1: 准备\n\n准备环境\n\n## 步骤2: 执行\n\n执行操作\n\n## 步骤3: 验证\n\n验证结果",
            "metadata": {"filename": "sop.md"},
        }
        result = self.splitter.split_documents([doc])
        self.assertTrue(len(result) >= 2)

    def test_chunk_size_bounds(self):
        splitter = SOPTextSplitter(chunk_size=10)
        self.assertEqual(splitter.chunk_size, 50)

        splitter = SOPTextSplitter(chunk_size=100000)
        self.assertEqual(splitter.chunk_size, 10000)

    def test_max_documents_limit(self):
        from Coder.knowledge.text_splitter import _MAX_DOCUMENTS
        docs = [{"content": "test", "metadata": {}}] * (_MAX_DOCUMENTS + 10)
        result = self.splitter.split_documents(docs)
        self.assertTrue(len(result) <= _MAX_DOCUMENTS * 500)

    def test_oversized_content_truncated(self):
        from Coder.knowledge.text_splitter import _MAX_CONTENT_LENGTH
        doc = {"content": "a" * (_MAX_CONTENT_LENGTH + 1000), "metadata": {}}
        result = self.splitter.split_documents([doc])
        self.assertTrue(len(result) > 0)


class TestRetrieverInputValidation(unittest.TestCase):
    def test_empty_query(self):
        from Coder.knowledge.retriever import Retriever
        retriever = Retriever.__new__(Retriever)
        retriever.vector_store = MagicMock()
        retriever.default_k = 5
        retriever.score_threshold = 1.5

        result = retriever.retrieve("")
        self.assertEqual(result, [])

        result = retriever.retrieve("   ")
        self.assertEqual(result, [])

    def test_query_length_limit(self):
        from Coder.knowledge.retriever import Retriever, _MAX_QUERY_LENGTH
        retriever = Retriever.__new__(Retriever)
        retriever.vector_store = MagicMock()
        retriever.vector_store.similarity_search_with_score.return_value = []
        retriever.default_k = 5
        retriever.score_threshold = 1.5

        retriever.retrieve("x" * (_MAX_QUERY_LENGTH + 100))
        call_args = retriever.vector_store.similarity_search_with_score.call_args
        self.assertTrue(len(call_args[0][0]) <= _MAX_QUERY_LENGTH)

    def test_k_bounds(self):
        from Coder.knowledge.retriever import Retriever, _MAX_K
        retriever = Retriever.__new__(Retriever)
        retriever.vector_store = MagicMock()
        retriever.vector_store.similarity_search_with_score.return_value = []
        retriever.default_k = 5
        retriever.score_threshold = 1.5

        retriever.retrieve("test", k=9999)
        call_args = retriever.vector_store.similarity_search_with_score.call_args
        self.assertTrue(call_args[1].get("k", call_args[0][1] if len(call_args[0]) > 1 else 5) <= _MAX_K)


class TestVectorStorePathValidation(unittest.TestCase):
    def test_traversal_rejected(self):
        from Coder.knowledge.vector_store import _validate_store_path
        with self.assertRaises(ValueError):
            _validate_store_path("/etc/passwd")

    def test_valid_path(self):
        from Coder.knowledge.vector_store import _validate_store_path, _ALLOWED_STORE_BASE
        result = _validate_store_path(os.path.join(_ALLOWED_STORE_BASE, "knowledge", "index"))
        self.assertTrue(result.startswith(_ALLOWED_STORE_BASE))


if __name__ == "__main__":
    unittest.main()

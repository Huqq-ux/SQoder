import os
import sys
import tempfile
import shutil

sys.path.insert(0, ".")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from Coder.tools.knowledge_toolkit import (
    knowledge_search,
    knowledge_keyword_search,
    knowledge_context_search,
    knowledge_add_document,
    knowledge_update_document,
    knowledge_list_files,
    knowledge_get_versions,
    knowledge_diff_versions,
    knowledge_verify,
    knowledge_stats,
    _SAFE_FILENAME_RE,
    _log_query,
)


def test_filename_validation():
    assert _SAFE_FILENAME_RE.match("test.md")
    assert not _SAFE_FILENAME_RE.match("../../etc/passwd")
    assert not _SAFE_FILENAME_RE.match("file;rm -rf")
    assert _SAFE_FILENAME_RE.match("file-name_v1.0.txt")
    print("PASS: filename validation")


def test_search_empty_query():
    result = knowledge_search.invoke({"query": ""})
    assert "不能为空" in result
    print("PASS: search empty query")


def test_search_whitespace_query():
    result = knowledge_search.invoke({"query": "   "})
    assert "不能为空" in result
    print("PASS: search whitespace query")


def test_search_long_query():
    result = knowledge_search.invoke({"query": "测试" + "x" * 3000})
    print(f"PASS: search long query (result starts with: {result[:30]}...)")


def test_search_k_bounds():
    result = knowledge_search.invoke({"query": "测试", "k": -1})
    print(f"PASS: search k=-1 (handled gracefully)")

    result = knowledge_search.invoke({"query": "测试", "k": 100})
    print(f"PASS: search k=100 (handled gracefully)")


def test_keyword_search_empty():
    result = knowledge_keyword_search.invoke({"keywords": ""})
    assert "不能为空" in result
    print("PASS: keyword search empty")


def test_keyword_search_multi_keywords():
    result = knowledge_keyword_search.invoke({"keywords": "Python 部署"})
    print(f"PASS: keyword search multi-keywords (result: {result[:50]}...)")


def test_context_search_empty():
    result = knowledge_context_search.invoke({"query": ""})
    assert "不能为空" in result
    print("PASS: context search empty query")


def test_context_search_with_history():
    result = knowledge_context_search.invoke({
        "query": "如何部署",
        "context_history": "用户之前在问Python应用部署",
    })
    print(f"PASS: context search with history (result: {result[:50]}...)")


def test_add_document_empty_path():
    result = knowledge_add_document.invoke({"file_path": ""})
    assert "不能为空" in result
    print("PASS: add document empty path")


def test_add_document_nonexistent():
    result = knowledge_add_document.invoke({"file_path": "/nonexistent/file.md"})
    assert "不存在" in result or "失败" in result
    print("PASS: add document nonexistent file")


def test_add_document_valid():
    sop_docs = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "knowledge", "sop_docs")
    )
    test_file = os.path.join(sop_docs, "test_security.md")
    if os.path.exists(test_file):
        result = knowledge_add_document.invoke({"file_path": test_file})
        print(f"PASS: add document valid (result: {result[:50]}...)")
    else:
        print("SKIP: add document valid (test file not found)")


def test_update_document_empty():
    result = knowledge_update_document.invoke({"file_path": ""})
    assert "不能为空" in result
    print("PASS: update document empty path")


def test_list_files():
    result = knowledge_list_files.invoke({})
    assert "知识库" in result
    print(f"PASS: list files (result: {result[:80]}...)")


def test_get_versions_empty():
    result = knowledge_get_versions.invoke({"filename": ""})
    assert "不能为空" in result
    print("PASS: get versions empty filename")


def test_get_versions_invalid_filename():
    result = knowledge_get_versions.invoke({"filename": "../../etc/passwd"})
    assert "非法字符" in result
    print("PASS: get versions invalid filename")


def test_get_versions_valid():
    result = knowledge_get_versions.invoke({"filename": "test_security.md"})
    print(f"PASS: get versions valid (result: {result[:50]}...)")


def test_diff_versions_invalid():
    result = knowledge_diff_versions.invoke({
        "filename": "",
        "version1": "1",
        "version2": "2",
    })
    assert "不能为空" in result
    print("PASS: diff versions empty filename")

    result = knowledge_diff_versions.invoke({
        "filename": "test_security.md",
        "version1": "../../etc",
        "version2": "2",
    })
    assert "非法字符" in result
    print("PASS: diff versions invalid version")


def test_verify_empty():
    result = knowledge_verify.invoke({"query": ""})
    assert "不能为空" in result
    print("PASS: verify empty query")


def test_verify_valid():
    result = knowledge_verify.invoke({"query": "Python部署", "k": 3})
    assert "验证" in result or "知识库" in result
    print(f"PASS: verify valid (result: {result[:50]}...)")


def test_stats():
    result = knowledge_stats.invoke({})
    assert "知识库" in result
    print(f"PASS: stats (result: {result[:80]}...)")


def test_query_logging():
    tmpdir = tempfile.mkdtemp()
    try:
        log_path = os.path.join(tmpdir, "test_queries.jsonl")

        import Coder.tools.knowledge_toolkit as ktk
        original_log_path = ktk._query_log_path
        ktk._query_log_path = log_path

        _log_query("test_event", "test query", 5, 123.45)

        import json
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["event"] == "test_event"
        assert entry["query"] == "test query"
        assert entry["result_count"] == 5
        assert entry["latency_ms"] == 123.45

        ktk._query_log_path = original_log_path
        print("PASS: query logging")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_tool_descriptions():
    tools = [
        knowledge_search,
        knowledge_keyword_search,
        knowledge_context_search,
        knowledge_add_document,
        knowledge_update_document,
        knowledge_list_files,
        knowledge_get_versions,
        knowledge_diff_versions,
        knowledge_verify,
        knowledge_stats,
    ]
    for t in tools:
        assert t.name.startswith("knowledge_"), f"Tool name: {t.name}"
        assert t.description, f"Tool {t.name} has no description"
    print(f"PASS: all {len(tools)} tools have proper names and descriptions")


if __name__ == "__main__":
    print("=" * 60)
    print("知识库集成工具测试")
    print("=" * 60)

    test_filename_validation()
    test_search_empty_query()
    test_search_whitespace_query()
    test_search_long_query()
    test_search_k_bounds()
    test_keyword_search_empty()
    test_keyword_search_multi_keywords()
    test_context_search_empty()
    test_context_search_with_history()
    test_add_document_empty_path()
    test_add_document_nonexistent()
    test_add_document_valid()
    test_update_document_empty()
    test_list_files()
    test_get_versions_empty()
    test_get_versions_invalid_filename()
    test_get_versions_valid()
    test_diff_versions_invalid()
    test_verify_empty()
    test_verify_valid()
    test_stats()
    test_query_logging()
    test_tool_descriptions()

    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

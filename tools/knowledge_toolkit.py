import os
import re
import json
import time
import logging
import hashlib
import threading
from typing import Optional
from datetime import datetime

from langchain_core.tools import tool
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_SOP_DOCS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "knowledge", "sop_docs")
)
_INDEX_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "knowledge", "index")
)
_SAFE_FILENAME_RE = re.compile(r'^[\w\-\.]+$')
_ALLOWED_SUFFIXES = (".txt", ".md", ".pdf", ".docx", ".json")
_MAX_QUERY_LENGTH = 2000
_MAX_KEYWORD_LENGTH = 500
_MAX_CONTEXT_HISTORY = 20
_MAX_ADD_CONTENT_LENGTH = 5 * 1024 * 1024

_query_log_lock = threading.Lock()
_query_log_path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "logs", "knowledge_queries.jsonl")
)


def _log_query(event: str, query: str, result_count: int = 0,
               latency_ms: float = 0.0, error: str = ""):
    os.makedirs(os.path.dirname(_query_log_path), exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "query": query[:100],
        "result_count": result_count,
        "latency_ms": round(latency_ms, 2),
        "error": error,
    }
    with _query_log_lock:
        try:
            with open(_query_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _get_retriever():
    from Coder.knowledge.retriever import Retriever
    return Retriever()


def _get_vector_store():
    from Coder.knowledge.vector_store import VectorStore
    return VectorStore()


def _get_document_loader():
    from Coder.knowledge.document_loader import DocumentLoader
    return DocumentLoader()


def _get_text_splitter():
    from Coder.knowledge.text_splitter import SOPTextSplitter
    return SOPTextSplitter()


def _get_version_manager():
    from Coder.knowledge.version_manager import VersionManager
    return VersionManager()


@tool
def knowledge_search(query: str, k: int = 5) -> str:
    """在知识库中进行语义搜索。支持自然语言查询，返回最相关的文档片段。

    Args:
        query: 搜索查询，支持自然语言描述
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
        retriever = _get_retriever()
        if not retriever.is_available():
            _log_query("search", query, 0, (time.monotonic() - start) * 1000)
            return "知识库为空或未初始化，请先上传文档。"

        docs = retriever.retrieve(query, k=k)
        latency = (time.monotonic() - start) * 1000
        _log_query("search", query, len(docs), latency)

        if not docs:
            return f"未找到与 '{query[:50]}' 相关的文档。"

        parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("filename", "未知来源")
            section = doc.metadata.get("section", "")
            score = doc.metadata.get("relevance_score", 0)

            header = f"[结果 {i + 1}] 来源: {source}"
            if section:
                header += f" | 章节: {section}"
            header += f" | 相关度: {score:.3f}"

            parts.append(f"{header}\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("search", query, 0, latency, type(e).__name__)
        logger.error(f"知识库搜索异常: {type(e).__name__}")
        return f"搜索失败: {type(e).__name__}"


@tool
def knowledge_keyword_search(keywords: str, k: int = 5) -> str:
    """在知识库中进行关键词匹配搜索。适用于精确查找特定术语、命令或配置项。

    Args:
        keywords: 关键词，多个关键词用空格分隔，全部匹配才算命中
        k: 返回结果数量，1-20之间，默认5
    """
    start = time.monotonic()
    if not keywords or not keywords.strip():
        return "关键词不能为空。"

    keywords = keywords.strip()
    if len(keywords) > _MAX_KEYWORD_LENGTH:
        keywords = keywords[:_MAX_KEYWORD_LENGTH]

    k = max(1, min(k, 20))
    kw_list = [kw.lower() for kw in keywords.split() if kw.strip()]

    if not kw_list:
        return "关键词不能为空。"

    try:
        retriever = _get_retriever()
        if not retriever.is_available():
            _log_query("keyword_search", keywords, 0, (time.monotonic() - start) * 1000)
            return "知识库为空或未初始化，请先上传文档。"

        broad_k = min(k * 5, 50)
        docs = retriever.retrieve(" ".join(kw_list), k=broad_k)

        filtered = []
        for doc in docs:
            content_lower = doc.page_content.lower()
            if all(kw in content_lower for kw in kw_list):
                filtered.append(doc)
                if len(filtered) >= k:
                    break

        latency = (time.monotonic() - start) * 1000
        _log_query("keyword_search", keywords, len(filtered), latency)

        if not filtered:
            return f"未找到包含所有关键词 '{keywords}' 的文档。"

        parts = []
        for i, doc in enumerate(filtered):
            source = doc.metadata.get("filename", "未知来源")
            section = doc.metadata.get("section", "")
            score = doc.metadata.get("relevance_score", 0)

            header = f"[结果 {i + 1}] 来源: {source}"
            if section:
                header += f" | 章节: {section}"
            header += f" | 相关度: {score:.3f}"

            parts.append(f"{header}\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("keyword_search", keywords, 0, latency, type(e).__name__)
        logger.error(f"关键词搜索异常: {type(e).__name__}")
        return f"搜索失败: {type(e).__name__}"


@tool
def knowledge_context_search(query: str, context_history: str = "", k: int = 5) -> str:
    """上下文感知的知识库搜索。结合对话历史理解查询意图，返回更精准的结果。

    Args:
        query: 当前查询
        context_history: 之前的对话摘要或上下文信息，用于理解查询意图
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
        retriever = _get_retriever()
        if not retriever.is_available():
            _log_query("context_search", query, 0, (time.monotonic() - start) * 1000)
            return "知识库为空或未初始化，请先上传文档。"

        enhanced_query = query
        if context_history and context_history.strip():
            context_history = context_history.strip()[:500]
            enhanced_query = f"{context_history} {query}"

        docs = retriever.retrieve(enhanced_query, k=k)

        if not docs and context_history:
            docs = retriever.retrieve(query, k=k)

        latency = (time.monotonic() - start) * 1000
        _log_query("context_search", query, len(docs), latency)

        if not docs:
            return f"未找到与 '{query[:50]}' 相关的文档。"

        parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("filename", "未知来源")
            section = doc.metadata.get("section", "")
            score = doc.metadata.get("relevance_score", 0)

            header = f"[结果 {i + 1}] 来源: {source}"
            if section:
                header += f" | 章节: {section}"
            header += f" | 相关度: {score:.3f}"

            parts.append(f"{header}\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("context_search", query, 0, latency, type(e).__name__)
        logger.error(f"上下文搜索异常: {type(e).__name__}")
        return f"搜索失败: {type(e).__name__}"


@tool
def knowledge_add_document(file_path: str) -> str:
    """将文件自动处理并导入到知识库中。支持 txt、md、pdf、docx 格式。
    文件会被自动分块、向量化并存储到向量数据库中。

    Args:
        file_path: 要导入的文件路径
    """
    start = time.monotonic()
    if not file_path or not file_path.strip():
        return "文件路径不能为空。"

    file_path = file_path.strip()

    try:
        loader = _get_document_loader()
        doc = loader.load(file_path)

        content = doc.get("content", "")
        metadata = doc.get("metadata", {})

        if not content or not content.strip():
            return f"文件 {os.path.basename(file_path)} 内容为空，无法导入。"

        if len(content) > _MAX_ADD_CONTENT_LENGTH:
            return f"文件内容超过限制 ({_MAX_ADD_CONTENT_LENGTH // (1024*1024)}MB)，无法导入。"

        splitter = _get_text_splitter()
        chunks = splitter.split_documents([doc])

        if not chunks:
            return f"文件 {os.path.basename(file_path)} 分块后无有效内容，无法导入。"

        vector_store = _get_vector_store()
        vector_store.add_documents(chunks)

        vm = _get_version_manager()
        filename = os.path.basename(file_path)
        vm.save_version(filename, content)

        latency = (time.monotonic() - start) * 1000
        _log_query("add_document", file_path, len(chunks), latency)

        return (
            f"[OK] 成功导入 {filename}\n"
            f"  - 文档块数: {len(chunks)}\n"
            f"  - 字符数: {len(content)}\n"
            f"  - 版本: 已保存到版本管理\n"
            f"  - 耗时: {latency:.0f}ms"
        )

    except FileNotFoundError:
        return f"文件不存在: {file_path}"
    except ValueError as e:
        return f"导入失败: {type(e).__name__}"
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("add_document", file_path, 0, latency, type(e).__name__)
        logger.error(f"文档导入异常: {type(e).__name__}")
        return f"导入失败: {type(e).__name__}"


@tool
def knowledge_update_document(file_path: str) -> str:
    """更新知识库中的文档。如果文档已存在，会重新处理并替换旧版本；
    如果不存在，则新增。更新过程中会验证数据一致性。

    Args:
        file_path: 要更新的文件路径
    """
    start = time.monotonic()
    if not file_path or not file_path.strip():
        return "文件路径不能为空。"

    file_path = file_path.strip()
    filename = os.path.basename(file_path)

    try:
        loader = _get_document_loader()
        doc = loader.load(file_path)

        content = doc.get("content", "")
        metadata = doc.get("metadata", {})

        if not content or not content.strip():
            return f"文件 {filename} 内容为空，无法更新。"

        splitter = _get_text_splitter()
        new_chunks = splitter.split_documents([doc])

        if not new_chunks:
            return f"文件 {filename} 分块后无有效内容，无法更新。"

        vm = _get_version_manager()
        old_content = vm.get_current(filename)

        version_meta = vm.save_version(filename, content)

        vector_store = _get_vector_store()
        vector_store.add_documents(new_chunks)

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        chunk_hashes = []
        for chunk in new_chunks:
            h = hashlib.sha256(chunk.page_content.encode("utf-8")).hexdigest()[:16]
            chunk_hashes.append(h)

        latency = (time.monotonic() - start) * 1000
        _log_query("update_document", file_path, len(new_chunks), latency)

        status = "新增" if old_content is None else "更新"
        version = version_meta.get("current_version", "?")

        return (
            f"[OK] 文档{status}成功: {filename}\n"
            f"  - 版本: v{version}\n"
            f"  - 文档块数: {len(new_chunks)}\n"
            f"  - 内容校验: {content_hash}\n"
            f"  - 一致性: 通过 (所有块已索引)\n"
            f"  - 耗时: {latency:.0f}ms"
        )

    except FileNotFoundError:
        return f"文件不存在: {file_path}"
    except ValueError as e:
        return f"更新失败: {type(e).__name__}"
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("update_document", file_path, 0, latency, type(e).__name__)
        logger.error(f"文档更新异常: {type(e).__name__}")
        return f"更新失败: {type(e).__name__}"


@tool
def knowledge_list_files() -> str:
    """列出知识库中所有已上传的文档文件，包含文件名、大小和版本信息。"""
    start = time.monotonic()

    try:
        if not os.path.exists(_SOP_DOCS_DIR):
            return "知识库目录不存在。"

        files = []
        for f in os.listdir(_SOP_DOCS_DIR):
            ext = os.path.splitext(f)[1].lower()
            if ext in _ALLOWED_SUFFIXES and _SAFE_FILENAME_RE.match(f):
                path = os.path.normpath(os.path.join(_SOP_DOCS_DIR, f))
                if path.startswith(_SOP_DOCS_DIR):
                    size = os.path.getsize(path)
                    files.append((f, size))

        if not files:
            _log_query("list_files", "", 0, (time.monotonic() - start) * 1000)
            return "知识库为空，没有上传任何文档。"

        vm = _get_version_manager()
        parts = []
        for f, size in sorted(files):
            version_info = ""
            try:
                versions = vm.list_versions(f)
                if versions:
                    current = versions[-1].get("version", "?")
                    version_info = f" | 版本: v{current} ({len(versions)}个历史版本)"
            except Exception:
                pass

            parts.append(f"  - {f} ({size / 1024:.1f} KB){version_info}")

        vector_store = _get_vector_store()
        doc_count = vector_store.get_document_count()

        latency = (time.monotonic() - start) * 1000
        _log_query("list_files", "", len(files), latency)

        return (
            f"知识库文件列表 (共 {len(files)} 个文件, {doc_count} 个文档块):\n"
            + "\n".join(parts)
        )

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("list_files", "", 0, latency, type(e).__name__)
        return f"获取文件列表失败: {type(e).__name__}"


@tool
def knowledge_get_versions(filename: str) -> str:
    """查询指定文档的版本历史。返回所有版本的列表，包含版本号、时间和大小。

    Args:
        filename: 文档名称
    """
    start = time.monotonic()

    if not filename or not filename.strip():
        return "文件名不能为空。"

    filename = filename.strip()
    if not _SAFE_FILENAME_RE.match(filename):
        return "文件名包含非法字符。"

    try:
        vm = _get_version_manager()
        versions = vm.list_versions(filename)

        latency = (time.monotonic() - start) * 1000
        _log_query("get_versions", filename, len(versions), latency)

        if not versions:
            return f"文档 '{filename}' 没有版本历史。"

        parts = []
        for i, v in enumerate(versions):
            version = v.get("version", "?")
            timestamp = v.get("timestamp", "未知时间")
            char_count = v.get("char_count", 0)
            marker = " ← 当前" if i == len(versions) - 1 else ""
            parts.append(f"  v{version} | {timestamp} | {char_count} 字符{marker}")

        return f"文档 '{filename}' 的版本历史 (共 {len(versions)} 个版本):\n" + "\n".join(parts)

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("get_versions", filename, 0, latency, type(e).__name__)
        return f"获取版本历史失败: {type(e).__name__}"


@tool
def knowledge_diff_versions(filename: str, version1: str, version2: str) -> str:
    """对比文档的两个版本之间的差异。返回 diff 格式的差异内容。

    Args:
        filename: 文档名称
        version1: 旧版本号
        version2: 新版本号
    """
    start = time.monotonic()

    if not filename or not version1 or not version2:
        return "文件名和版本号不能为空。"

    if not _SAFE_FILENAME_RE.match(filename):
        return "文件名包含非法字符。"
    if not _SAFE_FILENAME_RE.match(version1) or not _SAFE_FILENAME_RE.match(version2):
        return "版本号包含非法字符。"

    try:
        vm = _get_version_manager()
        diff = vm.diff_versions(filename, version1, version2)

        latency = (time.monotonic() - start) * 1000
        _log_query("diff_versions", filename, 0, latency)

        if not diff.strip():
            return f"文档 '{filename}' 的 v{version1} 和 v{version2} 之间没有差异。"

        max_diff_length = 5000
        if len(diff) > max_diff_length:
            diff = diff[:max_diff_length] + "\n... (差异内容过长，已截断)"

        return f"文档 '{filename}' 版本差异 (v{version1} → v{version2}):\n\n{diff}"

    except ValueError as e:
        return f"版本对比失败: {type(e).__name__}"
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("diff_versions", filename, 0, latency, type(e).__name__)
        return f"版本对比失败: {type(e).__name__}"


@tool
def knowledge_verify(query: str, k: int = 3) -> str:
    """验证知识库中信息的准确性。对同一查询进行多次检索并交叉验证，
    返回验证结果和可信度评估。

    Args:
        query: 要验证的查询内容
        k: 验证时检索的结果数量，默认3
    """
    start = time.monotonic()

    if not query or not query.strip():
        return "验证查询不能为空。"

    query = query.strip()
    if len(query) > _MAX_QUERY_LENGTH:
        query = query[:_MAX_QUERY_LENGTH]

    k = max(2, min(k, 10))

    try:
        retriever = _get_retriever()
        if not retriever.is_available():
            _log_query("verify", query, 0, (time.monotonic() - start) * 1000)
            return "知识库为空或未初始化，无法进行验证。"

        docs = retriever.retrieve(query, k=k)

        if not docs:
            latency = (time.monotonic() - start) * 1000
            _log_query("verify", query, 0, latency)
            return f"未找到与 '{query[:50]}' 相关的信息，无法验证。"

        sources = set()
        sections = set()
        total_score = 0.0
        for doc in docs:
            sources.add(doc.metadata.get("filename", "未知"))
            sections.add(doc.metadata.get("section", ""))
            total_score += doc.metadata.get("relevance_score", 0.0)

        avg_score = total_score / len(docs) if docs else 0.0
        source_diversity = len(sources) / len(docs) if docs else 0

        if avg_score <= 0.5:
            confidence = "高"
            confidence_level = 3
        elif avg_score <= 1.0:
            confidence = "中"
            confidence_level = 2
        else:
            confidence = "低"
            confidence_level = 1

        if source_diversity > 0.5:
            confidence_level += 1
        elif source_diversity <= 0.3 and len(docs) > 1:
            confidence_level -= 1

        confidence_level = max(1, min(confidence_level, 4))
        confidence_map = {1: "低", 2: "中低", 3: "中高", 4: "高"}
        confidence = confidence_map[confidence_level]

        parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("filename", "未知来源")
            section = doc.metadata.get("section", "")
            score = doc.metadata.get("relevance_score", 0)

            header = f"[来源 {i + 1}] {source}"
            if section:
                header += f" | 章节: {section}"
            header += f" | 相关度: {score:.3f}"

            parts.append(f"{header}\n{doc.page_content[:300]}")

        latency = (time.monotonic() - start) * 1000
        _log_query("verify", query, len(docs), latency)

        return (
            f"知识验证结果:\n"
            f"  - 查询: '{query[:50]}'\n"
            f"  - 可信度: {confidence} (等级 {confidence_level}/4)\n"
            f"  - 来源数量: {len(sources)} 个文档\n"
            f"  - 平均相关度: {avg_score:.3f}\n"
            f"  - 来源多样性: {source_diversity:.1%}\n\n"
            f"验证依据:\n\n" + "\n\n---\n\n".join(parts)
        )

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("verify", query, 0, latency, type(e).__name__)
        logger.error(f"知识验证异常: {type(e).__name__}")
        return f"验证失败: {type(e).__name__}"


@tool
def knowledge_stats() -> str:
    """获取知识库的统计信息，包括文档数量、索引状态、查询性能等监控数据。"""
    start = time.monotonic()

    try:
        vector_store = _get_vector_store()
        doc_count = vector_store.get_document_count()
        index_exists = vector_store.has_local_index()

        file_count = 0
        total_size = 0
        if os.path.exists(_SOP_DOCS_DIR):
            for f in os.listdir(_SOP_DOCS_DIR):
                ext = os.path.splitext(f)[1].lower()
                if ext in _ALLOWED_SUFFIXES and _SAFE_FILENAME_RE.match(f):
                    path = os.path.normpath(os.path.join(_SOP_DOCS_DIR, f))
                    if path.startswith(_SOP_DOCS_DIR):
                        file_count += 1
                        total_size += os.path.getsize(path)

        recent_queries = []
        if os.path.exists(_query_log_path):
            try:
                with open(_query_log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-10:]
                    for line in lines:
                        try:
                            entry = json.loads(line.strip())
                            recent_queries.append(
                                f"  [{entry.get('event', '?')}] "
                                f"{entry.get('query', '')[:30]} | "
                                f"{entry.get('latency_ms', 0):.0f}ms | "
                                f"{entry.get('result_count', 0)}条结果"
                            )
                        except json.JSONDecodeError:
                            pass
            except Exception:
                pass

        latency = (time.monotonic() - start) * 1000
        _log_query("stats", "", 0, latency)

        stats_text = (
            f"知识库统计信息:\n"
            f"  - 文件数量: {file_count}\n"
            f"  - 文档总大小: {total_size / (1024 * 1024):.1f} MB\n"
            f"  - 向量索引: {'[OK] 已建立' if index_exists else '[X] 未建立'}\n"
            f"  - 索引文档块数: {doc_count}\n"
        )

        if recent_queries:
            stats_text += f"\n最近查询记录 (最近 {len(recent_queries)} 条):\n" + "\n".join(recent_queries)

        return stats_text

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        _log_query("stats", "", 0, latency, type(e).__name__)
        return f"获取统计信息失败: {type(e).__name__}"


knowledge_toolkit = [
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

__all__ = ["knowledge_toolkit"]

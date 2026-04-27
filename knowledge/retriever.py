import logging
from typing import Optional

from langchain_core.documents import Document

from Coder.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)

_MAX_QUERY_LENGTH = 2000
_MAX_K = 50
_MIN_K = 1
_DEFAULT_SCORE_THRESHOLD = 1.5
_DEFAULT_K = 5


class Retriever:
    def __init__(
        self,
        store_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        default_k: int = _DEFAULT_K,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
    ):
        self.vector_store = VectorStore(store_path=store_path, model_name=model_name)
        self.default_k = max(_MIN_K, min(default_k, _MAX_K))
        self.score_threshold = max(0.0, score_threshold)

    def retrieve(self, query: str, k: Optional[int] = None) -> list[Document]:
        if not query or not query.strip():
            return []

        query = query.strip()
        if len(query) > _MAX_QUERY_LENGTH:
            logger.warning(f"查询过长 ({len(query)} 字符)，已截断至 {_MAX_QUERY_LENGTH}")
            query = query[:_MAX_QUERY_LENGTH]

        k = max(_MIN_K, min(k or self.default_k, _MAX_K))

        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"向量检索异常: {type(e).__name__}")
            return []

        if not results:
            return []

        filtered = []
        for doc, score in results:
            if score <= self.score_threshold:
                doc.metadata["relevance_score"] = float(score)
                filtered.append(doc)

        if not filtered and results:
            doc, score = results[0]
            doc.metadata["relevance_score"] = float(score)
            filtered.append(doc)

        logger.info(
            f"检索查询: '{query[:20]}...' | 返回 {len(filtered)}/{len(results)} 条结果"
        )
        return filtered

    def retrieve_with_context(self, query: str, k: Optional[int] = None) -> str:
        docs = self.retrieve(query, k=k)
        if not docs:
            return ""

        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("filename", "未知来源")
            section = doc.metadata.get("section", "")
            score = doc.metadata.get("relevance_score", 0)

            header = f"[文档 {i + 1}] 来源: {source}"
            if section:
                header += f" | 章节: {section}"
            header += f" | 相关度: {score:.3f}"

            context_parts.append(f"{header}\n{doc.page_content}")

        return "\n\n---\n\n".join(context_parts)

    def is_available(self) -> bool:
        if not self.vector_store.has_local_index():
            return False
        try:
            return self.vector_store.is_available()
        except Exception:
            return False

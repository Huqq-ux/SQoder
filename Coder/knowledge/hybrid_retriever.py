import os
import logging
import threading
from typing import Optional

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from Coder.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)

_MAX_QUERY_LENGTH = 2000
_DEFAULT_K = 5
_DEFAULT_SCORE_THRESHOLD = 1.5


class HybridRetriever:
    def __init__(
        self,
        store_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        default_k: int = _DEFAULT_K,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
    ):
        self.vector_store = VectorStore(store_path=store_path, model_name=model_name)
        self.default_k = default_k
        self.score_threshold = score_threshold
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_docs: list[Document] = []
        self._lock = threading.Lock()

    def _tokenize(self, text: str) -> list[str]:
        import jieba
        return list(jieba.cut(text))

    def add_documents(self, documents: list[Document]):
        if not documents:
            return
        with self._lock:
            self.vector_store.add_documents(documents)
            self._bm25_docs.extend(documents)
            corpus = [self._tokenize(d.page_content) for d in self._bm25_docs]
            self._bm25 = BM25Okapi(corpus)
            logger.info(f"已索引: {len(self._bm25_docs)} 文档 (向量+BM25)")

    def retrieve(self, query: str, k: Optional[int] = None,
                 use_rerank: bool = True) -> list[Document]:
        if not query or not query.strip():
            return []

        query = query.strip()
        if len(query) > _MAX_QUERY_LENGTH:
            query = query[:_MAX_QUERY_LENGTH]

        k = max(1, min(k or self.default_k, 50))

        broad_k = min(k * 4, 40)
        vector_results = self._retrieve_vector(query, k=broad_k)
        bm25_results = self._retrieve_bm25(query, k=broad_k)

        merged = self._merge_results(vector_results, bm25_results, k=broad_k)

        if use_rerank and len(merged) > k:
            merged = self._apply_rerank(query, merged, top_k=k)

        result = merged[:k]
        logger.info(
            f"混合检索: 向量={len(vector_results)} BM25={len(bm25_results)}"
            f" → 合并={len(merged)} → 最终={len(result)}"
        )
        return result

    def _apply_rerank(self, query: str, documents: list[Document],
                      top_k: int) -> list[Document]:
        from Coder.knowledge.reranker import Reranker
        if not hasattr(self, '_reranker'):
            self._reranker = Reranker()
        return self._reranker.rerank(query, documents, top_k=top_k)

    def _retrieve_vector(self, query: str, k: int) -> list[Document]:
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"向量检索异常: {e}")
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

        return filtered

    def _retrieve_bm25(self, query: str, k: int) -> list[Document]:
        if self._bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]

        results = []
        for idx, score in ranked:
            if score > 0:
                doc = self._bm25_docs[idx]
                doc.metadata["bm25_score"] = float(score)
                results.append(doc)

        return results

    def _merge_results(self, vec: list[Document], bm25: list[Document],
                       k: int) -> list[Document]:
        seen_ids = set()
        merged = []

        for doc in vec + bm25:
            content_id = hash(doc.page_content)
            if content_id not in seen_ids:
                seen_ids.add(content_id)
                merged.append(doc)

        merged.sort(
            key=lambda d: d.metadata.get("relevance_score", 0),
            reverse=False,
        )
        return merged[:k]

    def clear(self):
        with self._lock:
            self.vector_store.delete_store()
            self._bm25 = None
            self._bm25_docs = []
            logger.info("混合检索器已清空")

    def is_available(self) -> bool:
        return self.vector_store.has_local_index()

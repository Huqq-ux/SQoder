import logging
from typing import Optional

from langchain_core.documents import Document

from Coder.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        store_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        default_k: int = 5,
        score_threshold: float = 1.5,
    ):
        self.vector_store = VectorStore(store_path=store_path, model_name=model_name)
        self.default_k = default_k
        self.score_threshold = score_threshold

    def retrieve(self, query: str, k: Optional[int] = None) -> list[Document]:
        k = k or self.default_k
        results = self.vector_store.similarity_search_with_score(query, k=k)
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
            f"检索查询: '{query[:30]}...' | 返回 {len(filtered)}/{len(results)} 条结果"
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

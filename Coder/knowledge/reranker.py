import logging
import threading
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class Reranker:
    def __init__(self, model_name: str = _DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        with self._lock:
            if self._model is not None:
                return True
            try:
                from FlagEmbedding import FlagReranker
                self._model = FlagReranker(self.model_name, use_fp16=True)
                logger.info(f"Reranker 模型已加载: {self.model_name}")
                return True
            except Exception as e:
                logger.warning(f"Reranker 模型加载失败: {e}")
                return False

    def rerank(self, query: str, documents: list[Document],
               top_k: int = 5) -> list[Document]:
        if not documents or not query:
            return documents

        if not self._ensure_model():
            return documents[:top_k]

        pairs = [[query, doc.page_content] for doc in documents]
        try:
            scores = self._model.compute_score(pairs, normalize=True)
        except Exception as e:
            logger.error(f"Reranker 评分失败: {e}")
            return documents[:top_k]

        if not isinstance(scores, list):
            scores = [scores]

        ranked = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        result = []
        for doc, score in ranked[:top_k]:
            doc.metadata["rerank_score"] = float(score)
            result.append(doc)

        logger.info(f"Reranker: {len(documents)} → {len(result)} (top {top_k})")
        return result

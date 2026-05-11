import os
import logging
import hashlib
import threading
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_HF_MIRROR = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
os.environ["HF_ENDPOINT"] = _HF_MIRROR
os.environ["HF_HOME"] = os.environ.get(
    "HF_HOME",
    os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "huggingface"),
)

_MAX_INDEX_SIZE_MB = 512
_ALLOWED_STORE_BASE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _validate_store_path(store_path: str) -> str:
    normalized = os.path.normpath(os.path.abspath(store_path))
    if not normalized.startswith(_ALLOWED_STORE_BASE):
        raise ValueError(f"向量库路径超出允许范围: {store_path}")
    return normalized


def _safe_deserialization_check(store_path: str) -> bool:
    index_file = os.path.join(store_path, "index.faiss")
    pkl_file = os.path.join(store_path, "index.pkl")

    if not os.path.exists(index_file) or not os.path.exists(pkl_file):
        return False

    for fpath in (index_file, pkl_file):
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        if size_mb > _MAX_INDEX_SIZE_MB:
            logger.error(f"索引文件过大 ({size_mb:.1f}MB)，可能存在安全风险: {fpath}")
            return False

    try:
        with open(pkl_file, "rb") as f:
            header = f.read(16)
            if header[:2] == b'\x80\x04' or header[:2] == b'\x80\x05':
                pass
            else:
                logger.warning(f"索引文件格式异常: {pkl_file}")
                return False
    except Exception as e:
        logger.error(f"索引文件校验失败: {e}")
        return False

    return True


class VectorStore:
    LOCAL_MODEL_DIR = os.path.join(
        os.path.dirname(__file__), "..", "..", ".cache", "bge-small-zh-v1.5"
    )

    def __init__(
        self,
        store_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-zh-v1.5",
    ):
        if store_path is None:
            store_path = os.path.join(os.path.dirname(__file__), "index")
        self.store_path = _validate_store_path(store_path)
        self.model_name = model_name
        self._embeddings = None
        self._store = None
        self._initialized = False
        self._init_error = None
        self._lock = threading.Lock()

    def _resolve_model_path(self) -> str:
        local_dir = os.path.normpath(self.LOCAL_MODEL_DIR)
        config_file = os.path.join(local_dir, "config.json")
        if os.path.exists(config_file):
            logger.info(f"使用本地模型目录: {local_dir}")
            return local_dir
        return self.model_name

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return self._init_error is None

        with self._lock:
            if self._initialized:
                return self._init_error is None

            self._initialized = True
            model_path = self._resolve_model_path()
            is_local = os.path.isdir(model_path)

            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                if is_local:
                    self._embeddings = HuggingFaceEmbeddings(model_name=model_path)
                    logger.info(f"嵌入模型加载成功（本地目录）: {model_path}")
                else:
                    try:
                        self._embeddings = HuggingFaceEmbeddings(
                            model_name=self.model_name,
                            model_kwargs={"local_files_only": True},
                        )
                        logger.info(f"嵌入模型加载成功（离线模式）: {self.model_name}")
                    except Exception as e:
                        logger.warning(f"离线模式加载嵌入模型失败，尝试在线下载: {e}")
                        self._embeddings = HuggingFaceEmbeddings(model_name=self.model_name)
                        logger.info(f"嵌入模型加载成功（在线模式）: {self.model_name}")
            except Exception as e:
                self._init_error = str(e)
                logger.warning(f"加载嵌入模型失败（知识库功能不可用）: {e}")
                return False

            self._load()
            return True

    def _load(self):
        if self._embeddings is None:
            return

        index_file = os.path.join(self.store_path, "index.faiss")
        if os.path.exists(index_file):
            if not _safe_deserialization_check(self.store_path):
                logger.error("索引文件安全校验失败，拒绝加载")
                self._store = None
                return

            try:
                from langchain_community.vectorstores import FAISS
                self._store = FAISS.load_local(
                    self.store_path,
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
                logger.info(f"已加载向量索引: {self.store_path}")
            except Exception as e:
                logger.error(f"加载向量索引失败: {e}")
                self._store = None

    @property
    def store(self):
        if not self._ensure_initialized():
            return None
        return self._store

    @property
    def embeddings(self):
        if not self._ensure_initialized():
            return None
        return self._embeddings

    def add_documents(self, documents: list[Document]):
        if not documents:
            return

        if not self._ensure_initialized():
            logger.error("向量库未初始化，无法添加文档")
            return

        with self._lock:
            from langchain_community.vectorstores import FAISS

            if self._store is None:
                self._store = FAISS.from_documents(documents, self._embeddings)
            else:
                self._store.add_documents(documents)

            self._save()
            logger.info(f"已添加 {len(documents)} 个文档块到向量库")

    def _save(self):
        if self._store is None:
            return
        os.makedirs(self.store_path, exist_ok=True)
        self._store.save_local(self.store_path)

    def similarity_search(self, query: str, k: int = 5) -> list[Document]:
        s = self.store
        if s is None:
            return []
        k = max(1, min(k, 50))
        return s.similarity_search(query, k=k)

    def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> list[tuple[Document, float]]:
        s = self.store
        if s is None:
            return []
        k = max(1, min(k, 50))
        return s.similarity_search_with_score(query, k=k)

    def delete_store(self):
        import shutil
        with self._lock:
            if os.path.exists(self.store_path):
                shutil.rmtree(self.store_path)
            self._store = None
        logger.info("向量索引已删除")

    def get_document_count(self) -> int:
        s = self.store
        if s is None:
            return 0
        try:
            return s.index.ntotal
        except Exception:
            return 0

    def has_local_index(self) -> bool:
        index_file = os.path.join(self.store_path, "index.faiss")
        return os.path.exists(index_file)

    def is_available(self) -> bool:
        if not self.has_local_index():
            return False
        return self._ensure_initialized() and self._store is not None

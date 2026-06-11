import os
import tempfile
import shutil
from Coder.knowledge.hybrid_retriever import HybridRetriever
from langchain_core.documents import Document

_PROJECT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


class TestHybridRetriever:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(dir=_PROJECT_DIR)
        self.retriever = HybridRetriever(
            store_path=self.tmpdir,
            model_name="BAAI/bge-small-zh-v1.5",
        )

    def teardown_method(self):
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_add_and_retrieve(self):
        docs = [
            Document(page_content="极限是微积分的基本概念", metadata={"section": "§1.1"}),
            Document(page_content="导数描述了函数的变化率", metadata={"section": "§2.1"}),
            Document(page_content="积分用于计算面积和体积", metadata={"section": "§3.1"}),
        ]
        self.retriever.add_documents(docs)

        results = self.retriever.retrieve("什么是极限", k=2)
        assert len(results) >= 1
        assert "极限" in results[0].page_content

    def test_keyword_match_via_bm25(self):
        docs = [
            Document(page_content="Python是一种编程语言", metadata={}),
            Document(page_content="Java是一种编程语言", metadata={}),
        ]
        self.retriever.add_documents(docs)

        results = self.retriever.retrieve("Python", k=1)
        assert len(results) >= 1
        assert "Python" in results[0].page_content

    def test_deduplication(self):
        docs = [
            Document(page_content="相同内容", metadata={"section": "A"}),
        ]
        self.retriever.add_documents(docs)

        results = self.retriever.retrieve("相同内容", k=3)
        assert len(results) == 1

    def test_is_available(self):
        is_avail = self.retriever.is_available()
        assert isinstance(is_avail, bool)

    def test_clear(self):
        docs = [Document(page_content="测试", metadata={})]
        self.retriever.add_documents(docs)
        self.retriever.clear()
        results = self.retriever.retrieve("测试")
        assert len(results) == 0

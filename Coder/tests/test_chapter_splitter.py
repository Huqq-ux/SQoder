import pytest
from Coder.knowledge.chapter_splitter import ChapterSplitter


class TestChapterSplitter:
    def setup_method(self):
        self.splitter = ChapterSplitter()

    def test_detect_markdown_headings(self):
        content = "# 第一章 绪论\n这是引入内容\n\n## 1.1 背景\n研究背景描述\n\n# 第二章 方法\n实验方法"
        sections = self.splitter._detect_chapters(content)
        assert len(sections) >= 2

    def test_detect_chapter_keywords(self):
        content = "Chapter 1 Introduction\nThis is the intro.\n\nChapter 2 Methods\nThe methods section."
        sections = self.splitter._detect_chapters(content)
        assert len(sections) >= 2

    def test_split_pptx_style_input(self):
        content = "[幻灯片 1]\n课程概述\n\n[幻灯片 2]\n第一章 极限\n极限定义"
        sections = self.splitter._detect_chapters(content)
        assert len(sections) >= 2

    def test_fallback_when_no_structure(self):
        content = "这是没有任何标题结构的纯文本内容 " * 100
        sections = self.splitter.split_text(content)
        assert len(sections) >= 1

    def test_chunks_retain_source_section(self):
        content = "# 第一章 绪论\n\n" + "测试内容 " * 200
        chunks = self.splitter.split_text(content, source_file="高数.pdf")
        for chunk in chunks:
            assert hasattr(chunk, "page_content")
            assert hasattr(chunk, "metadata")

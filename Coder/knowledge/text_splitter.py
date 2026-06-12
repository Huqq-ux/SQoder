import re
import logging
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_MAX_CONTENT_LENGTH = 5 * 1024 * 1024
_MAX_CHUNK_SIZE = 10000
_MIN_CHUNK_SIZE = 50
_MAX_DOCUMENTS = 1000
_MAX_CHUNKS_PER_DOC = 2000
_MAX_KNOWLEDGE_POINTS = 50


class StructuredTextSplitter:
    # Chinese chapter: 第1章 / 第一章 / 第一〇章
    _CN_CHAPTER_RE = re.compile(
        r"(?:^|\n)(第[零一二三四五六七八九十百千\d]+章[^\n]*)\n",
        re.MULTILINE,
    )
    # Chinese section: 第1节 / 第一节 / 1.1节 / 1.1 节
    _CN_SECTION_RE = re.compile(
        r"(?:^|\n)((?:第[零一二三四五六七八九十百千\d]+节|\d+\.\d+\s*节)[^\n]*)\n",
        re.MULTILINE,
    )
    # Numbered subsection: 1.1 / 2.3.1  (but NOT 1.  which is a list item)
    _SUBSECTION_RE = re.compile(
        r"(?:^|\n)(\d+\.\d+(?:\.\d+)?\s+[^\n]+)",
        re.MULTILINE,
    )
    # Special sections: 前言/序/目录/附录/参考文献/习题/后记/索引/符号表/术语表
    _SPECIAL_RE = re.compile(
        r"(?:^|\n)(前言|序[言文]|目录|附录(?:\s*[A-Za-z\d]+)?|参考文献|参考书目|习题\d*|练习题\d*|课后习题|后记|索引|符号表|术语表|致谢|鸣谢)[\s\n]",
        re.MULTILINE,
    )
    # English chapter/section: Chapter 1 / Section 2.1 / Part I
    _EN_CHAPTER_RE = re.compile(
        r"(?:^|\n)((?:Chapter|Section|Part)\s+[IVX\d]+(?:\.\d+)?[^\n]*)",
        re.MULTILINE,
    )
    # Markdown headings: # / ## / ###
    _HEADING_RE = re.compile(
        r"(?:^|\n)(#{1,3}\s+.+?)(?=\n#{1,3}\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    # Step pattern: 步骤1：/ 步骤2：
    _STEP_RE = re.compile(
        r"(?:^|\n)(步骤\s*\d+[：:]\s*.+?)(?=\n步骤\s*\d+[：:]|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    # Numbered list: 1. / 2、 (lowest priority — too generic)
    _NUMBERED_RE = re.compile(
        r"(?:^|\n)(\d+[\.、]\s*.+?)(?=\n\d+[\.、]\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[list[str]] = None,
    ):
        if separators is None:
            separators = ["\n\n## ", "\n\n### ", "\n\n", "\n", "。", "；", "，", " "]

        self.chunk_size = max(_MIN_CHUNK_SIZE, min(chunk_size, _MAX_CHUNK_SIZE))
        self.chunk_overlap = min(chunk_overlap, self.chunk_size // 2)
        self.separators = separators

    def split_documents(self, documents: list[dict]) -> list[Document]:
        if not documents:
            return []

        if len(documents) > _MAX_DOCUMENTS:
            logger.warning(f"文档数量过多 ({len(documents)})，仅处理前 {_MAX_DOCUMENTS} 个")
            documents = documents[:_MAX_DOCUMENTS]

        all_chunks = []

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            if not content or not content.strip():
                continue

            if len(content) > _MAX_CONTENT_LENGTH:
                logger.warning(f"文档内容过长 ({len(content)} 字符)，已截断")
                content = content[:_MAX_CONTENT_LENGTH]

            sections = self._split_by_sop_structure(content)

            if not sections:
                sections = [{"content": content, "section": "全文"}]

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )

            doc_chunks = 0
            for section in sections:
                if doc_chunks >= _MAX_CHUNKS_PER_DOC:
                    logger.warning(f"单文档分块数超过限制 ({_MAX_CHUNKS_PER_DOC})")
                    break

                section_content = section["content"]
                section_title = section["section"]

                if len(section_content) <= self.chunk_size:
                    chunk_meta = {**metadata, "section": section_title}
                    all_chunks.append(Document(
                        page_content=section_content,
                        metadata=chunk_meta,
                    ))
                    doc_chunks += 1
                else:
                    chunks = splitter.split_text(section_content)
                    for i, chunk in enumerate(chunks):
                        if doc_chunks >= _MAX_CHUNKS_PER_DOC:
                            break
                        chunk_meta = {
                            **metadata,
                            "section": section_title,
                            "chunk_index": i,
                        }
                        all_chunks.append(Document(
                            page_content=chunk,
                            metadata=chunk_meta,
                        ))
                        doc_chunks += 1

        return all_chunks

    def _split_by_sop_structure(self, content: str) -> list[dict]:
        """Split content into sections using the best-matching structural pattern.

        Tries patterns from most specific (Chinese chapters) to most generic
        (numbered lists).  Picks the pattern that produces the most sections
        (≥ 2), with a bias toward chapter-level patterns.  Falls back to a
        single "全文" section when nothing matches.
        """
        patterns: list[tuple[str, re.Pattern, str | None]] = [
            ("cn_chapter",     self._CN_CHAPTER_RE,     "第[零一二三四五六七八九十百千\\d]+章"),
            ("cn_section",     self._CN_SECTION_RE,     "第[零一二三四五六七八九十百千\\d]+节|\\d+\\.\\d+\\s*节"),
            ("subsection",     self._SUBSECTION_RE,     None),
            ("special",        self._SPECIAL_RE,        None),
            ("en_chapter",     self._EN_CHAPTER_RE,     None),
            ("heading",        self._HEADING_RE,        "^#{1,3}\\s+"),
            ("step",           self._STEP_RE,           "^步骤\\s*\\d+[：:]\\s*"),
            ("numbered",       self._NUMBERED_RE,       "^\\d+[\\.、]\\s*"),
        ]

        best_sections: list[dict] = []
        best_type = ""

        for ptype, pattern, title_strip_re in patterns:
            matches = list(pattern.finditer(content))
            if len(matches) < 2:
                continue

            sections = self._build_sections(content, matches, pattern, title_strip_re)
            # Prefer earlier (more specific) patterns; if already found, skip later ones
            if len(sections) >= 2:
                best_sections = sections
                best_type = ptype
                break  # first match wins since patterns are priority-ordered

        if best_sections:
            logger.debug(f"结构识别: {best_type} → {len(best_sections)} 个段落")
        return best_sections

    def _build_sections(
        self,
        content: str,
        matches: list[re.Match],
        pattern: re.Pattern,
        title_strip_re: str | None,
    ) -> list[dict]:
        """Build section list from regex matches, including text between matches."""
        sections: list[dict] = []
        strip = re.compile(title_strip_re) if title_strip_re else None

        for i, match in enumerate(matches):
            start = match.start()
            # Content from this match to the next match start (or end of document)
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            text = content[start:end].strip()
            if not text:
                continue

            raw_title = match.group(0).strip()
            # Clean title: remove structural prefix (第X章, 1.1, #, 步骤1：, etc.)
            if strip:
                title = strip.sub("", raw_title).strip()
            else:
                title = raw_title
            # Also trim common suffixes
            title = title.split("\n")[0].strip()
            if not title:
                title = raw_title.split("\n")[0].strip()

            sections.append({"content": text, "section": title[:80]})

        return sections

    # ── Quality filter patterns ──
    _BAD_STARTS = re.compile(
        r'^(在|对|关于|从|根据|按照|由于|如果|虽然|但是|因此|所以|'
        r'此外|另外|最后|首先|其次|然后|接着|例如|比如|其中|具体|'
        r'特别|尤其|一般|通常|假设|考虑|给定|令|设|则|且|并|或|'
        r'这里|下面|上面|前面|后面|类似|相关)'
    )
    _BAD_ENDS = re.compile(
        r'(的|了|吗|呢|吧|啊|等|等等|包括|如下|为例|所示|'
        r'相关|各种|不同|其他|以上|以下|一些|几个|很多)$'
    )

    def _validate_point(self, name: str) -> bool:
        """Check if a knowledge point name is valid."""
        if not name or len(name) < 2 or len(name) > 30:
            return False
        if self._BAD_STARTS.match(name) or self._BAD_ENDS.search(name):
            return False
        if len(re.findall(r'[一-鿿a-zA-Z]', name)) < 2:
            return False
        return True

    def _parse_llm_response(self, text: str, chunk: str, source_file: str,
                            seen_names: set[str]) -> list[dict]:
        """Parse LLM output lines into knowledge point dicts."""
        points = []
        for line in text.strip().split("\n"):
            name = line.strip().lstrip("-•·1234567890.、 ）}⟩】").strip()
            if not self._validate_point(name):
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            points.append({
                "name": name[:80],
                "section": "",
                "chunk_content": chunk[:200],
                "source_file": source_file,
                "source_page": 0,
            })
        return points

    def _llm_extract(self, prompts: list[str], chunks: list[str],
                     source_file: str) -> list[dict]:
        """Send prompts to LLM, parse and deduplicate results."""
        from Coder.model.model import llm
        from langchain_core.messages import HumanMessage

        all_points: list[dict] = []
        seen_names: set[str] = set()

        for i, (prompt, chunk) in enumerate(zip(prompts, chunks)):
            try:
                resp = llm.invoke([HumanMessage(content=prompt)])
                pts = self._parse_llm_response(
                    resp.content or "", chunk, source_file, seen_names
                )
                all_points.extend(pts)
            except Exception as e:
                logger.warning(f"LLM 第{i + 1}段提取失败: {e}")
                continue

        return all_points

    def extract_knowledge_points(
        self, content: str, metadata: dict
    ) -> list[dict]:
        """Extract knowledge points from document content.

        Regex splits content into sections for structural context.
        LLM extracts and names knowledge points from each section.
        Falls back to chunk-based LLM extraction if no sections found.
        """
        source_file = metadata.get("filename", "")
        sections = self._split_by_sop_structure(content)

        prompts: list[str] = []
        chunks: list[str] = []

        if sections and len(sections) >= 2:
            # Batch 3 sections per LLM call, each with section title as context
            batch_size = 3
            for i in range(0, len(sections), batch_size):
                batch = sections[i:i + batch_size]
                context_parts = []
                chunk_parts = []
                for sec in batch:
                    title = sec["section"]
                    text = sec["content"][:1500]
                    context_parts.append(f"## {title}\n{text}")
                    chunk_parts.append(text)
                combined = "\n\n".join(context_parts)
                chunk_combined = "\n\n".join(chunk_parts)
                prompts.append(
                    "你是一个教学专家。从以下教材章节中提取最重要的知识点。\n\n"
                    "每个知识点占一行，格式：知识点名称\n\n"
                    "要求：\n"
                    "- 每个章节最多提取 5 个最核心的知识点\n"
                    "- 知识点应是一个明确的概念、定理、方法或定义（2-20字）\n"
                    "- 优先提取核心概念，跳过细节和例子\n"
                    "- 章节标题（## 开头）仅供上下文参考，不要提取标题本身作为知识点\n"
                    "- 如果某个章节没有明确的知识点，跳过即可\n"
                    "- 只返回知识点列表，不要解释\n\n"
                    f"{combined}\n\n"
                    "知识点："
                )
                chunks.append(chunk_combined)
        else:
            # No structure: chunk the full text
            chunk_size = 3000
            overlap = 200
            start = 0
            while start < len(content) and len(prompts) < 8:
                end = min(start + chunk_size, len(content))
                chunk = content[start:end]
                prompts.append(
                    "你是一个教学专家。从以下教材片段中提取最重要的知识点。\n\n"
                    "每个知识点占一行，格式：知识点名称\n\n"
                    "要求：\n"
                    "- 最多提取 5 个最核心的知识点\n"
                    "- 知识点应是一个明确的概念、定理、方法或定义（2-20字）\n"
                    "- 优先提取核心概念，跳过细节和例子\n"
                    "- 如果片段中没有明确的知识点，返回空\n"
                    "- 只返回知识点列表，不要解释\n\n"
                    f"教材片段：\n{chunk}\n\n"
                    "知识点："
                )
                chunks.append(chunk)
                start += chunk_size - overlap

        try:
            points = self._llm_extract(prompts, chunks, source_file)
            if points:
                points = points[:_MAX_KNOWLEDGE_POINTS]
                logger.info(f"LLM 提取了 {len(points)} 个知识点（上限 {_MAX_KNOWLEDGE_POINTS}）")
                return points
        except Exception as e:
            logger.warning(f"LLM 知识点提取失败: {e}")

        # Ultimate fallback
        title = metadata.get("title", "") or source_file or "未知文档"
        return [{
            "name": title[:80],
            "section": "",
            "chunk_content": content[:2000],
            "source_file": source_file,
            "source_page": 0,
        }]

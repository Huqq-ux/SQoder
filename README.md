# CourseMate — 课程 AI 学习伴侣

基于 LangChain + LangGraph 的课程学习平台。上传教材课件后，所有 AI 回答严格基于课程材料，同时追踪知识点掌握度。

**核心三角**：课程 RAG → 学习路径追踪 → 智能笔记生成

## 功能

- **课程知识库**：上传课件（pdf/pptx/docx/epub），按课程独立向量索引，互不污染
- **精准问答**：RAG 问答附原文引用（文件名 + 章节），回答后可一键生成笔记
- **知识图谱**：力导向图可视化知识点关联，按掌握度着色，点击节点跳转问答
- **学习进度**：知识点掌握度标签（未学/学习中/已掌握）+ 进度条
- **智能笔记** + **错题本**：自动收录 + 手动管理
- **技能系统**：上传 .md 文件自定义 AI 能力，沙箱编译，Agent 动态调用

## 技术栈

FastAPI + LangChain + LangGraph + React 18 + TypeScript + Vite + Tailwind CSS 4 + PostgreSQL + Redis + FAISS

## 快速开始

```bash
# 环境变量
set DEEPSEEK_API_KEY=sk-xxx

# 安装
pip install -e .
cd Coder/web && npm install

# 启动
python run.py                  # 后端 http://localhost:8000
cd Coder/web && npm run dev    # 前端 http://localhost:5173

# 一键启停 (Windows)
start_dev.bat
stop_dev.bat
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | 流式对话 (SSE) |
| GET/POST | `/api/sessions` | 会话管理，支持 `?course_id=` |
| GET/POST/DELETE | `/api/courses` | 课程 CRUD |
| POST | `/api/knowledge/upload` | 文档上传，支持 `?course_id=` |
| POST | `/api/knowledge/search` | 知识库检索 |
| GET/POST/DELETE | `/api/skills` | 技能管理 |

## License

MIT

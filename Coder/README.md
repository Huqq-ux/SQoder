# CourseMate — 课程 AI 学习伴侣

基于 LangChain + LangGraph 构建的课程学习平台。上传教材课件后，所有 AI 回答严格基于课程材料，同时追踪知识点掌握度。聚焦高等教育场景，以**课程知识库 + RAG 精准问答 + 学习路径追踪**为核心。

## 功能

- **课程知识库**：上传课件（pdf/pptx/docx/epub/xlsx/csv/txt/md），按课程建立独立向量索引
- **精准问答**：基于指定课程知识库的 RAG 问答，回答附带原文引用（文件名 + 章节）
- **知识图谱**：力导向图可视化课程知识点关联，按掌握度着色
- **学习进度追踪**：知识点掌握度标签（未学/学习中/已掌握）+ 进度条
- **智能笔记**：问答后一键生成复习笔记，支持手动创建和管理
- **错题本**：自动收录 + 手动添加，按知识点分类，红绿对比展示
- **技能系统**：上传 .md 文件自定义 AI 能力，沙箱编译，Agent 对话中动态调用

## 技术栈

| 层级 | 技术 |
|------|------|
| **LLM** | DeepSeek (ChatOpenAI API) |
| **Agent** | LangChain + LangGraph (checkpoint 持久化) |
| **后端** | FastAPI + uvicorn, SSE 流式响应 |
| **前端** | React 18 + TypeScript + Vite + Tailwind CSS 4 + shadcn/ui |
| **数据库** | PostgreSQL (psycopg 连接池), Redis |
| **向量库** | FAISS + bge-small-zh-v1.5 (HuggingFaceEmbeddings) |
| **容器化** | Docker + docker-compose + Nginx |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

### 配置

```bash
# 必需
set DEEPSEEK_API_KEY=sk-xxx

# 可选
set DATABASE_URL=postgresql://user:pass@localhost:5432/coder_db
set REDIS_URL=redis://localhost:6379/0
```

### 启动

```bash
# 安装依赖
pip install -e .
cd Coder/web && npm install && npm run build && cd ../..

# 启动后端 (端口 8000)
python run.py

# 开发模式前端 (端口 5173)
cd Coder/web && npm run dev

# 一键启停 (Windows)
start_dev.bat
stop_dev.bat
```

### Docker

```bash
cd Coder/deploy
docker-compose up -d
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | 流式对话（SSE），支持 `course_id` |
| GET/POST | `/api/sessions` | 会话 CRUD，支持 `?course_id=` 过滤 |
| GET/POST/DELETE | `/api/courses` | 课程 CRUD |
| GET | `/api/courses/:slug/progress` | 学习进度 |
| GET/POST | `/api/courses/:slug/notes` | 笔记管理 |
| GET/POST | `/api/courses/:slug/wrong-answers` | 错题本 |
| GET | `/api/courses/:slug/knowledge-graph` | 知识图谱 |
| POST | `/api/knowledge/upload` | 文档上传，支持 `?course_id=` |
| POST | `/api/knowledge/search` | 知识库检索 |
| GET/POST/DELETE | `/api/skills` | 技能管理 |

## 数据库

11 张表：courses / course_files / knowledge_points / learning_progress / notes / wrong_answers / sessions / messages / skills / mcp_servers，详情见 `Coder/storage/db.py`。

## 项目结构

```
CourseMate/
├── Coder/
│   ├── agent/              # Agent 核心
│   ├── knowledge/          # 知识库（向量存储、检索、文档加载）
│   ├── server/             # FastAPI + 路由
│   ├── storage/            # PostgreSQL + Redis + 数据管理
│   ├── tools/              # Agent 工具集 + 技能系统
│   ├── MCP/                # MCP 协议适配
│   └── web/                # React 前端
├── start_dev.bat / stop_dev.bat
└── run.py
```

## License

MIT

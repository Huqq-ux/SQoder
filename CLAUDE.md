# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CourseMate — 围绕课程教材的 AI 学习伴侣。基于 LangChain + LangGraph 构建，聚焦高等教育课程学习场景，以课程知识库 + RAG 精准问答 + 学习路径追踪为核心差异化。后端 FastAPI + 前端 React。

## 常用命令

### 开发环境

```bash
# 创建虚拟环境并安装依赖
uv sync
# 或 pip install -e .

# 启动后端 (端口 8000)
python run.py

# 启动前端 (端口 5173)
cd Coder/web && npm install && npm run dev

# 一键启停 (Windows)
start_dev.bat   # 启动前后端
stop_dev.bat    # 停止前后端
```

### 测试

```bash
# 全部测试
pytest Coder/tests/ -v

# 单模块
pytest Coder/tests/test_skill_system.py -v
pytest Coder/tests/test_knowledge_toolkit.py -v
pytest Coder/tests/test_document_loader.py -v

# 构建前端
cd Coder/web && npm run build
```

### 环境变量

```bash
set DEEPSEEK_API_KEY=sk-xxx        # 必需
set DATABASE_URL=postgresql://...  # 可选，默认本地 coder_db
set REDIS_URL=redis://...          # 可选，默认本地 6379
```

## 架构

### 启动链路

`run.py` → uvicorn → `Coder.server.main:app` → lifespan 中依次初始化 PostgreSQL 连接池、Redis、PgSessionManager、PgSkillStore、MCP Manager、Agent Manager。

### 核心 Agent (`Coder/agent/code_agent.py`)

使用 `langchain.agents.create_agent()` 创建，checkpointer = `AsyncPostgresSaver`。工具集 = file_management + knowledge + web_search + skill + docx + time + PowerShell MCP（仅 Windows）。

流式响应 `stream_agent_response()` 使用 `agent.astream(stream_mode="messages")`，yield 统一事件格式 `{"type": "content"|"tool_call"|"tool_result", ...}`。

课程问答时通过 `contextvars` 将 `course_id` 注入 knowledge_toolkit，实现课程级向量检索隔离。

### API 路由

| 前缀 | 用途 |
|------|------|
| `/api/chat` | 流式对话 SSE + 停止 |
| `/api/sessions` | 会话 CRUD（支持 `?course_id=` 过滤） |
| `/api/courses` | 课程 CRUD / 知识点 / 笔记 / 错题 / 图谱 / 进度 |
| `/api/knowledge` | 文档上传 / 检索（支持 `?course_id=` 课程隔离） |
| `/api/skills` | 技能上传 / 解析 / 启用切换 / 删除 |
| `/api/mcp` | MCP 服务管理 |

### 数据库 (PostgreSQL)

11 张业务表：
- **courses** — 课程（id, slug, name, semester）
- **course_files** — 课件文件（FK → courses CASCADE）
- **knowledge_points** — 知识点（FK → courses CASCADE）
- **learning_progress** — 学习进度（unlearned/learning/mastered）
- **notes** — 智能笔记（FK → courses CASCADE）
- **wrong_answers** — 错题本（FK → courses CASCADE）
- **sessions** — 会话（course_id FK → courses.slug CASCADE）
- **messages** — 消息（FK → sessions CASCADE）
- **skills** — 用户技能定义
- **mcp_servers** — MCP 服务注册

LangGraph checkpoint 表由框架自动管理。

### 知识库 (`Coder/knowledge/`)

FAISS + bge-small-zh-v1.5（HuggingFaceEmbeddings）。课程级向量索引存储在 `knowledge/index/{course_id}/`，`contextvars` 注入 course_id 实现检索隔离。

### 技能系统 (`Coder/tools/skill_*.py`)

Markdown 定义 → SkillParser 解析 → SkillStore 持久化（PgSkillStore）→ SkillRegistry 注册 → SkillCompiler 沙箱编译（AST 安全检查 + 受限 namespace exec）。前端设置页可上传/启用/删除。

### 前端 (`Coder/web/`)

React 18 + TypeScript + Vite + Tailwind CSS 4 + shadcn/ui + zustand。三栏布局（IconNav 52px + Sidebar 260px 可拖拽 + 主内容区），双主题（暗色紫蓝 / 亮色青绿），6 个页面：

| 路由 | 页面 |
|------|------|
| `/` | 首页（统计卡片 + 课程列表 + 创建课程） |
| `/course/:slug` | 课程工作台（问答/笔记/图谱/错题，侧栏子导航切换） |
| `/chat` | 通用对话（不关联课程） |
| `/knowledge` | 知识库管理（课程选择器 + 上传 + 文档列表） |
| `/settings/:category` | 设置（通用/模型/技能管理/知识库/关于） |

## 对话规范

- 所有回答使用中文

## 代码规范

- Python 文件编码 UTF-8，前端 TypeScript strict 模式
- 工具函数用 `@tool` 装饰器，docstring 即为工具描述
- 异步数据库操作使用 `DatabaseManager.fetch/fetchrow/execute`
- Redis 使用 `RedisManager` 类方法
- 文件路径操作使用 `os.path.normpath` + 白名单前缀校验
- 用户输入使用正则校验（`_SAFE_THREAD_ID_RE` 等）
- 模块懒加载：`_get_xxx()` + `threading.Lock` 双重检查锁
- 管道式数据流：`create_agent()` → `astream()` → yield 事件 → SSE → 前端
- 新增工具放 `Coder/tools/`，在 `code_agent.py` 注册
- 新增 API 路由在 `Coder/server/routes/`，在 `main.py` 中 `include_router`

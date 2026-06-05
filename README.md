# Qbot — 通用 AI 智能体

基于 LangChain + LangGraph 的通用 AI 智能体系统，集成 FastAPI 后端 + React 前端。支持多智能体协作、RAG 知识库检索、Web 搜索、Word 文档生成、技能系统。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | FastAPI + LangChain + LangGraph |
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 模型 | DeepSeek (ChatOpenAI 兼容) |
| 数据库 | PostgreSQL + Redis |
| 向量库 | FAISS + bge-small-zh-v1.5 |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+
- Redis (可选)

### 安装

```bash
# 克隆仓库
git clone https://github.com/Huqq-ux/SQoder.git
cd SQoder

# 后端
uv sync
# 或: pip install -e .

# 前端
cd Coder/web && npm install
```

### 配置

```bash
# 必需
set DEEPSEEK_API_KEY=sk-xxx

# 可选（默认连接本地 PostgreSQL）
set DATABASE_URL=postgresql://user:pass@localhost:5432/coder_db
set REDIS_URL=redis://localhost:6379
```

### 启动

```bash
# 后端 (http://localhost:8000)
python run.py

# 前端 (http://localhost:5173)
cd Coder/web && npm run dev

# 构建前端 (生产)
cd Coder/web && npm run build
```

### Docker

```bash
cd Coder/deploy
docker-compose up -d    # api + postgres + redis + nginx
docker-compose down
```

## 功能

### 主对话

- 流式对话 (SSE)
- 文件操作 (LangChain FileManagementToolkit)
- 知识库 RAG 检索 (FAISS 向量搜索)
- Web 搜索 (DDGS / 百度 / DuckDuckGo)
- 技能系统 (用户自定义 Markdown 技能，沙箱编译执行)
- Word 文档生成与预览 (python-docx + mammoth.js)
- PowerShell MCP 集成 (Windows)

### 多智能体协调

Agent-as-Tool 架构，4 个子智能体自动协作：

| 子 Agent | 工具 | 职责 |
|----------|------|------|
| Coder | 文件操作 + 知识库 + Word 文档 | 代码生成、调试、重构 |
| Searcher | Web 搜索 + 知识库 | 信息检索、文档查询 |
| Ops | 文件操作 | 部署、配置、故障排查 |
| Skill Executor | 技能注册表 | 调用已注册的用户技能 |

支持 SSE 流式输出和会话持久化。

### API

| 前缀 | 用途 |
|------|------|
| `/api/chat` | 流式对话、停止 |
| `/api/sessions` | 会话管理 |
| `/api/knowledge` | 文档管理 + RAG 搜索 + Word 预览 |
| `/api/skills` | 技能管理 |
| `/api/agent-orchestrator` | 多智能体执行 + 流式 |

## 项目结构

```
Coder/
├── agent/          # 主 Agent 创建和流式响应
├── multi_agent/    # 多智能体 (编排器 + AgentBuilder + 配置)
├── browser/        # Web 搜索 (搜索策略 + 页面抓取 + SSRF 防护)
├── knowledge/      # RAG 知识库 (FAISS + bge 嵌入)
├── tools/          # 工具集 (文件、知识库、搜索、技能、Word)
├── storage/        # 数据层 (PostgreSQL + Redis + 会话管理)
├── server/         # FastAPI (路由 + 中间件 + SSE)
│   └── routes/     # chat / sessions / knowledge / skills / agent_orchestrator / mcp
├── model/          # LLM 模型封装
├── tests/          # 测试
└── web/            # React 前端 (Vite + TypeScript + Tailwind)
```

## 命令行

```bash
# 终端对话模式
python -m Coder.agent.code_agent
```

## 测试

```bash
pytest Coder/tests/ -v
pytest Coder/tests/test_multi_agent.py -v
```

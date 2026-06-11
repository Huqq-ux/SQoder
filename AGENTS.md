# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 项目概述

Qbot-通用智能体，基于 LangChain + LangGraph 的通用 AI 智能体系统。使用 DeepSeek 模型，集成 FastAPI 后端 + React 前端。支持多智能体协作、RAG 知识库检索、Web 搜索、技能系统。

## 常用命令

### 开发环境

```bash
# 创建虚拟环境并安装依赖
uv sync
# 或 pip install -e .

# 启动后端开发服务器 (自动重载)
python run.py
# 或: uvicorn Coder.server.main:app --host 0.0.0.0 --port 8000 --reload

# 安装前端依赖
cd Coder/web && npm install

# 启动前端开发服务器 (端口 5173)
# 端口被占用时用 netstat 查 PID 并杀掉，不要切换到其他端口
cd Coder/web && npm run dev

# 构建前端 (后端会服务静态文件)
cd Coder/web && npm run build
```

### 测试

```bash
# 运行所有测试
pytest Coder/tests/ -v

# 运行单个测试模块
pytest Coder/tests/test_skill_system.py -v
pytest Coder/tests/test_multi_agent.py -v

pytest Coder/tests/test_knowledge_toolkit.py -v
pytest Coder/tests/test_web_search_toolkit.py -v

# 运行安全测试
python Coder/tests/run_security_tests.py
```

### 环境变量

```bash
set DEEPSEEK_API_KEY=sk-xxx        # 必需
set DATABASE_URL=postgresql://...  # 可选，默认本地 coder_db
set REDIS_URL=redis://...          # 可选，默认本地 6379
```

### Docker 部署

```bash
cd Coder/deploy
docker-compose up -d    # 启动 api + postgres + redis + nginx
docker-compose down     # 停止
```

### 命令行 Agent 模式

```bash
python -m Coder.agent.code_agent    # 终端交互式对话
```

## 架构

### 启动链路

`run.py` → uvicorn → `Coder.server.main:app` → lifespan 中依次初始化 PostgreSQL 连接池、Redis 客户端、PgSessionManager、PgSkillStore，调用 `create_code_agent()` 创建核心 Agent 并挂载到 `app.state`。

### 核心 Agent (`Coder/agent/code_agent.py`)

主 Agent 使用 `langchain.agents.create_agent()` 创建，checkpointer = `AsyncPostgresSaver`（对话状态持久化）。工具集 = file_management_toolkit + knowledge_toolkit + web_search_toolkit + PowerShell MCP（仅 Windows）。

**输入处理流程：** 用户消息直接传递给 Agent，由 LLM 根据 system prompt 自主决定调用哪些工具。

**流式响应：** `stream_agent_response()` 使用 `agent.astream(stream_mode="messages")`，yield 统一事件格式 `{"type": "content"|"tool_call"|"tool_result", ...}`。工具调用硬上限 15 次。

### 多智能体系统 (`Coder/multi_agent/`)

Agent-as-Tool 架构：`AgentOrchestrator` 创建 4 个子 Agent（Coder/Searcher/Ops/SkillExecutor），每个子 Agent 包装为 `@langchain_tool`，主 Orchestrator Agent 按需调度。子 Agent 使用 MemorySaver（无状态），主 Orchestrator 使用 MemorySaver。超时 300s。

子 Agent 工具分配：Coder → file_tools + knowledge_toolkit；Searcher → web_search + knowledge；Ops → file_tools；Skill Executor → 动态加载对应工具。

### 知识库 (`Coder/knowledge/`)

FAISS + bge-small-zh-v1.5（HuggingFaceEmbeddings），优先本地缓存 → 离线模式 → 在线下载兜底。文档加载支持 pdf/docx/txt/md，分块前按文档结构（标题/步骤/编号）预分段，再递归分块。Retriever 的 score_threshold 默认 1.5，低于此分数才纳入结果。

### Web 搜索 (`Coder/browser/`)

链路：`query_parser` 解析（城市/日期/意图）→ `search_strategy.search_engine()` 优先 DDGS 库 → fallback 百度/DuckDuckGo/Bing HTTP CSS 选择器解析 → 天气类直连中国天气网 → 摘要不足时抓取前 2 条结果详情。有 SSRF 防护（拦截内网 IP 和云元数据端点）。

### 技能系统 (`Coder/tools/skill_*.py`)

用户技能用 Markdown 定义（`## 描述`/`## 分类`/`## 参数`/代码块），`SkillParser` 解析 → `SkillStore` 持久化（JSON 文件 + PostgreSQL 双存储）→ `SkillRegistry` 注册（内置技能 + 用户技能元数据预加载、懒编译）→ `SkillCompiler` 沙箱编译（AST 安全检查：禁止危险模块和内置函数，白名单 safe builtins，受限 namespace exec）→ `SkillExecutor` 执行（threading.Thread + join 超时，重试，回退）。

### 数据层 (`Coder/storage/`)

- **PostgreSQL**：psycopg AsyncConnectionPool（2-10 连接），3 张业务表（sessions/messages/skills）+ LangGraph checkpoint 表
- **Redis**：会话列表缓存（300s TTL）、停止标志、Pub/Sub
- **会话管理**：`PgSessionManager`，自动从首条用户消息生成标题，消息历史从 LangGraph checkpoint 恢复（含 reasoning_content 和 tool_calls）

### API 路由

| 前缀 | 用途 |
|------|------|
| `/api/chat` | 流式对话 SSE（`POST /stream`）、停止（`POST /stop/{id}`） |
| `/api/sessions` | 会话 CRUD + 消息历史 |
| `/api/knowledge` | 文档上传导入、RAG 搜索 |

| `/api/skills` | 技能上传/解析/启用切换/删除 |
| `/api/agent-orchestrator` | 多智能体同步/流式执行 |

### 前端 (`Coder/web/`)

React 18 + TypeScript + Vite。4 个页面（Chat/Knowledge/Skills/MultiAgent），核心组件 Sidebar + ChatMessage。chatStore 管理会话状态，`api/chat.ts` 处理 SSE 流式读取。

## 对话规范

- 所有回答统一使用中文

## 代码规范

- Python 文件编码 UTF-8，前端 TypeScript strict 模式
- 使用 `logging.getLogger(__name__)` 记录日志，logger 命名为模块级别变量
- 工具函数用 `@tool` 装饰器（LangChain），docstring 即为工具描述
- 异步数据库操作使用 `DatabaseManager.fetch/fetchrow/execute` 类方法，配合 `async with` 上下文管理器
- Redis 操作使用 `RedisManager` 类方法，不要直接实例化客户端
- 所有文件路径操作使用 `os.path.normpath` + 白名单前缀校验防路径遍历
- 用户输入（thread_id、文件名、查询字符串）使用正则校验（`_SAFE_THREAD_ID_RE`、`_SAFE_FILENAME_RE`），不符合的用默认值降级
- 模块级别懒加载：重量级组件（模型、向量库、检索器）通过 `_get_xxx()` 函数 + `threading.Lock` 双重检查锁实现线程安全延迟初始化
- 管道式数据流：`create_agent()` → `astream()` → yield 事件 → SSE → 前端渲染，中间不阻塞
- 新增工具放在 `Coder/tools/` 对应工具文件中，在 `code_agent.py` 的 `create_code_agent()` 中注册到 tools 列表
- 新增 API 路由在 `Coder/server/routes/` 创建文件，在 `server/main.py` 中 `include_router`

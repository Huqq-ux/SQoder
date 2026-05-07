# SQoder

基于 LangChain + LangGraph 的 AI 编程助手，集成 FastAPI 后端 + React 前端，支持多智能体协作、SOP 流程执行、知识库检索、Web 搜索等功能。

## 功能特点

- **智能编程助手**：基于 DeepSeek 模型，提供代码生成、审查、调试等专业支持
- **多智能体系统**：Supervisor 监督 + 任务路由，支持 Coder / Searcher / Ops 多角色 Hierarchical 协作
- **SOP 流程执行**：标准操作流程管理，支持步骤追踪、技能执行、状态机、回退与断点续传
- **技能系统**：用户可定义和注册技能（JSON DSL），沙箱编译执行，支持懒加载、重试、回退
- **知识库检索**：基于 FAISS + bge-small-zh 向量化 + RAG，支持语义搜索和文档自动分块导入
- **Web 搜索**：集成 Bing / Baidu / DuckDuckGo 多引擎搜索，支持天气/新闻/通用页面获取
- **文件管理**：工作区文件读写、目录遍历、PowerShell 命令执行（Windows）
- **会话管理**：PostgreSQL 持久化会话和消息，Redis 缓存与 Pub/Sub 通信
- **现代 UI**：React + TypeScript 前端，流式 SSE 响应，多面板架构
- **Docker 部署**：提供 Dockerfile + docker-compose，支持 Nginx 反向代理

## 技术栈

| 层级 | 技术 |
|------|------|
| **LLM** | DeepSeek (ChatOpenAI API), DashScope 备选 |
| **Agent 框架** | LangChain, LangGraph (checkpoint + state 持久化) |
| **后端** | FastAPI + uvicorn, SSE 流式响应 |
| **前端** | React 18 + TypeScript + Vite |
| **数据库** | PostgreSQL (psycopg 连接池), Redis (aioredis) |
| **向量库** | FAISS + sentence-transformers (bge-small-zh-v1.5) |
| **搜索** | httpx + BeautifulSoup4, DDGS |
| **容器化** | Docker + docker-compose + Nginx |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

### 1. 克隆仓库

```bash
git clone https://github.com/Huqq-ux/SQoder.git
cd SQoder
```

### 2. 配置环境变量

```bash
# 必需：DeepSeek API Key
set DEEPSEEK_API_KEY=sk-xxx

# 可选：覆盖默认数据库连接
set DATABASE_URL=postgresql://user:pass@localhost:5432/coder_db
set REDIS_URL=redis://localhost:6379/0
```

### 3. 安装 Python 依赖

```bash
pip install -e .
```

### 4. 安装前端依赖 & 构建

```bash
cd web
npm install
npm run build
cd ..
```

### 5. 启动服务

```bash
# 启动后端
python -m uvicorn Coder.server.main:app --host 0.0.0.0 --port 8000 --reload

# 开发模式前端（可选，后端已服务静态文件）
cd web && npm run dev
```

### 6. Docker 部署

```bash
cd deploy
docker-compose up -d
```

## 项目结构

```
SQoder/
├── Coder/
│   ├── agent/              # Agent 实现（code_agent, multi_chat）
│   │   └── code_agent.py   # 核心 Agent 创建、流式响应、SOP 集成
│   ├── browser/            # Web 搜索子系统
│   │   ├── browser_config.py    # 浏览器/搜索配置
│   │   ├── query_parser.py      # 查询解析（意图识别、城市/日期提取）
│   │   ├── search_strategy.py   # 多引擎搜索策略（Baidu/Bing/DDGS）
│   │   └── content_extractor.py # 内容清洗、验证、格式化
│   ├── knowledge/          # 知识库子系统
│   │   ├── vector_store.py      # FAISS 向量库（安全校验、本地模型）
│   │   ├── retriever.py         # 检索器（语义搜索 + 上下文构建）
│   │   ├── document_loader.py   # 文档加载（txt/md/pdf/docx）
│   │   ├── text_splitter.py     # 文档分块（SOP 优化分块器）
│   │   └── version_manager.py   # 文档版本管理
│   ├── model/              # LLM 模型适配
│   │   └── model.py        # DeepSeek ChatOpenAI 封装（reasoning_content）
│   ├── multi_agent/        # 多智能体系统
│   │   ├── crew.py              # MultiAgentCrew 核心调度
│   │   ├── supervisor.py        # Supervisor Agent（任务分解、分配、整合）
│   │   ├── router.py            # 任务路由器（意图分析、关键词匹配）
│   │   ├── registry.py          # Agent 注册中心
│   │   ├── protocol.py          # Agent 间通信协议
│   │   ├── agent_builder.py     # Agent 构建器
│   │   ├── integrations.py      # 默认配置、Prompt 模板
│   │   └── types.py             # 数据类型定义
│   ├── prompts/            # Prompt 模板
│   │   ├── sop_execution.py     # SOP 执行提示词
│   │   ├── step_decomposition.py
│   │   └── validation.py
│   ├── server/             # FastAPI 后端
│   │   ├── main.py              # 应用入口（lifespan 初始化）
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   └── routes/              # API 路由
│   │       ├── chat.py          # 流式对话 + 停止
│   │       ├── sessions.py      # 会话 CRUD
│   │       ├── knowledge.py     # 知识库管理
│   │       ├── sop.py           # SOP 管理
│   │       ├── skills.py        # 技能管理
│   │       └── multi_agent.py   # 多智能体执行
│   ├── sop/                # SOP 执行子系统
│   │   ├── executor.py          # SOP 执行器（步骤执行、技能调用）
│   │   ├── flow_orchestrator.py # 流程编排器
│   │   ├── state_machine.py     # 状态机（状态转换、步骤追踪）
│   │   ├── skill_executor.py    # 技能执行器（重试、超时、回退）
│   │   ├── skill_nl_invoker.py  # NL 技能调用
│   │   ├── intent_classifier.py # 意图分类器
│   │   ├── checkpoint_manager.py # 断点管理器
│   │   └── validator.py         # 结果验证器
│   ├── storage/            # 数据持久化
│   │   ├── db.py                # PostgreSQL 异步连接池
│   │   ├── redis_client.py      # Redis 客户端
│   │   ├── session_store.py     # 会话存储（PgSessionManager）
│   │   └── skill_store.py       # 技能存储（PgSkillStore）
│   ├── tools/              # 工具集
│   │   ├── file_tools.py        # 文件管理工具
│   │   ├── file_saver.py        # Checkpoint 文件持久化
│   │   ├── knowledge_toolkit.py  # 知识库工具（搜索/导入/更新/上下文搜索）
│   │   ├── web_search_toolkit.py # Web 搜索工具（搜索/天气/新闻/页面获取）
│   │   ├── skill_registry.py    # 技能注册中心
│   │   ├── skill_compiler.py    # 技能沙箱编译器
│   │   ├── skill_parser.py      # 技能 JSON 解析器
│   │   ├── skill_store.py       # 技能文件存储
│   │   └── powershell_tools.py  # PowerShell 执行工具
│   ├── MCP/                # MCP 协议适配
│   └── web/                # React 前端
│       ├── src/
│       │   ├── api/             # API 客户端
│       │   ├── components/      # 组件（ChatMessage, Sidebar 等）
│       │   ├── pages/           # 页面（Chat, Knowledge, SOP, Skills, MultiAgent）
│       │   ├── stores/          # 状态管理
│       │   └── types.ts         # TypeScript 类型
│       └── vite.config.ts
├── deploy/                # Docker 部署文件
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx-docker.conf
├── tests/                 # 测试文件
├── pyproject.toml         # 项目配置
└── main.py                # 命令行入口
```

## 多智能体系统

系统采用 Hierarchical（分层）架构：

```
用户输入 → TaskRouter（意图分析+任务分解）
                ↓
         SupervisorAgent（调度分配）
          ↙      ↓       ↘
    Coder    Searcher    Ops
          ↘      ↓       ↙
         SupervisorAgent（结果整合）
                ↓
            最终回答
```

启动后默认注册 6 个 Agent：

| Agent | 角色 | 职责 |
|-------|------|------|
| Supervisor | 任务监督者 | 任务分解、分配、结果整合 |
| Coder | 编程专家 | 代码生成、审查、调试 |
| Searcher | 搜索专家 | 信息检索、知识查询 |
| Ops | 运维专家 | 系统部署、故障排查 |
| SOP Executor | SOP 执行器 | 标准操作流程执行 |
| Skill Executor | 技能执行器 | 注册技能的匹配和执行 |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | 流式对话（SSE） |
| POST | `/api/chat/stop/{thread_id}` | 停止对话 |
| GET/POST | `/api/sessions` | 会话 CRUD |
| POST | `/api/knowledge/search` | 知识库搜索 |
| POST | `/api/knowledge/upload` | 文档上传 |
| GET | `/api/sop/list` | SOP 列表 |
| POST | `/api/skills/upload` | 技能上传 |
| POST | `/api/multi-agent/execute` | 多智能体任务执行 |
| GET | `/api/multi-agent/agents` | Agent 列表 |
| GET | `/api/multi-agent/status` | 多智能体状态 |

## 安全特性

- **沙箱编译**：技能代码在受限命名空间中编译执行，禁止危险内置函数（`exec`, `eval`, `__import__`, `open`, `os`, `sys`）
- **反序列化安全**：移除 pickle 反序列化，使用安全的 JsonPlus 序列化器
- **SSRF 防护**：Web 搜索和页面获取拦截 RFC 1918 私有网段和云元数据端点
- **路径遍历防护**：文件操作和 checkpoint 路径均经过路径规范化和白名单验证
- **输入验证**：thread_id 等用户输入通过正则校验，请求体限制 10MB
- **内存管理**：StateMachine、Protocol、Cache、Contexts 等组件均设上限并自动清理

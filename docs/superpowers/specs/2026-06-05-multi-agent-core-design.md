# 多智能体核心功能升级 — 设计文档

## 目标

将多智能体从基础的一次性任务提交升级为核心功能，分两阶段交付：

- **Phase 1**：架构清理 + 能力补全（AgentBuilder 统一、超时、调用可见性、bug 修复）
- **Phase 2**：SSE 流式输出 + 会话持久化 + 前端对话界面

## 架构总览

```
MultiAgentPage (Phase1: 表单 / Phase2: 对话)
    │
    ├── POST /api/agent-orchestrator/execute  (Phase1)
    ├── POST /api/agent-orchestrator/stream    (Phase2, SSE)
    ├── GET  /api/agent-orchestrator/sessions  (Phase2)
    └── GET  /api/agent-orchestrator/sessions/{id}/sidechains (Phase2)
         │
    AgentOrchestrator (重构)
    ├── _agent_configs: Dict[AgentRole, AgentConfig]  ← 配置驱动
    ├── run(user_input) → Dict  (Phase1)
    └── astream(user_input) → AsyncIterator[Event]  (Phase2)
         │
    AgentBuilder.build_agent(config)  ← 统一子 Agent 工厂
         │
    ├── Coder (file_tools + knowledge_toolkit)
    ├── Searcher (web_search_toolkit + knowledge_toolkit)
    ├── Ops (file_tools)
    └── SkillExecutor (skill_tools, 动态注入)
```

## Phase 1 — 架构清理 + 能力补全

### 1. AgentConfig 集中配置

新增 `Coder/multi_agent/agent_configs.py`，用 `AgentConfig` 数据类定义 4 个角色的默认配置，替代散落在 `integrations.py` 各处的 system prompt 字符串和 `_resolve_sub_tools()` 的角色映射。

```python
DEFAULT_AGENT_CONFIGS: dict[AgentRole, AgentConfig] = {
    AgentRole.CODER: AgentConfig(
        role=AgentRole.CODER, name="coder", display_name="编程专家",
        system_prompt="你是一个编程专家。直接给出高质量、可运行的代码。\n"
                       "重要：只需要给出代码本身和简短说明，不要大段分析过程。",
        description="负责代码生成、调试、重构、算法实现",
        capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.CODE_DEBUGGING],
        tools=["file_tools", "knowledge_toolkit"],
        timeout_seconds=120.0,
    ),
    AgentRole.SEARCHER: AgentConfig(
        role=AgentRole.SEARCHER, name="searcher", display_name="搜索专家",
        system_prompt="你是一个信息检索专家。\n核心规则：\n"
                       "1. 只输出基于事实的简洁回答\n"
                       "2. 不要列出信息来源URL或大段引用原文\n"
                       "3. 不确定时直接说明，不要编造\n"
                       "4. 优先使用搜索工具获取最新信息",
        description="负责信息检索、文档查询、知识库搜索",
        capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.KNOWLEDGE_RETRIEVAL],
        tools=["web_search_toolkit", "knowledge_toolkit"],
        timeout_seconds=120.0,
    ),
    AgentRole.OPS: AgentConfig(
        role=AgentRole.OPS, name="ops", display_name="运维专家",
        system_prompt="你是一个运维专家。直接给出操作命令和配置方案。\n"
                       "重要：只输出关键操作步骤和命令，不要大段分析。",
        description="负责部署、配置、故障排查",
        capabilities=[AgentCapability.SYSTEM_OPERATION, AgentCapability.TROUBLESHOOTING],
        tools=["file_tools"],
        timeout_seconds=120.0,
    ),
    AgentRole.SKILL_EXECUTOR: AgentConfig(
        role=AgentRole.SKILL_EXECUTOR, name="skill_executor", display_name="技能执行器",
        system_prompt="你是一个技能执行器。根据需求调用已注册的技能。\n"
                       "重要：只输出执行结果，不要多余说明。",
        description="调用已注册的技能",
        capabilities=[AgentCapability.SKILL_EXECUTION],
        tools=[],  # 技能工具在 AgentBuilder 中动态注入
        timeout_seconds=120.0,
    ),
}
```

- Coder system prompt 去掉了对 `web_search` 的引用（修正 bug）
- 每个 AgentConfig 自带独立的 timeout_seconds

### 2. AgentBuilder 激活

`AgentBuilder` 现有代码基本可用，微调：

- `build_agent()` 将 `AgentConfig.timeout_seconds` 挂载到返回的 agent 实例 `_timeout_seconds` 属性
- `build_with_config()` 沿用 `AgentConfig.timeout_seconds`

### 3. AgentOrchestrator 重构

核心变化：

- 删除 4 个 `_make_*_tool()` 工厂函数，替换为单一通用函数 `_build_agent_tool(config, model)`
- `_build_agent_tool` 内部：
  - 通过 `AgentBuilder.build_agent(config, model)` 创建子 Agent
  - 用 `asyncio.wait_for` 对每个子 Agent 调用施加独立超时
  - 记录每次调用到 `self._tool_call_log`（agent 名、任务描述、耗时、成功/失败）
- `run()` 返回的字典中新增 `tool_calls` 字段
- 删除 `_resolve_sub_tools()`（逻辑已在 AgentBuilder 中）

```python
class AgentOrchestrator:
    def __init__(self, agent_configs=None, timeout=300.0):
        self._configs = agent_configs or DEFAULT_AGENT_CONFIGS
        self._timeout = timeout
        self._builder = AgentBuilder()
        self._tool_call_log = []

    def _build_agent_tool(self, config: AgentConfig, model):
        # 统一子 Agent 创建逻辑
        ...

    async def run(self, user_input: str) -> dict:
        # 返回新增 tool_calls 字段
        return {
            "success": True, "answer": ..., "error": None,
            "duration_seconds": ..., "tool_calls": self._tool_call_log,
        }
```

### 4. 技能执行器动态参数

`execute_skill_by_name` 工具签名新增 `params: dict = None` 参数，由 LLM 自动填充：

```python
@tool
def execute_skill_by_name(skill_name: str, params: dict = None) -> str:
    """按名称执行指定技能。params 为技能参数字典。"""
    ...
    result = executor.execute(
        step={"skill": skill_name, "params": params or {}, "name": skill_name},
        context=context,
    )
```

### 5. 死代码清理

| 删除 / 精简 | 说明 |
|-------------|------|
| `integrations.py` 中 `_CODER_SYSTEM_PROMPT` 等 4 个常量 | 移到 `agent_configs.py` |
| `integrations.py` 中 `build_system_prompt_for_role()` | 改为从 AgentConfig 读取 |
| `agent_orchestrator.py` 中 `_make_coder_tool` 等 4 个函数 | 被 `_build_agent_tool` 替代 |
| `agent_orchestrator.py` 中 `_resolve_sub_tools()` | 已在 AgentBuilder 中存在 |
| `types.py` 中 `AgentRole.SUPERVISOR`、`GENERAL` | 未使用，保留但标注 |

### 6. 前端改动

- 保持表单提交模式
- 响应 `tool_calls` 数组驱动 badge 区域动态渲染
- 每个 badge 显示：子 Agent 名称 + 耗时 + 成功/失败状态（绿色/红色）

### 7. 测试覆盖

- `DEFAULT_AGENT_CONFIGS` 每个角色配置正确
- `AgentBuilder.build_agent(config)` 可在无 LLM 调用的情况下构建
- `_build_agent_tool` 超时处理
- `_tool_call_log` 记录完整性
- `execute_skill_by_name` 接收动态 params

---

## Phase 2 — 流式 + 会话

### 1. SSE 流式端点

新增 `POST /api/agent-orchestrator/stream`，`text/event-stream`。

事件格式复用主对话 `{type: content|tool_call|tool_result}`：

```
data: {"type": "tool_call", "name": "run_coder", "args": {"task": "写快排"}}

data: {"type": "tool_result", "name": "run_coder", "content": "def quicksort...", "duration_ms": 2300}

data: {"type": "content", "content": "已为您生成快排代码..."}

data: {"type": "done"}
```

Orchestrator 新增 `astream()` 方法，使用 LangGraph 的 `astream_events(version="v2")` 捕获子 Agent 工具调用的 `on_tool_start`/`on_tool_end` 和 LLM 输出的 `on_chat_model_stream` 事件。

### 2. 会话持久化

**Orchestrator 主会话** — 走现有 `sessions` 表，新增 `mode` 字段：

| mode | 含义 |
|------|------|
| `chat` | 普通对话（默认） |
| `orchestrator` | 多智能体编排 |

**子 Agent 旁链** — 用层级 thread_id 写入 LangGraph checkpoint：

```
orch_{session_id}              ← 编排器主 thread
orch_{session_id}/coder_1      ← 第 1 次调用 Coder
orch_{session_id}/search_1     ← 第 1 次调用 Searcher
```

层级命名天然形成树形结构，前缀查询可得所有子 Agent 调用记录。前端可按需请求旁链详情。

**PgSessionManager 扩展** — `list_sessions()` 支持 `mode` 过滤参数。

### 3. 前端对话界面

`MultiAgentPage.tsx` 从表单升级为对话界面：

- 复用 `ChatMessage` 组件
- 新增 `ToolCallCard` 组件（可折叠，显示子 Agent 名 + 耗时 + 状态 + 任务描述）
- SSE 流式渲染，边收边显示
- Sidebar 新增"多智能体"会话类型，图标区分

### 4. API 路由

| 方法 | 路径 | Phase | 用途 |
|------|------|-------|------|
| POST | `/api/agent-orchestrator/execute` | 1 | 同步执行 |
| POST | `/api/agent-orchestrator/stream` | 2 | SSE 流式执行 |
| GET | `/api/agent-orchestrator/sessions` | 2 | 会话列表 |
| GET | `/api/agent-orchestrator/sessions/{id}/sidechains` | 2 | 子 Agent 旁链 |

---

## 边界与取舍

- **不引入 AgentPool 或事件总线**：当前 4 个子 Agent 场景下，Agent-as-Tool 足够简洁
- **子 Agent 间不直接通信**：由编排器协调足够覆盖典型场景（搜索→编码、编码→运维）
- **子 Agent 配置保持硬编码**：不引入运行时动态注册，需求出现时再扩展
- **Checkpoint 用 MemorySaver**（Phase 1），Phase 2 子 Agent 旁链可升级为 PostgreSQL 持久化
- **不修改主对话 Agent（code_agent.py）**：多智能体独立演进，不和现有单 Agent 流程耦合

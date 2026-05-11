# 多智能体架构设计文档

## 架构演进

| | 旧版 MultiAgentCrew | 新版 AgentOrchestrator |
|---|---|---|
| 模式 | Supervisor 监督 + 关键词路由 | Agent-as-Tool（工具化调用） |
| 全局状态 | `agent_registry` 等 5 个全局单例 | 零全局状态，每次请求全新实例 |
| 任务路由 | 正则关键词匹配，容易误判 | LLM function calling 自动决策 |
| 并行执行 | 手动 `asyncio.gather` | LLM 自然发起并行 tool call |
| 通信层 | `CommunicationProtocol`（实际未使用） | 无需通信层，工具返回值即通信 |
| Checkpoint | LangGraph 持久化，跨请求污染 | 每请求独立 `MemorySaver` |
| 扩展性 | 需要修改 registry/router/crew 三层 | 新增 `@tool` 函数即可 |

## 架构图

```
POST /api/agent-orchestrator/execute
            │
            ▼
    ┌───────────────────┐
    │  AgentOrchestrator │  ← 单个 Agent，负责协调
    │  (system prompt)   │
    └───────┬───────────┘
            │ function calling
   ┌────────┼────────┬────────┬──────────┐
   ▼        ▼        ▼        ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│coder │ │search│ │ ops  │ │skill │ │ sop  │
│Agent │ │Agent │ │Agent │ │exec  │ │exec  │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
   │        │        │        │        │
   └────────┴────┬───┴────────┴────────┘
                 │ 各自返回结果
                 ▼
    ┌───────────────────┐
    │  最终整合回答       │
    └───────────────────┘
```

## 核心文件

| 文件 | 职责 |
|------|------|
| `multi_agent/agent_orchestrator.py` | Orchestrator 主逻辑，为每个子 Agent 封装 `@tool` |
| `multi_agent/integrations.py` | 子 Agent 的 system prompt 和工具加载 |
| `multi_agent/agent_builder.py` | Agent 实例构建器，工具解析 |
| `multi_agent/types.py` | 枚举类型（AgentRole / AgentCapability / AgentConfig） |
| `server/routes/agent_orchestrator.py` | REST API 路由 |

## API

### POST /api/agent-orchestrator/execute

```json
// Request
{
  "task": "用 Python 实现快速排序"
}

// Response
{
  "success": true,
  "answer": "def quick_sort(arr):\n    ...",
  "error": null,
  "duration_seconds": 12.5
}
```

### POST /api/agent-orchestrator/execute-stream

SSE 流式响应，`text/event-stream`。

## 可用专家

| 工具名 | 角色 | 触发场景 |
|--------|------|----------|
| `run_coder` | 编程专家 | 代码生成、调试、重构、算法实现 |
| `run_searcher` | 搜索专家 | 信息检索、文档查询、知识库搜索 |
| `run_ops` | 运维专家 | 部署配置、故障排查、性能调优 |
| `run_skill_executor` | 技能执行器 | 调用已注册的用户技能 |
| `run_sop_executor` | SOP 执行器 | 按标准操作流程执行任务 |

## 如何扩展新 Agent

1. 在 `agent_orchestrator.py` 中新增 `_make_xxx_tool(model)` 函数：

```python
def _make_designer_tool(model):
    agent = create_agent(
        model=model,
        system_prompt="你是一个 UI 设计师...",
        checkpointer=MemorySaver(),
    )

    @langchain_tool
    async def run_designer(task_description: str) -> str:
        """UI 设计专家。当需要设计界面、优化用户体验时调用。"""
        resp = await agent.ainvoke({...})
        return _extract_content(resp)

    return run_designer
```

2. 在 `AgentOrchestrator.run()` 中的 `tools` 列表里追加：

```python
try:
    tools.append(_make_designer_tool(model))
except Exception as e:
    logger.warning(f"创建 designer tool 失败: {e}")
```

3. 更新 `_ORCHESTRATOR_SYSTEM_PROMPT` 的工具说明。

## 设计原则

- **零全局状态**：每次 `run()` 创建全新的 Agent 和工具实例
- **独立 checkpoint**：使用纳秒时间戳作为 thread_id，彻底隔离
- **工具即接口**：Agent 之间通过 `@tool` 返回值通信，无需额外通信层
- **按需创建**：子 Agent 在 orchestrator 调用时才创建，不占用常驻资源
- **简洁输出**：system prompt 强制约束输出风格，不展示内部过程

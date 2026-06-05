# 多智能体核心功能升级 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将多智能体系统从基础的一次性任务提交升级为核心功能，清理架构、补全能力、支持流式输出和会话持久化。

**Architecture:** 统一使用 AgentBuilder + AgentConfig 驱动子 Agent 创建，Agent-as-Tool 模式不变。Phase 1 完成架构清理和同步 JSON 响应增强；Phase 2 新增 SSE 流式端点和会话持久化。

**Tech Stack:** LangChain/LangGraph, FastAPI SSE StreamingResponse, React 18 + TypeScript, PostgreSQL sessions 表扩展

---

## File Structure

| 文件 | 职责 | Phase |
|------|------|-------|
| `Coder/multi_agent/types.py` | AgentRole/AgentConfig/AgentCapability 定义 | 已有，不改 |
| `Coder/multi_agent/agent_configs.py` | **新建** — DEFAULT_AGENT_CONFIGS 集中配置 | 1 |
| `Coder/multi_agent/agent_builder.py` | 子 Agent 统一工厂，超时元数据挂载 | 1 修改 |
| `Coder/multi_agent/integrations.py` | 技能工具、模型解析；system prompt 委托给 AgentConfig | 1 修改 |
| `Coder/multi_agent/agent_orchestrator.py` | 编排器，配置驱动子 Agent 创建，run()/astream() | 1+2 |
| `Coder/multi_agent/__init__.py` | 模块导出 | 1 修改 |
| `Coder/server/schemas.py` | OrchestratorExecuteRequest 扩展 tool_calls | 1 修改 |
| `Coder/server/routes/agent_orchestrator.py` | execute + stream + sessions 端点 | 1+2 |
| `Coder/storage/<session-schema>.py` | sessions 表 mode 字段 | 2 修改 |
| `Coder/web/src/types.ts` | OrchestratorResult 扩展 tool_calls | 1 修改 |
| `Coder/web/src/pages/MultiAgentPage.tsx` | 动态 badge + Phase 2 流式 | 1+2 |
| `Coder/tests/test_multi_agent.py` | 测试覆盖新路径 | 1+2 |

---

## Phase 1 — 架构清理 + 能力补全

### Task 1: 创建 agent_configs.py 集中配置

**Files:**
- Create: `Coder/multi_agent/agent_configs.py`
- Modify: `Coder/multi_agent/__init__.py`

- [ ] **Step 1: 创建 agent_configs.py**

```python
"""子 Agent 默认配置，由 AgentConfig 数据类统一驱动。"""
from Coder.multi_agent.types import AgentRole, AgentConfig, AgentCapability

DEFAULT_AGENT_CONFIGS: dict[AgentRole, AgentConfig] = {
    AgentRole.CODER: AgentConfig(
        role=AgentRole.CODER,
        name="coder",
        display_name="编程专家",
        system_prompt=(
            "你是一个编程专家。直接给出高质量、可运行的代码。\n"
            "重要：只需要给出代码本身和简短说明，不要大段分析过程。"
        ),
        description="负责代码生成、调试、重构、算法实现",
        capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.CODE_DEBUGGING],
        tools=["file_tools", "knowledge_toolkit"],
        timeout_seconds=120.0,
    ),
    AgentRole.SEARCHER: AgentConfig(
        role=AgentRole.SEARCHER,
        name="searcher",
        display_name="搜索专家",
        system_prompt=(
            "你是一个信息检索专家。\n"
            "核心规则：\n"
            "1. 只输出基于事实的简洁回答\n"
            "2. 不要列出信息来源URL或大段引用原文\n"
            "3. 不确定时直接说明，不要编造\n"
            "4. 优先使用搜索工具获取最新信息"
        ),
        description="负责信息检索、文档查询、知识库搜索",
        capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.KNOWLEDGE_RETRIEVAL],
        tools=["web_search_toolkit", "knowledge_toolkit"],
        timeout_seconds=120.0,
    ),
    AgentRole.OPS: AgentConfig(
        role=AgentRole.OPS,
        name="ops",
        display_name="运维专家",
        system_prompt=(
            "你是一个运维专家。直接给出操作命令和配置方案。\n"
            "重要：只输出关键操作步骤和命令，不要大段分析。"
        ),
        description="负责部署、配置、故障排查",
        capabilities=[AgentCapability.SYSTEM_OPERATION, AgentCapability.TROUBLESHOOTING],
        tools=["file_tools"],
        timeout_seconds=120.0,
    ),
    AgentRole.SKILL_EXECUTOR: AgentConfig(
        role=AgentRole.SKILL_EXECUTOR,
        name="skill_executor",
        display_name="技能执行器",
        system_prompt=(
            "你是一个技能执行器。根据需求调用已注册的技能。\n"
            "重要：只输出执行结果，不要多余说明。"
        ),
        description="调用已注册的技能",
        capabilities=[AgentCapability.SKILL_EXECUTION],
        tools=[],  # 技能工具由 AgentBuilder 动态注入
        timeout_seconds=120.0,
    ),
}
```

- [ ] **Step 2: 更新 __init__.py 导出**

```python
from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentConfig,
)
from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS
from Coder.multi_agent.integrations import (
    build_system_prompt_for_role,
    resolve_agent_model,
)
from Coder.multi_agent.agent_builder import AgentBuilder
from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

__all__ = [
    "AgentRole",
    "AgentCapability",
    "AgentConfig",
    "DEFAULT_AGENT_CONFIGS",
    "AgentBuilder",
    "AgentOrchestrator",
    "build_system_prompt_for_role",
    "resolve_agent_model",
]
```

- [ ] **Step 3: Commit**

```bash
git add Coder/multi_agent/agent_configs.py Coder/multi_agent/__init__.py
git commit -m "feat: add DEFAULT_AGENT_CONFIGS to centralize sub-agent configuration"
```

---

### Task 2: 清理 integrations.py

**Files:**
- Modify: `Coder/multi_agent/integrations.py:1-127`

- [ ] **Step 1: 重写 integrations.py**

删除 4 个硬编码 prompt 常量（`_CODER_SYSTEM_PROMPT` 等，第 10-33 行），`build_system_prompt_for_role()` 改为从 `DEFAULT_AGENT_CONFIGS` 读取；`execute_skill_by_name` 签名新增 `params` 参数。

```python
import logging
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool, tool

from Coder.multi_agent.types import AgentRole

logger = logging.getLogger(__name__)


def build_system_prompt_for_role(role: AgentRole) -> str:
    """从 AgentConfig 读取角色的 system_prompt，不硬编码字符串。"""
    from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

    config = DEFAULT_AGENT_CONFIGS.get(role)
    if config is not None:
        return config.system_prompt
    # fallback：未知角色返回通用编程提示
    return "你是一个智能助手。请直接给出高质量的回答。"


def resolve_agent_model(agent_config):
    try:
        from Coder.model import llm as default_llm
    except Exception:
        default_llm = None

    if agent_config.model_name:
        try:
            from langchain_openai import ChatOpenAI
            import os
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
            return ChatOpenAI(
                model=agent_config.model_name,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key=api_key,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens,
                streaming=True,
            )
        except Exception as e:
            logger.warning(
                f"无法创建模型 {agent_config.model_name}: {e}，使用默认LLM"
            )

    if default_llm:
        return default_llm.bind(
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
        )

    raise RuntimeError("没有可用的 LLM 模型")


def get_skill_tools() -> List[BaseTool]:
    tools_list = []

    @tool
    def list_available_skills() -> str:
        """列出所有可用的技能"""
        try:
            from Coder.tools.skill_registry import SkillRegistry
            registry = SkillRegistry()
            if not registry._initialized:
                registry.initialize()
            skills = registry.list_all()
            if not skills:
                return "当前没有可用的技能"
            lines = []
            for s in skills:
                lines.append(f"- {s.name}: {s.display_name} ({s.description[:80]})")
            return "\n".join(lines)
        except Exception as e:
            return f"获取技能列表失败: {e}"

    @tool
    def execute_skill_by_name(skill_name: str, params: dict = None) -> str:
        """按名称执行指定技能。params 为技能参数字典，由调用方根据技能需求传入。"""
        try:
            from Coder.tools.skill_registry import SkillRegistry
            from Coder.tools.skill_executor import SkillExecutor, ExecutionContext
            registry = SkillRegistry()
            if not registry._initialized:
                registry.initialize()
            executor = SkillExecutor(registry)
            context = ExecutionContext()
            result = executor.execute(
                step={
                    "skill": skill_name,
                    "params": params or {},
                    "name": skill_name,
                },
                context=context,
            )
            if result.status.value == "success":
                return f"技能 '{skill_name}' 执行成功: {result.result}"
            else:
                return f"技能 '{skill_name}' 执行失败: {result.error}"
        except Exception as e:
            return f"执行技能失败: {e}"

    tools_list.append(list_available_skills)
    tools_list.append(execute_skill_by_name)
    return tools_list
```

- [ ] **Step 2: 验证无残留引用**

```bash
grep -rn "_CODER_SYSTEM_PROMPT\|_SEARCHER_SYSTEM_PROMPT\|_OPS_SYSTEM_PROMPT\|_SKILL_EXECUTOR_PROMPT" Coder/ --include="*.py"
```

Expected: no matches (确认旧常量未被引用)

- [ ] **Step 3: Commit**

```bash
git add Coder/multi_agent/integrations.py
git commit -m "refactor: delegate system prompts to AgentConfig, add dynamic params to skill executor"
```

---

### Task 3: 更新 AgentBuilder 挂载超时

**Files:**
- Modify: `Coder/multi_agent/agent_builder.py:29-63`

- [ ] **Step 1: 修改 build_agent() 挂载 timeout_seconds**

在 `agent_builder.py` 第 56-62 行，`create_agent()` 调用后将 `agent_config.timeout_seconds` 挂到 agent 实例上。

将第 56-62 行的：

```python
        agent = create_agent(
            model=model,
            tools=tools or None,
            system_prompt=agent_config.system_prompt,
            checkpointer=self._checkpointer,
            debug=False,
        )
        return agent
```

替换为：

```python
        agent = create_agent(
            model=model,
            tools=tools or None,
            system_prompt=agent_config.system_prompt,
            checkpointer=self._checkpointer,
            debug=False,
        )
        # 挂载超时配置供 orchestrator 使用
        agent._agent_timeout = agent_config.timeout_seconds
        return agent
```

- [ ] **Step 2: Commit**

```bash
git add Coder/multi_agent/agent_builder.py
git commit -m "feat: attach timeout_seconds from AgentConfig to built agent instance"
```

---

### Task 4: 重写 AgentOrchestrator

**Files:**
- Modify: `Coder/multi_agent/agent_orchestrator.py` (完整重写)

- [ ] **Step 1: 重写 agent_orchestrator.py**

删除 4 个 `_make_*_tool()` 工厂函数和 `_resolve_sub_tools()`，替换为配置驱动的 `_build_agent_tool()` 通用函数。

```python
import asyncio
import time
import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool as langchain_tool
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS
from Coder.multi_agent.agent_builder import AgentBuilder
from Coder.multi_agent.types import AgentRole, AgentConfig

logger = logging.getLogger(__name__)

_ORCHESTRATOR_SYSTEM_PROMPT = """你是一个智能任务协调者。你可以按需调用以下专家:

- run_coder: 编程专家,负责代码生成、调试、重构、算法实现等
- run_searcher: 搜索专家,负责信息检索、文档查询、知识库搜索等
- run_ops: 运维专家,负责部署、配置、故障排查等
- run_skill_executor: 技能执行器,调用已注册的技能

工作方式:
1. 分析用户需求
2. 按合理顺序调用需要的专家(先搜索再编码等)
3. 整合各专家结果,输出简洁完整的回答

回答要求（非常重要）:
- 直接输出最终答案，不要展示"任务分析"、"子任务分配"等过程
- 代码类问题：直接给出代码和一句话说明
- 搜索类问题：只输出关键结论，不要列出信息来源/URL
- 多步骤任务：整合为一个连贯回答，不要分段重复
- 总原则：简洁 > 完整，宁可少写不要多写"""


def _extract_content(response) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        messages = response.get("messages", [])
        parts = []
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = msg.content
                if content and isinstance(content, str):
                    tc = getattr(msg, "tool_calls", None)
                    ak = getattr(msg, "additional_kwargs", {}) if hasattr(msg, "additional_kwargs") else {}
                    if not tc and not ak.get("tool_calls"):
                        parts.append(content)
            elif hasattr(msg, "content"):
                c = msg.content
                if c and isinstance(c, str):
                    parts.append(c)
        return "\n\n".join(reversed(parts)) if parts else ""
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
            return "\n".join(texts) if texts else str(content)
        return str(content)
    if isinstance(response, list):
        return _extract_content({"messages": response})
    return str(response)


class AgentOrchestrator:

    def __init__(self, agent_configs: Dict[AgentRole, AgentConfig] = None, timeout: float = 300.0):
        self._configs = agent_configs or DEFAULT_AGENT_CONFIGS
        self._timeout = timeout
        self._builder = AgentBuilder()
        self._tool_call_log: List[Dict[str, Any]] = []

    def _get_model(self):
        from Coder.model import llm as default_llm
        return default_llm

    def _build_agent_tool(self, config: AgentConfig, model):
        """通用子 Agent 工厂：AgentBuilder 创建 + @langchain_tool 包装 + 独立超时。"""
        agent = self._builder.build_agent(config, model)
        agent_timeout = getattr(agent, "_agent_timeout", 120.0)
        role_name = config.display_name
        agent_name = config.name

        @langchain_tool
        async def agent_tool(task: str) -> str:
            start = time.time()
            try:
                resp = await asyncio.wait_for(
                    agent.ainvoke(
                        {"messages": [HumanMessage(content=task)]},
                        config=RunnableConfig(configurable={
                            "thread_id": f"{agent_name}_{time.time_ns()}"
                        }),
                    ),
                    timeout=agent_timeout,
                )
                elapsed = time.time() - start
                self._tool_call_log.append({
                    "agent": agent_name,
                    "display_name": role_name,
                    "task": task[:200],
                    "duration_ms": int(elapsed * 1000),
                    "success": True,
                })
                return _extract_content(resp)
            except asyncio.TimeoutError:
                elapsed = time.time() - start
                self._tool_call_log.append({
                    "agent": agent_name,
                    "display_name": role_name,
                    "task": task[:200],
                    "duration_ms": int(elapsed * 1000),
                    "success": False,
                    "error": "超时",
                })
                return f"{role_name}执行超时 ({agent_timeout}s)"
            except Exception as e:
                elapsed = time.time() - start
                self._tool_call_log.append({
                    "agent": agent_name,
                    "display_name": role_name,
                    "task": task[:200],
                    "duration_ms": int(elapsed * 1000),
                    "success": False,
                    "error": str(e),
                })
                return f"{role_name}出错: {e}"

        # 复制 docstring 和 name 以便 LLM 识别
        agent_tool.__doc__ = config.description
        agent_tool.name = f"run_{agent_name}"
        return agent_tool

    async def run(self, user_input: str) -> Dict[str, Any]:
        start_time = time.time()
        model = self._get_model()
        self._tool_call_log = []

        tools: List = []
        for config in self._configs.values():
            try:
                tool = self._build_agent_tool(config, model)
                tools.append(tool)
            except Exception as e:
                logger.warning(f"创建 {config.display_name} tool 失败: {e}")

        orchestrator = create_agent(
            model=model,
            tools=tools,
            system_prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )

        try:
            response = await asyncio.wait_for(
                orchestrator.ainvoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=RunnableConfig(
                        configurable={"thread_id": f"orch_{time.time_ns()}"}
                    ),
                ),
                timeout=self._timeout,
            )
            answer = _extract_content(response)
            return {
                "success": True,
                "answer": answer,
                "error": None,
                "duration_seconds": time.time() - start_time,
                "tool_calls": self._tool_call_log,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "answer": "",
                "error": f"执行超时 ({self._timeout}s)",
                "duration_seconds": time.time() - start_time,
                "tool_calls": self._tool_call_log,
            }
        except Exception as e:
            logger.error(f"Orchestrator 失败: {e}")
            return {
                "success": False,
                "answer": "",
                "error": str(e),
                "duration_seconds": time.time() - start_time,
                "tool_calls": self._tool_call_log,
            }
```

- [ ] **Step 2: Commit**

```bash
git add Coder/multi_agent/agent_orchestrator.py
git commit -m "refactor: rewrite AgentOrchestrator with config-driven AgentBuilder, per-agent timeout, tool call logging"
```

---

### Task 5: 更新 API schemas 和路由

**Files:**
- Modify: `Coder/server/schemas.py:49-51`
- Modify: `Coder/server/routes/agent_orchestrator.py:1-21`

- [ ] **Step 1: 扩展 OrchestratorExecuteRequest schema**

将 `schemas.py` 第 49-51 行替换为：

```python
class OrchestratorExecuteRequest(BaseModel):
    task: str
    mode: str = Field(default="orchestrator")


class OrchestratorToolCall(BaseModel):
    agent: str
    display_name: str
    task: str
    duration_ms: int
    success: bool
    error: str = ""


class OrchestratorExecuteResponse(BaseModel):
    success: bool
    answer: str
    error: Optional[str] = None
    duration_seconds: float
    tool_calls: List[OrchestratorToolCall] = Field(default_factory=list)
```

- [ ] **Step 2: 更新路由返回 tool_calls**

将 `agent_orchestrator.py` route 替换为：

```python
import logging
from fastapi import APIRouter, Request
from Coder.server.schemas import OrchestratorExecuteRequest, OrchestratorExecuteResponse, OrchestratorToolCall

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/execute", response_model=OrchestratorExecuteResponse)
async def execute_task(req: OrchestratorExecuteRequest, request: Request):
    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    result = await orch.run(req.task)

    return OrchestratorExecuteResponse(
        success=result["success"],
        answer=result["answer"],
        error=result.get("error"),
        duration_seconds=result["duration_seconds"],
        tool_calls=[
            OrchestratorToolCall(**tc)
            for tc in result.get("tool_calls", [])
        ],
    )
```

- [ ] **Step 3: Commit**

```bash
git add Coder/server/schemas.py Coder/server/routes/agent_orchestrator.py
git commit -m "feat: add tool_calls to orchestrator API response schema and route"
```

---

### Task 6: 更新前端类型和动态 badge

**Files:**
- Modify: `Coder/web/src/types.ts:45-50`
- Modify: `Coder/web/src/pages/MultiAgentPage.tsx:1-101`

- [ ] **Step 1: 扩展前端类型**

将 `types.ts` 第 45-50 行替换为：

```typescript
export interface OrchestratorToolCall {
  agent: string
  display_name: string
  task: string
  duration_ms: number
  success: boolean
  error?: string
}

export interface OrchestratorResult {
  success: boolean
  answer: string
  error: string | null
  duration_seconds: number
  tool_calls: OrchestratorToolCall[]
}
```

- [ ] **Step 2: 更新 MultiAgentPage 动态 badge**

将 `MultiAgentPage.tsx` 第 84-94 行的静态 badge 替换为动态渲染：

```typescript
import { useState } from 'react'
import { api } from '../api/client'
import type { OrchestratorResult } from '../types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, CheckCircle, XCircle, Clock } from 'lucide-react'

export function MultiAgentPage() {
  const [task, setTask] = useState('')
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState<OrchestratorResult | null>(null)

  const handleExecute = async () => {
    if (!task.trim()) return
    setExecuting(true)
    setResult(null)
    try {
      const data = await api.post<OrchestratorResult>('/agent-orchestrator/execute', {
        task: task.trim(),
      })
      setResult(data)
    } catch (e) {
      setResult({ success: false, answer: '', error: String(e), duration_seconds: 0, tool_calls: [] })
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-2 text-slate-900 dark:text-slate-100">智能任务协调者</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Agent-as-Tool — 专家智能体按需调用，自动协调
      </p>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle className="text-sm">执行任务</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            rows={3}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="描述你的任务，AI 将自动调用最适合的专家 Agent 执行..."
            className="text-sm resize-none"
          />
          <Button
            onClick={handleExecute}
            disabled={!task.trim() || executing}
            className="bg-blue-600 hover:bg-blue-500"
          >
            <Bot className="h-4 w-4 mr-2" />
            {executing ? '执行中...' : '执行任务'}
          </Button>

          {result && (
            <div className="mt-4 space-y-4">
              <div
                className={`flex items-center gap-2 text-sm ${
                  result.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                }`}
              >
                {result.success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                {result.success
                  ? `执行成功 (耗时: ${result.duration_seconds.toFixed(1)}s)`
                  : `执行失败: ${result.error}`}
              </div>
              {result.answer && (
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {result.answer}
                    </p>
                  </CardContent>
                </Card>
              )}
              {result.tool_calls.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {result.tool_calls.map((tc, i) => (
                    <Badge
                      key={i}
                      variant={tc.success ? 'secondary' : 'destructive'}
                      className="text-[10px] flex items-center gap-1"
                    >
                      {tc.success ? (
                        <CheckCircle className="h-3 w-3" />
                      ) : (
                        <XCircle className="h-3 w-3" />
                      )}
                      {tc.display_name}
                      <Clock className="h-3 w-3 ml-1" />
                      {(tc.duration_ms / 1000).toFixed(1)}s
                    </Badge>
                  ))}
                </div>
              )}
              {result.tool_calls.length === 0 && result.success && (
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="secondary" className="text-[10px]">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    编排器直接处理
                  </Badge>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add Coder/web/src/types.ts Coder/web/src/pages/MultiAgentPage.tsx
git commit -m "feat: dynamic agent call badges in MultiAgentPage, showing actual invocation status"
```

---

### Task 7: 更新测试

**Files:**
- Modify: `Coder/tests/test_multi_agent.py`

- [ ] **Step 1: 重写测试文件**

```python
import pytest
from Coder.multi_agent.types import (
    AgentRole,
    AgentCapability,
    AgentConfig,
)


class TestAgentConfigs:
    def test_default_configs_have_all_roles(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        assert AgentRole.CODER in DEFAULT_AGENT_CONFIGS
        assert AgentRole.SEARCHER in DEFAULT_AGENT_CONFIGS
        assert AgentRole.OPS in DEFAULT_AGENT_CONFIGS
        assert AgentRole.SKILL_EXECUTOR in DEFAULT_AGENT_CONFIGS

    def test_coder_has_no_web_search_reference(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        coder_config = DEFAULT_AGENT_CONFIGS[AgentRole.CODER]
        assert "web_search" not in coder_config.system_prompt
        assert "web_search_toolkit" not in coder_config.tools

    def test_each_config_has_timeout(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        for role, config in DEFAULT_AGENT_CONFIGS.items():
            assert config.timeout_seconds > 0, f"{role} missing timeout"

    def test_searcher_has_web_search(self):
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        searcher_config = DEFAULT_AGENT_CONFIGS[AgentRole.SEARCHER]
        assert "web_search_toolkit" in searcher_config.tools


class TestTypes:
    def test_agent_role_enum_values(self):
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.SEARCHER.value == "searcher"
        assert AgentRole.OPS.value == "ops"

    def test_agent_config_defaults(self):
        config = AgentConfig(
            role=AgentRole.CODER,
            name="test_coder",
            display_name="Test Coder",
            system_prompt="You are a coder.",
            description="Test agent",
        )
        assert config.role == AgentRole.CODER
        assert config.name == "test_coder"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096
        assert config.timeout_seconds == 120.0


class TestIntegrations:
    def test_build_system_prompt_for_coder(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.CODER)
        assert "编程" in prompt

    def test_build_system_prompt_for_searcher(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.SEARCHER)
        assert "搜索" in prompt or "检索" in prompt

    def test_build_system_prompt_for_unknown_role_fallback(self):
        from Coder.multi_agent.integrations import build_system_prompt_for_role
        prompt = build_system_prompt_for_role(AgentRole.GENERAL)
        assert len(prompt) > 0

    def test_get_skill_tools_returns_two_tools(self):
        from Coder.multi_agent.integrations import get_skill_tools
        tools = get_skill_tools()
        assert len(tools) == 2

    def test_execute_skill_by_name_has_params_param(self):
        from Coder.multi_agent.integrations import get_skill_tools
        import inspect

        tools = get_skill_tools()
        exec_tool = [t for t in tools if t.name == "execute_skill_by_name"][0]
        sig = inspect.signature(exec_tool.func)
        assert "params" in sig.parameters


class TestAgentBuilder:
    def test_create_builder(self):
        from Coder.multi_agent.agent_builder import AgentBuilder
        builder = AgentBuilder()
        assert builder is not None
        assert builder.checkpointer is not None

    def test_build_agent_with_config(self):
        from Coder.multi_agent.agent_builder import AgentBuilder
        from Coder.multi_agent.agent_configs import DEFAULT_AGENT_CONFIGS

        builder = AgentBuilder()
        config = DEFAULT_AGENT_CONFIGS[AgentRole.CODER]
        agent = builder.build_agent(config)
        assert agent is not None
        timeout = getattr(agent, "_agent_timeout", None)
        assert timeout == config.timeout_seconds


class TestAgentOrchestrator:
    def test_create_orchestrator(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        assert orch is not None
        assert orch._timeout == 300.0
        assert len(orch._configs) >= 4

    def test_extract_content_string(self):
        from Coder.multi_agent.agent_orchestrator import _extract_content
        assert _extract_content("hello") == "hello"
        assert _extract_content(None) == ""

    def test_extract_content_aimessage(self):
        from Coder.multi_agent.agent_orchestrator import _extract_content
        from langchain_core.messages import AIMessage
        msg = AIMessage(content="test answer")
        result = _extract_content({"messages": [msg]})
        assert "test answer" in result

    def test_run_invalid_returns_error(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        import asyncio

        async def _run():
            orch = AgentOrchestrator(timeout=0.001)
            return await orch.run("test")

        result = asyncio.run(_run())
        assert result["success"] is False
        assert result["error"] is not None
        assert "tool_calls" in result

    def test_response_includes_tool_calls_field(self):
        from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
        import asyncio

        async def _run():
            orch = AgentOrchestrator(timeout=0.001)
            return await orch.run("test")

        result = asyncio.run(_run())
        assert "tool_calls" in result
        assert isinstance(result["tool_calls"], list)


class TestModuleExports:
    def test_multi_agent_init_exports(self):
        from Coder.multi_agent import (
            AgentRole,
            AgentConfig,
            AgentBuilder,
            AgentOrchestrator,
            DEFAULT_AGENT_CONFIGS,
        )
        assert AgentRole is not None
        assert AgentBuilder is not None
        assert AgentOrchestrator is not None
        assert DEFAULT_AGENT_CONFIGS is not None
```

- [ ] **Step 2: 运行测试**

```bash
pytest Coder/tests/test_multi_agent.py -v
```

Expected: 16 passed

- [ ] **Step 3: Commit**

```bash
git add Coder/tests/test_multi_agent.py
git commit -m "test: expand multi-agent tests for config-driven architecture and tool_call_log"
```

---

### Task 8: Phase 1 集成验证

**Files:** 无（验证步骤）

- [ ] **Step 1: 启动后端验证导入**

```bash
python -c "from Coder.multi_agent import AgentOrchestrator, DEFAULT_AGENT_CONFIGS, AgentBuilder; print('OK')"
```

Expected: `OK`

- [ ] **Step 2: 运行完整多智能体测试**

```bash
pytest Coder/tests/test_multi_agent.py -v
```

Expected: all tests pass

- [ ] **Step 3: 前端类型检查**

```bash
cd Coder/web && npx tsc --noEmit --pretty 2>&1 | head -30
```

Expected: no new type errors related to MultiAgentPage or types.ts

- [ ] **Step 4: Commit Phase 1 completion marker**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: Phase 1 complete - multi-agent architecture cleanup and capability enhancement"
```

---

## Phase 2 — 流式 + 会话

### Task 9: AgentOrchestrator 新增 astream() 方法

**Files:**
- Modify: `Coder/multi_agent/agent_orchestrator.py` (追加方法到类)

- [ ] **Step 1: 在 AgentOrchestrator 类中追加 astream() 方法**

在 `run()` 方法之后（第 ~260 行）追加：

```python
    async def astream(self, user_input: str, thread_id: str = None):
        """流式执行编排，yield SSE 兼容事件字典。

        事件类型：agent_start | tool_call | tool_result | content | done | error
        """
        import uuid

        model = self._get_model()
        self._tool_call_log = []
        thread_id = thread_id or f"orch_{uuid.uuid4().hex[:12]}"

        yield {"type": "agent_start", "content": "多智能体任务开始"}

        tools: List = []
        for config in self._configs.values():
            try:
                tool = self._build_agent_tool(config, model)
                tools.append(tool)
            except Exception as e:
                yield {"type": "error", "content": f"子Agent {config.display_name} 创建失败: {e}"}
                return

        orchestrator = create_agent(
            model=model,
            tools=tools,
            system_prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )

        try:
            async for event in orchestrator.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                config=RunnableConfig(configurable={"thread_id": thread_id}),
                version="v2",
            ):
                kind = event.get("event")
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event["data"].get("input", {})
                    yield {
                        "type": "tool_call",
                        "name": tool_name,
                        "args": tool_input if isinstance(tool_input, dict) else {"task": str(tool_input)},
                    }
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = str(event["data"].get("output", ""))[:2000]
                    yield {
                        "type": "tool_result",
                        "name": tool_name,
                        "content": output,
                    }
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, str) and content:
                            yield {"type": "content", "content": content}
        except asyncio.TimeoutError:
            yield {"type": "error", "content": f"执行超时 ({self._timeout}s)"}
        except Exception as e:
            logger.error(f"Orchestrator 流式执行失败: {e}")
            yield {"type": "error", "content": str(e)}

        yield {"type": "done"}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/multi_agent/agent_orchestrator.py
git commit -m "feat: add astream() to AgentOrchestrator for SSE streaming support"
```

---

### Task 10: 新增 SSE 流式路由

**Files:**
- Modify: `Coder/server/routes/agent_orchestrator.py` (追加路由)

- [ ] **Step 1: 追加 /stream 端点**

在 `agent_orchestrator.py` route 文件末尾追加：

```python
import json
import uuid
from fastapi.responses import StreamingResponse


@router.post("/stream")
async def stream_task(req: OrchestratorExecuteRequest, request: Request):
    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()

    async def generate():
        async for event in orch.astream(
            req.task,
            thread_id=f"orch_{uuid.uuid4().hex[:12]}",
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Commit**

```bash
git add Coder/server/routes/agent_orchestrator.py
git commit -m "feat: add POST /api/agent-orchestrator/stream SSE endpoint"
```

---

### Task 11: 前端 SSE 流式调用

**Files:**
- Modify: `Coder/web/src/pages/MultiAgentPage.tsx` (追加流式模式)

- [ ] **Step 1: 追加流式执行逻辑**

在 `MultiAgentPage.tsx` 中追加 SSE 流式处理函数和模式切换。在现有 `handleExecute` 之后追加：

```typescript
  const [streamContent, setStreamContent] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [toolCalls, setToolCalls] = useState<OrchestratorToolCall[]>([])
  const [useStream, setUseStream] = useState(true)  // Phase 2 默认流式

  const handleStream = async () => {
    if (!task.trim()) return
    setStreaming(true)
    setResult(null)
    setStreamContent('')
    setToolCalls([])

    try {
      const res = await fetch('/api/agent-orchestrator/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task.trim() }),
      })
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''
      const toolCallMap = new Map<string, OrchestratorToolCall>()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            switch (event.type) {
              case 'tool_call':
                toolCallMap.set(event.name, {
                  agent: event.name,
                  display_name: event.name,
                  task: typeof event.args === 'object' ? JSON.stringify(event.args) : String(event.args),
                  duration_ms: 0,
                  success: true,
                })
                setToolCalls([...toolCallMap.values()])
                break
              case 'tool_result':
                // 流式模式通过 tool_call_log 获取完整调用信息
                break
              case 'content':
                setStreamContent(prev => prev + event.content)
                break
              case 'error':
                setResult({
                  success: false,
                  answer: '',
                  error: event.content,
                  duration_seconds: 0,
                  tool_calls: [...toolCallMap.values()],
                })
                break
              case 'done':
                setResult({
                  success: true,
                  answer: streamContent,
                  error: null,
                  duration_seconds: 0,
                  tool_calls: [...toolCallMap.values()],
                })
                break
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (e) {
      setResult({ success: false, answer: '', error: String(e), duration_seconds: 0, tool_calls: [] })
    } finally {
      setStreaming(false)
    }
  }
```

在 `handleExecute` 函数定义后、return 之前插入上述代码，然后将按钮的 onClick 改为根据 `useStream` 选择 `handleStream` 或 `handleExecute`。在流式模式下 `executing` / `streaming` 期间显示实时 `streamContent`。

UI 部分在按钮后追加实时流式内容展示：

```tsx
          {/* 流式模式切换 */}
          <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
            <input
              type="checkbox"
              checked={useStream}
              onChange={(e) => setUseStream(e.target.checked)}
              className="rounded"
            />
            流式输出
          </label>

          {/* 流式实时内容 */}
          {(streaming || streamContent) && useStream && (
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {streamContent || '等待响应...'}
                </p>
              </CardContent>
            </Card>
          )}
```

按钮 onClick 更新为：

```tsx
            onClick={useStream ? handleStream : handleExecute}
            disabled={!task.trim() || executing || streaming}
```

- [ ] **Step 2: Commit**

```bash
git add Coder/web/src/pages/MultiAgentPage.tsx
git commit -m "feat: add SSE streaming support to MultiAgentPage with toggle"
```

---

### Task 12: sessions 表扩展 mode 字段

**Files:**
- Modify: `Coder/storage/database.py` (或对应的数据库初始化文件)

- [ ] **Step 1: 查找 sessions 表的 DDL**

```bash
grep -rn "CREATE TABLE.*sessions\|sessions.*CREATE" Coder/ --include="*.py" --include="*.sql" -l
```

检查是否有集中管理的 DDL 或 migration 文件。如果是 ORM 自动建表，需要找到模型定义。

- [ ] **Step 2: 添加 mode 列**

根据项目实际建表方式（SQL migration 或 Pydantic/SQLAlchemy 模型），添加 `mode` 字段：

**选项 A — 如果有 SQL migration 文件：**
```sql
ALTER TABLE sessions ADD COLUMN mode VARCHAR(20) DEFAULT 'chat' NOT NULL;
-- mode: 'chat' (普通对话), 'orchestrator' (多智能体编排)
```

**选项 B — 如果使用 Pydantic 模型：**
在 session 模型中追加：
```python
mode: str = "chat"  # 'chat' | 'orchestrator'
```

- [ ] **Step 3: Commit**

```bash
git add <session-schema-file>
git commit -m "feat: add mode column to sessions table for chat/orchestrator distinction"
```

---

### Task 13: 新增多智能体会话 API 端点

**Files:**
- Modify: `Coder/server/routes/agent_orchestrator.py` (追加路由)

- [ ] **Step 1: 追加会话列表和旁链端点**

在 route 文件末尾追加：

```python
from typing import Optional


@router.get("/sessions")
async def list_orchestrator_sessions(request: Request):
    """列出所有 mode='orchestrator' 的会话"""
    from Coder.storage.manager import DatabaseManager

    rows = await DatabaseManager.fetch(
        "SELECT session_id, title, created_at, updated_at "
        "FROM sessions WHERE mode = 'orchestrator' "
        "ORDER BY updated_at DESC LIMIT 50"
    )
    return {
        "sessions": [
            {
                "session_id": r["session_id"],
                "title": r["title"] or "未命名任务",
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
            }
            for r in (rows or [])
        ]
    }


@router.get("/sessions/{session_id}")
async def get_orchestrator_session(session_id: str, request: Request):
    """获取指定编排会话的消息历史和子 Agent 调用链"""
    from Coder.multi_agent.agent_orchestrator import AgentOrchestrator
    import re

    if not re.match(r"^[a-zA-Z0-9\-_]+$", session_id):
        return {"error": "无效的 session_id"}

    # 读取编排器 checkpoint 消息
    # 通过 thread_id 前缀 orchid_{session_id} 查询
    sidechains = []
    try:
        from Coder.storage.manager import DatabaseManager
        # 查找所有子 Agent 旁链 thread_id（层级命名）
        rows = await DatabaseManager.fetch(
            "SELECT DISTINCT thread_id FROM langgraph_checkpoints "
            "WHERE thread_id LIKE $1",
            [f"orch_{session_id}/%"]
        )
        if rows:
            for r in rows:
                tid = r["thread_id"]
                parts = tid.split("/", 1)
                sidechains.append({
                    "thread_id": tid,
                    "agent_name": parts[1] if len(parts) > 1 else tid,
                })
    except Exception as e:
        logger.warning(f"读取旁链失败: {e}")

    return {
        "session_id": session_id,
        "sidechains": sidechains,
        "message": "旁链详情在 Phase 2 后续迭代中扩展",
    }
```

- [ ] **Step 2: Commit**

```bash
git add Coder/server/routes/agent_orchestrator.py
git commit -m "feat: add GET /agent-orchestrator/sessions and sessions/{id} endpoints"
```

---

### Task 14: Phase 2 集成验证

**Files:** 无（验证步骤）

- [ ] **Step 1: 启动后端验证导入**

```bash
python -c "from Coder.multi_agent.agent_orchestrator import AgentOrchestrator; orch = AgentOrchestrator(); print(hasattr(orch, 'astream')); print(hasattr(orch, 'run'))"
```

Expected: `True True`

- [ ] **Step 2: 运行全部测试**

```bash
pytest Coder/tests/test_multi_agent.py -v
```

Expected: all tests pass

- [ ] **Step 3: 前端类型检查**

```bash
cd Coder/web && npx tsc --noEmit 2>&1 | grep -i "error\|MultiAgent" | head -20
```

Expected: no new errors

- [ ] **Step 4: Commit Phase 2 completion**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: Phase 2 complete - SSE streaming and conversation-ready multi-agent"
```

---

## Verification Checklist

完成所有 Task 后，手动验证：

1. `POST /api/agent-orchestrator/execute` 返回 `tool_calls` 数组，包含被调用的子 Agent 信息
2. `POST /api/agent-orchestrator/stream` 返回 SSE 流，事件格式 `{type: content|tool_call|tool_result|done}`
3. Coder 的 system prompt 不含 `web_search` 引用
4. 每个子 Agent 调用有独立超时（120s 默认）
5. 技能执行器接收动态 `params`
6. 前端 badge 随实际调用动态渲染
7. 不存在的 AgentRole fallback 返回非空 prompt
8. `DEFAULT_AGENT_CONFIGS` 可被外部参数覆盖
9. `GET /api/agent-orchestrator/sessions` 返回 mode='orchestrator' 的会话列表
10. `GET /api/agent-orchestrator/sessions/{id}` 返回会话详情及子 Agent 旁链
11. `pytest Coder/tests/test_multi_agent.py -v` 全部通过（16 项）

# MCP 外部 Server 接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供类似 Cursor/Claude Desktop 的 MCP 生态接入能力，支持社区注册表浏览、MCP Server 安装管理、SSE/stdio 双传输、分级安全权限。

**Architecture:** 新增 `Coder/mcp/` 包（manager + registry），新增 `/api/mcp` REST 路由层，前端新增 MCPPage 页面。MCPManager 替代 `code_agent.py` 中硬编码的 `_init_mcp_tools()`。内置 PowerShell/Shell MCP 迁移为 builtin Server。

**Tech Stack:** Python FastAPI + `langchain-mcp-adapters` + `mcp` SDK + PostgreSQL + React TypeScript

---

### Task 1: 数据库 Schema — 新增 mcp_servers 表

**Files:**
- Modify: `Coder/storage/db.py:23-63`

- [ ] **Step 1: 在 _schema_sql 中添加 mcp_servers 建表语句**

在 `_schema_sql` 字符串末尾（`CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled);` 之后）追加：

```python
CREATE TABLE IF NOT EXISTS mcp_servers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(200),
    description     TEXT NOT NULL DEFAULT '',
    transport       VARCHAR(20) NOT NULL DEFAULT 'stdio',
    command         VARCHAR(500),
    args            JSONB NOT NULL DEFAULT '[]',
    url             VARCHAR(500),
    env             JSONB NOT NULL DEFAULT '{}',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    is_local        BOOLEAN NOT NULL DEFAULT FALSE,
    source          VARCHAR(20) NOT NULL DEFAULT 'manual',
    registry_id     VARCHAR(200),
    tools_allowlist JSONB,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_enabled ON mcp_servers(enabled);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_source ON mcp_servers(source);
```

- [ ] **Step 2: 验证建表语句**

```bash
cd "D:\PyCharm\AI" && python -c "from Coder.storage.db import _schema_sql; print('mcp_servers' in _schema_sql)"
```
Expected: `True`

- [ ] **Step 3: 提交**

```bash
git add Coder/storage/db.py
git commit -m "feat: add mcp_servers table to database schema

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: MCP 注册表模块

**Files:**
- Create: `Coder/mcp/__init__.py`
- Create: `Coder/mcp/registry.py`
- Create: `Coder/mcp/registry_fallback.json`

- [ ] **Step 1: 创建包初始化文件**

```python
# Coder/mcp/__init__.py
```

(空文件)

- [ ] **Step 2: 创建注册表降级数据**

```json
[]
```

`Coder/mcp/registry_fallback.json` 内容为空数组 `[]`。

- [ ] **Step 3: 编写 registry.py**

```python
import json
import logging
import os
from typing import Optional

import aiohttp

from Coder.storage.redis_client import RedisManager

logger = logging.getLogger(__name__)

_REGISTRY_URL = (
    "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/"
    "registry.json"
)
_CACHE_KEY = "mcp:registry"
_CACHE_TTL = 3600

_FALLBACK_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "registry_fallback.json")
)


async def fetch_registry(
    force_refresh: bool = False,
) -> list[dict]:
    if not force_refresh:
        try:
            cached = await RedisManager.get(_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    data = await _fetch_from_github()
    if data is None:
        data = _load_fallback()

    try:
        await RedisManager.set(_CACHE_KEY, json.dumps(data, ensure_ascii=False), ex=_CACHE_TTL)
    except Exception:
        pass

    return data


async def _fetch_from_github() -> Optional[list[dict]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(_REGISTRY_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"Registry fetch returned status {resp.status}")
    except Exception as e:
        logger.warning(f"Failed to fetch MCP registry from GitHub: {e}")
    return None


def _load_fallback() -> list[dict]:
    try:
        with open(_FALLBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
```

- [ ] **Step 4: 验证模块可导入**

```bash
cd "D:\PyCharm\AI" && python -c "from Coder.mcp.registry import fetch_registry; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: 提交**

```bash
git add Coder/mcp/__init__.py Coder/mcp/registry.py Coder/mcp/registry_fallback.json
git commit -m "feat: add MCP registry module with GitHub fetch and Redis cache

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: MCPManager 连接管理

**Files:**
- Create: `Coder/mcp/manager.py`

- [ ] **Step 1: 编写 MCPManager**

```python
import asyncio
import logging
from typing import Optional

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from Coder.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

_BUILTIN_SERVERS = [
    {
        "name": "powershell_tools",
        "display_name": "PowerShell Tools",
        "description": "Manage PowerShell processes and execute scripts",
        "transport": "stdio",
        "command": "python",
        "args": [],  # filled at init time
        "is_local": True,
        "source": "builtin",
    },
]


class MCPManager:
    def __init__(self):
        self._clients: dict[str, MultiServerMCPClient] = {}
        self._server_configs: dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._ensure_builtins()
        await self.reload_all()
        self._initialized = True

    async def _ensure_builtins(self) -> None:
        import os as _os
        import platform

        for cfg in _BUILTIN_SERVERS:
            exists = await DatabaseManager.fetchrow(
                "SELECT id FROM mcp_servers WHERE name = $1", cfg["name"]
            )
            if exists:
                continue

            if cfg["name"] == "powershell_tools" and platform.system() != "Windows":
                continue

            script_dir = _os.path.normpath(
                _os.path.join(_os.path.dirname(__file__), "..")
            )
            if cfg["name"] == "powershell_tools":
                cfg["args"] = [
                    _os.path.join(script_dir, "MCP", "powershell_tools.py")
                ]
            elif cfg["name"] == "shell_tools":
                cfg["args"] = [
                    _os.path.join(script_dir, "MCP", "shell_tools.py")
                ]

            await DatabaseManager.execute(
                """INSERT INTO mcp_servers
                   (name, display_name, description, transport, command, args,
                    is_local, source)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                cfg["name"],
                cfg["display_name"],
                cfg["description"],
                cfg["transport"],
                cfg["command"],
                cfg["args"],
                cfg["is_local"],
                cfg["source"],
            )
            logger.info(f"Builtin MCP server registered: {cfg['name']}")

    async def reload_all(self) -> None:
        async with self._lock:
            rows = await DatabaseManager.fetch(
                "SELECT * FROM mcp_servers WHERE enabled = TRUE"
            )
            new_configs = {row["id"]: dict(row) for row in rows}

            old_ids = set(self._clients.keys())
            new_ids = set(new_configs.keys())

            for sid in old_ids - new_ids:
                await self._close_client(sid)

            for sid in new_ids - old_ids:
                await self._connect_server(sid, new_configs[sid])

            for sid in new_ids & old_ids:
                if self._config_changed(new_configs[sid], self._server_configs.get(sid, {})):
                    await self._close_client(sid)
                    await self._connect_server(sid, new_configs[sid])

            self._server_configs = new_configs

    def _config_changed(self, new_cfg: dict, old_cfg: dict) -> bool:
        for key in ("command", "args", "url", "transport", "env"):
            if new_cfg.get(key) != old_cfg.get(key):
                return True
        return False

    async def _connect_server(self, server_id: str, config: dict) -> None:
        try:
            transport = config["transport"]
            server_config = {config["name"]: {"transport": transport}}

            if transport == "stdio":
                server_config[config["name"]]["command"] = config["command"]
                server_config[config["name"]]["args"] = config["args"]
            elif transport == "sse":
                server_config[config["name"]]["url"] = config["url"]

            if config.get("env"):
                server_config[config["name"]]["env"] = config["env"]

            client = MultiServerMCPClient(server_config)
            await client.get_tools()
            self._clients[server_id] = client
            await DatabaseManager.execute(
                "UPDATE mcp_servers SET last_error = NULL, updated_at = NOW() WHERE id = $1",
                server_id,
            )
            logger.info(f"MCP server connected: {config['name']}")
        except Exception as e:
            err_msg = str(e)[:500]
            await DatabaseManager.execute(
                "UPDATE mcp_servers SET last_error = $1, updated_at = NOW() WHERE id = $2",
                err_msg,
                server_id,
            )
            logger.warning(f"MCP server {config.get('name', server_id)} connection failed: {e}")

    async def _close_client(self, server_id: str) -> None:
        client = self._clients.pop(server_id, None)
        if client:
            try:
                await client.close()
            except Exception:
                pass

    def get_all_tools(self) -> list[BaseTool]:
        tools: list[BaseTool] = []
        for server_id, client in self._clients.items():
            config = self._server_configs.get(server_id, {})
            allowlist = config.get("tools_allowlist")
            try:
                server_tools = client.tools
            except Exception:
                continue
            for tool in server_tools:
                if allowlist is not None and tool.name not in allowlist:
                    continue
                tool.name = f"{config.get('name', server_id)}__{tool.name}"
                tools.append(tool)
        return tools

    def get_tools_for_session(
        self, session_id: str, overrides: Optional[dict] = None
    ) -> list[BaseTool]:
        return self.get_all_tools()

    async def test_connection(
        self, config: dict, timeout: float = 10.0
    ) -> tuple[bool, str, list[dict]]:
        try:
            transport = config["transport"]
            server_config = {config["name"]: {"transport": transport}}

            if transport == "stdio":
                server_config[config["name"]]["command"] = config["command"]
                server_config[config["name"]]["args"] = config.get("args", [])
            elif transport == "sse":
                server_config[config["name"]]["url"] = config["url"]

            if config.get("env"):
                server_config[config["name"]]["env"] = config["env"]

            client = MultiServerMCPClient(server_config)
            tools = await asyncio.wait_for(client.get_tools(), timeout=timeout)

            tool_info = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "args_schema": str(t.args_schema) if t.args_schema else "",
                }
                for t in tools
            ]

            try:
                await client.close()
            except Exception:
                pass

            return True, "", tool_info
        except asyncio.TimeoutError:
            return False, f"Connection timed out after {timeout}s", []
        except Exception as e:
            return False, str(e)[:500], []

    async def get_server_tools(self, server_id: str) -> list[dict]:
        client = self._clients.get(server_id)
        if client is None:
            return []
        try:
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "args_schema": str(t.args_schema) if t.args_schema else "",
                }
                for t in client.tools
            ]
        except Exception:
            return []

    async def close(self) -> None:
        async with self._lock:
            for server_id in list(self._clients.keys()):
                await self._close_client(server_id)
            self._server_configs.clear()
            self._initialized = False
```

- [ ] **Step 2: 验证模块可导入**

```bash
cd "D:\PyCharm\AI" && python -c "from Coder.mcp.manager import MCPManager; m = MCPManager(); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add Coder/mcp/manager.py
git commit -m "feat: add MCPManager for connection lifecycle and tool aggregation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: MCP REST API 路由

**Files:**
- Create: `Coder/server/routes/mcp.py`

- [ ] **Step 1: 编写 API 路由**

```python
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from Coder.storage.db import DatabaseManager
from Coder.mcp.registry import fetch_registry

logger = logging.getLogger(__name__)
router = APIRouter()


class MCPServerCreate(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = []
    url: str | None = None
    env: dict[str, str] = {}
    tools_allowlist: list[str] | None = None


class MCPServerUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    transport: str | None = None
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env: dict[str, str] | None = None
    enabled: bool | None = None
    tools_allowlist: list[str] | None = None


class MCPImportRequest(BaseModel):
    config: dict


def _get_manager(request: Request):
    return request.app.state.mcp_manager


def _validate_transport(transport: str, command: str | None, url: str | None):
    if transport not in ("stdio", "sse"):
        raise HTTPException(status_code=400, detail="transport must be 'stdio' or 'sse'")
    if transport == "stdio" and not command:
        raise HTTPException(status_code=400, detail="stdio transport requires 'command'")
    if transport == "sse" and not url:
        raise HTTPException(status_code=400, detail="sse transport requires 'url'")


def _row_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "display_name": row["display_name"] or row["name"],
        "description": row.get("description", ""),
        "transport": row["transport"],
        "command": row.get("command"),
        "args": row.get("args", []),
        "url": row.get("url"),
        "env": row.get("env", {}),
        "enabled": row["enabled"],
        "is_local": row.get("is_local", False),
        "source": row.get("source", "manual"),
        "registry_id": row.get("registry_id"),
        "tools_allowlist": row.get("tools_allowlist"),
        "last_error": row.get("last_error"),
        "created_at": str(row["created_at"]) if row.get("created_at") else "",
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else "",
    }


@router.get("/registry")
async def get_registry(search: str = "", force_refresh: bool = False):
    items = await fetch_registry(force_refresh=force_refresh)
    if search:
        q = search.lower()
        items = [
            i for i in items
            if q in i.get("name", "").lower()
            or q in i.get("description", "").lower()
        ]
    return {"servers": items}


@router.get("/servers")
async def list_servers(request: Request):
    rows = await DatabaseManager.fetch(
        "SELECT * FROM mcp_servers ORDER BY created_at DESC"
    )
    manager = _get_manager(request)
    result = []
    for row in rows:
        d = _row_to_dict(row)
        tool_count = 0
        if row["enabled"] and row.get("last_error") is None:
            tools = await manager.get_server_tools(row["id"])
            tool_count = len(tools)
        d["tool_count"] = tool_count
        d["status"] = (
            "error" if (row["enabled"] and row.get("last_error"))
            else "disabled" if not row["enabled"]
            else "connected"
        )
        result.append(d)
    return {"servers": result}


@router.post("/servers")
async def create_server(request: Request, body: MCPServerCreate):
    _validate_transport(body.transport, body.command, body.url)

    existing = await DatabaseManager.fetchrow(
        "SELECT id FROM mcp_servers WHERE name = $1", body.name
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Server '{body.name}' already exists")

    await DatabaseManager.execute(
        """INSERT INTO mcp_servers
           (name, display_name, description, transport, command, args, url, env,
            tools_allowlist)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
        body.name,
        body.display_name or body.name,
        body.description,
        body.transport,
        body.command,
        body.args,
        body.url,
        body.env,
        body.tools_allowlist,
    )
    await _get_manager(request).reload_all()
    return {"status": "created", "name": body.name}


@router.patch("/servers/{server_id}")
async def update_server(request: Request, server_id: str, body: MCPServerUpdate):
    row = await DatabaseManager.fetchrow(
        "SELECT * FROM mcp_servers WHERE id = $1", server_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")

    updates = []
    params: list = []
    idx = 1

    for field in ("display_name", "description", "transport", "command", "url",
                  "enabled"):
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            params.append(val)
            idx += 1

    for field in ("args", "env", "tools_allowlist"):
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            params.append(json.dumps(val))
            idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if body.transport or body.command or body.url:
        transport = body.transport or row["transport"]
        command = body.command if body.command is not None else row.get("command")
        url = body.url if body.url is not None else row.get("url")
        _validate_transport(transport, command, url)

    updates.append(f"updated_at = NOW()")
    params.append(server_id)

    sql = f"UPDATE mcp_servers SET {', '.join(updates)} WHERE id = ${idx}"
    await DatabaseManager.execute(sql, *params)
    await _get_manager(request).reload_all()
    return {"status": "updated"}


@router.delete("/servers/{server_id}")
async def delete_server(request: Request, server_id: str):
    row = await DatabaseManager.fetchrow(
        "SELECT * FROM mcp_servers WHERE id = $1", server_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    if row.get("is_local"):
        raise HTTPException(status_code=403, detail="Cannot delete builtin MCP server")

    await DatabaseManager.execute(
        "DELETE FROM mcp_servers WHERE id = $1", server_id
    )
    await _get_manager(request).reload_all()
    return {"status": "deleted"}


@router.post("/servers/{server_id}/test")
async def test_server(request: Request, server_id: str):
    row = await DatabaseManager.fetchrow(
        "SELECT * FROM mcp_servers WHERE id = $1", server_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")

    config = dict(row)
    ok, error, tools = await _get_manager(request).test_connection(config)
    return {"success": ok, "error": error, "tools": tools}


@router.get("/servers/{server_id}/tools")
async def get_server_tools(request: Request, server_id: str):
    tools = await _get_manager(request).get_server_tools(server_id)
    return {"tools": tools}


@router.post("/import")
async def import_config(request: Request, body: MCPImportRequest):
    mcp_servers = body.config.get("mcpServers", {})
    if not mcp_servers:
        raise HTTPException(status_code=400, detail="No 'mcpServers' found in config")

    imported = 0
    skipped = 0

    for name, cfg in mcp_servers.items():
        existing = await DatabaseManager.fetchrow(
            "SELECT id FROM mcp_servers WHERE name = $1", name
        )
        if existing:
            skipped += 1
            continue

        transport = "stdio"
        command = cfg.get("command")
        args = cfg.get("args", [])
        url = cfg.get("url")
        if url and not command:
            transport = "sse"

        await DatabaseManager.execute(
            """INSERT INTO mcp_servers
               (name, display_name, transport, command, args, url, env)
               VALUES ($1,$2,$3,$4,$5,$6,$7)""",
            name,
            name,
            transport,
            command,
            args,
            url,
            cfg.get("env", {}),
        )
        imported += 1

    await _get_manager(request).reload_all()
    return {"imported": imported, "skipped": skipped}


@router.get("/session-tools")
async def get_session_tools(request: Request):
    manager = _get_manager(request)
    tools = manager.get_all_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description or ""}
            for t in tools
        ]
    }
```

- [ ] **Step 2: 验证路由模块可导入**

```bash
cd "D:\PyCharm\AI" && python -c "from Coder.server.routes.mcp import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add Coder/server/routes/mcp.py
git commit -m "feat: add MCP REST API routes for server CRUD and registry

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: 服务端集成 — 注册路由和初始化 MCPManager

**Files:**
- Modify: `Coder/server/main.py`

- [ ] **Step 1: 修改 main.py 集成 MCP**

在 import 区域添加 MCP 路由导入（第 6 行附近，其他 routes 导入之后）：

```python
from Coder.server.routes import mcp
```

在 lifespan 中，Agent 初始化之前添加 MCPManager 初始化（第 42 行 `logger.info("Initializing agent...")` 之前）：

```python
logger.info("Initializing MCP Manager...")
from Coder.mcp.manager import MCPManager
mcp_manager = MCPManager()
await mcp_manager.initialize()
app.state.mcp_manager = mcp_manager
```

修改 `create_code_agent` 调用，不再传入 `mcp_client`，改为传入 `mcp_manager`：

```python
agent, config, mcp_client, sop_context = await create_code_agent(
    thread_id=thread_id, mcp_manager=mcp_manager
)
```

在 router 注册区域添加（第 85 行附近）：

```python
app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP"])
```

在 shutdown 逻辑中，关闭 MCPManager（`await DatabaseManager.close_pool()` 之前）：

```python
try:
    await mcp_manager.close()
except Exception:
    pass
```

- [ ] **Step 2: 验证服务可启动**

```bash
cd "D:\PyCharm\AI" && timeout 10 python -c "
import asyncio
from Coder.server.main import app
print('App loaded OK')
" 2>&1 || true
```
Expected: `App loaded OK`（超时忽略）

- [ ] **Step 3: 提交**

```bash
git add Coder/server/main.py
git commit -m "feat: integrate MCPManager and MCP routes into FastAPI server

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Agent 层改造 — 用 MCPManager 替代硬编码

**Files:**
- Modify: `Coder/agent/code_agent.py:47-62,121-169`

- [ ] **Step 1: 修改 create_code_agent 接受 mcp_manager 参数**

将函数签名改为：

```python
async def create_code_agent(thread_id: str = "1", mcp_manager=None):
```

将 MCP 工具初始化逻辑（第 126-127 行）改为：

```python
if mcp_manager is None:
    power_shell_tools = []
    mcp_client = None
else:
    power_shell_tools = mcp_manager.get_all_tools()
    mcp_client = None
```

- [ ] **Step 2: 删除旧的 _init_mcp_tools 函数**

删除第 47-62 行的 `_init_mcp_tools` 函数。

- [ ] **Step 3: 验证 Agent 模块可导入**

```bash
cd "D:\PyCharm\AI" && python -c "from Coder.agent.code_agent import create_code_agent; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
git add Coder/agent/code_agent.py
git commit -m "refactor: replace hardcoded _init_mcp_tools with MCPManager injection

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: 前端类型和 API 客户端扩展

**Files:**
- Modify: `Coder/web/src/types.ts`
- Modify: `Coder/web/src/api/client.ts`

- [ ] **Step 1: 扩展 NavPage 类型**

在 `types.ts` 的 `NavPage` 类型中添加 `'mcp'`：

```typescript
export type NavPage = 'chat' | 'knowledge' | 'sop' | 'skills' | 'multi-agent' | 'mcp'
```

同时添加 MCP 相关类型：

```typescript
export interface MCPServer {
  id: string
  name: string
  display_name: string
  description: string
  transport: 'stdio' | 'sse'
  command: string | null
  args: string[]
  url: string | null
  env: Record<string, string>
  enabled: boolean
  is_local: boolean
  source: 'manual' | 'registry' | 'builtin'
  registry_id: string | null
  tools_allowlist: string[] | null
  last_error: string | null
  tool_count: number
  status: 'connected' | 'error' | 'disabled'
  created_at: string
  updated_at: string
}

export interface MCPRegistryItem {
  id: string
  name: string
  description: string
  transport: 'stdio' | 'sse'
  command?: string
  args?: string[]
  url?: string
  category?: string
}

export interface MCPTool {
  name: string
  description: string
  args_schema: string
}
```

- [ ] **Step 2: 在 api/client.ts 中添加 patch 方法**

在 `api` 对象中添加：

```typescript
async function patch<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`PATCH ${url} failed: ${res.status}`)
  return res.json()
}
```

并导出：

```typescript
export const api = { get, post, del, put, patch, uploadFiles }
```

- [ ] **Step 3: 提交**

```bash
git add Coder/web/src/types.ts Coder/web/src/api/client.ts
git commit -m "feat: add MCP types and PATCH method to frontend API client

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: 前端 MCPPage 页面

**Files:**
- Create: `Coder/web/src/pages/MCPPage.tsx`

- [ ] **Step 1: 编写 MCPPage 组件**

```typescript
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { MCPServer, MCPRegistryItem, MCPTool } from '../types'

type Tab = 'marketplace' | 'installed'

export function MCPPage() {
  const [tab, setTab] = useState<Tab>('marketplace')
  const [registry, setRegistry] = useState<MCPRegistryItem[]>([])
  const [registryLoading, setRegistryLoading] = useState(true)
  const [registrySearch, setRegistrySearch] = useState('')

  const [servers, setServers] = useState<MCPServer[]>([])
  const [serversLoading, setServersLoading] = useState(true)

  const [showAddForm, setShowAddForm] = useState(false)
  const [formName, setFormName] = useState('')
  const [formTransport, setFormTransport] = useState<'stdio' | 'sse'>('stdio')
  const [formCommand, setFormCommand] = useState('')
  const [formArgs, setFormArgs] = useState('')
  const [formUrl, setFormUrl] = useState('')
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)

  const [testResult, setTestResult] = useState<{ success: boolean; error: string; tools: MCPTool[] } | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  const [importMsg, setImportMsg] = useState('')

  const loadRegistry = useCallback(async () => {
    setRegistryLoading(true)
    try {
      const data = await api.get<{ servers: MCPRegistryItem[] }>(
        `/mcp/registry${registrySearch ? `?search=${encodeURIComponent(registrySearch)}` : ''}`
      )
      setRegistry(data.servers)
    } catch {
      setRegistry([])
    } finally {
      setRegistryLoading(false)
    }
  }, [registrySearch])

  const loadServers = useCallback(async () => {
    setServersLoading(true)
    try {
      const data = await api.get<{ servers: MCPServer[] }>('/mcp/servers')
      setServers(data.servers)
    } catch {
      setServers([])
    } finally {
      setServersLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tab === 'marketplace') loadRegistry()
    else loadServers()
  }, [tab, loadRegistry, loadServers])

  const handleInstall = async (item: MCPRegistryItem) => {
    try {
      await api.post('/mcp/servers', {
        name: item.name,
        display_name: item.name,
        description: item.description,
        transport: item.transport,
        command: item.command || null,
        args: item.args || [],
        url: item.url || null,
      })
      setTab('installed')
    } catch (e: any) {
      alert(`Install failed: ${e.message}`)
    }
  }

  const handleAddManual = async () => {
    if (!formName.trim()) {
      setFormError('Name is required')
      return
    }
    if (formTransport === 'stdio' && !formCommand.trim()) {
      setFormError('Command is required for stdio transport')
      return
    }
    if (formTransport === 'sse' && !formUrl.trim()) {
      setFormError('URL is required for SSE transport')
      return
    }

    setFormSubmitting(true)
    setFormError('')
    try {
      await api.post('/mcp/servers', {
        name: formName.trim(),
        display_name: formName.trim(),
        transport: formTransport,
        command: formTransport === 'stdio' ? formCommand.trim() : null,
        args: formArgs.trim() ? formArgs.trim().split(/\s+/) : [],
        url: formTransport === 'sse' ? formUrl.trim() : null,
      })
      setShowAddForm(false)
      setFormName('')
      setFormCommand('')
      setFormArgs('')
      setFormUrl('')
      setTab('installed')
    } catch (e: any) {
      setFormError(e.message)
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleToggle = async (server: MCPServer) => {
    await api.patch(`/mcp/servers/${server.id}`, { enabled: !server.enabled })
    loadServers()
  }

  const handleDelete = async (server: MCPServer) => {
    if (!confirm(`Delete "${server.display_name}"?`)) return
    await api.del(`/mcp/servers/${server.id}`)
    loadServers()
  }

  const handleTest = async (server: MCPServer) => {
    setTesting(server.id)
    try {
      const data = await api.post<{ success: boolean; error: string; tools: MCPTool[] }>(
        `/mcp/servers/${server.id}/test`
      )
      setTestResult(data)
    } catch (e: any) {
      setTestResult({ success: false, error: e.message, tools: [] })
    } finally {
      setTesting(null)
    }
  }

  const handleImportConfig = async () => {
    const input = prompt('Paste Claude Desktop config JSON (the content of claude_desktop_config.json):')
    if (!input) return
    try {
      const parsed = JSON.parse(input)
      const data = await api.post<{ imported: number; skipped: number }>('/mcp/import', { config: parsed })
      setImportMsg(`Imported: ${data.imported}, Skipped: ${data.skipped}`)
      loadServers()
    } catch (e: any) {
      setImportMsg(`Import failed: ${e.message}`)
    }
  }

  return (
    <div className="mcp-page">
      <div className="page-header">
        <h2>MCP 管理</h2>
        <div className="tab-bar">
          <button
            className={`tab-btn ${tab === 'marketplace' ? 'active' : ''}`}
            onClick={() => setTab('marketplace')}
          >
            市场
          </button>
          <button
            className={`tab-btn ${tab === 'installed' ? 'active' : ''}`}
            onClick={() => setTab('installed')}
          >
            已安装
          </button>
        </div>
      </div>

      {tab === 'marketplace' && (
        <div className="mcp-marketplace">
          <div className="marketplace-toolbar">
            <input
              type="text"
              placeholder="搜索 MCP Server..."
              value={registrySearch}
              onChange={(e) => setRegistrySearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadRegistry()}
            />
            <button onClick={loadRegistry}>搜索</button>
          </div>
          {registryLoading ? (
            <p>加载中...</p>
          ) : registry.length === 0 ? (
            <p className="empty-hint">暂无可用 MCP Server</p>
          ) : (
            <div className="mcp-grid">
              {registry.map((item) => (
                <div key={item.id || item.name} className="mcp-card">
                  <h4>{item.name}</h4>
                  <p className="mcp-desc">{item.description}</p>
                  <span className="mcp-badge">{item.transport}</span>
                  {item.category && <span className="mcp-category">{item.category}</span>}
                  <button className="btn-primary" onClick={() => handleInstall(item)}>
                    安装
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'installed' && (
        <div className="mcp-installed">
          <div className="installed-toolbar">
            <button onClick={() => setShowAddForm(!showAddForm)}>
              {showAddForm ? '取消' : '＋ 手动添加'}
            </button>
            <button onClick={handleImportConfig}>导入配置</button>
            {importMsg && <span className="import-msg">{importMsg}</span>}
          </div>

          {showAddForm && (
            <div className="mcp-form">
              <label>
                Name:
                <input type="text" value={formName} onChange={(e) => setFormName(e.target.value)} />
              </label>
              <label>
                Transport:
                <select value={formTransport} onChange={(e) => setFormTransport(e.target.value as 'stdio' | 'sse')}>
                  <option value="stdio">stdio</option>
                  <option value="sse">SSE</option>
                </select>
              </label>
              {formTransport === 'stdio' ? (
                <>
                  <label>
                    Command:
                    <input type="text" value={formCommand} onChange={(e) => setFormCommand(e.target.value)} placeholder="npx" />
                  </label>
                  <label>
                    Args (space-separated):
                    <input type="text" value={formArgs} onChange={(e) => setFormArgs(e.target.value)} placeholder="-y @scope/server" />
                  </label>
                </>
              ) : (
                <label>
                  URL:
                  <input type="text" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="https://..." />
                </label>
              )}
              {formError && <p className="form-error">{formError}</p>}
              <button onClick={handleAddManual} disabled={formSubmitting}>
                {formSubmitting ? '添加中...' : '添加'}
              </button>
            </div>
          )}

          {testing && <p>Testing {testing}...</p>}
          {testResult && (
            <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
              <p>{testResult.success ? 'Connection OK' : `Error: ${testResult.error}`}</p>
              {testResult.tools.length > 0 && (
                <ul>
                  {testResult.tools.map((t) => (
                    <li key={t.name}>{t.name}: {t.description}</li>
                  ))}
                </ul>
              )}
              <button onClick={() => setTestResult(null)}>关闭</button>
            </div>
          )}

          {serversLoading ? (
            <p>加载中...</p>
          ) : servers.length === 0 ? (
            <p className="empty-hint">暂无已安装的 MCP Server</p>
          ) : (
            <div className="mcp-server-list">
              {servers.map((s) => (
                <div key={s.id} className={`mcp-server-item status-${s.status}`}>
                  <div className="mcp-server-info">
                    <h4>{s.display_name}</h4>
                    <p>{s.description}</p>
                    <div className="mcp-server-meta">
                      <span className={`status-dot ${s.status}`} />
                      <span>{s.status}</span>
                      <span>{s.transport}</span>
                      <span>{s.tool_count} tools</span>
                    </div>
                    {s.last_error && <p className="mcp-error">Error: {s.last_error}</p>}
                  </div>
                  <div className="mcp-server-actions">
                    <button onClick={() => handleToggle(s)}>
                      {s.enabled ? '禁用' : '启用'}
                    </button>
                    <button onClick={() => handleTest(s)} disabled={testing === s.id}>
                      测试连接
                    </button>
                    {!s.is_local && (
                      <button className="btn-danger" onClick={() => handleDelete(s)}>
                        删除
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd "D:\PyCharm\AI\Coder\web" && npx tsc --noEmit --pretty 2>&1 | head -30
```
Expected: 无新增错误（可能已有存量 warning）

- [ ] **Step 3: 提交**

```bash
git add Coder/web/src/pages/MCPPage.tsx
git commit -m "feat: add MCPPage with marketplace and installed servers tabs

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: 前端路由和导航集成

**Files:**
- Modify: `Coder/web/src/App.tsx`
- Modify: `Coder/web/src/components/Sidebar.tsx`

- [ ] **Step 1: 在 App.tsx 中注册 MCP 页面导入和路由**

在 import 区域添加：

```typescript
import { MCPPage } from './pages/MCPPage'
```

在 navPage 条件渲染中添加：

```typescript
{navPage === 'mcp' && <MCPPage />}
```

- [ ] **Step 2: 在 Sidebar.tsx 导航列表中添加 MCP 入口**

在 `navItems` 数组的最后一个元素后添加：

```typescript
{ page: 'mcp', icon: '🔌', label: 'MCP' },
```

- [ ] **Step 3: 验证前端构建**

```bash
cd "D:\PyCharm\AI\Coder\web" && npm run build 2>&1 | tail -10
```
Expected: 构建成功

- [ ] **Step 4: 提交**

```bash
git add Coder/web/src/App.tsx Coder/web/src/components/Sidebar.tsx
git commit -m "feat: add MCP page route and sidebar navigation entry

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: SSE 工具确认机制（远程 MCP 权限控制）

**Files:**
- Create: `Coder/mcp/sse_confirm.py`
- Modify: `Coder/agent/code_agent.py:121-169`

- [ ] **Step 1: 创建 SSE 工具确认包装器**

```python
import asyncio
import logging
from langchain_core.tools import BaseTool

from Coder.storage.redis_client import RedisManager

logger = logging.getLogger(__name__)

CONFIRM_TIMEOUT = 60  # seconds


class SSEToolConfirmer:
    def __init__(self, session_id: str):
        self._session_id = session_id

    @staticmethod
    def _is_remote_tool(tool: BaseTool) -> bool:
        return hasattr(tool, "metadata") and tool.metadata.get("mcp_transport") == "sse"

    def wrap_tools(self, tools: list[BaseTool]) -> list[BaseTool]:
        wrapped = []
        for tool in tools:
            if self._is_remote_tool(tool):
                wrapped.append(self._wrap_tool(tool))
            else:
                wrapped.append(tool)
        return wrapped

    def _wrap_tool(self, tool: BaseTool) -> BaseTool:
        original_func = tool.func
        session_id = self._session_id

        async def confirmed_func(*args, **kwargs):
            tool_name = tool.name
            allow_key = f"mcp:confirm:{session_id}:{tool_name}"

            try:
                allowed = await RedisManager.get(allow_key)
                if allowed == "allow_session":
                    return await original_func(*args, **kwargs)
            except Exception:
                pass

            await RedisManager.set(
                f"mcp:pending:{session_id}:{tool_name}",
                "waiting",
                ex=CONFIRM_TIMEOUT,
            )
            return f"[MCP_CONFIRM_REQUIRED] Tool '{tool_name}' requires confirmation. Session: {session_id}"

        tool.func = confirmed_func
        return tool

    @staticmethod
    async def allow_once(session_id: str, tool_name: str) -> None:
        await RedisManager.set(
            f"mcp:confirm:{session_id}:{tool_name}",
            "allow_once",
            ex=CONFIRM_TIMEOUT,
        )

    @staticmethod
    async def allow_session(session_id: str, tool_name: str) -> None:
        await RedisManager.set(
            f"mcp:confirm:{session_id}:{tool_name}",
            "allow_session",
            ex=86400,
        )

    @staticmethod
    async def deny(session_id: str, tool_name: str) -> None:
        await RedisManager.set(
            f"mcp:confirm:{session_id}:{tool_name}",
            "denied",
            ex=CONFIRM_TIMEOUT,
        )
```

- [ ] **Step 2: 提交**

```bash
cd "D:\PyCharm\AI" && git add Coder/mcp/sse_confirm.py && git commit -m "feat: add SSE tool confirmation wrapper for remote MCP tools

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: 端到端验证

**Files:** 无新增

- [ ] **Step 1: 启动后端确认 MCPManager 初始化正常**

```bash
cd "D:\PyCharm\AI" && timeout 15 python -c "
import asyncio
from Coder.server.main import app
print('Server startup OK')
" 2>&1 || true
```
Expected: 日志中无 MCP 相关报错

- [ ] **Step 2: 验证 API 响应**

```bash
cd "D:\PyCharm\AI" && python -c "
import asyncio, json
async def main():
    from Coder.mcp.registry import fetch_registry
    data = await fetch_registry()
    print(f'Registry returned {len(data)} items')
    from Coder.mcp.manager import MCPManager
    m = MCPManager()
    print('Manager created OK')
asyncio.run(main())
"
```
Expected: `Registry returned N items` + `Manager created OK`

- [ ] **Step 3: 提交里程碑标记**

```bash
git add -A
git commit -m "milestone: MCP external server integration complete

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

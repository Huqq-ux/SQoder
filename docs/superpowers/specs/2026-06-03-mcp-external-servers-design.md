# MCP 外部 Server 接入设计

## 目标

提供类似 Cursor/Claude Desktop 的 MCP 生态接入能力，支持社区 MCP Server 浏览安装、手动注册、配置导入，以及分级安全权限控制。

## 架构

```
┌─ Frontend (MCPPage.tsx) ──────────────────────────────────────┐
│  市场 Tab (浏览安装)  │  已安装 Tab (启用/禁用/删除/配置)   │
└──────────────────────────┬─────────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼─────────────────────────────────────┐
│  /api/mcp 路由层 (Coder/server/routes/mcp.py)                   │
│  GET  /registry         → 获取社区 MCP 列表                     │
│  GET  /servers          → 获取已安装列表                         │
│  POST /servers          → 安装/注册                              │
│  PATCH /servers/{id}    → 更新配置/启用禁用/工具白名单            │
│  DELETE /servers/{id}   → 删除（builtin 拒绝）                   │
│  POST /servers/{id}/test→ 测试连接                               │
│  GET  /servers/{id}/tools→ 预览工具列表                          │
│  POST /import           → 导入 claude_desktop_config.json        │
└──────────────────────────┬─────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│  MCPManager (Coder/mcp/manager.py)                              │
│  - 连接池：每个 MCP Server 独立 MultiServerMCPClient            │
│  - reload_all(): 从 PG 加载所有 enabled Server 并建立连接        │
│  - get_all_tools(): 返回所有已连接 Server 的 LangChain 工具      │
│  - get_tools_for_session(): 考虑会话级开关覆盖                   │
│  - test_connection(): 测试连接并返回工具列表                     │
│  - 连接隔离、失败降级、热加载、asyncio.Lock 并发安全              │
└──────────────────────────┬─────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│  注册表 (Coder/mcp/registry.py)                                 │
│  - 从 GitHub raw URL 拉取社区 MCP 索引 JSON                     │
│  - Redis 缓存 1 小时，失败降级到本地 registry_fallback.json     │
└─────────────────────────────────────────────────────────────────┘
```

## 数据模型

```sql
CREATE TABLE mcp_servers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(200),
    description     TEXT,
    transport       VARCHAR(20) NOT NULL DEFAULT 'stdio',  -- stdio | sse
    command         VARCHAR(500),     -- stdio 用
    args            JSONB DEFAULT '[]',
    url             VARCHAR(500),     -- sse 用
    env             JSONB DEFAULT '{}',
    enabled         BOOLEAN DEFAULT TRUE,
    is_local        BOOLEAN DEFAULT FALSE,   -- builtin 不可删除
    source          VARCHAR(20) DEFAULT 'manual',  -- manual | registry | builtin
    registry_id     VARCHAR(200),
    tools_allowlist JSONB DEFAULT NULL,  -- NULL=全部, []=全禁, ["a"]=白名单
    last_error      TEXT,                -- 最近连接错误
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

- `transport` + `command`/`url` 互斥：stdio 用 command+args，SSE 用 url
- `tools_allowlist`: 安装或编辑时可指定，Manager 层生效
- `is_local`: builtin Server 前端隐藏删除按钮

## 传输协议

首期支持 stdio + SSE，Streamable HTTP 后续按需添加。

## 安全权限模型

| 传输类型 | 行为 |
|---------|------|
| 本地 stdio | 自动信任，工具调用无需确认 |
| 远程 SSE | 调用前弹出确认卡片（Allow once / Allow this session / Deny，60s 超时自动 Deny） |

- 确认状态存 Redis（会话级 TTL），不持久化
- `tools_allowlist` 在 Manager 层生效，未列入的工具不注入 Agent

## API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/mcp/registry | 社区 MCP 列表，支持 ?search= |
| GET | /api/mcp/servers | 已安装列表（含连接状态、工具数量） |
| POST | /api/mcp/servers | 安装/注册 |
| PATCH | /api/mcp/servers/{id} | 更新配置/启用禁用/白名单 |
| DELETE | /api/mcp/servers/{id} | 删除（builtin 拒绝） |
| POST | /api/mcp/servers/{id}/test | 测试连接并返回工具列表 |
| GET | /api/mcp/servers/{id}/tools | 预览工具列表 |
| POST | /api/mcp/import | 导入 Claude Desktop 配置 |
| GET | /api/mcp/session-tools | 当前会话可用的 MCP 工具 |

## 导入兼容

`POST /import` 接受 Claude Desktop 格式，自动解析写入，按 name 去重跳过。

## 工具冲突处理

多 Server 同名工具自动加前缀：`{server_name}__{tool_name}`。

## Agent 注入模式

混合模式：默认加载全局 enabled 的 MCP 工具，前端可通过 `session-tools` API 传入会话级覆盖（临时禁用特定 Server）。

## 内置 Server 迁移

现有 `Coder/MCP/powershell_tools.py` 和 `shell_tools.py` 改为通过 MCPManager 统一管理，标记 `is_local=True, source='builtin'`。

## 前端页面

新页面 `MCPPage.tsx`，两个 Tab：

- **市场 Tab**：搜索/浏览社区 MCP Server，显示名称、描述、分类，一键安装
- **已安装 Tab**：列表，每项显示名称、状态（connected/error/disabled）、工具数量、操作按钮（启用/禁用、编辑白名单、测试连接、删除）

路由注册到 `/mcp`，侧边栏新增"MCP"入口。

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Coder/mcp/__init__.py` | 包初始化 |
| 新增 | `Coder/mcp/manager.py` | MCPManager 连接管理 |
| 新增 | `Coder/mcp/registry.py` | 社区注册表拉取 |
| 新增 | `Coder/mcp/registry_fallback.json` | 注册表本地降级数据 |
| 新增 | `Coder/server/routes/mcp.py` | REST API 路由 |
| 新增 | `Coder/web/src/pages/MCPPage.tsx` | 前端管理页面 |
| 修改 | `Coder/server/main.py` | 注册 MCP 路由，lifespan 中初始化 MCPManager |
| 修改 | `Coder/agent/code_agent.py` | 通过 MCPManager 获取工具替代硬编码 |
| 修改 | `Coder/web/src/App.tsx` | 注册 MCP 页面路由 |
| 修改 | `Coder/web/src/components/Sidebar.tsx` | 侧边栏添加 MCP 入口 |
| 修改 | `Coder/storage/db.py` | 新增 mcp_servers 建表迁移 |

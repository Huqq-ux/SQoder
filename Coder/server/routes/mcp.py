import json
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from Coder.storage.db import DatabaseManager
from Coder.MCP.registry import fetch_registry

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
        "id": str(row["id"]),
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
        "SELECT id FROM mcp_servers WHERE name = %s", body.name
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Server '{body.name}' already exists")

    await DatabaseManager.execute(
        """INSERT INTO mcp_servers
           (name, display_name, description, transport, command, args, url, env,
            tools_allowlist)
           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s::jsonb)""",
        body.name,
        body.display_name or body.name,
        body.description,
        body.transport,
        body.command,
        json.dumps(body.args),
        body.url,
        json.dumps(body.env),
        json.dumps(body.tools_allowlist) if body.tools_allowlist is not None else None,
    )
    await _get_manager(request).reload_all()
    return {"status": "created", "name": body.name}


@router.patch("/servers/{server_id}")
async def update_server(request: Request, server_id: str, body: MCPServerUpdate):
    row = await DatabaseManager.fetchrow(
        "SELECT * FROM mcp_servers WHERE id = %s", server_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")

    updates = []
    params: list = []

    for field in ("display_name", "description", "transport", "command", "url",
                  "enabled"):
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{field} = %s")
            params.append(val)

    for field in ("args", "env", "tools_allowlist"):
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{field} = %s")
            params.append(json.dumps(val))

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if body.transport or body.command or body.url:
        transport = body.transport or row["transport"]
        command = body.command if body.command is not None else row.get("command")
        url = body.url if body.url is not None else row.get("url")
        _validate_transport(transport, command, url)

    updates.append("updated_at = NOW()")
    params.append(server_id)

    sql = f"UPDATE mcp_servers SET {', '.join(updates)} WHERE id = %s"
    await DatabaseManager.execute(sql, *params)
    await _get_manager(request).reload_all()
    return {"status": "updated"}


@router.delete("/servers/{server_id}")
async def delete_server(request: Request, server_id: str):
    row = await DatabaseManager.fetchrow(
        "SELECT * FROM mcp_servers WHERE id = %s", server_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    if row.get("is_local"):
        raise HTTPException(status_code=403, detail="Cannot delete builtin MCP server")

    await DatabaseManager.execute(
        "DELETE FROM mcp_servers WHERE id = %s", server_id
    )
    await _get_manager(request).reload_all()
    return {"status": "deleted"}


@router.post("/servers/{server_id}/test")
async def test_server(request: Request, server_id: str):
    row = await DatabaseManager.fetchrow(
        "SELECT * FROM mcp_servers WHERE id = %s", server_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")

    config = dict(row)
    config["id"] = str(config["id"])
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
            "SELECT id FROM mcp_servers WHERE name = %s", name
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
               VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb)""",
            name,
            name,
            transport,
            command,
            json.dumps(args),
            url,
            json.dumps(cfg.get("env", {})),
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

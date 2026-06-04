import asyncio
import copy
import hashlib
import json
import logging
import os as _os
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
        "args": [],
        "is_local": True,
        "source": "builtin",
    },
    {
        "name": "shell_tools",
        "display_name": "Shell Tools",
        "description": "Execute shell commands",
        "transport": "stdio",
        "command": "python",
        "args": [],
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
        import platform

        for cfg in _BUILTIN_SERVERS:
            exists = await DatabaseManager.fetchrow(
                "SELECT id FROM mcp_servers WHERE name = %s", cfg["name"]
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
                   VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""",
                cfg["name"],
                cfg["display_name"],
                cfg["description"],
                cfg["transport"],
                cfg["command"],
                json.dumps(cfg["args"]),
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
            server_name = config["name"]
            server_config = {server_name: {"transport": transport}}

            if transport == "stdio":
                server_config[server_name]["command"] = config["command"]
                args_val = config.get("args", [])
                if isinstance(args_val, str):
                    args_val = json.loads(args_val)
                server_config[server_name]["args"] = args_val
            elif transport == "sse":
                server_config[server_name]["url"] = config["url"]

            if config.get("env"):
                env_val = config["env"]
                if isinstance(env_val, str):
                    env_val = json.loads(env_val)
                server_config[server_name]["env"] = env_val

            client = MultiServerMCPClient(server_config)
            await client.get_tools()
            self._clients[server_id] = client
            await DatabaseManager.execute(
                "UPDATE mcp_servers SET last_error = NULL, updated_at = NOW() WHERE id = %s",
                server_id,
            )
            logger.info(f"MCP server connected: {server_name}")
        except Exception as e:
            err_msg = str(e)[:500]
            await DatabaseManager.execute(
                "UPDATE mcp_servers SET last_error = %s, updated_at = NOW() WHERE id = %s",
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
                tool = copy.copy(tool)
                tool.name = f"{config.get('name', server_id)}__{tool.name}"
                tools.append(tool)
        return tools

    def get_tools_fingerprint(self) -> str:
        tools = self.get_all_tools()
        names = sorted(t.name for t in tools)
        return hashlib.md5(",".join(names).encode()).hexdigest()

    def get_tools_for_session(
        self, session_id: str, overrides: Optional[dict] = None
    ) -> list[BaseTool]:
        return self.get_all_tools()

    async def test_connection(
        self, config: dict, timeout: float = 10.0
    ) -> tuple[bool, str, list[dict]]:
        try:
            transport = config["transport"]
            server_name = config["name"]
            server_config = {server_name: {"transport": transport}}

            if transport == "stdio":
                server_config[server_name]["command"] = config["command"]
                args_val = config.get("args", [])
                if isinstance(args_val, str):
                    args_val = json.loads(args_val)
                server_config[server_name]["args"] = args_val
            elif transport == "sse":
                server_config[server_name]["url"] = config["url"]

            if config.get("env"):
                env_val = config["env"]
                if isinstance(env_val, str):
                    env_val = json.loads(env_val)
                server_config[server_name]["env"] = env_val

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

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
_CACHE_TTL = 86400

_FALLBACK_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "registry_fallback.json")
)


async def fetch_registry(
    force_refresh: bool = False,
) -> list[dict]:
    if not force_refresh:
        try:
            cached = await RedisManager.get_json(_CACHE_KEY)
            if cached:
                return cached
        except Exception:
            pass

    data = await _fetch_from_github()
    if data is not None:
        try:
            await RedisManager.set_json(_CACHE_KEY, data, ttl=_CACHE_TTL)
        except Exception:
            pass
    else:
        data = _load_fallback()

    return data


async def _fetch_from_github() -> Optional[list[dict]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(_REGISTRY_URL, timeout=aiohttp.ClientTimeout(total=60)) as resp:
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

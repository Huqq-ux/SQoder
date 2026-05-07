import os
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class RedisManager:
    _client: Optional[aioredis.Redis] = None

    @classmethod
    def get_url(cls) -> str:
        return REDIS_URL

    @classmethod
    async def init_client(cls) -> aioredis.Redis:
        if cls._client is not None:
            return cls._client

        cls._client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        await cls._client.ping()
        logger.info("Redis 连接已建立")
        return cls._client

    @classmethod
    async def close_client(cls):
        if cls._client is not None:
            await cls._client.close()
            cls._client = None
            logger.info("Redis 连接已关闭")

    @classmethod
    def client(cls) -> aioredis.Redis:
        if cls._client is None:
            raise RuntimeError("Redis 客户端未初始化")
        return cls._client

    @classmethod
    async def get_json(cls, key: str) -> Optional[dict]:
        data = await cls.client().get(key)
        if data is None:
            return None
        return json.loads(data)

    @classmethod
    async def set_json(cls, key: str, value: dict, ttl: int = None):
        data = json.dumps(value, ensure_ascii=False)
        if ttl:
            await cls.client().setex(key, ttl, data)
        else:
            await cls.client().set(key, data)

    @classmethod
    async def delete(cls, *keys: str):
        if keys:
            await cls.client().delete(*keys)

    @classmethod
    async def exists(cls, key: str) -> bool:
        return await cls.client().exists(key) > 0

    @classmethod
    async def publish(cls, channel: str, message: dict):
        await cls.client().publish(channel, json.dumps(message, ensure_ascii=False))

    @classmethod
    async def subscribe(cls, channel: str):
        pubsub = cls.client().pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    @classmethod
    async def unsubscribe(cls, pubsub):
        if pubsub is None:
            return
        try:
            await pubsub.unsubscribe()
            await pubsub.aclose()
        except Exception as e:
            logger.warning(f"关闭 pubsub 失败: {e}")

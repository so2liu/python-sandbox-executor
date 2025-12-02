from __future__ import annotations

from typing import AsyncGenerator

import redis.asyncio as redis

from job_runner.redis_client import get_redis


class LogStore:
    """Redis-backed log store with list + pubsub for streaming."""

    def __init__(self, client: redis.Redis | None = None) -> None:
        self.redis = client or get_redis()
        self._complete_key = "log:complete:"
        self._list_key = "log:list:"
        self._channel_key = "log:channel:"

    def _list(self, job_id: str) -> str:
        return f"{self._list_key}{job_id}"

    def _complete(self, job_id: str) -> str:
        return f"{self._complete_key}{job_id}"

    def _channel(self, job_id: str) -> str:
        return f"{self._channel_key}{job_id}"

    async def register(self, job_id: str) -> None:
        await self.redis.delete(self._list(job_id), self._complete(job_id))

    async def append(self, job_id: str, text: str) -> None:
        await self.redis.rpush(self._list(job_id), text)  # type: ignore[misc]
        await self.redis.publish(self._channel(job_id), text)  # type: ignore[misc]

    async def mark_complete(self, job_id: str) -> None:
        await self.redis.set(self._complete(job_id), "1")
        await self.redis.publish(self._channel(job_id), "__complete__")

    async def tail(self, job_id: str) -> list[str]:
        raw = await self.redis.lrange(self._list(job_id), 0, -1)  # type: ignore[misc]
        return [self._decode(item) for item in raw]

    async def stream(self, job_id: str, start_at: int = 0) -> AsyncGenerator[str, None]:
        # yield backlog
        buffer = await self.redis.lrange(self._list(job_id), start_at, -1)  # type: ignore[misc]
        idx = start_at
        for line in buffer:
            yield self._decode(line)
            idx += 1

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel(job_id))

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = self._decode(message["data"])
                if data == "__complete__":
                    return
                yield str(data)
                idx += 1
        finally:
            await pubsub.unsubscribe(self._channel(job_id))
            await pubsub.close()

    @staticmethod
    def _decode(value: str | bytes) -> str:
        if isinstance(value, bytes):
            return value.decode()
        return str(value)

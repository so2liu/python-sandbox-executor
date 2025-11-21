from __future__ import annotations

import redis.asyncio as redis

from job_runner.settings import get_settings

try:
    import fakeredis.aioredis as fakeredis
except ImportError:  # pragma: no cover - optional
    fakeredis = None

_redis_cache: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_cache
    if _redis_cache is not None:
        return _redis_cache
    settings = get_settings()
    if settings.use_fake_redis:
        if fakeredis is None:
            raise RuntimeError("FAKE_REDIS is set but fakeredis is not installed")
        _redis_cache = fakeredis.FakeRedis()
    else:
        _redis_cache = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_cache

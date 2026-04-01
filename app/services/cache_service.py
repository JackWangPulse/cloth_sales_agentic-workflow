"""Safe Redis JSON cache helper."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client = None


def get_cache_client():
    """Return a lazy Redis client, or ``None`` when Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    if not settings.redis_url:
        logger.info("[CACHE] Redis URL not configured; cache disabled")
        return None

    try:
        import redis

        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_client = client
        logger.info("[CACHE] Redis connected")
        return _redis_client
    except Exception as exc:
        logger.warning("[CACHE] Redis unavailable: %s", exc)
        _redis_client = None
        return None


def get_json(key: str) -> dict[str, Any] | list[Any] | None:
    """Read a JSON payload from Redis, returning ``None`` on cache failure."""
    client = get_cache_client()
    if client is None:
        return None

    try:
        raw_value = client.get(key)
        if not raw_value:
            return None
        return json.loads(raw_value)
    except Exception as exc:
        logger.warning("[CACHE] Cache read failed for key=%s: %s", key, exc)
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    """Write a JSON payload to Redis, returning ``False`` on cache failure."""
    client = get_cache_client()
    if client is None:
        return False

    try:
        payload = json.dumps(value, ensure_ascii=False)
        client.setex(key, ttl_seconds, payload)
        return True
    except Exception as exc:
        logger.warning("[CACHE] Cache write failed for key=%s: %s", key, exc)
        return False

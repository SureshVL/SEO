"""Redis caching layer for production.

Falls back to in-memory cache when Redis is unavailable.
Used for SERP results, Claude responses, and PageSpeed data.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger("omnirank.cache")

_redis_client = None
_redis_available = False


def _get_redis():
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None

    from app.core.config import settings
    if not settings.redis_url:
        _redis_available = False
        return None

    try:
        import redis
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis connected: %s", settings.redis_url)
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable (%s), using in-memory fallback", exc)
        _redis_available = False
        _redis_client = True  # mark as attempted
        return None


class _InMemoryFallback:
    """Simple LRU fallback when Redis is down. Entries expire at their TTL."""

    def __init__(self, max_size: int = 500):
        # key -> (expires_at, value)
        self._store: dict[str, tuple[float, str]] = {}
        self._max_size = max_size

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, val = entry
        if time.time() >= expires_at:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda x: self._store[x][0])
            del self._store[oldest]
        self._store[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


_fallback = _InMemoryFallback()


def cache_key(*parts: str) -> str:
    raw = ":".join(str(p) for p in parts)
    return f"omnirank:{hashlib.md5(raw.encode()).hexdigest()}"


def cache_get(key: str) -> str | None:
    r = _get_redis()
    if r:
        try:
            return r.get(key)
        except Exception:
            pass
    return _fallback.get(key)


def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, value)
            return
        except Exception:
            pass
    _fallback.set(key, value, ttl)


def cache_delete(key: str) -> None:
    r = _get_redis()
    if r:
        try:
            r.delete(key)
            return
        except Exception:
            pass
    _fallback.delete(key)


def cache_json_get(key: str) -> dict | list | None:
    raw = cache_get(key)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return None


def cache_json_set(key: str, data: Any, ttl: int = 3600) -> None:
    cache_set(key, json.dumps(data, default=str), ttl)


# ── Decorator for easy function caching ──

def cached(prefix: str, ttl: int = 1800):
    """Decorator to cache function results.

    Usage:
        @cached("serp", ttl=86400)
        def search(keyword, region): ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            parts = [prefix] + [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
            key = cache_key(*parts)
            hit = cache_get(key)
            if hit:
                logger.debug("Cache hit: %s", prefix)
                try:
                    return json.loads(hit)
                except json.JSONDecodeError:
                    return hit

            result = func(*args, **kwargs)
            try:
                serialized = json.dumps(result, default=str)
                cache_set(key, serialized, ttl)
            except (TypeError, ValueError):
                pass
            return result
        return wrapper
    return decorator

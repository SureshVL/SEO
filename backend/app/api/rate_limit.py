"""Rate limiting with Redis backend and in-memory fallback."""

from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import HTTPException, Request

from app.core.config import settings


class InMemoryRateLimiter:
    """Fallback rate limiter when Redis is unavailable."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time()
        q = self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        q.append(now)


class RedisRateLimiter:
    """Sliding window rate limiter backed by Redis."""

    def __init__(self, per_minute: int, redis_url: str):
        self.per_minute = per_minute
        self._redis = None
        self._redis_url = redis_url
        self._fallback = InMemoryRateLimiter(per_minute)

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.from_url(self._redis_url, decode_responses=True, socket_timeout=1)
            self._redis.ping()
            return self._redis
        except Exception:
            self._redis = False  # mark as attempted
            return None

    def check(self, key: str) -> None:
        r = self._get_redis()
        if not r:
            self._fallback.check(key)
            return

        try:
            redis_key = f"ratelimit:{key}"
            now = time()
            pipe = r.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - 60)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, 120)
            results = pipe.execute()

            count = results[2]
            if count > self.per_minute:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
        except HTTPException:
            raise
        except Exception:
            # Redis error — fall back
            self._fallback.check(key)


def _create_limiter():
    if settings.redis_url:
        return RedisRateLimiter(settings.rate_limit_per_minute, settings.redis_url)
    return InMemoryRateLimiter(settings.rate_limit_per_minute)


rate_limiter = _create_limiter()


def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    api_key = request.headers.get("X-API-KEY", "anon")
    key = f"{api_key}:{client}:{request.url.path}"
    rate_limiter.check(key)

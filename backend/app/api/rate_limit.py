from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import Header, HTTPException, Request

from app.core.config import settings


class SimpleRateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time()
        window = 60
        q = self.hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= self.per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        q.append(now)


rate_limiter = SimpleRateLimiter(settings.rate_limit_per_minute)


def enforce_rate_limit(request: Request, x_api_key: str | None = Header(default="anon")) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"{x_api_key}:{client}:{request.url.path}"
    rate_limiter.check(key)

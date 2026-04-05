"""Claude AI client with caching, model routing, and cost tracking."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("omnirank.ai")

# Pricing per 1M tokens (USD)
MODEL_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
}

SONNET = "claude-sonnet-4-20250514"
HAIKU = "claude-haiku-4-5-20251001"


@dataclass
class AIResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool = False
    latency_ms: int = 0


@dataclass
class AIUsageAccumulator:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def record(self, resp: AIResponse) -> None:
        self.total_input_tokens += resp.input_tokens
        self.total_output_tokens += resp.output_tokens
        self.total_cost_usd += resp.cost_usd
        self.calls.append({
            "model": resp.model,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
            "cached": resp.cached,
        })


class SimpleCache:
    """In-memory LRU cache. Replace with Redis in production."""

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._store: dict[str, tuple[float, str]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _key(self, model: str, system: str, messages: list[dict]) -> str:
        raw = json.dumps({"model": model, "system": system, "messages": messages}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, model: str, system: str, messages: list[dict]) -> str | None:
        k = self._key(model, system, messages)
        entry = self._store.get(k)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self._ttl:
            del self._store[k]
            return None
        return value

    def set(self, model: str, system: str, messages: list[dict], value: str) -> None:
        k = self._key(model, system, messages)
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda x: self._store[x][0])
            del self._store[oldest]
        self._store[k] = (time.time(), value)


_cache = SimpleCache(max_size=1000, ttl_seconds=1800)


class ClaudeClient:
    """Anthropic Claude API client with retry, caching, and cost tracking."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        timeout: int = 120,
    ):
        self.api_key = api_key or settings.anthropic_api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for AI operations")

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        model: str = SONNET,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        use_cache: bool = True,
    ) -> AIResponse:
        if use_cache:
            cached = _cache.get(model, system, messages)
            if cached is not None:
                logger.info("Cache hit for prompt (model=%s)", model)
                return AIResponse(
                    content=cached,
                    model=model,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    cached=True,
                )

        start = time.time()
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/v1/messages",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    break
            except Exception as exc:
                last_error = exc
                wait = 1.5 * (2 ** attempt)
                logger.warning("Claude API attempt %d failed: %s (retrying in %.1fs)", attempt + 1, exc, wait)
                time.sleep(wait)
        else:
            raise RuntimeError(f"Claude API failed after 3 retries: {last_error}")

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        pricing = MODEL_PRICING.get(model, MODEL_PRICING[SONNET])
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        latency_ms = int((time.time() - start) * 1000)

        if use_cache and content:
            _cache.set(model, system, messages, content)

        logger.info(
            "Claude API call: model=%s tokens=%d+%d cost=$%.4f latency=%dms",
            model, input_tokens, output_tokens, cost, latency_ms,
        )

        return AIResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
            latency_ms=latency_ms,
        )

    def complete_json(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        model: str = SONNET,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        use_cache: bool = True,
    ) -> tuple[dict[str, Any], AIResponse]:
        """Complete and parse JSON from response. Returns (parsed_dict, ai_response)."""
        full_system = system + "\n\nRespond ONLY with valid JSON. No markdown fences, no preamble."
        resp = self.complete(messages, full_system, model, max_tokens, temperature, use_cache)

        text = resp.content.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response: %s", text[:200])
            parsed = {"error": "Failed to parse AI response", "raw": text[:500]}

        return parsed, resp

    def route_model(self, task_complexity: str) -> str:
        """Route to appropriate model based on task complexity."""
        if task_complexity in ("simple", "classification", "extraction"):
            return HAIKU
        return SONNET

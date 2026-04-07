"""Google Gemini AI client.

Uses the new google-genai SDK (not the deprecated google.generativeai).
Drop-in alternative to ClaudeClient for cost-free development.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("omnirank.gemini")

GEMINI_MODELS = {
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-1.5-flash": "gemini-1.5-flash-latest",
}

DEFAULT_MODEL = "gemini-2.5-flash"


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


class _SimpleCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 1800):
        self._store: dict[str, tuple[float, str]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _key(self, model: str, system: str, messages: list[dict]) -> str:
        raw = json.dumps({"model": model, "system": system, "messages": messages}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, model: str, system: str, messages: list[dict]) -> str | None:
        k = self._key(model, system, messages)
        entry = self._store.get(k)
        if not entry:
            return None
        ts, val = entry
        if time.time() - ts > self._ttl:
            del self._store[k]
            return None
        return val

    def set(self, model: str, system: str, messages: list[dict], value: str) -> None:
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda x: self._store[x][0])
            del self._store[oldest]
        self._store[(self._key(model, system, messages))] = (time.time(), value)


_cache = _SimpleCache()


class GeminiClient:
    """Google Gemini API client via REST (no deprecated SDK needed).

    Uses the Gemini REST API directly with httpx.
    Compatible interface with ClaudeClient for easy swapping.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        use_cache: bool = True,
    ) -> AIResponse:
        if use_cache:
            cached = _cache.get(model, system, messages)
            if cached is not None:
                return AIResponse(content=cached, model=model, input_tokens=0, output_tokens=0, cost_usd=0.0, cached=True)

        # Build Gemini request
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"[System instruction]: {system}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})

        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        model_id = GEMINI_MODELS.get(model, model)
        url = f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}"

        start = time.time()
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                with httpx.Client(timeout=120) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    break
            except Exception as exc:
                last_error = exc
                wait = 1.5 * (2 ** attempt)
                logger.warning("Gemini API attempt %d failed: %s", attempt + 1, exc)
                time.sleep(wait)
        else:
            raise RuntimeError(f"Gemini API failed after 3 retries: {last_error}")

        # Extract text
        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        # Token usage
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        # Gemini free tier = $0 cost
        cost = 0.0

        latency_ms = int((time.time() - start) * 1000)

        if use_cache and content:
            _cache.set(model, system, messages, content)

        logger.info("Gemini call: model=%s tokens=%d+%d latency=%dms", model_id, input_tokens, output_tokens, latency_ms)

        return AIResponse(
            content=content, model=model_id,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cost_usd=cost, latency_ms=latency_ms,
        )

    def complete_json(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        use_cache: bool = True,
    ) -> tuple[dict[str, Any], AIResponse]:
        full_system = system + "\n\nRespond ONLY with valid JSON. No markdown fences, no preamble."
        resp = self.complete(messages, full_system, model, max_tokens, temperature, use_cache)

        text = resp.content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Gemini: %s", text[:200])
            parsed = {"error": "Failed to parse AI response", "raw": text[:500]}

        return parsed, resp

    def route_model(self, task_complexity: str) -> str:
        return DEFAULT_MODEL  # Gemini free tier uses same model

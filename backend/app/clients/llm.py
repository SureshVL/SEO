# backend/app/clients/llm.py
"""Smart LLM Router: auto-fallback, cheapest-first, retry with backoff."""

from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import json
import re
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger("omnirank.llm")

class LLMSettings(BaseSettings):
    llm_provider: str = "auto"
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    default_claude_model: str = "claude-sonnet-4-20250514"
    default_gemini_model: str = "gemini-2.0-flash"
    default_groq_model: str = "llama-3.3-70b-versatile"
    default_openai_model: str = "gpt-4o"
    default_perplexity_model: str = "sonar-pro"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = LLMSettings()

PROVIDER_COST_TIERS = {
    "gemini":     {"input": 0.0,    "output": 0.0,    "free_tier": True,  "free_rpm": 15},
    "groq":       {"input": 0.0,    "output": 0.0,    "free_tier": True,  "free_rpm": 30},
    "perplexity": {"input": 0.001,  "output": 0.001,  "free_tier": False, "free_rpm": 0},
    "openai":     {"input": 0.0025, "output": 0.01,   "free_tier": False, "free_rpm": 0},
    "claude":     {"input": 0.003,  "output": 0.015,  "free_tier": False, "free_rpm": 0},
}
CHEAPEST_FIRST_ORDER = ["gemini", "groq", "perplexity", "openai", "claude"]

@dataclass
class ProviderStatus:
    name: str
    requests_made: int = 0
    errors: int = 0
    last_error: str = ""
    last_error_time: float = 0
    rate_limited_until: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    exhausted: bool = False

class LLMClient:
    def __init__(self):
        self.provider = self._determine_provider()
        self._status: Dict[str, ProviderStatus] = {}
        self.allow_paid: bool = True
        for p in self._get_available():
            self._status[p] = ProviderStatus(name=p)

    def _get_available(self) -> List[str]:
        a = []
        if settings.gemini_api_key: a.append("gemini")
        if settings.groq_api_key: a.append("groq")
        if settings.perplexity_api_key: a.append("perplexity")
        if settings.openai_api_key: a.append("openai")
        if settings.anthropic_api_key: a.append("claude")
        return a

    def _determine_provider(self) -> str:
        if settings.llm_provider != "auto":
            return settings.llm_provider.lower()
        keys = {"gemini": settings.gemini_api_key, "groq": settings.groq_api_key,
                "perplexity": settings.perplexity_api_key, "openai": settings.openai_api_key,
                "claude": settings.anthropic_api_key}
        for p in CHEAPEST_FIRST_ORDER:
            if keys.get(p): return p
        return "none"

    def _get_fallback_order(self, primary: str) -> List[str]:
        available = self._get_available()
        order = []
        for p in ([primary] if primary in available else []) + CHEAPEST_FIRST_ORDER:
            if p not in available or p in order:
                continue
            s = self._status.get(p)
            if s and s.rate_limited_until > time.time():
                continue
            if not self.allow_paid and not PROVIDER_COST_TIERS.get(p, {}).get("free_tier"):
                continue  # paid providers excluded while allow_paid is off
            order.append(p)
        return order

    @staticmethod
    def _model_for_provider(provider: str, model: Optional[str]) -> Optional[str]:
        """Only forward a model override to the provider family it belongs to."""
        if not model:
            return None
        families = {
            "claude": ("claude",),
            "gemini": ("gemini",),
            "openai": ("gpt", "o1", "o3", "o4"),
            "perplexity": ("sonar",),
            "groq": ("llama", "mixtral", "gemma", "qwen", "deepseek"),
        }
        prefixes = families.get(provider, ())
        if any(model.startswith(p) for p in prefixes):
            return model
        return None  # fall back to that provider's default model

    @staticmethod
    def _normalize(result) -> Dict[str, Any]:
        """Providers return either a dict or an AIResponse dataclass; unify to dict."""
        if isinstance(result, dict):
            return result
        return {
            "content": getattr(result, "content", str(result)),
            "model": getattr(result, "model", ""),
            "input_tokens": getattr(result, "input_tokens", 0),
            "output_tokens": getattr(result, "output_tokens", 0),
            "cost_usd": getattr(result, "cost_usd", 0.0),
            "cached": getattr(result, "cached", False),
        }

    def _call_provider(self, provider, messages, model=None, temperature=0.7, max_tokens=4000, **kw):
        model = self._model_for_provider(provider, model)
        if provider == "claude":
            from .claude_client import ClaudeClient
            result = ClaudeClient().complete(messages, model=model or settings.default_claude_model, temperature=temperature, max_tokens=max_tokens, **kw)
        elif provider == "gemini":
            from .gemini_client import GeminiClient
            result = GeminiClient().complete(messages, model=model or settings.default_gemini_model, temperature=temperature, max_tokens=max_tokens, **kw)
        elif provider == "groq":
            from .groq_client import GroqClient
            result = GroqClient().complete(messages, model=model or settings.default_groq_model, temperature=temperature, max_tokens=max_tokens, **kw)
        elif provider == "openai":
            from .openai_client import OpenAIClient
            result = OpenAIClient().complete(messages, model=model or settings.default_openai_model, temperature=temperature, max_tokens=max_tokens, **kw)
        elif provider == "perplexity":
            from .perplexity_client import PerplexityClient
            result = PerplexityClient().complete(messages, model=model or settings.default_perplexity_model, temperature=temperature, max_tokens=max_tokens, **kw)
        else:
            raise Exception(f"Unknown provider: {provider}")
        return self._normalize(result)

    def complete(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Smart complete: cheapest first, auto-fallback on 429/503."""
        requested = kwargs.pop("provider", self.provider)
        model = kwargs.pop("model", None)
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", 4000)
        fallback_order = self._get_fallback_order(requested)
        if not fallback_order:
            raise Exception("No LLM providers available. Add API keys to .env")
        last_error = None
        for provider in fallback_order:
            status = self._status.get(provider, ProviderStatus(name=provider))
            for attempt in range(2):
                try:
                    logger.info("LLM: %s (attempt %d)", provider, attempt+1)
                    result = self._call_provider(provider, messages, model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
                    status.requests_made += 1
                    if isinstance(result, dict):
                        status.total_input_tokens += result.get("input_tokens", 0)
                        status.total_output_tokens += result.get("output_tokens", 0)
                        status.total_cost_usd += result.get("cost_usd", 0)
                        result["_provider_used"] = provider
                    self._status[provider] = status
                    logger.info("LLM OK: %s", provider)
                    return result
                except Exception as exc:
                    err = str(exc)
                    status.errors += 1
                    status.last_error = err[:200]
                    status.last_error_time = time.time()
                    self._status[provider] = status
                    last_error = exc
                    if "429" in err or "rate" in err.lower() or "quota" in err.lower():
                        status.rate_limited_until = time.time() + 60
                        if PROVIDER_COST_TIERS.get(provider, {}).get("free_tier"):
                            status.exhausted = True
                        logger.warning("RATE LIMITED: %s — next provider", provider)
                        break
                    if any(c in err for c in ["503", "500", "502", "overloaded"]):
                        wait = 2 * (2 ** attempt)
                        logger.warning("%s error, retry in %ds", provider, wait)
                        time.sleep(wait)
                        continue
                    logger.warning("%s failed: %s", provider, err[:100])
                    break
        raise Exception(f"All providers failed: {last_error}")

    async def agenerate_text(self, prompt: str, model: Optional[str] = None,
                             max_tokens: int = 4000, temperature: float = 0.7, **kwargs) -> str:
        """Async text generation used by the agent classes. Returns the raw text."""
        import asyncio

        def _run() -> str:
            result = self.complete(
                [{"role": "user", "content": prompt}],
                model=model, max_tokens=max_tokens, temperature=temperature, **kwargs,
            )
            if isinstance(result, dict):
                return result.get("content", "")
            return getattr(result, "content", str(result))

        return await asyncio.to_thread(_run)

    def complete_json(self, messages: List[Dict], system: str = None, **kwargs) -> tuple:
        if system:
            messages = [{"role": "user", "content": f"{system}\n\n{messages[0]['content']}"}]
        result = self.complete(messages, **kwargs)
        text = result.get("content", str(result)) if isinstance(result, dict) else str(result)
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try: parsed = json.loads(match.group())
                except: parsed = {"score": 50, "recommendations": [text[:500]]}
            else:
                parsed = {"score": 50, "recommendations": [text[:500]]}
        return parsed, result

    def is_enabled(self) -> bool:
        return self.provider != "none"

    def get_status(self) -> Dict[str, Any]:
        providers = {}
        for name, s in self._status.items():
            tier = PROVIDER_COST_TIERS.get(name, {})
            providers[name] = {
                "requests": s.requests_made, "errors": s.errors,
                "last_error": s.last_error or None,
                "rate_limited": s.rate_limited_until > time.time(),
                "exhausted": s.exhausted, "free_tier": tier.get("free_tier", False),
                "cost_usd": round(s.total_cost_usd, 4),
                "tokens": s.total_input_tokens + s.total_output_tokens,
            }
        all_free_gone = all(s.exhausted for s in self._status.values()
            if PROVIDER_COST_TIERS.get(s.name, {}).get("free_tier")) if self._status else False
        return {
            "active_provider": self.provider, "available": list(self._status.keys()),
            "fallback_order": self._get_fallback_order(self.provider),
            "all_free_exhausted": all_free_gone, "allow_paid": self.allow_paid,
            "providers": providers,
        }

    def set_allow_paid(self, allow: bool):
        self.allow_paid = allow

llm_client = LLMClient()

def get_llm_client():
    return llm_client

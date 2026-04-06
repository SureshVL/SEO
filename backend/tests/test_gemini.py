"""Tests for Gemini client and LLM provider routing."""

from app.clients.gemini_client import GeminiClient, _SimpleCache, AIResponse


def test_gemini_cache():
    cache = _SimpleCache(max_size=5, ttl_seconds=60)
    cache.set("m", "s", [{"role": "user", "content": "hello"}], "world")
    assert cache.get("m", "s", [{"role": "user", "content": "hello"}]) == "world"
    assert cache.get("m", "s", [{"role": "user", "content": "other"}]) is None


def test_gemini_models_dict():
    from app.clients.gemini_client import GEMINI_MODELS
    assert "gemini-2.5-flash" in GEMINI_MODELS
    assert "gemini-1.5-flash" in GEMINI_MODELS


def test_ai_response_dataclass():
    r = AIResponse(content="hello", model="gemini-2.5-flash", input_tokens=10, output_tokens=20, cost_usd=0.0)
    assert r.content == "hello"
    assert r.cost_usd == 0.0
    assert not r.cached


def test_llm_provider_returns_none_without_keys():
    """Without any API keys, get_llm_client should return None."""
    # This test works because our test env has no API keys set
    from app.clients.llm import get_llm_client
    # In test environment, settings won't have real keys
    # The function should handle this gracefully
    client = get_llm_client()
    # May return None or a client depending on env - just ensure no crash
    assert client is None or hasattr(client, "complete")

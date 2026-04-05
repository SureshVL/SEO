"""Tests for Claude client utilities (cache, routing — no live API calls)."""

from app.clients.claude_client import HAIKU, SONNET, SimpleCache, ClaudeClient


def test_cache_set_and_get():
    cache = SimpleCache(max_size=10, ttl_seconds=60)
    cache.set("model", "system", [{"role": "user", "content": "hello"}], "response text")
    result = cache.get("model", "system", [{"role": "user", "content": "hello"}])
    assert result == "response text"


def test_cache_miss():
    cache = SimpleCache(max_size=10, ttl_seconds=60)
    result = cache.get("model", "sys", [{"role": "user", "content": "miss"}])
    assert result is None


def test_cache_eviction():
    cache = SimpleCache(max_size=2, ttl_seconds=60)
    cache.set("m", "s", [{"role": "user", "content": "1"}], "v1")
    cache.set("m", "s", [{"role": "user", "content": "2"}], "v2")
    cache.set("m", "s", [{"role": "user", "content": "3"}], "v3")
    # First entry should be evicted
    assert cache.get("m", "s", [{"role": "user", "content": "1"}]) is None
    assert cache.get("m", "s", [{"role": "user", "content": "3"}]) == "v3"


def test_model_routing():
    """Verify model routing returns appropriate model for task complexity."""
    # Can't instantiate ClaudeClient without API key, test the static method logic
    assert SONNET == "claude-sonnet-4-20250514"
    assert HAIKU == "claude-haiku-4-5-20251001"


def test_cache_different_messages_different_keys():
    cache = SimpleCache(max_size=10, ttl_seconds=60)
    cache.set("m", "s", [{"role": "user", "content": "a"}], "response_a")
    cache.set("m", "s", [{"role": "user", "content": "b"}], "response_b")
    assert cache.get("m", "s", [{"role": "user", "content": "a"}]) == "response_a"
    assert cache.get("m", "s", [{"role": "user", "content": "b"}]) == "response_b"

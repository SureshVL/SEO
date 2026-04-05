"""Tests for auth, rate limiting, and deploy agent."""

import base64
import json
import time

from app.api.auth import _decode_jwt_payload
from app.api.rate_limit import InMemoryRateLimiter
from app.agents.deploy_agent import DeployAgent
from app.schemas.deploy import DeployRequest


# ── JWT decoding ──

def _make_jwt(payload: dict) -> str:
    """Create a fake JWT for testing (no signature verification)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"


def test_decode_jwt_valid():
    token = _make_jwt({"sub": "user-123", "email": "dev@test.com", "exp": time.time() + 3600})
    payload = _decode_jwt_payload(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "dev@test.com"


def test_decode_jwt_expired():
    token = _make_jwt({"sub": "user-123", "exp": time.time() - 100})
    try:
        _decode_jwt_payload(token)
        assert False, "Expected ValueError for expired token"
    except ValueError as exc:
        assert "expired" in str(exc).lower()


def test_decode_jwt_invalid_format():
    try:
        _decode_jwt_payload("not.a.valid.jwt.token")
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ── Rate Limiter ──

def test_rate_limiter_allows_within_limit():
    limiter = InMemoryRateLimiter(per_minute=5)
    for _ in range(5):
        limiter.check("test-key")  # should not raise


def test_rate_limiter_blocks_over_limit():
    from fastapi import HTTPException
    limiter = InMemoryRateLimiter(per_minute=3)
    for _ in range(3):
        limiter.check("test-key-2")
    try:
        limiter.check("test-key-2")
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 429


def test_rate_limiter_separate_keys():
    limiter = InMemoryRateLimiter(per_minute=2)
    limiter.check("key-a")
    limiter.check("key-a")
    limiter.check("key-b")  # different key, should work
    limiter.check("key-b")


# ── Deploy Agent ──

def test_deploy_agent_dry_run():
    agent = DeployAgent()
    result = agent.run(DeployRequest(project_id="p1", platform="wordpress", dry_run=True))
    assert result.status == "dry_run_complete"
    assert result.actions


def test_deploy_agent_invalid_platform():
    agent = DeployAgent()
    result = agent.run(DeployRequest(project_id="p1", platform="unknown", dry_run=False))
    assert result.status == "failed"


def test_deploy_agent_no_webhook():
    agent = DeployAgent()
    result = agent.run(DeployRequest(project_id="p1", platform="wordpress", dry_run=False))
    assert result.status == "failed"
    assert any("No deploy webhook" in a for a in result.actions)

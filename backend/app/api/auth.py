"""Supabase JWT authentication for frontend users.

Verifies the JWT from Supabase Auth (sent as `Authorization: Bearer <token>`)
and resolves the user's organization so requests can be scoped to the tenant.

Verification strategy (in priority order):
1. If SUPABASE_JWT_SECRET is set: verify the HS256 signature locally (stdlib
   hmac) — fast, no network. This is Supabase's default signing scheme.
2. Otherwise, validate the token by calling Supabase `GET /auth/v1/user`
   (works with any signing algorithm, also catches revoked tokens). Cached.

CRITICAL: the previous implementation decoded the payload WITHOUT verifying
the signature, which let anyone forge a token with an arbitrary user id.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger("omnirank.auth")

# token -> (validated_user, expires_at_epoch) for the remote-validation path
_token_cache: dict[str, tuple[dict[str, Any], float]] = {}
_TOKEN_CACHE_TTL = 60.0
# user_id -> (org_id, expires_at_epoch)
_org_cache: dict[str, tuple[str, float]] = {}
_ORG_CACHE_TTL = 300.0


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _verify_hs256(token: str, secret: str) -> dict[str, Any]:
    """Verify an HS256 JWT signature and return the claims. Raises on failure."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header_b64, payload_b64, sig_b64 = parts

    header = json.loads(_b64url_decode(header_b64))
    if header.get("alg") != "HS256":
        # never allow 'none' or an unexpected algorithm (algorithm-confusion guard)
        raise ValueError(f"Unsupported JWT alg: {header.get('alg')}")

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise ValueError("Bad signature")

    claims = json.loads(_b64url_decode(payload_b64))
    exp = claims.get("exp")
    if not exp or time.time() > exp:
        raise ValueError("Token expired")
    return claims


def _validate_remote(token: str) -> dict[str, Any]:
    """Validate a token by asking Supabase who it belongs to. Cached briefly."""
    cached = _token_cache.get(token)
    now = time.time()
    if cached and cached[1] > now:
        return cached[0]

    if not (settings.supabase_url and settings.supabase_anon_key):
        raise ValueError("No JWT verification configured")

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_anon_key,
                },
            )
    except httpx.HTTPError as exc:
        raise ValueError(f"Auth service unreachable: {exc}")

    if resp.status_code != 200:
        raise ValueError("Invalid or expired token")

    user = resp.json()
    claims = {
        "sub": user.get("id"),
        "email": user.get("email", ""),
        "role": user.get("role", "authenticated"),
        "app_metadata": user.get("app_metadata", {}),
        "user_metadata": user.get("user_metadata", {}),
    }
    if len(_token_cache) > 5000:
        _token_cache.clear()
    _token_cache[token] = (claims, now + _TOKEN_CACHE_TTL)
    return claims


def _verify_token(token: str) -> dict[str, Any]:
    if settings.supabase_jwt_secret:
        return _verify_hs256(token, settings.supabase_jwt_secret)
    return _validate_remote(token)


async def get_current_user(request: Request) -> dict[str, Any]:
    """Extract and VERIFY the Supabase user from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:].strip()
    try:
        claims = _verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")

    return {
        "user_id": user_id,
        "email": claims.get("email", ""),
        "role": claims.get("role", "authenticated"),
        "app_metadata": claims.get("app_metadata", {}),
        "user_metadata": claims.get("user_metadata", {}),
    }


async def get_optional_user(request: Request) -> dict[str, Any] | None:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def resolve_user_org(user_id: str, db_fn) -> str | None:
    """Look up the user's org_id (cached). db_fn is the Supabase REST helper."""
    cached = _org_cache.get(user_id)
    now = time.time()
    if cached and cached[1] > now:
        return cached[0] or None
    try:
        rows = db_fn("get", "users", params=f"id=eq.{user_id}&select=org_id")
        rows = rows if isinstance(rows, list) else [rows] if rows else []
        org_id = rows[0].get("org_id") if rows else None
    except Exception as exc:
        logger.warning("Could not resolve org for user %s: %s", user_id, exc)
        return None
    if len(_org_cache) > 5000:
        _org_cache.clear()
    _org_cache[user_id] = (org_id or "", now + _ORG_CACHE_TTL)
    return org_id

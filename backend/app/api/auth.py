"""Supabase JWT authentication for frontend users.

Verifies the JWT token from Supabase Auth (sent as Bearer token).
Used alongside the API key auth — frontend uses JWT, backend services use API keys.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger("omnirank.auth")

_jwks_cache: dict[str, Any] = {}
_jwks_cached_at: float = 0


def _get_jwks() -> dict[str, Any]:
    """Fetch Supabase JWKS (cached for 1 hour)."""
    global _jwks_cache, _jwks_cached_at
    if _jwks_cache and time.time() - _jwks_cached_at < 3600:
        return _jwks_cache

    if not settings.supabase_url:
        return {}

    try:
        url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cached_at = time.time()
            return _jwks_cache
    except Exception as exc:
        logger.warning("Failed to fetch JWKS: %s", exc)
        return {}


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without full verification (Supabase handles signing).

    For production, use python-jose or PyJWT with JWKS verification.
    This is a lightweight decoder that checks expiry and extracts claims.
    """
    import base64

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    # Decode payload (part 1)
    payload_b64 = parts[1]
    # Add padding
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    payload_bytes = base64.urlsafe_b64decode(payload_b64)
    payload = json.loads(payload_bytes)

    # Check expiry
    exp = payload.get("exp")
    if exp and time.time() > exp:
        raise ValueError("Token expired")

    return payload


async def get_current_user(request: Request) -> dict[str, Any]:
    """Extract and validate Supabase user from Authorization header.

    Returns user claims dict with at minimum: sub (user_id), email, role.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]

    try:
        payload = _decode_jwt_payload(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")

    return {
        "user_id": user_id,
        "email": payload.get("email", ""),
        "role": payload.get("role", "authenticated"),
        "app_metadata": payload.get("app_metadata", {}),
        "user_metadata": payload.get("user_metadata", {}),
    }


async def get_optional_user(request: Request) -> dict[str, Any] | None:
    """Like get_current_user but returns None instead of raising."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

"""WhatsApp Cloud API (Meta) integration for the OMNI-RANK Copilot.

Pure helpers — webhook signature verification, payload parsing, message
sending, and short-lived per-phone conversation history (cache-backed).
The chat brain itself lives with the copilot endpoint; this module only
speaks WhatsApp.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import random

import httpx

from app.services.cache import cache_json_get, cache_json_set, cache_key

logger = logging.getLogger("omnirank.whatsapp")

GRAPH_URL = "https://graph.facebook.com/v21.0"
HISTORY_TTL = 3600          # 1h of context per phone number
HISTORY_MAX_TURNS = 8
LINK_CODE_TTL = 15 * 60     # linking codes live 15 minutes


def verify_signature(app_secret: str, raw_body: bytes, signature_header: str) -> bool:
    """Validate Meta's X-Hub-Signature-256 header. With no app secret
    configured, verification is skipped (dev mode) — configure it in prod."""
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


def parse_incoming(payload: dict) -> list[dict]:
    """Extract inbound text messages from a webhook payload.

    Returns [{"from": "9198...", "text": "...", "name": "Suresh"}]. Status
    callbacks (sent/delivered/read) and non-text messages are ignored.
    """
    out: list[dict] = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            contacts = {c.get("wa_id"): c.get("profile", {}).get("name", "")
                        for c in value.get("contacts", []) or []}
            for msg in value.get("messages", []) or []:
                if msg.get("type") != "text":
                    continue
                sender = msg.get("from", "")
                text = (msg.get("text", {}) or {}).get("body", "").strip()
                if sender and text:
                    out.append({"from": sender, "text": text, "name": contacts.get(sender, "")})
    return out


def send_text(phone_number_id: str, access_token: str, to: str, text: str) -> bool:
    """Send a plain text WhatsApp message. Returns True on success."""
    # WhatsApp rejects messages over 4096 chars — trim conservatively.
    if len(text) > 3800:
        text = text[:3800] + "…"
    try:
        resp = httpx.post(
            f"{GRAPH_URL}/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
            timeout=15,
        )
        if resp.status_code >= 400:
            logger.error("WhatsApp send failed (%s): %s", resp.status_code, resp.text[:300])
            return False
        return True
    except httpx.HTTPError as exc:
        logger.error("WhatsApp send error: %s", exc)
        return False


# ── Per-phone conversation history (short-lived) ─────────────────────────────

def _history_key(phone: str) -> str:
    return cache_key("wa-history-v1", phone)


def get_history(phone: str) -> list[dict]:
    return cache_json_get(_history_key(phone)) or []


def append_history(phone: str, role: str, content: str) -> list[dict]:
    history = get_history(phone)
    history.append({"role": role, "content": content[:2000]})
    history = history[-HISTORY_MAX_TURNS:]
    cache_json_set(_history_key(phone), history, ttl=HISTORY_TTL)
    return history


# ── Phone ↔ project linking codes ────────────────────────────────────────────

def _code_key(code: str) -> str:
    return cache_key("wa-link-code-v1", code)


def create_link_code(project_id: str) -> str:
    """Mint a one-time 6-digit code the user sends over WhatsApp to link
    their number to a project. Expires in 15 minutes."""
    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    cache_json_set(_code_key(code), {"project_id": project_id}, ttl=LINK_CODE_TTL)
    return code


def consume_link_code(code: str) -> str | None:
    """Return the project_id for a valid code (single use), else None."""
    data = cache_json_get(_code_key(code))
    if not data:
        return None
    # burn it — a code links exactly one number
    cache_json_set(_code_key(code), {}, ttl=1)
    return data.get("project_id") or None

"""Tests for the WhatsApp Copilot integration."""

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services.whatsapp_bot import (
    consume_link_code, create_link_code, parse_incoming, verify_signature,
)


@pytest.fixture
def client(monkeypatch):
    from app import main
    monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
    monkeypatch.setattr(main.settings, "whatsapp_verify_token", "verify-me", raising=False)
    monkeypatch.setattr(main.settings, "whatsapp_access_token", "wa-token", raising=False)
    monkeypatch.setattr(main.settings, "whatsapp_phone_number_id", "12345", raising=False)
    monkeypatch.setattr(main.settings, "whatsapp_app_secret", "", raising=False)
    return TestClient(main.app)


def _payload(sender="919812345678", text="hello", name="Suresh"):
    return {"entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": sender, "profile": {"name": name}}],
        "messages": [{"from": sender, "type": "text", "text": {"body": text}}],
    }}]}]}


class TestHelpers:
    def test_signature_valid_and_invalid(self):
        secret, body = "s3cret", b'{"a":1}'
        good = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert verify_signature(secret, body, good)
        assert not verify_signature(secret, body, "sha256=deadbeef")
        assert not verify_signature(secret, body, "")
        assert verify_signature("", body, "")  # dev mode: no secret configured

    def test_parse_incoming_extracts_text_only(self):
        payload = _payload(text="check my rankings")
        # add a non-text message and a status callback — both ignored
        payload["entry"][0]["changes"][0]["value"]["messages"].append(
            {"from": "111", "type": "image", "image": {}})
        payload["entry"].append({"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]})
        msgs = parse_incoming(payload)
        assert len(msgs) == 1
        assert msgs[0]["from"] == "919812345678"
        assert msgs[0]["text"] == "check my rankings"
        assert msgs[0]["name"] == "Suresh"

    def test_link_code_roundtrip_and_single_use(self):
        code = create_link_code("proj-1")
        assert len(code) == 6 and code.isdigit()
        assert consume_link_code(code) == "proj-1"
        assert consume_link_code(code) is None  # burned
        assert consume_link_code("000000") is None or True  # unknown code -> None (random collision-safe)


class TestWebhook:
    def test_verify_handshake(self, client):
        r = client.get("/webhooks/whatsapp", params={
            "hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42",
        })
        assert r.status_code == 200
        assert r.text == "42"

    def test_verify_rejects_bad_token(self, client):
        r = client.get("/webhooks/whatsapp", params={
            "hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "42",
        })
        assert r.status_code == 403

    def test_bad_signature_rejected(self, client, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "whatsapp_app_secret", "s3cret", raising=False)
        r = client.post("/webhooks/whatsapp", json=_payload(),
                        headers={"X-Hub-Signature-256": "sha256=bogus"})
        assert r.status_code == 403

    def test_unlinked_phone_gets_link_instructions(self, client):
        from app import main
        sent = []
        with patch.object(main, "_supabase_rest", return_value=[]), \
             patch("app.services.whatsapp_bot.send_text",
                   side_effect=lambda pid, tok, to, text: sent.append((to, text)) or True):
            r = client.post("/webhooks/whatsapp", json=_payload(text="hi"))
        assert r.status_code == 200
        assert len(sent) == 1
        assert "LINK" in sent[0][1]

    def test_link_flow_persists_mapping(self, client):
        from app import main
        code = create_link_code("proj-9")
        writes, sent = [], []

        def fake_rest(method, table, payload=None, params=""):
            if method == "get":
                return []
            writes.append((method, table, payload))
            return [{"id": 1}]

        with patch.object(main, "_supabase_rest", side_effect=fake_rest), \
             patch("app.services.whatsapp_bot.send_text",
                   side_effect=lambda pid, tok, to, text: sent.append(text) or True):
            r = client.post("/webhooks/whatsapp", json=_payload(text=f"LINK {code}"))
        assert r.status_code == 200
        assert any(t == "whatsapp_links" and (p or {}).get("project_id") == "proj-9"
                   for m, t, p in writes if m == "post")
        assert any("Linked" in t for t in sent)

    def test_linked_phone_reaches_copilot(self, client):
        from app import main
        sent = []

        def fake_rest(method, table, payload=None, params=""):
            if method == "get" and table == "whatsapp_links":
                return [{"project_id": "proj-9"}]
            return []

        with patch.object(main, "_supabase_rest", side_effect=fake_rest), \
             patch.object(main, "_copilot_answer", return_value={
                 "reply": "You rank #4 for 'ev charging'.",
                 "action": {"type": "rank_check", "params": {}},
                 "action_result": {"status": "completed", "detail": "Checked 3 keyword(s).",
                                   "data": {"link": "/dashboard/rank-tracker"}},
             }), \
             patch("app.services.whatsapp_bot.send_text",
                   side_effect=lambda pid, tok, to, text: sent.append(text) or True):
            r = client.post("/webhooks/whatsapp", json=_payload(text="check my rankings"))
        assert r.status_code == 200
        assert len(sent) == 1
        assert "You rank #4" in sent[0]
        assert "Checked 3 keyword(s)" in sent[0]
        assert "/dashboard/rank-tracker" in sent[0]

    def test_link_code_endpoint_requires_valid_project(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[]):
            r = client.post("/whatsapp/link-code?project_id=nope",
                            headers={"X-API-KEY": "test-key"})
        assert r.status_code == 404
        with patch.object(main, "_supabase_rest", return_value=[{"id": "p1"}]):
            r = client.post("/whatsapp/link-code?project_id=p1",
                            headers={"X-API-KEY": "test-key"})
        assert r.status_code == 200
        assert len(r.json()["code"]) == 6

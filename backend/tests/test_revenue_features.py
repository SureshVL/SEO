"""Tests for revenue features: plan budgets, Stripe signatures, wins, git PRs, LLM router."""

import hashlib
import hmac
import inspect
import json
import time

from unittest.mock import patch

from app.services.billing import PLANS, crawl_budget_for, StripeClient, stripe_price_id_for


class TestCrawlBudgets:
    def test_unpaid_gets_trial_cap(self):
        assert crawl_budget_for(None, None) == 25
        assert crawl_budget_for("agency", "trialing") == 25
        assert crawl_budget_for("agency", "past_due") == 25
        assert crawl_budget_for("agency", "cancelled") == 25

    def test_paid_tiers_unlock_depth(self):
        assert crawl_budget_for("starter", "active") == 100
        assert crawl_budget_for("growth", "active") == 1000
        assert crawl_budget_for("agency", "active") == 5000
        assert crawl_budget_for("enterprise", "active") == 10000

    def test_all_plans_have_usd_pricing(self):
        for plan_id, plan in PLANS.items():
            if plan_id == "free":
                assert plan.get("price_usd") == 0
            else:
                assert plan.get("price_usd"), "international pricing missing"


class TestStripeWebhookSignature:
    SECRET = "whsec_testsecret"

    def _sign(self, body: bytes, ts: int) -> str:
        sig = hmac.new(self.SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_valid_signature_accepted(self):
        body = json.dumps({"type": "invoice.paid"}).encode()
        header = self._sign(body, int(time.time()))
        assert StripeClient.verify_webhook_signature(body, header, self.SECRET) is True

    def test_tampered_signature_rejected(self):
        body = b"{}"
        header = f"t={int(time.time())},v1=deadbeef"
        assert StripeClient.verify_webhook_signature(body, header, self.SECRET) is False

    def test_wrong_secret_rejected(self):
        body = b"{}"
        header = self._sign(body, int(time.time()))
        assert StripeClient.verify_webhook_signature(body, header, "whsec_other") is False

    def test_expired_timestamp_rejected(self):
        body = b"{}"
        header = self._sign(body, int(time.time()) - 9999)
        assert StripeClient.verify_webhook_signature(body, header, self.SECRET) is False

    def test_missing_header_rejected(self):
        assert StripeClient.verify_webhook_signature(b"{}", "", self.SECRET) is False

    def test_price_id_lookup_unconfigured(self):
        assert stripe_price_id_for("nonexistent") == ""


class TestWinsService:
    def test_compute_wins_prices_agency_value(self):
        from app.services.wins_service import WinsService

        def fake_db(method, table, payload=None, params=""):
            counts = {"audit_runs": 2, "audit_issues": 5,
                      "bulk_content_articles": 3, "internal_link_opportunities": 4}
            return [{"id": i} for i in range(counts.get(table, 0))]

        wins = WinsService().compute_wins("proj-1", days=7, db_fn=fake_db)
        assert wins["total_actions"] > 0
        assert wins["value_inr"] > 0
        assert wins["value_usd"] == round(wins["value_inr"] / 84)

    def test_no_db_returns_empty(self):
        from app.services.wins_service import WinsService
        assert WinsService().compute_wins("proj-1", days=7, db_fn=None) == {}


class TestGitWriteback:
    def test_open_fix_pr_flow(self):
        from app.services.git_writeback_service import GitWritebackService, GitHubClient

        conn = {"id": "c1", "repo_owner": "acme", "repo_name": "site",
                "base_branch": "main", "access_token": "ghp_x", "enabled": True}
        stored = {}

        def fake_db(method, path, payload=None, params=""):
            if method == "get" and path == "git_connections":
                return [conn]
            if method == "post" and path == "git_pull_requests":
                stored["pr"] = payload
                return [payload]
            return []

        with patch.object(GitHubClient, "get_branch_sha", lambda s, o, r, b: "sha1"), \
             patch.object(GitHubClient, "create_branch", lambda s, o, r, br, sha: None), \
             patch.object(GitHubClient, "get_file_sha", lambda s, o, r, p, ref: None if "new" in p else "old"), \
             patch.object(GitHubClient, "put_file", lambda s, o, r, p, c, message, branch, sha=None: None), \
             patch.object(GitHubClient, "create_pull_request",
                          lambda s, o, r, t, b, head, base: {"number": 7, "html_url": "https://gh/pr/7"}):
            result = GitWritebackService().open_fix_pr(
                "proj", "c1", "Add schema", "desc", "schema",
                [{"path": "src/new-file.tsx", "content": "x"},
                 {"path": "src/existing.tsx", "content": "y"}],
                fake_db,
            )

        assert result["pr_number"] == 7
        assert result["branch"].startswith("omnirank/schema-")
        actions = {f["path"]: f["action"] for f in result["files"]}
        assert actions["src/new-file.tsx"] == "create"
        assert actions["src/existing.tsx"] == "update"
        assert stored["pr"]["status"] == "open"

    def test_validation_guards(self):
        import pytest
        from app.services.git_writeback_service import GitWritebackService

        def fake_db(method, path, payload=None, params=""):
            return [{"id": "c1", "enabled": True, "repo_owner": "a",
                     "repo_name": "b", "base_branch": "main", "access_token": "t"}]

        svc = GitWritebackService()
        with pytest.raises(ValueError):
            svc.open_fix_pr("p", "c1", "t", "", "bad_type", [{"path": "a", "content": "x"}], fake_db)
        with pytest.raises(ValueError):
            svc.open_fix_pr("p", "c1", "t", "", "schema", [], fake_db)
        with pytest.raises(ValueError):
            svc.open_fix_pr("p", "c1", "t", "", "schema", [{"path": "", "content": "x"}], fake_db)

    def test_tokens_never_leak(self):
        from app.services.git_writeback_service import GitWritebackService

        def fake_db(method, path, payload=None, params=""):
            return [{"id": "c1", "repo_owner": "a", "repo_name": "b",
                     "access_token": "SECRET", "enabled": True}]

        conns = GitWritebackService().get_connections("p", fake_db)
        assert conns and "access_token" not in conns[0]


class TestLLMRouter:
    def test_agenerate_text_exists_and_async(self):
        from app.clients.llm import llm_client
        assert hasattr(llm_client, "agenerate_text")
        assert inspect.iscoroutinefunction(llm_client.agenerate_text)

    def test_model_family_guard(self):
        from app.clients.llm import LLMClient
        # claude models only forwarded to claude, never to gemini/groq
        assert LLMClient._model_for_provider("claude", "claude-opus-4-8") == "claude-opus-4-8"
        assert LLMClient._model_for_provider("gemini", "claude-opus-4-8") is None
        assert LLMClient._model_for_provider("groq", "claude-opus-4-8") is None
        assert LLMClient._model_for_provider("gemini", "gemini-2.0-flash") == "gemini-2.0-flash"
        assert LLMClient._model_for_provider("claude", None) is None

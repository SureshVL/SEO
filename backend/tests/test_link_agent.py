"""Tests for LinkAgent (backlinks + outreach drafting) and routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.link_agent import (
    LinkAgent,
    OutreachEmail,
    BacklinkReport,
)


# ── Utilities ────────────────────────────────────────────────────────────────

class TestDomainNormalization:
    def test_strips_protocol(self):
        assert LinkAgent._normalize_domain("https://acme.com/foo") == "acme.com"
        assert LinkAgent._normalize_domain("HTTP://Acme.com") == "acme.com"

    def test_passthrough(self):
        assert LinkAgent._normalize_domain("acme.com") == "acme.com"
        assert LinkAgent._normalize_domain("") == ""

    def test_strips_trailing_slash(self):
        assert LinkAgent._normalize_domain("acme.com/") == "acme.com"


class TestProspectScoring:
    def test_high_dr_with_email_scores_highest(self):
        s = LinkAgent.score_prospect({
            "domain_rating": 90,
            "referring_domains": 5000,
            "contact_email": "x@y.com",
            "already_linking": False,
        })
        # 0.6*90 + 15 (referring cap) + 15 (email) = 84
        assert s == pytest.approx(84.0, abs=0.5)

    def test_already_linking_penalty(self):
        s = LinkAgent.score_prospect({
            "domain_rating": 50, "already_linking": True,
        })
        # 0.6*50 + 0 - 40 = -10 → clamped to 0
        assert s == 0.0

    def test_missing_fields_defaults_to_zero(self):
        assert LinkAgent.score_prospect({}) == 0.0

    def test_never_exceeds_100(self):
        s = LinkAgent.score_prospect({
            "domain_rating": 100, "referring_domains": 99999, "contact_email": "a@b.com",
        })
        assert s <= 100.0


# ── Backlink profile ─────────────────────────────────────────────────────────

class TestBacklinkProfile:
    def test_no_dataforseo_returns_empty_with_warning(self):
        agent = LinkAgent(dataforseo_client=None)
        report = agent.backlink_profile("acme.com")
        assert isinstance(report, BacklinkReport)
        assert report.domain == "acme.com"
        assert report.total_backlinks == 0
        assert any("DataForSEO" in w for w in report.warnings)

    def test_happy_path_merges_summary_anchors_referring(self):
        dfs = MagicMock()
        summary = MagicMock()
        summary.total_backlinks = 500
        summary.referring_domains = 120
        summary.domain_rank = 67
        summary.dofollow_ratio = 88.5
        dfs.backlink_summary.return_value = summary
        dfs.backlink_anchors.return_value = [
            {"anchor": "seo tools", "backlinks": 50, "referring_domains": 20, "dofollow": True},
        ]
        dfs.backlink_referring_domains.return_value = [
            {"domain": "moz.com", "rank": 92, "backlinks": 10, "dofollow": True},
        ]
        agent = LinkAgent(dataforseo_client=dfs)
        report = agent.backlink_profile("acme.com")
        assert report.total_backlinks == 500
        assert report.referring_domains == 120
        assert report.domain_rank == 67
        assert report.dofollow_ratio == 88.5
        assert report.top_anchors[0]["anchor"] == "seo tools"
        assert report.top_referring[0]["domain"] == "moz.com"
        assert report.warnings == []

    def test_anchors_failure_adds_warning_but_returns_rest(self):
        dfs = MagicMock()
        summary = MagicMock()
        summary.total_backlinks = 100
        summary.referring_domains = 5
        summary.domain_rank = 10
        summary.dofollow_ratio = 80.0
        dfs.backlink_summary.return_value = summary
        dfs.backlink_anchors.side_effect = RuntimeError("quota hit")
        dfs.backlink_referring_domains.return_value = []
        agent = LinkAgent(dataforseo_client=dfs)
        report = agent.backlink_profile("acme.com")
        assert report.total_backlinks == 100
        assert any("Anchors" in w for w in report.warnings)


# ── Outreach drafting ────────────────────────────────────────────────────────

class TestOutreachDraft:
    def test_fallback_intro(self):
        agent = LinkAgent()  # no claude
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com", "contact_name": "Jamie"},
            campaign={"sender_name": "Alex", "sender_site": "acme.com",
                      "value_prop": "we publish data-driven SEO studies"},
            template="intro",
        )
        assert email.fallback is True
        assert "Jamie" in email.body
        assert "moz.com" in email.body
        assert "Alex" in email.body
        assert email.template == "intro"

    def test_fallback_broken_link_uses_broken_url(self):
        agent = LinkAgent()
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"},
            campaign={"broken_url": "https://moz.com/old-page", "target_url": "https://acme.com/new"},
            template="broken_link",
        )
        assert "moz.com/old-page" in email.body
        assert "Broken link" in email.subject

    def test_fallback_guest_post(self):
        agent = LinkAgent()
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"},
            campaign={"value_prop": "we publish SEO research"},
            template="guest_post",
        )
        assert "Guest post" in email.subject
        assert "SEO research" in email.body

    def test_fallback_resource_page(self):
        agent = LinkAgent()
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"},
            campaign={"target_url": "https://acme.com/guide"},
            template="resource_page",
        )
        assert "resources page" in email.subject.lower() or "resources" in email.body.lower()
        assert "acme.com/guide" in email.body

    def test_invalid_template_falls_back_to_intro(self):
        agent = LinkAgent()
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"},
            campaign={},
            template="bogus",
        )
        assert email.template == "intro"

    def test_claude_success_uses_ai_output(self):
        claude = MagicMock()
        claude.complete_json.return_value = (
            {"subject": "Ai-crafted subject", "body": "Ai-crafted body text"},
            MagicMock(model="claude-haiku-4-5", cost_usd=0.003,
                      input_tokens=10, output_tokens=20, cached=False),
        )
        agent = LinkAgent(claude_client=claude)
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"}, campaign={}, template="intro",
        )
        assert email.subject == "Ai-crafted subject"
        assert email.body == "Ai-crafted body text"
        assert email.fallback is False
        assert email.cost_usd == 0.003

    def test_claude_exception_falls_back(self):
        claude = MagicMock()
        claude.complete_json.side_effect = RuntimeError("rate limited")
        agent = LinkAgent(claude_client=claude)
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"}, campaign={}, template="intro",
        )
        assert email.fallback is True

    def test_claude_empty_body_falls_back(self):
        claude = MagicMock()
        claude.complete_json.return_value = (
            {"subject": "Hello", "body": ""},
            MagicMock(model="haiku", cost_usd=0.0,
                      input_tokens=0, output_tokens=0, cached=False),
        )
        agent = LinkAgent(claude_client=claude)
        email = agent.draft_outreach_email(
            prospect={"domain": "moz.com"}, campaign={}, template="intro",
        )
        assert email.fallback is True


# ── Route integration ────────────────────────────────────────────────────────

class TestLinkRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_backlinks_route(self, client):
        from app import main
        fake_agent = MagicMock()
        fake_report = BacklinkReport(
            domain="acme.com",
            total_backlinks=42, referring_domains=8,
            domain_rank=55, dofollow_ratio=80.0,
            top_anchors=[{"anchor": "hi", "backlinks": 1, "referring_domains": 1, "dofollow": True}],
            top_referring=[{"domain": "moz.com", "rank": 90, "backlinks": 2, "dofollow": True}],
        )
        fake_agent.backlink_profile.return_value = fake_report

        with patch.object(main, "_build_link_agent", return_value=fake_agent):
            r = client.post(
                "/links/backlinks",
                headers={"X-API-KEY": "test-key"},
                json={"domain": "acme.com"},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["domain"] == "acme.com"
        assert body["total_backlinks"] == 42
        assert body["top_anchors"][0]["anchor"] == "hi"

    def test_outreach_draft_route(self, client):
        from app import main
        fake_agent = MagicMock()
        fake_agent.draft_outreach_email.return_value = OutreachEmail(
            subject="Hello", body="World", template="intro", model_used="haiku",
            cost_usd=0.001, fallback=False,
        )
        with patch.object(main, "_build_link_agent", return_value=fake_agent):
            r = client.post(
                "/links/outreach/draft",
                headers={"X-API-KEY": "test-key"},
                json={
                    "prospect": {"domain": "moz.com"},
                    "campaign": {"sender_name": "Alex"},
                    "template": "intro",
                },
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["subject"] == "Hello"
        assert body["body"] == "World"
        assert body["fallback"] is False

    def test_outreach_template_validation(self, client):
        r = client.post(
            "/links/outreach/draft",
            headers={"X-API-KEY": "test-key"},
            json={"prospect": {"domain": "x.com"}, "template": "garbage"},
        )
        assert r.status_code == 422

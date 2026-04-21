"""Tests for full-site crawl audit: DataForSEO on-page parsing + TechnicalAgent + API."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.technical_agent import (
    SiteCrawlResult,
    TechnicalAction,
    TechnicalAgent,
)
from app.clients.dataforseo_client import DataForSEOClient


# ── Sample DataForSEO responses ────────────────────────────────────────────────

SUMMARY_FINISHED = {
    "tasks": [
        {
            "result": [
                {
                    "crawl_progress": "finished",
                    "pages_crawled": 47,
                    "crawl_status": {"pages_in_queue": 0, "max_crawl_pages": 100},
                    "page_metrics": {
                        "onpage_score": 86.4,
                        "links_internal": 412,
                        "links_external": 28,
                        "checks": {
                            "duplicate_title": 3,
                            "duplicate_description": 5,
                            "no_h1_tag": 2,
                            "is_broken": 4,
                            "no_image_alt": 11,
                            "no_canonical": 1,
                            "high_loading_time": 2,
                            "is_5xx_code": 0,
                        },
                    },
                }
            ]
        }
    ],
    "status_code": 20000,
}

SUMMARY_IN_PROGRESS = {
    "tasks": [
        {
            "result": [
                {
                    "crawl_progress": {
                        "pages_crawled": 10,
                        "pages_in_queue": 40,
                        "max_crawl_pages": 50,
                    },
                    "page_metrics": {"checks": {}},
                }
            ]
        }
    ],
    "status_code": 20000,
}


def _make_agent_with_client(client: DataForSEOClient) -> TechnicalAgent:
    return TechnicalAgent(claude_client=None, dataforseo_client=client)


# ── TechnicalAgent parsing ─────────────────────────────────────────────────────

class TestActionsFromChecks:
    def test_empty_checks_produces_no_actions(self):
        agent = TechnicalAgent()
        assert agent._actions_from_checks({}, pages_crawled=50) == []

    def test_zero_count_checks_are_dropped(self):
        agent = TechnicalAgent()
        out = agent._actions_from_checks({"no_h1_tag": 0, "duplicate_title": 0}, 50)
        assert out == []

    def test_actions_have_readable_labels_and_severity(self):
        agent = TechnicalAgent()
        out = agent._actions_from_checks(
            {"is_5xx_code": 2, "duplicate_title": 4, "no_image_alt": 10}, 40
        )
        labels = {a.category for a in out}
        assert "crawl_errors" in labels
        assert "metadata" in labels
        # critical (5xx) comes before high (duplicate_title) comes before medium (alt)
        assert out[0].impact == "critical"
        assert out[-1].impact == "medium"

    def test_auto_fixable_flag_set_for_metadata_checks(self):
        agent = TechnicalAgent()
        out = agent._actions_from_checks({"no_h1_tag": 3}, 30)
        assert len(out) == 1
        assert out[0].auto_fixable is True

    def test_unknown_check_still_produces_action(self):
        agent = TechnicalAgent()
        out = agent._actions_from_checks({"totally_new_check": 2}, 10)
        assert len(out) == 1
        assert out[0].category == "technical"


class TestFetchSiteCrawl:
    def test_no_credentials_returns_failed(self):
        agent = TechnicalAgent(dataforseo_client=DataForSEOClient("", ""))
        out = agent.fetch_site_crawl("task123", domain="example.com")
        assert out.status == "failed"
        assert "credentials" in (out.error or "").lower()

    def test_in_progress_summary_yields_crawling_status(self):
        client = DataForSEOClient("u", "p")
        with patch("httpx.Client") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.json.return_value = SUMMARY_IN_PROGRESS
            mock_httpx.return_value.__enter__.return_value.get.return_value = mock_resp
            agent = _make_agent_with_client(client)
            out = agent.fetch_site_crawl("abc", domain="example.com", include_samples=False)
        assert out.status == "crawling"
        assert out.pages_in_queue == 40

    def test_finished_summary_parses_metrics_and_actions(self):
        client = DataForSEOClient("u", "p")
        with patch("httpx.Client") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.json.return_value = SUMMARY_FINISHED
            mock_httpx.return_value.__enter__.return_value.get.return_value = mock_resp
            agent = _make_agent_with_client(client)
            out = agent.fetch_site_crawl("abc", domain="example.com", include_samples=False)
        assert out.status == "finished"
        assert out.pages_crawled == 47
        assert out.onpage_score == 86.4
        assert out.issues_by_check["duplicate_title"] == 3
        assert out.issues_by_check["is_broken"] == 4
        # zero-count checks must not appear
        assert "is_5xx_code" not in out.issues_by_check
        assert len(out.actions) >= 3
        # highest severity (broken links) should be first
        assert out.actions[0].impact == "critical"


class TestStartSiteCrawl:
    def test_no_credentials_returns_failed(self):
        agent = TechnicalAgent(dataforseo_client=DataForSEOClient("", ""))
        out = agent.start_site_crawl("example.com", max_pages=20)
        assert out.status == "failed"

    def test_task_post_failure_captured(self):
        client = DataForSEOClient("u", "p")
        client.onpage_audit = MagicMock(side_effect=RuntimeError("boom"))
        agent = _make_agent_with_client(client)
        out = agent.start_site_crawl("example.com")
        assert out.status == "failed"
        assert "boom" in (out.error or "")

    def test_happy_path_returns_task_id(self):
        client = DataForSEOClient("u", "p")
        client.onpage_audit = MagicMock(return_value="task-xyz")
        agent = _make_agent_with_client(client)
        out = agent.start_site_crawl("example.com", max_pages=50)
        assert out.status == "crawling"
        assert out.task_id == "task-xyz"
        assert out.max_crawl_pages == 50


# ── DataForSEO client parsing ──────────────────────────────────────────────────

class TestDataForSEOOnPage:
    def test_onpage_check_keys_constant(self):
        assert "duplicate_title" in DataForSEOClient.ONPAGE_CHECK_KEYS
        assert "is_broken" in DataForSEOClient.ONPAGE_CHECK_KEYS

    def test_onpage_summary_reads_checks_and_score(self):
        client = DataForSEOClient("u", "p")
        with patch("httpx.Client") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.json.return_value = SUMMARY_FINISHED
            mock_httpx.return_value.__enter__.return_value.get.return_value = mock_resp
            out = client.onpage_summary("task")
        assert out["pages_crawled"] == 47
        assert out["page_metrics"]["onpage_score"] == 86.4
        assert out["checks"]["duplicate_title"] == 3


# ── FastAPI route integration ──────────────────────────────────────────────────

class TestCrawlAuditRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "dataforseo_login", "u", raising=False)
        monkeypatch.setattr(main.settings, "dataforseo_password", "p", raising=False)
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_missing_credentials_returns_400(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "dataforseo_login", "", raising=False)
        monkeypatch.setattr(main.settings, "dataforseo_password", "", raising=False)
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        c = TestClient(main.app)
        r = c.post("/audit/crawl?domain=example.com", headers={"X-API-KEY": "test-key"})
        assert r.status_code == 400
        assert "DATAFORSEO" in r.text

    def test_max_pages_bounds_enforced(self, client):
        r = client.post(
            "/audit/crawl?domain=example.com&max_pages=5000",
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 400

    def test_start_crawl_returns_task_id(self, client, monkeypatch):
        mock_result = SiteCrawlResult(
            domain="example.com",
            task_id="t1",
            status="crawling",
            max_crawl_pages=50,
        )
        from app import main
        fake_agent = MagicMock()
        fake_agent.start_site_crawl.return_value = mock_result
        monkeypatch.setattr(main, "_build_technical_agent", lambda: fake_agent)

        r = client.post(
            "/audit/crawl?domain=example.com&max_pages=50",
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["task_id"] == "t1"
        assert body["status"] == "crawling"
        assert body["actions"] == []

    def test_get_crawl_returns_serialized_result(self, client, monkeypatch):
        mock_result = SiteCrawlResult(
            domain="example.com",
            task_id="t1",
            status="finished",
            pages_crawled=20,
            onpage_score=91.0,
            issues_by_check={"duplicate_title": 2},
            actions=[
                TechnicalAction(
                    category="metadata",
                    action="Duplicate title tags — 2 page(s)",
                    impact="high",
                )
            ],
        )
        from app import main
        fake_agent = MagicMock()
        fake_agent.fetch_site_crawl.return_value = mock_result
        monkeypatch.setattr(main, "_build_technical_agent", lambda: fake_agent)

        r = client.get(
            "/audit/crawl/t1?domain=example.com",
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "finished"
        assert body["onpage_score"] == 91.0
        assert body["actions"][0]["impact"] == "high"

"""Tests for AI visibility (GEO) tracking: DataForSEO AI endpoints, agent scoring, routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.ai_visibility_agent import (
    AIVisibilityAgent,
    AIVisibilityReport,
    KeywordVisibility,
)
from app.clients.dataforseo_client import DataForSEOClient


# ── Sample responses ───────────────────────────────────────────────────────────

SERP_WITH_AI_OVERVIEW = {
    "tasks": [
        {
            "result": [
                {
                    "items": [
                        {
                            "type": "ai_overview",
                            "items": [
                                {"text": "For SEO tools, consider these options."},
                                {"title": "Recommendations"},
                            ],
                            "references": [
                                {"domain": "ahrefs.com", "url": "https://ahrefs.com/", "title": "Ahrefs"},
                                {"domain": "www.example.com", "url": "https://example.com/seo", "title": "Example SEO"},
                                {"domain": "semrush.com", "url": "https://semrush.com/", "title": "Semrush"},
                            ],
                        },
                        {"type": "organic", "url": "https://x.com", "domain": "x.com"},
                    ]
                }
            ]
        }
    ],
    "status_code": 20000,
    "cost": 0.002,
}

SERP_WITHOUT_AI_OVERVIEW = {
    "tasks": [
        {
            "result": [
                {
                    "items": [
                        {"type": "organic", "url": "https://a.com", "domain": "a.com"},
                    ]
                }
            ]
        }
    ],
    "status_code": 20000,
    "cost": 0.002,
}

LLM_RESPONSE_WITH_CITATION = {
    "tasks": [
        {
            "result": [
                {
                    "items": [
                        {
                            "response_text": "Top picks include Example (example.com) and Ahrefs.",
                            "references": [
                                {"domain": "example.com", "url": "https://example.com", "title": "Example"},
                                {"domain": "ahrefs.com", "url": "https://ahrefs.com", "title": "Ahrefs"},
                            ],
                        }
                    ]
                }
            ]
        }
    ],
    "status_code": 20000,
    "cost": 0.001,
}

LLM_RESPONSE_TEXT_ONLY = {
    "tasks": [
        {
            "result": [
                {
                    "items": [
                        {
                            "response_text": "Consider visiting example.com for more info.",
                            "references": [],
                        }
                    ]
                }
            ]
        }
    ],
    "status_code": 20000,
    "cost": 0.001,
}

LLM_RESPONSE_NO_MENTION = {
    "tasks": [
        {
            "result": [
                {
                    "items": [
                        {
                            "response_text": "Try ahrefs or semrush.",
                            "references": [{"domain": "ahrefs.com", "url": "https://ahrefs.com"}],
                        }
                    ]
                }
            ]
        }
    ],
    "status_code": 20000,
    "cost": 0.001,
}


# ── DataForSEO client: AI endpoints ────────────────────────────────────────────

class TestDataForSEOAIOverview:
    def test_extract_domain_strips_protocol_and_www(self):
        assert DataForSEOClient._extract_domain("https://www.Example.com/path") == "example.com"
        assert DataForSEOClient._extract_domain("") == ""
        assert DataForSEOClient._extract_domain("foo.bar") == "foo.bar"

    def test_ai_overview_present_and_cited(self):
        client = DataForSEOClient("u", "p")
        with patch.object(client, "_post", return_value=SERP_WITH_AI_OVERVIEW):
            out = client.ai_overview_for_keyword("seo tools", domain="example.com")
        assert out["present"] is True
        assert out["domain_cited"] is True
        assert out["domain_position"] == 2
        assert "Ahrefs" in [c["title"] for c in out["citations"]]
        assert out["snippet"].startswith("For SEO tools")

    def test_ai_overview_present_but_not_cited(self):
        client = DataForSEOClient("u", "p")
        with patch.object(client, "_post", return_value=SERP_WITH_AI_OVERVIEW):
            out = client.ai_overview_for_keyword("seo tools", domain="unrelated.com")
        assert out["present"] is True
        assert out["domain_cited"] is False
        assert out["domain_position"] is None

    def test_ai_overview_absent(self):
        client = DataForSEOClient("u", "p")
        with patch.object(client, "_post", return_value=SERP_WITHOUT_AI_OVERVIEW):
            out = client.ai_overview_for_keyword("obscure query", domain="example.com")
        assert out["present"] is False
        assert out["citations"] == []


class TestDataForSEOLLMResponse:
    def test_rejects_unknown_model(self):
        client = DataForSEOClient("u", "p")
        with pytest.raises(ValueError):
            client.llm_response("test", model="unknown_llm")

    def test_parses_text_and_references(self):
        client = DataForSEOClient("u", "p")
        with patch.object(client, "_post", return_value=LLM_RESPONSE_WITH_CITATION):
            out = client.llm_response("best seo tools", model="chat_gpt")
        assert out["model"] == "chat_gpt"
        assert "Example" in out["text"]
        assert len(out["references"]) == 2
        assert out["references"][0]["domain"] == "example.com"

    def test_handles_error_from_upstream(self):
        client = DataForSEOClient("u", "p")
        with patch.object(client, "_post", side_effect=RuntimeError("boom")):
            out = client.llm_response("test", model="perplexity")
        assert out["text"] == ""
        assert out["error"] == "boom"


# ── Agent scoring & orchestration ──────────────────────────────────────────────

class TestAIVisibilityAgent:
    def _mk(self) -> AIVisibilityAgent:
        return AIVisibilityAgent(dataforseo_client=DataForSEOClient("u", "p"))

    def test_domain_mentioned_matches_word_boundary(self):
        assert AIVisibilityAgent._domain_mentioned(
            "visit example.com for info", "example.com"
        )
        assert AIVisibilityAgent._domain_mentioned(
            "Go to HTTPS://example.com/page", "example.com"
        )
        # substring matches should not false-positive
        assert not AIVisibilityAgent._domain_mentioned(
            "counterexample.com is different", "example.com"
        )
        assert not AIVisibilityAgent._domain_mentioned("", "example.com")
        assert not AIVisibilityAgent._domain_mentioned("hi", "")

    def test_domain_in_refs(self):
        refs = [{"domain": "a.com"}, {"domain": "example.com"}, {"domain": "b.com"}]
        assert AIVisibilityAgent._domain_in_refs(refs, "example.com") == 2
        assert AIVisibilityAgent._domain_in_refs(refs, "missing.com") is None

    def test_score_keyword_full_overview_and_all_llm_cited(self):
        kv = KeywordVisibility(
            keyword="x",
            ai_overview_present=True,
            ai_overview_cited=True,
            ai_overview_position=1,
            llm_results={
                "chat_gpt": {"mentioned": True, "citation_position": 1, "reference_count": 3, "snippet": ""},
                "perplexity": {"mentioned": True, "citation_position": 2, "reference_count": 2, "snippet": ""},
                "gemini": {"mentioned": True, "citation_position": 1, "reference_count": 5, "snippet": ""},
            },
        )
        score = AIVisibilityAgent._score_keyword(kv, ("chat_gpt", "perplexity", "gemini"))
        assert score == 80.0  # 40 overview + 40 LLM (full credit)

    def test_score_keyword_overview_present_uncited_no_llm(self):
        kv = KeywordVisibility(
            keyword="x",
            ai_overview_present=True,
            ai_overview_cited=False,
            llm_results={
                "chat_gpt": {"mentioned": False, "citation_position": None, "reference_count": 0, "snippet": ""},
            },
        )
        score = AIVisibilityAgent._score_keyword(kv, ("chat_gpt",))
        assert score == 10.0

    def test_score_keyword_text_mention_half_credit(self):
        kv = KeywordVisibility(
            keyword="x",
            llm_results={
                "chat_gpt": {"mentioned": True, "citation_position": None, "reference_count": 0, "snippet": ""},
                "perplexity": {"mentioned": False, "citation_position": None, "reference_count": 0, "snippet": ""},
            },
        )
        score = AIVisibilityAgent._score_keyword(kv, ("chat_gpt", "perplexity"))
        # 0.5 / 2 * 40 = 10
        assert score == 10.0

    def test_score_keyword_errors_excluded_from_avg(self):
        kv = KeywordVisibility(
            keyword="x",
            llm_results={
                "chat_gpt": {"mentioned": True, "citation_position": 1, "reference_count": 1, "snippet": "", "error": None},
                "perplexity": {"mentioned": False, "citation_position": None, "reference_count": 0, "snippet": "", "error": "timeout"},
            },
        )
        # Only chat_gpt counted — full credit / 1 * 40 = 40
        score = AIVisibilityAgent._score_keyword(kv, ("chat_gpt", "perplexity"))
        assert score == 40.0

    def test_run_aggregates_per_keyword_and_rates(self):
        agent = self._mk()

        def fake_ai_overview(kw, domain, **_):
            if kw == "cited":
                return {
                    "keyword": kw, "present": True, "snippet": "",
                    "citations": [], "domain_cited": True, "domain_position": 1,
                }
            return {
                "keyword": kw, "present": False, "snippet": "",
                "citations": [], "domain_cited": False, "domain_position": None,
            }

        def fake_llm(prompt, model, language_code="en"):
            if "cited" in prompt and model == "chat_gpt":
                return {
                    "model": model, "prompt": prompt,
                    "text": "Go to example.com for more.",
                    "references": [{"domain": "example.com", "url": "https://example.com"}],
                }
            return {"model": model, "prompt": prompt, "text": "no match", "references": []}

        agent.dfs.ai_overview_for_keyword = MagicMock(side_effect=fake_ai_overview)
        agent.dfs.llm_response = MagicMock(side_effect=fake_llm)

        report = agent.run(
            keywords=["cited", "missed"],
            domain="example.com",
            engines=("chat_gpt", "perplexity"),
        )

        assert report.total_keywords == 2
        assert report.ai_overview_coverage == 50.0
        assert report.ai_overview_citation_rate == 100.0  # 1 of 1 present, cited
        # chat_gpt: mentioned in "cited" keyword only → 50%
        assert report.llm_mention_rate["chat_gpt"] == 50.0
        assert report.llm_mention_rate["perplexity"] == 0.0
        assert report.keywords[0].visibility_score > report.keywords[1].visibility_score


# ── Route integration ─────────────────────────────────────────────────────────

class TestGeoRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "dataforseo_login", "u", raising=False)
        monkeypatch.setattr(main.settings, "dataforseo_password", "p", raising=False)
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_missing_creds_returns_400(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "dataforseo_login", "", raising=False)
        monkeypatch.setattr(main.settings, "dataforseo_password", "", raising=False)
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        c = TestClient(main.app)
        r = c.post(
            "/geo/check",
            json={"keywords": ["a"], "domain": "example.com"},
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 400

    def test_rejects_invalid_engines(self, client):
        r = client.post(
            "/geo/check",
            json={"keywords": ["a"], "domain": "example.com", "engines": ["bogus"]},
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 400

    def test_geo_check_returns_serialized_report(self, client, monkeypatch):
        from app import main

        fake_report = AIVisibilityReport(
            domain="example.com",
            total_keywords=1,
            engines=["chat_gpt"],
            overall_score=55.0,
            ai_overview_coverage=100.0,
            ai_overview_citation_rate=100.0,
            llm_mention_rate={"chat_gpt": 100.0},
            keywords=[
                KeywordVisibility(
                    keyword="test",
                    ai_overview_present=True,
                    ai_overview_cited=True,
                    ai_overview_position=1,
                    visibility_score=80.0,
                    llm_results={"chat_gpt": {"mentioned": True, "citation_position": 1, "reference_count": 1, "snippet": ""}},
                )
            ],
        )
        fake_agent = MagicMock()
        fake_agent.run.return_value = fake_report
        monkeypatch.setattr(main, "_build_ai_visibility_agent", lambda: fake_agent)

        r = client.post(
            "/geo/check",
            json={"keywords": ["test"], "domain": "example.com", "engines": ["chat_gpt"]},
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["overall_score"] == 55.0
        assert body["keywords"][0]["ai_overview_cited"] is True
        assert body["keywords"][0]["llm_results"]["chat_gpt"]["citation_position"] == 1

"""Phase 2 tests: dashboard wiring endpoints, API schema validation, report generation."""
import pytest
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timezone


# ── Supabase mock helper ──────────────────────────────────────────────────────
def _make_project(name="Test", url="https://test.com", pid=None):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": pid or str(uuid.uuid4()),
        "name": name,
        "client_url": url,
        "domain": None,
        "target_niche": None,
        "status": "active",
        "goal_keywords": [],
        "settings": {},
        "created_at": now,
        "updated_at": now,
    }


def _make_keyword(keyword="seo tools", pid=None, kid=None):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": kid or str(uuid.uuid4()),
        "project_id": pid or str(uuid.uuid4()),
        "keyword": keyword,
        "locale": "en-US",
        "target_region": "IN",
        "search_volume": None,
        "difficulty": None,
        "intent": None,
        "is_primary": False,
        "tags": [],
        "latest_position": None,
        "previous_position": None,
        "created_at": now,
        "updated_at": now,
    }


# ── Project schema tests ───────────────────────────────────────────────────────
class TestProjectSchema:
    def test_project_create_requires_name_and_url(self):
        from app.schemas.project import ProjectCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProjectCreate(name="", client_url="not-a-url")

    def test_project_create_valid(self):
        from app.schemas.project import ProjectCreate
        p = ProjectCreate(name="My Site", client_url="https://mysite.com")
        assert p.name == "My Site"

    def test_project_create_accepts_settings(self):
        from app.schemas.project import ProjectCreate
        p = ProjectCreate(
            name="Hyderabad Biz",
            client_url="https://hyd.com",
            settings={"city": "hyderabad", "business_type": "restaurant"},
        )
        assert p.settings["city"] == "hyderabad"

    def test_project_create_accepts_goal_keywords(self):
        from app.schemas.project import ProjectCreate
        p = ProjectCreate(
            name="KW Test",
            client_url="https://kwtest.com",
            goal_keywords=["seo tools", "rank tracker"],
        )
        assert len(p.goal_keywords) == 2

    def test_project_response_schema(self):
        from app.schemas.project import ProjectResponse
        now = datetime.now(timezone.utc)
        r = ProjectResponse(
            id="abc", name="Test", client_url="https://test.com",
            created_at=now, updated_at=now,
        )
        assert r.status == "active"


# ── Keyword schema tests ───────────────────────────────────────────────────────
class TestKeywordSchema:
    def test_keyword_create_minimal(self):
        from app.schemas.project import KeywordCreate
        k = KeywordCreate(keyword="seo tools india")
        assert k.target_region == "IN"

    def test_keyword_create_primary_flag(self):
        from app.schemas.project import KeywordCreate
        k = KeywordCreate(keyword="primary kw", is_primary=True)
        assert k.is_primary is True

    def test_keyword_response_positions(self):
        from app.schemas.project import KeywordResponse
        k = KeywordResponse(
            id="k1", keyword="test", locale="en-US", target_region="IN",
            latest_position=5, previous_position=12,
        )
        assert k.latest_position == 5
        assert k.previous_position == 12


# ── PDF report with keywords_with_ranks ───────────────────────────────────────
class TestPDFWithKeywordRanks:
    def test_multi_keyword_trend_table(self):
        from app.services.pdf_report import generate_seo_report_html
        kws = [
            {"keyword": "seo tools india", "current_rank": 7},
            {"keyword": "rank tracker india", "current_rank": 18},
            {"keyword": "keyword research tool", "current_rank": 35},
            {"keyword": "local seo hyderabad", "current_rank": 4},
        ]
        html = generate_seo_report_html(
            client_url="https://mysite.com",
            keyword="seo tools india",
            seo_score=74,
            competitors=[],
            gap_analysis={"missing_entities": []},
            recommendations=["[HIGH] Improve page speed -> +10 positions"],
            raw_metrics={"client_backlinks": {"total": 500, "referring_domains": 120, "domain_rank": 40}},
            keywords_with_ranks=kws,
            city="Hyderabad",
            business_type="SaaS / Tech",
        )
        for kw in kws:
            assert kw["keyword"] in html
        assert "Hyderabad" in html
        assert "SaaS" in html
        assert "Monthly Keyword Rankings" in html

    def test_report_has_print_button(self):
        from app.services.pdf_report import generate_seo_report_html
        html = generate_seo_report_html(
            client_url="https://example.com",
            keyword="test",
            seo_score=60,
            competitors=[],
            gap_analysis={},
            recommendations=[],
            raw_metrics={},
        )
        assert "window.print()" in html
        assert "Download as PDF" in html

    def test_recommendations_severity_colours(self):
        from app.services.pdf_report import generate_seo_report_html
        html = generate_seo_report_html(
            client_url="https://example.com",
            keyword="test",
            seo_score=45,
            competitors=[],
            gap_analysis={},
            recommendations=[
                "[CRITICAL] Fix broken links -> -30% crawl errors",
                "[HIGH] Add schema markup -> featured snippet",
                "[MEDIUM] Improve meta descriptions",
            ],
            raw_metrics={},
        )
        assert "CRITICAL" in html
        assert "HIGH" in html
        assert "MEDIUM" in html
        assert "#E24B4A" in html   # critical red
        assert "#BA7517" in html   # high amber

    def test_competitor_rows_render(self):
        from app.services.pdf_report import generate_seo_report_html
        competitors = [
            {"url": "https://comp1.com/page", "word_count": 2500, "keyword_density": 1.8, "top_entities": ["A", "B"], "h2": ["H1", "H2", "H3"]},
            {"url": "https://comp2.com/page", "word_count": 1800, "keyword_density": 1.2, "top_entities": ["C"], "h2": ["H1"]},
        ]
        html = generate_seo_report_html(
            client_url="https://mysite.com",
            keyword="seo",
            seo_score=55,
            competitors=competitors,
            gap_analysis={"missing_entities": ["schema", "faq", "reviews"]},
            recommendations=[],
            raw_metrics={},
        )
        assert "comp1.com" in html
        assert "comp2.com" in html
        assert "2,500" in html
        assert "schema" in html


# ── Analytics route schema tests ───────────────────────────────────────────────
class TestAnalyticsSchemas:
    def test_ga4_metrics_request_defaults(self):
        from app.api.analytics import GA4MetricsRequest
        req = GA4MetricsRequest(access_token="tok", property_id="12345")
        assert req.date_range == "30daysAgo"

    def test_ga4_metrics_request_custom_range(self):
        from app.api.analytics import GA4MetricsRequest
        req = GA4MetricsRequest(access_token="tok", property_id="12345", date_range="90daysAgo")
        assert req.date_range == "90daysAgo"

    def test_gsc_metrics_request_defaults(self):
        from app.api.analytics import GSCMetricsRequest
        req = GSCMetricsRequest(access_token="tok", site_url="https://example.com")
        assert req.date_range_days == 30

    def test_token_exchange_service_ga4(self):
        from app.api.analytics import TokenExchangeRequest
        req = TokenExchangeRequest(code="abc", service="ga4")
        assert req.service == "ga4"
        assert req.project_id == ""

    def test_token_exchange_service_gsc(self):
        from app.api.analytics import TokenExchangeRequest
        req = TokenExchangeRequest(code="xyz", service="gsc", project_id="proj-1")
        assert req.service == "gsc"
        assert req.project_id == "proj-1"

    def test_token_exchange_response_empty_properties(self):
        from app.api.analytics import TokenExchangeResponse
        resp = TokenExchangeResponse(access_token="tok", service="gsc")
        assert resp.properties == []
        assert resp.refresh_token is None
        assert resp.email is None


# ── Research request with city/business_type ──────────────────────────────────
class TestResearchWithProfile:
    def test_research_request_city_localisation(self):
        from app.schemas.research import ResearchRequest
        req = ResearchRequest(
            client_url="https://biryaniplace.in",
            primary_keyword="best biryani hyderabad",
            city="hyderabad",
            business_type="restaurant",
            target_region="IN",
        )
        assert req.city == "hyderabad"
        assert req.business_type == "restaurant"
        assert req.target_region == "IN"

    def test_research_request_all_india_no_city(self):
        from app.schemas.research import ResearchRequest
        req = ResearchRequest(
            client_url="https://saasproduct.com",
            primary_keyword="crm software india",
        )
        assert req.city is None
        assert req.business_type is None

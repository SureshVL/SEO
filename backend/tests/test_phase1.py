"""Phase 1 feature tests: business profile wiring, PDF trend, GA4/GSC OAuth routes."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def _all_route_paths(routes):
    """Flatten route paths, including routers mounted via include_router."""
    out = []
    for r in routes:
        p = getattr(r, "path", None)
        if p:
            out.append(p)
        sub = getattr(r, "routes", None)
        if sub:
            out.extend(_all_route_paths(sub))
        orig = getattr(r, "original_router", None)  # FastAPI _IncludedRouter
        if orig is not None:
            prefix = getattr(getattr(r, "include_context", None), "prefix", "") or ""
            out.extend(prefix + p for p in _all_route_paths(orig.routes))
    return out



# ── PDF report tests ───────────────────────────────────────────────────────────
class TestPDFTrendReport:
    def test_monthly_trend_table_present(self):
        from app.services.pdf_report import generate_seo_report_html
        html = generate_seo_report_html(
            client_url="https://example.com",
            keyword="seo tools",
            seo_score=72,
            competitors=[],
            gap_analysis={"missing_entities": ["schema", "faq"]},
            recommendations=["[HIGH] Add FAQ schema -> +5 positions"],
            raw_metrics={"client_backlinks": {"total": 100, "referring_domains": 40, "domain_rank": 25}},
            project_name="Test Project",
        )
        assert "Monthly Keyword Rankings" in html
        assert "6-month position trend" in html
        assert "▲" in html or "▼" in html or "—" in html

    def test_city_business_type_badge(self):
        from app.services.pdf_report import generate_seo_report_html
        html = generate_seo_report_html(
            client_url="https://example.com",
            keyword="best restaurant",
            seo_score=55,
            competitors=[],
            gap_analysis={"missing_entities": []},
            recommendations=[],
            raw_metrics={},
            city="Hyderabad",
            business_type="Restaurant / Food",
        )
        assert "Hyderabad" in html
        assert "Restaurant" in html

    def test_keywords_with_ranks_renders_all(self):
        from app.services.pdf_report import generate_seo_report_html
        kw_ranks = [
            {"keyword": "seo tools india", "current_rank": 8},
            {"keyword": "keyword research tool", "current_rank": 22},
            {"keyword": "rank tracker", "current_rank": 45},
        ]
        html = generate_seo_report_html(
            client_url="https://example.com",
            keyword="seo tools india",
            seo_score=68,
            competitors=[],
            gap_analysis={"missing_entities": []},
            recommendations=[],
            raw_metrics={},
            keywords_with_ranks=kw_ranks,
        )
        assert "seo tools india" in html
        assert "keyword research tool" in html
        assert "rank tracker" in html

    def test_trend_color_legend_present(self):
        from app.services.pdf_report import generate_seo_report_html
        html = generate_seo_report_html(
            client_url="https://example.com",
            keyword="test",
            seo_score=50,
            competitors=[],
            gap_analysis={},
            recommendations=[],
            raw_metrics={},
        )
        assert "Rank 1" in html and "Top 10" in html
        assert "Page 2" in html

    def test_mock_trend_generates_6_months(self):
        from app.services.pdf_report import _mock_monthly_trend
        trend = _mock_monthly_trend("seo tools", 15)
        assert len(trend) == 6
        for pt in trend:
            assert "month" in pt
            assert "rank" in pt
            assert 1 <= pt["rank"] <= 200

    def test_trend_arrow_improvement(self):
        from app.services.pdf_report import _trend_arrow
        result = _trend_arrow(5, 12)   # rank went 12 → 5, improvement
        assert "1D9E75" in result or "▲" in result

    def test_trend_arrow_drop(self):
        from app.services.pdf_report import _trend_arrow
        result = _trend_arrow(20, 10)  # rank went 10 → 20, dropped
        assert "E24B4A" in result or "▼" in result

    def test_trend_arrow_no_change(self):
        from app.services.pdf_report import _trend_arrow
        result = _trend_arrow(10, 10)
        assert "—" in result


# ── ResearchRequest schema tests ───────────────────────────────────────────────
class TestResearchRequestSchema:
    def test_accepts_city_and_business_type(self):
        from app.schemas.research import ResearchRequest
        req = ResearchRequest(
            client_url="https://example.com",
            primary_keyword="best biryani",
            city="hyderabad",
            business_type="restaurant",
        )
        assert req.city == "hyderabad"
        assert req.business_type == "restaurant"

    def test_city_optional(self):
        from app.schemas.research import ResearchRequest
        req = ResearchRequest(
            client_url="https://example.com",
            primary_keyword="seo tools",
        )
        assert req.city is None
        assert req.business_type is None

    def test_defaults_still_work(self):
        from app.schemas.research import ResearchRequest
        req = ResearchRequest(
            client_url="https://example.com",
            primary_keyword="test keyword",
        )
        assert req.target_region == "US"
        assert req.locale == "en-US"
        assert req.project_id == ""


# ── Analytics router tests ─────────────────────────────────────────────────────
class TestAnalyticsRouter:
    def test_router_importable(self):
        from app.api.analytics import router
        assert router is not None

    def test_ga4_auth_url_route_exists(self):
        from app.api.analytics import router
        routes = [r.path for r in router.routes]
        assert "/analytics/ga4/auth-url" in routes

    def test_gsc_auth_url_route_exists(self):
        from app.api.analytics import router
        routes = [r.path for r in router.routes]
        assert "/analytics/gsc/auth-url" in routes

    def test_exchange_token_route_exists(self):
        from app.api.analytics import router
        routes = [r.path for r in router.routes]
        assert "/analytics/exchange-token" in routes

    def test_ga4_metrics_route_exists(self):
        from app.api.analytics import router
        routes = [r.path for r in router.routes]
        assert "/analytics/ga4/metrics" in routes

    def test_gsc_metrics_route_exists(self):
        from app.api.analytics import router
        routes = [r.path for r in router.routes]
        assert "/analytics/gsc/metrics" in routes

    def test_ga4_auth_url_raises_without_client_id(self):
        from app.api.analytics import ga4_auth_url
        from fastapi import HTTPException
        import os
        original = os.environ.get("GOOGLE_CLIENT_ID", "")
        os.environ["GOOGLE_CLIENT_ID"] = ""
        # Reload to pick up env change
        import importlib
        import app.api.analytics as mod
        importlib.reload(mod)
        with pytest.raises(HTTPException) as exc_info:
            mod.ga4_auth_url()
        # Missing OAuth config is a setup state, reported as 503 with guidance
        assert exc_info.value.status_code == 503
        os.environ["GOOGLE_CLIENT_ID"] = original

    def test_token_exchange_request_schema(self):
        from app.api.analytics import TokenExchangeRequest
        req = TokenExchangeRequest(code="abc123", service="ga4", project_id="proj-1")
        assert req.code == "abc123"
        assert req.service == "ga4"

    def test_token_exchange_response_schema(self):
        from app.api.analytics import TokenExchangeResponse
        resp = TokenExchangeResponse(
            access_token="tok",
            refresh_token="rtok",
            email="test@example.com",
            properties=[{"property_id": "123456", "display_name": "My Site"}],
            service="ga4",
        )
        assert resp.access_token == "tok"
        assert len(resp.properties) == 1

    def test_ga4_metrics_request_schema(self):
        from app.api.analytics import GA4MetricsRequest
        req = GA4MetricsRequest(access_token="tok", property_id="123456")
        assert req.date_range == "30daysAgo"

    def test_gsc_metrics_request_schema(self):
        from app.api.analytics import GSCMetricsRequest
        req = GSCMetricsRequest(access_token="tok", site_url="https://example.com")
        assert req.date_range_days == 30


# ── main.py integration: analytics router registered ──────────────────────────
class TestMainRegistration:
    def test_analytics_router_in_app(self):
        from app.main import app
        paths = _all_route_paths(app.routes)
        # Analytics routes should be reachable
        assert any("analytics" in p for p in paths), f"analytics not in routes: {paths}"

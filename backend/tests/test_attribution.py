"""Tests for AttributionAgent (GA4 + GSC merged revenue attribution) and routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.attribution_agent import (
    AttributionAgent,
    AttributionReport,
    PageAttribution,
    QueryAttribution,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

GA4_CHANNELS = [
    {"channel": "Organic Search", "sessions": 1000, "revenue": 5000.0, "conversions": 50, "new_users": 600},
    {"channel": "Direct", "sessions": 300, "revenue": 1500.0, "conversions": 15, "new_users": 50},
    {"channel": "Paid Search", "sessions": 700, "revenue": 3500.0, "conversions": 35, "new_users": 400},
]

GA4_PAGES = [
    # /guide: organic revenue 3000, total revenue 3000
    {"page_path": "/guide", "channel": "Organic Search", "sessions": 600, "revenue": 3000.0, "conversions": 30},
    # /pricing: organic 2000 + direct 1500 = 3500 total
    {"page_path": "/pricing", "channel": "Organic Search", "sessions": 400, "revenue": 2000.0, "conversions": 20},
    {"page_path": "/pricing", "channel": "Direct", "sessions": 300, "revenue": 1500.0, "conversions": 15},
    # /blog: only paid
    {"page_path": "/blog", "channel": "Paid Search", "sessions": 700, "revenue": 3500.0, "conversions": 35},
]

GSC_QUERIES = [
    {"query": "seo guide", "clicks": 500, "impressions": 10000, "ctr": 0.05, "position": 3.2},
    {"query": "seo pricing", "clicks": 200, "impressions": 4000, "ctr": 0.05, "position": 4.5},
    {"query": "best seo platform", "clicks": 100, "impressions": 3000, "ctr": 0.033, "position": 7.1},
]

GSC_PAGES = [
    {"page": "https://acme.com/guide", "clicks": 500, "impressions": 10000, "ctr": 0.05, "position": 3.2},
    {"page": "https://acme.com/pricing", "clicks": 300, "impressions": 7000, "ctr": 0.043, "position": 5.3},
]

GSC_PAGE_QUERIES = [
    # /guide: 400 clicks from "seo guide", 100 from "best seo platform"
    {"page": "https://acme.com/guide", "query": "seo guide", "clicks": 400, "impressions": 8000, "position": 3.0},
    {"page": "https://acme.com/guide", "query": "best seo platform", "clicks": 100, "impressions": 3000, "position": 7.1},
    # /pricing: 200 clicks from "seo pricing", 100 from "seo guide"
    {"page": "https://acme.com/pricing", "query": "seo pricing", "clicks": 200, "impressions": 4000, "position": 4.5},
    {"page": "https://acme.com/pricing", "query": "seo guide", "clicks": 100, "impressions": 2000, "position": 3.8},
]


def build(**overrides):
    kwargs = {
        "date_range_days": 30,
        "ga4_property_id": "12345",
        "gsc_site_url": "https://acme.com/",
        "ga4_pages": GA4_PAGES,
        "ga4_channel_totals": GA4_CHANNELS,
        "gsc_queries": GSC_QUERIES,
        "gsc_pages": GSC_PAGES,
        "gsc_page_queries": GSC_PAGE_QUERIES,
        "top_n": 15,
    }
    kwargs.update(overrides)
    return AttributionAgent().build_report(**kwargs)


# ── Utilities ─────────────────────────────────────────────────────────────────

class TestUtilities:
    def test_is_organic(self):
        assert AttributionAgent._is_organic("Organic Search") is True
        assert AttributionAgent._is_organic("organic search") is True
        assert AttributionAgent._is_organic("Direct") is False
        assert AttributionAgent._is_organic("") is False
        assert AttributionAgent._is_organic(None) is False  # type: ignore

    def test_normalize_path_from_full_url(self):
        assert AttributionAgent._normalize_path("https://acme.com/foo") == "/foo"
        assert AttributionAgent._normalize_path("https://acme.com/foo?bar=1") == "/foo"
        assert AttributionAgent._normalize_path("https://acme.com/") == "/"

    def test_normalize_path_passthrough(self):
        assert AttributionAgent._normalize_path("/already/path") == "/already/path"
        assert AttributionAgent._normalize_path("") == ""


# ── Channel totals ────────────────────────────────────────────────────────────

class TestChannelTotals:
    def test_sums_channels(self):
        r = build()
        assert r.total_sessions == 2000
        assert r.organic_sessions == 1000
        assert r.total_revenue == 10000.0
        assert r.organic_revenue == 5000.0

    def test_organic_share(self):
        r = build()
        assert r.organic_share_pct == 50.0
        assert r.organic_revenue_share_pct == 50.0

    def test_empty_channels_sets_warning(self):
        r = build(ga4_channel_totals=[])
        assert "No GA4 channel data" in r.warnings[0]
        assert r.total_sessions == 0


# ── Page attribution ──────────────────────────────────────────────────────────

class TestPageAttribution:
    def test_ranks_by_organic_revenue(self):
        r = build()
        # /guide has 3000 organic, /pricing has 2000 — guide should win
        assert r.top_pages[0].page_path == "/guide"
        assert r.top_pages[0].organic_revenue == 3000.0
        assert r.top_pages[1].page_path == "/pricing"
        assert r.top_pages[1].organic_revenue == 2000.0

    def test_pricing_page_sums_all_channels_for_total(self):
        r = build()
        pricing = next(p for p in r.top_pages if p.page_path == "/pricing")
        # Total sessions across Organic+Direct = 700
        assert pricing.sessions == 700
        # Total revenue across channels = 3500
        assert pricing.revenue == 3500.0
        # But organic-only revenue is 2000
        assert pricing.organic_revenue == 2000.0

    def test_gsc_metrics_merge_onto_ga4_pages(self):
        r = build()
        guide = next(p for p in r.top_pages if p.page_path == "/guide")
        assert guide.gsc_clicks == 500
        assert guide.gsc_impressions == 10000
        assert guide.avg_position == 3.2

    def test_gsc_only_pages_still_appear(self):
        # /orphan exists only in GSC, never in GA4
        r = build(
            gsc_pages=[
                *GSC_PAGES,
                {"page": "https://acme.com/orphan", "clicks": 50, "impressions": 800, "ctr": 0.0625, "position": 8.0},
            ],
        )
        orphan = next((p for p in r.top_pages if p.page_path == "/orphan"), None)
        assert orphan is not None
        assert orphan.organic_revenue == 0.0
        assert orphan.gsc_clicks == 50

    def test_top_queries_attached_to_pages(self):
        r = build()
        guide = next(p for p in r.top_pages if p.page_path == "/guide")
        assert guide.top_queries
        # Highest-click query on /guide is "seo guide" (400 clicks)
        assert guide.top_queries[0]["query"] == "seo guide"
        assert guide.top_queries[0]["clicks"] == 400


# ── Query attribution ─────────────────────────────────────────────────────────

class TestQueryAttribution:
    def test_attributed_revenue_split_by_click_share(self):
        r = build()
        # "seo guide" appears on /guide (400 of 500 page clicks = 80%) and
        # /pricing (100 of 300 page clicks = 33%). Expected:
        #   0.80 * 3000 (organic /guide) + 0.33 * 2000 (organic /pricing) = 2400 + 666.67 = 3066.67
        seo_guide = next(q for q in r.top_queries if q.query == "seo guide")
        assert seo_guide.attributed_revenue == pytest.approx(3066.67, abs=0.05)

    def test_ranks_queries_by_attributed_revenue(self):
        r = build()
        # seo guide should top the list
        assert r.top_queries[0].query == "seo guide"
        assert r.top_queries[0].attributed_revenue > 0

    def test_query_landing_pages_listed(self):
        r = build()
        seo_guide = next(q for q in r.top_queries if q.query == "seo guide")
        # Should list both landing pages
        assert "/guide" in seo_guide.landing_pages
        assert "/pricing" in seo_guide.landing_pages

    def test_ctr_normalised_when_passed_as_fraction(self):
        r = build()
        q = next(q for q in r.top_queries if q.query == "seo guide")
        # 0.05 should become 5.0 (percent)
        assert q.ctr == 5.0

    def test_ctr_normalised_when_passed_as_percent(self):
        r = build(
            gsc_queries=[
                {"query": "x", "clicks": 10, "impressions": 100, "ctr": 10.0, "position": 5.0},
            ],
        )
        q = r.top_queries[0]
        # 10.0 (already percent) is divided by 100 then multiplied by 100 → 10.0
        assert q.ctr == 10.0

    def test_empty_gsc_adds_warning(self):
        r = build(gsc_queries=[])
        assert any("GSC" in w for w in r.warnings)


# ── Route integration ─────────────────────────────────────────────────────────

class TestAttributionRoute:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_happy_path(self, client):
        """Stub the Google API helpers and verify the route serialises correctly."""
        from app.api import analytics

        async def fake_ga4_pages(*a, **kw):
            return GA4_PAGES

        async def fake_ga4_channels(*a, **kw):
            return GA4_CHANNELS

        async def fake_gsc_query(client, access_token, site_url, start, end, dimensions, row_limit=200):
            if dimensions == ["query"]:
                return GSC_QUERIES
            if dimensions == ["page"]:
                return GSC_PAGES
            return GSC_PAGE_QUERIES

        with (
            patch.object(analytics, "_ga4_pages", new=AsyncMock(side_effect=fake_ga4_pages)),
            patch.object(analytics, "_ga4_channel_totals", new=AsyncMock(side_effect=fake_ga4_channels)),
            patch.object(analytics, "_gsc_query", new=AsyncMock(side_effect=fake_gsc_query)),
        ):
            r = client.post(
                "/analytics/attribution",
                json={
                    "ga4_access_token": "fake",
                    "ga4_property_id": "12345",
                    "gsc_access_token": "fake",
                    "gsc_site_url": "https://acme.com/",
                    "date_range_days": 30,
                    "top_n": 5,
                },
            )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["date_range_days"] == 30
        assert body["ga4"]["organic_revenue"] == 5000.0
        assert body["ga4"]["organic_share_pct"] == 50.0
        assert body["top_pages"][0]["page_path"] == "/guide"
        assert body["top_queries"][0]["query"] == "seo guide"
        assert body["gsc"]["total_clicks"] == 800

    def test_route_returns_dataclass_keys(self, client):
        from app.api import analytics

        empty = AsyncMock(return_value=[])
        with (
            patch.object(analytics, "_ga4_pages", new=empty),
            patch.object(analytics, "_ga4_channel_totals", new=empty),
            patch.object(analytics, "_gsc_query", new=empty),
        ):
            r = client.post(
                "/analytics/attribution",
                json={
                    "ga4_access_token": "fake",
                    "ga4_property_id": "12345",
                    "gsc_access_token": "fake",
                    "gsc_site_url": "https://acme.com/",
                },
            )
        assert r.status_code == 200
        body = r.json()
        for key in ("date_range_days", "ga4_property_id", "gsc_site_url", "ga4",
                    "gsc", "top_pages", "top_queries", "warnings"):
            assert key in body
        # Both warnings fire on empty inputs
        assert any("GA4" in w for w in body["warnings"])
        assert any("GSC" in w for w in body["warnings"])

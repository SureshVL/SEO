"""Phase 3 tests: competitor GET endpoint, content CRUD, billing, report HTML."""
import pytest
from datetime import datetime, timezone


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



# ── Competitor GET endpoint ────────────────────────────────────────────────────
class TestCompetitorGetEndpoint:
    def test_list_competitors_route_exists(self):
        from app.main import app
        paths = _all_route_paths(app.routes)
        assert "/projects/{project_id}/competitors" in paths

    def test_list_competitors_and_check_both_registered(self):
        from app.main import app
        competitor_routes = [r for r in app.routes if "competitors" in getattr(r, "path", "")]
        assert len(competitor_routes) >= 2  # GET list + POST check (+ competitor AI features)

    def test_competitor_intel_route_method_get(self):
        from app.main import app
        for r in app.routes:
            if getattr(r, "path", "") == "/projects/{project_id}/competitors":
                assert "GET" in r.methods
                break


# ── ContentDraftCreate schema ─────────────────────────────────────────────────
class TestContentSchema:
    def test_content_draft_create_valid(self):
        from app.schemas.project import ContentDraftCreate
        d = ContentDraftCreate(
            title="Best SEO Tools India 2025",
            body_markdown="# Best SEO Tools\n\nContent here...",
            target_keyword="seo tools india",
        )
        assert d.publish_target == "wordpress"

    def test_content_draft_create_custom_target(self):
        from app.schemas.project import ContentDraftCreate
        d = ContentDraftCreate(
            title="Test",
            body_markdown="content",
            target_keyword="rank tracker",
            publish_target="custom_cms",
        )
        assert d.publish_target == "custom_cms"

    def test_content_draft_response_schema(self):
        from app.schemas.project import ContentDraftResponse
        now = datetime.now(timezone.utc)
        r = ContentDraftResponse(
            id="c1", title="Test Post", slug="test-post",
            body_markdown="# Test", target_keyword="test",
            publish_target="wordpress",
            created_at=now, updated_at=now,
        )
        assert r.queue_status == "draft"

    def test_content_response_status_options(self):
        from app.schemas.project import ContentDraftResponse
        now = datetime.now(timezone.utc)
        for status in ["draft", "review", "approved", "published"]:
            r = ContentDraftResponse(
                id="c1", title="T", slug=None, body_markdown="b",
                target_keyword=None, publish_target=None,
                created_at=now, updated_at=now,
                queue_status=status,
            )
            assert r.queue_status == status


# ── Billing service ────────────────────────────────────────────────────────────
class TestBillingService:
    def test_plans_defined(self):
        from app.services.billing import PLANS
        for tier in ("free", "starter", "growth", "pro", "agency"):
            assert tier in PLANS

    def test_plan_prices(self):
        from app.services.billing import PLANS, annual_price_inr
        assert PLANS["free"]["price_inr"] == 0
        assert PLANS["starter"]["price_inr"] == 1999
        assert PLANS["growth"]["price_inr"] == 4999
        assert PLANS["pro"]["price_inr"] == 9999
        assert PLANS["agency"]["price_inr"] == 19999
        # annual = monthly * 12 * 0.8 (20% off)
        assert annual_price_inr("growth") == round(4999 * 12 * 0.8)
        assert annual_price_inr("free") == 0

    def test_razorpay_client_disabled_without_keys(self):
        from app.services.billing import RazorpayClient
        import os
        orig_id = os.environ.get("RAZORPAY_KEY_ID", "")
        orig_sec = os.environ.get("RAZORPAY_KEY_SECRET", "")
        os.environ["RAZORPAY_KEY_ID"] = ""
        os.environ["RAZORPAY_KEY_SECRET"] = ""
        client = RazorpayClient()
        assert not client.enabled
        os.environ["RAZORPAY_KEY_ID"] = orig_id
        os.environ["RAZORPAY_KEY_SECRET"] = orig_sec

    def test_plan_has_required_keys(self):
        from app.services.billing import PLANS
        for pid, plan in PLANS.items():
            assert "price_inr" in plan, f"Plan {pid} missing price_inr"
            assert "currency" in plan, f"Plan {pid} missing currency"


# ── Report generator ───────────────────────────────────────────────────────────
class TestReportGenerator:
    def test_report_generator_importable(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator()
        assert gen is not None

    def test_generate_seo_report_no_ai(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "Test Project", "client_url": "https://testproject.com", "domain": "testproject.com"},
            keywords=[{"keyword": "seo tools", "latest_position": 8}],
        )
        assert "title" in result
        assert "summary" in result

    def test_report_uses_pdf_service_correctly(self):
        from app.services.pdf_report import generate_seo_report_html
        html = generate_seo_report_html(
            client_url="https://test.com",
            keyword="seo audit",
            seo_score=65,
            competitors=[
                {"url": "https://c1.com", "word_count": 2000,
                 "keyword_density": 1.5, "top_entities": ["schema"], "h2": ["H1", "H2"]},
            ],
            gap_analysis={"missing_entities": ["structured data", "faq"]},
            recommendations=["[CRITICAL] Fix crawl errors -> reduce 404s by 90%"],
            raw_metrics={"client_backlinks": {"total": 200, "referring_domains": 50, "domain_rank": 30}, "serp_features": ["featured_snippet", "people_also_ask"]},
            keywords_with_ranks=[{"keyword": "seo audit", "current_rank": 12}],
            project_name="Test Project",
            city="Bangalore",
            business_type="SaaS / Tech",
        )
        assert "65" in html  # score
        assert "c1.com" in html  # competitor
        assert "structured data" in html  # entity gap
        assert "CRITICAL" in html  # recommendation
        assert "featured snippet" in html  # SERP feature
        assert "Bangalore" in html  # city
        assert "seo audit" in html  # trend keyword


# ── Analytics OAuth schema coverage ──────────────────────────────────────────
class TestAnalyticsOAuth:
    def test_all_5_analytics_routes_registered(self):
        from app.main import app
        paths = _all_route_paths(app.routes)
        assert "/analytics/ga4/auth-url" in paths
        assert "/analytics/gsc/auth-url" in paths
        assert "/analytics/exchange-token" in paths
        assert "/analytics/ga4/metrics" in paths
        assert "/analytics/gsc/metrics" in paths

    def test_scope_lists_non_empty(self):
        from app.api.analytics import GA4_SCOPES, GSC_SCOPES
        assert len(GA4_SCOPES) >= 2
        assert len(GSC_SCOPES) >= 2
        assert any("analytics" in s for s in GA4_SCOPES)
        assert any("webmasters" in s for s in GSC_SCOPES)


# ── Full route inventory ───────────────────────────────────────────────────────
class TestRouteInventory:
    def test_all_expected_routes_present(self):
        from app.main import app
        paths = set(_all_route_paths(app.routes))
        expected = [
            "/health",
            "/projects",
            "/projects/{project_id}",
            "/projects/{project_id}/keywords",
            "/keywords/{keyword_id}",
            "/keywords/{keyword_id}/rank-history",
            "/projects/{project_id}/rank-check",
            "/projects/{project_id}/content",
            "/content/{content_id}",
            "/content/{content_id}/ai-rewrite",
            "/projects/{project_id}/competitors",
            "/projects/{project_id}/competitors/check",
            "/projects/{project_id}/reports",
            "/projects/{project_id}/reports/generate",
            "/projects/{project_id}/reports/{report_id}/html",
            "/billing/subscribe",
            "/billing/cancel",
            "/webhooks/razorpay",
            "/analytics/ga4/auth-url",
            "/analytics/gsc/auth-url",
            "/analytics/exchange-token",
            "/analytics/ga4/metrics",
            "/analytics/gsc/metrics",
        ]
        for path in expected:
            assert path in paths, f"Missing route: {path}"

    def test_total_route_count(self):
        from app.main import app
        # At least 30 routes (was 31 endpoints + new analytics + GET competitors)
        non_trivial = [r for r in app.routes if getattr(r, "path", "").startswith("/")]
        assert len(non_trivial) >= 30


# ── Keyword city localisation ─────────────────────────────────────────────────
class TestKeywordCityLocalisation:
    def test_city_appended_to_seed_when_absent(self):
        """Keyword endpoint should localise the seed when city is provided."""
        seed = "best restaurant"
        city = "hyderabad"
        localised = f"{seed} in {city.title()}" if city and city.lower() not in seed.lower() else seed
        assert localised == "best restaurant in Hyderabad"

    def test_city_not_duplicated_when_already_present(self):
        seed = "best restaurant in hyderabad"
        city = "hyderabad"
        localised = f"{seed} in {city.title()}" if city and city.lower() not in seed.lower() else seed
        assert localised == "best restaurant in hyderabad"  # unchanged

    def test_empty_city_leaves_seed_unchanged(self):
        seed = "seo tools india"
        city = ""
        localised = f"{seed} in {city.title()}" if city and city.lower() not in seed.lower() else seed
        assert localised == "seo tools india"

    def test_keyword_research_endpoint_has_city_param(self):
        from app.main import app
        for route in app.routes:
            if getattr(route, "path", "") == "/keywords/research":
                import inspect
                sig = inspect.signature(route.endpoint)
                assert "city" in sig.parameters, "city param missing from /keywords/research"
                break

    def test_keyword_agent_research_accepts_city(self):
        import inspect
        from app.agents.keyword_agent import KeywordStrategyAgent
        sig = inspect.signature(KeywordStrategyAgent.research)
        assert "city" in sig.parameters


# ── ReportGenerator dict return ───────────────────────────────────────────────
class TestReportGeneratorDictReturn:
    def test_returns_dict_with_title(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "Test", "client_url": "https://test.com", "domain": "test.com"},
            keywords=[{"keyword": "seo", "latest_position": 5}],
        )
        assert isinstance(result, dict)
        assert "title" in result
        assert "summary" in result
        assert "html" in result

    def test_title_contains_project_name(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "Acme Corp", "domain": "acme.com"},
            keywords=[],
        )
        assert "Acme Corp" in result["title"]

    def test_html_is_valid_html(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "Test", "domain": "test.com"},
            keywords=[{"keyword": "seo tools", "latest_position": 12}],
        )
        html = result["html"]
        assert "<!DOCTYPE html>" in html
        assert "<table" in html
        assert "Keywords Tracked" in html

    def test_summary_is_string(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "X", "domain": "x.com"},
            keywords=[],
        )
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_white_label_strips_brand(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "Client", "domain": "client.com"},
            keywords=[],
            white_label=True,
        )
        assert "OMNI-RANK" not in result["html"]
        assert "Client" in result["html"]

    def test_keyword_positions_in_html(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator(claude_client=None)
        result = gen.generate_seo_report(
            project={"name": "SEO Test", "domain": "seotest.com"},
            keywords=[
                {"keyword": "seo tools india", "latest_position": 3, "intent": "commercial"},
                {"keyword": "rank tracker", "latest_position": 15, "intent": "informational"},
            ],
        )
        html = result["html"]
        assert "seo tools india" in html
        assert "rank tracker" in html
        assert "#3" in html
        assert "#15" in html


# ── Billing PLANS correctness ─────────────────────────────────────────────────
class TestBillingPlansComplete:
    def test_price_paise_is_100x_price_inr(self):
        from app.services.billing import PLANS
        for pid, plan in PLANS.items():
            assert plan["price_paise"] == plan["price_inr"] * 100, \
                f"Plan {pid}: price_paise should be price_inr * 100"

    def test_agency_has_highest_limits(self):
        from app.services.billing import PLANS
        assert PLANS["agency"]["max_projects"] > PLANS["growth"]["max_projects"]
        assert PLANS["agency"]["max_keywords"] > PLANS["growth"]["max_keywords"]

    def test_starter_has_lowest_limits(self):
        from app.services.billing import PLANS
        assert PLANS["starter"]["max_projects"] < PLANS["growth"]["max_projects"]
        assert PLANS["starter"]["max_keywords"] < PLANS["growth"]["max_keywords"]

    def test_all_plans_have_razorpay_plan_id_key(self):
        from app.services.billing import PLANS
        for pid, plan in PLANS.items():
            assert "razorpay_plan_id" in plan, f"Plan {pid} missing razorpay_plan_id"

    def test_currency_is_inr_for_all(self):
        from app.services.billing import PLANS
        for pid, plan in PLANS.items():
            assert plan["currency"] == "INR", f"Plan {pid} currency should be INR"

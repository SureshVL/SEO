"""Tests for Week 5-12 services."""

from app.services.cache import cache_key
from app.services.billing import PLANS, UsageLimiter
from app.services.email import EmailService, SafeDict, TEMPLATES
from app.services.report_generator import ReportGenerator


# ── Cache ──

class SimpleCache:
    """Reuse the in-memory fallback for testing."""
    def __init__(self):
        self._store = {}
    def get(self, key):
        return self._store.get(key)
    def set(self, key, val, ttl=3600):
        self._store[key] = val


def test_cache_key_deterministic():
    k1 = cache_key("serp", "ai seo", "IN")
    k2 = cache_key("serp", "ai seo", "IN")
    assert k1 == k2
    assert k1.startswith("omnirank:")


def test_cache_key_different_inputs():
    k1 = cache_key("serp", "ai seo", "IN")
    k2 = cache_key("serp", "ai seo", "US")
    assert k1 != k2


# ── Billing ──

def test_plans_have_required_fields():
    for plan_id, plan in PLANS.items():
        assert "name" in plan
        assert "price_inr" in plan
        assert "max_projects" in plan
        assert "max_keywords" in plan
        assert plan["price_inr"] > 0


def test_plan_hierarchy():
    assert PLANS["starter"]["max_projects"] < PLANS["growth"]["max_projects"]
    assert PLANS["growth"]["max_keywords"] < PLANS["agency"]["max_keywords"]


# ── Email ──

def test_safe_dict_missing_key():
    d = SafeDict({"name": "Dev"})
    assert d["name"] == "Dev"
    assert d["missing"] == "{missing}"


def test_email_templates_exist():
    assert "welcome" in TEMPLATES
    assert "rank_alert" in TEMPLATES
    assert "report_ready" in TEMPLATES
    assert "billing_success" in TEMPLATES
    assert "trial_ending" in TEMPLATES


def test_email_template_formatting():
    tmpl = TEMPLATES["welcome"]
    body = tmpl["body"].format_map(SafeDict({"name": "Dev", "app_url": "https://app.omnirank.app"}))
    assert "Dev" in body
    assert "omnirank" in body


def test_email_service_disabled_without_key():
    svc = EmailService(api_key="")
    assert not svc.enabled


# ── Reports ──

def test_report_generator_fallback_narrative():
    gen = ReportGenerator()
    project = {"domain": "example.com"}
    keywords = [{"keyword": "seo"}, {"keyword": "ranking"}]
    html = gen.generate_seo_report(project=project, keywords=keywords)
    assert "example.com" in html
    assert "<!DOCTYPE html>" in html
    assert "Keywords Tracked" in html


def test_report_generator_white_label():
    gen = ReportGenerator()
    html = gen.generate_seo_report(
        project={"domain": "client.com", "name": "Client SEO"},
        keywords=[],
        white_label=True,
    )
    assert "OMNI-RANK" not in html
    assert "Client SEO" in html

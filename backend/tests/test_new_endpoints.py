"""Endpoint-level tests for features added in the platform expansion."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _all_route_paths(routes):
    out = []
    for r in routes:
        p = getattr(r, "path", None)
        if p:
            out.append(p)
        sub = getattr(r, "routes", None)
        if sub:
            out.extend(_all_route_paths(sub))
        orig = getattr(r, "original_router", None)
        if orig is not None:
            prefix = getattr(getattr(r, "include_context", None), "prefix", "") or ""
            out.extend(prefix + p for p in _all_route_paths(orig.routes))
    return out


class TestRouteInventory:
    def test_all_new_feature_routes_registered(self):
        paths = set(_all_route_paths(app.routes))
        expected = [
            # competitors / linking / keywords / multilingual / audits
            "/competitors/add", "/linking/pages", "/multilingual/languages",
            "/audits/run", "/audits/summary",
            # free audit funnel
            "/public/audit", "/public/audit/{audit_id}",
            # edge injection
            "/edge/v1/omnirank.js", "/edge/v1/config", "/edge/sites", "/edge/rules",
            # git write-back
            "/git/connect", "/git/pr", "/git/prs",
            # product feeds
            "/feeds/import", "/feeds/{feed_id}/optimize", "/feeds/{feed_id}/export",
            # revenue
            "/billing/plans", "/billing/stripe/checkout", "/webhooks/stripe",
            "/wins/summary",
        ]
        missing = [p for p in expected if p not in paths]
        assert not missing, f"Missing routes: {missing}"


class TestPublicEndpoints:
    def test_edge_snippet_served_cacheable_js(self):
        r = client.get("/edge/v1/omnirank.js")
        assert r.status_code == 200
        assert "javascript" in r.headers["content-type"]
        assert "max-age" in r.headers.get("cache-control", "")

    def test_edge_config_unknown_token_returns_empty_not_error(self):
        r = client.get("/edge/v1/config?token=or_unknown&url=/page")
        assert r.status_code == 200
        assert r.json() == {"directives": []}

    def test_edge_config_rejects_giant_token(self):
        r = client.get(f"/edge/v1/config?token={'x' * 200}&url=/")
        assert r.status_code == 400

    def test_public_audit_unknown_id_404(self):
        r = client.get("/public/audit/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_public_audit_requires_valid_email(self):
        r = client.post("/public/audit", json={"domain": "example.com", "email": "not-an-email"})
        assert r.status_code == 400

    def test_billing_plans_public_catalog(self):
        r = client.get("/billing/plans")
        assert r.status_code == 200
        data = r.json()
        assert {p["id"] for p in data["plans"]} == {"starter", "growth", "agency"}
        assert all(p["price_usd"] for p in data["plans"])
        assert "razorpay" in data["rails"] and "stripe" in data["rails"]

    def test_stripe_webhook_rejects_unsigned(self):
        r = client.post("/webhooks/stripe", content=b"{}")
        assert r.status_code == 400


class TestAuthRequired:
    def test_protected_endpoints_reject_missing_key(self):
        protected = [
            ("GET", "/edge/sites"), ("GET", "/git/connections"),
            ("GET", "/feeds"), ("GET", "/wins/summary"), ("GET", "/audits/summary"),
        ]
        for method, path in protected:
            r = client.request(method, path)
            assert r.status_code in (401, 403, 422), f"{path} not protected: {r.status_code}"

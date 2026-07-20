"""Tests for edge snippet injection: matching, resolution, caching, snippet."""

import json

from app.services.edge_service import (
    EdgeService, EDGE_SNIPPET_JS, rule_matches, _norm_path,
    ALLOWED_RULE_TYPES, ALLOWED_MATCH_TYPES,
)

SITE = {"id": "site-1", "site_token": "or_tok", "enabled": True, "domain": "shop.com"}
RULES = [
    {"id": 1, "rule_type": "schema", "url_pattern": "*", "match_type": "all",
     "payload": json.dumps({"jsonld": {"@type": "Organization"}}), "enabled": True},
    {"id": 2, "rule_type": "title", "url_pattern": "/products/widget", "match_type": "exact",
     "payload": json.dumps({"value": "Best Widget"}), "enabled": True},
    {"id": 3, "rule_type": "meta_description", "url_pattern": "/blog", "match_type": "prefix",
     "payload": json.dumps({"value": "Blog desc"}), "enabled": True},
]


def fake_db(method, path, payload=None, params=""):
    if path == "edge_sites" and "site_token" in params:
        return [SITE] if "or_tok" in params else []
    if path == "edge_rules":
        return RULES
    return []


class TestPathNormalization:
    def test_full_url_to_path(self):
        assert _norm_path("https://x.com/products/widget/?a=1") == "/products/widget"

    def test_bare_segment(self):
        assert _norm_path("products") == "/products"

    def test_root(self):
        assert _norm_path("") == "/"
        assert _norm_path("/") == "/"


class TestRuleMatching:
    def test_wildcard(self):
        assert rule_matches({"url_pattern": "*", "match_type": "all"}, "/anything")

    def test_exact(self):
        rule = {"url_pattern": "/products/widget", "match_type": "exact"}
        assert rule_matches(rule, "/products/widget")
        assert not rule_matches(rule, "/products/other")

    def test_prefix(self):
        rule = {"url_pattern": "/products", "match_type": "prefix"}
        assert rule_matches(rule, "/products/widget")
        assert not rule_matches(rule, "/blog/products")

    def test_contains(self):
        assert rule_matches({"url_pattern": "sale", "match_type": "contains"}, "/summer-sale-2026")


class TestDirectiveResolution:
    def setup_method(self):
        EdgeService._cache.clear()
        EdgeService._seen_writes.clear()

    def test_page_specific_plus_sitewide(self):
        r = EdgeService().resolve_directives("or_tok", "/products/widget", fake_db)
        types = {d["rule_type"] for d in r["directives"]}
        assert types == {"schema", "title"}

    def test_sitewide_only_elsewhere(self):
        r = EdgeService().resolve_directives("or_tok", "/about", fake_db)
        assert [d["rule_type"] for d in r["directives"]] == ["schema"]

    def test_prefix_match(self):
        r = EdgeService().resolve_directives("or_tok", "/blog/post-1", fake_db)
        types = {d["rule_type"] for d in r["directives"]}
        assert "meta_description" in types

    def test_unknown_token_returns_none(self):
        assert EdgeService().resolve_directives("or_nope", "/", fake_db) is None

    def test_payload_decoded_to_dict(self):
        r = EdgeService().resolve_directives("or_tok", "/", fake_db)
        assert isinstance(r["directives"][0]["payload"], dict)

    def test_cache_avoids_repeat_lookups(self):
        calls = {"n": 0}

        def counting_db(method, path, payload=None, params=""):
            calls["n"] += 1
            return fake_db(method, path, payload, params)

        svc = EdgeService()
        svc.resolve_directives("or_tok", "/", counting_db)
        first = calls["n"]
        svc.resolve_directives("or_tok", "/other", counting_db)
        # second call may only touch the throttled last-seen patch, not site/rules
        assert calls["n"] <= first + 1


class TestSnippet:
    def test_snippet_references_config_endpoint(self):
        assert "/edge/v1/config" in EDGE_SNIPPET_JS

    def test_snippet_handles_all_rule_types(self):
        for rule_type in ALLOWED_RULE_TYPES:
            assert rule_type in EDGE_SNIPPET_JS

    def test_rule_type_validation(self):
        import pytest
        svc = EdgeService()
        with pytest.raises(ValueError):
            svc.create_rule("p", "s", "*", "all", "evil_type", {}, db_fn=fake_db)
        with pytest.raises(ValueError):
            svc.create_rule("p", "s", "*", "regex", "title", {}, db_fn=fake_db)
        assert "exact" in ALLOWED_MATCH_TYPES

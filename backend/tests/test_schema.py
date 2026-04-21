"""Tests for Schema markup (JSON-LD) detection and generation."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.schema_agent import (
    GENERATABLE_TYPES,
    RECOMMENDED_BY_BUSINESS,
    SchemaAgent,
    SchemaDetectionResult,
    _domain_name,
    _origin,
    _unwrap_graph,
)


# ── Sample HTML fixtures ──────────────────────────────────────────────────────

HTML_WITH_ORG_AND_WEBSITE = """
<html>
<head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Acme","url":"https://acme.com"}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite","name":"Acme","url":"https://acme.com"}
</script>
</head>
<body>hi</body>
</html>
"""

HTML_WITH_GRAPH = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Organization", "name": "Acme", "url": "https://acme.com"},
    {"@type": "WebSite", "name": "Acme Site", "url": "https://acme.com"},
    {"@type": "BreadcrumbList", "itemListElement": []}
  ]
}
</script>
"""

HTML_WITH_ARRAY = """
<script type='application/ld+json'>
[
  {"@type": "Organization", "name": "Acme"},
  {"@type": "FAQPage", "mainEntity": []}
]
</script>
"""

HTML_WITH_BROKEN_JSON = """
<script type="application/ld+json">
{"@type":"Organization","name":"Good"}
</script>
<script type="application/ld+json">
{"@type":"Broken",,, oops }
</script>
"""

HTML_WITH_TYPE_LIST = """
<script type="application/ld+json">
{"@context":"https://schema.org","@type":["Organization","LocalBusiness"],"name":"Acme"}
</script>
"""

HTML_NO_JSONLD = "<html><body>nothing here</body></html>"


# ── Helpers ───────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_origin_strips_path(self):
        assert _origin("https://example.com/foo/bar") == "https://example.com"
        assert _origin("http://a.b.c/x") == "http://a.b.c"
        assert _origin("") == ""

    def test_domain_name_strips_protocol_and_www(self):
        assert _domain_name("https://www.example.com/page") == "example.com"
        assert _domain_name("http://foo.bar/x") == "foo.bar"

    def test_unwrap_graph_flattens(self):
        block = {
            "@context": "https://schema.org",
            "@graph": [{"@type": "A"}, {"@type": "B"}],
        }
        out = _unwrap_graph(block)
        assert len(out) == 2
        assert [b["@type"] for b in out] == ["A", "B"]

    def test_unwrap_graph_returns_self_if_no_graph(self):
        block = {"@type": "Organization", "name": "x"}
        assert _unwrap_graph(block) == [block]


# ── Extraction ────────────────────────────────────────────────────────────────

class TestExtraction:
    def test_extracts_multiple_script_tags(self):
        blocks = SchemaAgent.extract_jsonld_blocks(HTML_WITH_ORG_AND_WEBSITE)
        types = [b.get("@type") for b in blocks]
        assert types == ["Organization", "WebSite"]

    def test_unwraps_graph(self):
        blocks = SchemaAgent.extract_jsonld_blocks(HTML_WITH_GRAPH)
        assert len(blocks) == 3
        assert [b.get("@type") for b in blocks] == [
            "Organization", "WebSite", "BreadcrumbList",
        ]

    def test_handles_array_in_single_script(self):
        blocks = SchemaAgent.extract_jsonld_blocks(HTML_WITH_ARRAY)
        assert len(blocks) == 2
        assert {b.get("@type") for b in blocks} == {"Organization", "FAQPage"}

    def test_skips_broken_json(self):
        blocks = SchemaAgent.extract_jsonld_blocks(HTML_WITH_BROKEN_JSON)
        assert len(blocks) == 1
        assert blocks[0]["@type"] == "Organization"

    def test_empty_html_returns_empty(self):
        assert SchemaAgent.extract_jsonld_blocks("") == []
        assert SchemaAgent.extract_jsonld_blocks(HTML_NO_JSONLD) == []

    def test_type_list_resolves_first(self):
        blocks = SchemaAgent.extract_jsonld_blocks(HTML_WITH_TYPE_LIST)
        assert len(blocks) == 1
        t = SchemaAgent._schema_type(blocks[0])
        assert t == "Organization"


# ── Detection + gap analysis ──────────────────────────────────────────────────

class TestDetect:
    def test_detects_types_and_finds_missing(self):
        agent = SchemaAgent()
        result = agent.detect(
            url="https://acme.com/",
            html=HTML_WITH_ORG_AND_WEBSITE,
            business_type="saas",
            business_name="Acme",
        )
        assert result.blocks_found == 2
        assert "Organization" in result.detected_types
        assert "WebSite" in result.detected_types
        # saas recommends Organization, WebSite, SoftwareApplication, FAQPage, BreadcrumbList
        assert "SoftwareApplication" in result.missing_recommended
        assert "FAQPage" in result.missing_recommended
        assert "BreadcrumbList" in result.missing_recommended
        assert "Organization" not in result.missing_recommended
        assert "WebSite" not in result.missing_recommended

    def test_generates_stubs_for_missing(self):
        agent = SchemaAgent()
        result = agent.detect(
            url="https://acme.com/",
            html=HTML_NO_JSONLD,
            business_type="default",
            business_name="Acme",
        )
        gen_types = {g["@type"] for g in result.generated}
        # default = Organization, WebSite, BreadcrumbList, FAQPage — all generatable
        assert gen_types == {"Organization", "WebSite", "BreadcrumbList", "FAQPage"}

    def test_parse_errors_counted(self):
        agent = SchemaAgent()
        result = agent.detect(
            url="https://x.com/",
            html=HTML_WITH_BROKEN_JSON,
            business_type="default",
        )
        assert result.parse_errors
        assert "failed to parse" in result.parse_errors[0]

    def test_no_parse_errors_when_all_valid(self):
        agent = SchemaAgent()
        result = agent.detect(
            url="https://x.com/",
            html=HTML_WITH_ORG_AND_WEBSITE,
            business_type="default",
        )
        assert result.parse_errors == []

    def test_unknown_business_type_falls_back_to_default(self):
        agent = SchemaAgent()
        result = agent.detect(
            url="https://x.com/",
            html=HTML_NO_JSONLD,
            business_type="nonsense",
        )
        assert set(result.missing_recommended) == set(
            RECOMMENDED_BY_BUSINESS["default"]
        )

    def test_fetch_html_called_when_html_empty(self):
        agent = SchemaAgent()
        with patch.object(agent, "fetch_html", return_value=HTML_WITH_ORG_AND_WEBSITE) as m:
            result = agent.detect(url="https://acme.com/", business_type="default")
        m.assert_called_once_with("https://acme.com/")
        assert result.blocks_found == 2

    def test_fetch_html_uses_firecrawl_when_available(self):
        fc = MagicMock()
        fc.scrape_html.return_value = HTML_WITH_ORG_AND_WEBSITE
        agent = SchemaAgent(firecrawl_client=fc)
        html = agent.fetch_html("https://acme.com/")
        assert "Organization" in html
        fc.scrape_html.assert_called_once_with("https://acme.com/")


# ── Generator ─────────────────────────────────────────────────────────────────

class TestGenerate:
    def _agent(self) -> SchemaAgent:
        return SchemaAgent()

    def test_unsupported_type_returns_none(self):
        assert self._agent().generate("NotARealType", {"url": "https://x.com"}) is None

    def test_organization_minimum_fields(self):
        out = self._agent().generate(
            "Organization", {"url": "https://acme.com/", "business_name": "Acme"},
        )
        assert out["@context"] == "https://schema.org"
        assert out["@type"] == "Organization"
        assert out["name"] == "Acme"
        assert out["url"] == "https://acme.com"
        assert out["logo"].endswith("/logo.png")

    def test_local_business_has_address_and_phone(self):
        out = self._agent().generate(
            "LocalBusiness",
            {"url": "https://acme.com/", "business_name": "Acme", "city": "Mumbai"},
        )
        assert out["@type"] == "LocalBusiness"
        assert out["address"]["@type"] == "PostalAddress"
        assert out["address"]["addressLocality"] == "Mumbai"
        assert out["telephone"]
        assert out["openingHours"]

    def test_restaurant_adds_cuisine_and_pricerange(self):
        out = self._agent().generate(
            "Restaurant", {"url": "https://r.com/", "business_name": "R"},
        )
        assert out["@type"] == "Restaurant"
        assert "servesCuisine" in out
        assert out["priceRange"]
        # restaurants are also local businesses — should have address
        assert "address" in out

    def test_website_has_search_action(self):
        out = self._agent().generate(
            "WebSite", {"url": "https://acme.com/foo", "business_name": "Acme"},
        )
        assert out["@type"] == "WebSite"
        assert out["potentialAction"]["@type"] == "SearchAction"
        assert "search_term_string" in out["potentialAction"]["target"]["urlTemplate"]

    def test_breadcrumb_list_uses_page_url_for_last_item(self):
        out = self._agent().generate(
            "BreadcrumbList", {"url": "https://acme.com/cat/page"},
        )
        items = out["itemListElement"]
        assert len(items) == 3
        assert items[0]["item"] == "https://acme.com"
        assert items[-1]["item"] == "https://acme.com/cat/page"

    def test_article_and_blogposting(self):
        for t in ("Article", "BlogPosting"):
            out = self._agent().generate(
                t, {"url": "https://x.com/post", "business_name": "X"},
            )
            assert out["@type"] == t
            assert out["headline"]
            assert out["author"]["@type"] == "Organization"
            assert out["mainEntityOfPage"]["@id"] == "https://x.com/post"

    def test_faqpage_has_two_questions(self):
        out = self._agent().generate(
            "FAQPage", {"url": "https://x.com", "business_name": "X"},
        )
        assert out["@type"] == "FAQPage"
        assert len(out["mainEntity"]) == 2
        assert all(q["@type"] == "Question" for q in out["mainEntity"])

    def test_product_has_offers_and_rating(self):
        out = self._agent().generate(
            "Product", {"url": "https://x.com/p", "business_name": "X"},
        )
        assert out["@type"] == "Product"
        assert out["offers"]["@type"] == "Offer"
        assert out["aggregateRating"]["@type"] == "AggregateRating"

    def test_service_has_provider(self):
        out = self._agent().generate(
            "Service", {"url": "https://x.com", "business_name": "X"},
        )
        assert out["@type"] == "Service"
        assert out["provider"]["name"] == "X"

    def test_software_application(self):
        out = self._agent().generate(
            "SoftwareApplication", {"url": "https://x.com", "business_name": "X"},
        )
        assert out["@type"] == "SoftwareApplication"
        assert out["operatingSystem"]

    def test_menu_has_section_structure(self):
        out = self._agent().generate(
            "Menu", {"url": "https://r.com", "business_name": "R"},
        )
        assert out["@type"] == "Menu"
        assert out["hasMenuSection"][0]["@type"] == "MenuSection"

    def test_all_generatable_types_produce_output(self):
        """Every type declared in GENERATABLE_TYPES must return a stub."""
        ctx = {"url": "https://x.com/p", "business_name": "Acme"}
        for t in GENERATABLE_TYPES:
            out = self._agent().generate(t, ctx)
            assert out is not None, f"{t} produced no stub"
            assert out["@type"] == t
            assert out["@context"] == "https://schema.org"


# ── Routes ────────────────────────────────────────────────────────────────────

class TestSchemaRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_detect_with_inline_html(self, client, monkeypatch):
        from app import main

        fake_agent = SchemaAgent()
        monkeypatch.setattr(main, "_build_schema_agent", lambda: fake_agent)

        r = client.post(
            "/schema/detect",
            json={
                "url": "https://acme.com/",
                "html": HTML_WITH_ORG_AND_WEBSITE,
                "business_type": "saas",
                "business_name": "Acme",
            },
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["blocks_found"] == 2
        assert "Organization" in body["detected_types"]
        assert "SoftwareApplication" in body["missing_recommended"]
        gen_types = {g["@type"] for g in body["generated"]}
        assert "SoftwareApplication" in gen_types

    def test_detect_requires_auth(self, client):
        r = client.post(
            "/schema/detect",
            json={"url": "https://x.com/", "html": HTML_NO_JSONLD},
        )
        assert r.status_code in (401, 403)

    def test_generate_route_returns_stubs_and_unsupported(self, client, monkeypatch):
        from app import main
        monkeypatch.setattr(main, "_build_schema_agent", lambda: SchemaAgent())

        r = client.post(
            "/schema/generate",
            json={
                "schema_types": ["Organization", "WebSite", "NotARealType"],
                "url": "https://acme.com/",
                "business_name": "Acme",
            },
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert {g["type"] for g in body["generated"]} == {"Organization", "WebSite"}
        assert body["unsupported"] == ["NotARealType"]

    def test_generate_route_rejects_empty_list(self, client):
        r = client.post(
            "/schema/generate",
            json={"schema_types": []},
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 422

    def test_detect_route_serializes_detected_raw(self, client, monkeypatch):
        from app import main
        monkeypatch.setattr(main, "_build_schema_agent", lambda: SchemaAgent())

        r = client.post(
            "/schema/detect",
            json={
                "url": "https://acme.com/",
                "html": HTML_WITH_ORG_AND_WEBSITE,
                "business_type": "default",
            },
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        # detected blocks include the raw parsed JSON-LD for inspection
        assert len(body["detected"]) == 2
        assert body["detected"][0]["raw"]["@type"] == "Organization"

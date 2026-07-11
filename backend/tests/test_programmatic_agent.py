"""Tests for the programmatic SEO agent + route."""

import pytest
from fastapi.testclient import TestClient

from app.agents.programmatic_agent import (
    ProgrammaticAgent,
    extract_variables,
    slugify,
    substitute,
)


# ── Utility helpers ──────────────────────────────────────────────────────────

class TestExtractVariables:
    def test_finds_simple_vars(self):
        assert extract_variables("{{city}} / {{service}}") == {"city", "service"}

    def test_tolerates_whitespace(self):
        assert extract_variables("{{  city }}") == {"city"}

    def test_allows_dotted_names(self):
        assert extract_variables("{{user.name}}") == {"user.name"}

    def test_empty_input(self):
        assert extract_variables("") == set()
        assert extract_variables(None) == set()


class TestSubstitute:
    def test_replaces_known_vars(self):
        assert substitute("Hello {{name}}", {"name": "Bob"}) == "Hello Bob"

    def test_missing_vars_become_blank(self):
        assert substitute("Hello {{missing}}", {}) == "Hello "

    def test_none_values_become_blank(self):
        assert substitute("Hi {{x}}", {"x": None}) == "Hi "

    def test_coerces_non_string(self):
        assert substitute("Rank {{n}}", {"n": 7}) == "Rank 7"

    def test_empty_template(self):
        assert substitute("", {"x": "y"}) == ""


class TestSlugify:
    def test_basic(self):
        assert slugify("Plumbing in Austin") == "plumbing-in-austin"

    def test_strips_punctuation(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_preserves_leading_slash(self):
        assert slugify("/Plumbing in Austin!") == "/plumbing-in-austin"

    def test_no_leading_slash(self):
        assert slugify("foo bar") == "foo-bar"

    def test_empty(self):
        assert slugify("") == ""
        assert slugify(None) == ""

    def test_collapses_repeated_separators(self):
        assert slugify("a---b   c") == "a-b-c"


# ── CSV parsing ──────────────────────────────────────────────────────────────

class TestParseCsv:
    def test_empty_returns_empty_list(self):
        assert ProgrammaticAgent.parse_csv("") == []
        assert ProgrammaticAgent.parse_csv(None) == []

    def test_happy_path(self):
        rows = ProgrammaticAgent.parse_csv("city,service\nAustin,plumbing\nDallas,roofing\n")
        assert rows == [
            {"city": "Austin", "service": "plumbing"},
            {"city": "Dallas", "service": "roofing"},
        ]

    def test_strips_whitespace(self):
        rows = ProgrammaticAgent.parse_csv("city,service\n  Austin  , plumbing \n")
        assert rows == [{"city": "Austin", "service": "plumbing"}]


# ── Generate ─────────────────────────────────────────────────────────────────

TEMPLATE = {
    "name": "city-services",
    "slug_template": "/{{service}}-in-{{city}}",
    "title_template": "{{service}} in {{city}}",
    "meta_description_template": "Find {{service}} in {{city}}",
    "h1_template": "Best {{service}} in {{city}}",
    "body_template": "## {{service}} near {{city}}\n\nContent for {{city}}.",
}


class TestGenerate:
    def test_basic_generation(self):
        agent = ProgrammaticAgent()
        rows = [
            {"service": "plumbing", "city": "Austin"},
            {"service": "roofing", "city": "Dallas"},
        ]
        result = agent.generate(TEMPLATE, rows)
        assert result.generated == 2
        assert result.skipped == 0
        assert result.total_rows == 2
        assert sorted(result.variables_used) == ["city", "service"]
        assert result.pages[0].slug == "/plumbing-in-austin"
        assert result.pages[0].title == "plumbing in Austin"
        assert result.pages[0].h1 == "Best plumbing in Austin"

    def test_dedupes_by_slug(self):
        agent = ProgrammaticAgent()
        rows = [
            {"service": "plumbing", "city": "Austin"},
            {"service": "plumbing", "city": "Austin"},
        ]
        result = agent.generate(TEMPLATE, rows)
        assert result.generated == 1
        assert result.skipped == 1

    def test_missing_variable_warns_per_page(self):
        agent = ProgrammaticAgent()
        rows = [{"service": "plumbing"}]  # missing city
        result = agent.generate(TEMPLATE, rows)
        assert result.generated == 1
        assert any("city" in w for w in result.pages[0].warnings)

    def test_max_pages_truncates_with_warning(self):
        agent = ProgrammaticAgent()
        rows = [{"service": f"s{i}", "city": "X"} for i in range(5)]
        result = agent.generate(TEMPLATE, rows, max_pages=3)
        assert result.generated == 3
        assert any("truncated" in w for w in result.warnings)

    def test_template_without_variables_warns(self):
        agent = ProgrammaticAgent()
        template = {
            "name": "static",
            "slug_template": "/static",
            "title_template": "Static",
            "meta_description_template": "",
            "h1_template": "Static",
            "body_template": "Same for everyone",
        }
        result = agent.generate(template, [{"x": "a"}, {"x": "b"}])
        assert any("no {{variables}}" in w for w in result.warnings)

    def test_dedupe_on_custom_key(self):
        agent = ProgrammaticAgent()
        rows = [
            {"service": "plumbing", "city": "Austin", "id": "1"},
            {"service": "roofing", "city": "Dallas", "id": "1"},  # same id
        ]
        result = agent.generate(TEMPLATE, rows, dedupe_on="id")
        assert result.generated == 1
        assert result.skipped == 1


# ── Route integration ───────────────────────────────────────────────────────

class TestProgrammaticRoute:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_generate_with_rows(self, client):
        r = client.post(
            "/programmatic/generate",
            headers={"X-API-KEY": "test-key"},
            json={
                "template": {
                    "slug_template": "/{{city}}",
                    "title_template": "{{city}} guide",
                    "meta_description_template": "guide for {{city}}",
                    "body_template": "Welcome to {{city}}",
                },
                "rows": [{"city": "Austin"}, {"city": "Dallas"}],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["generated"] == 2
        assert body["total_rows"] == 2
        assert body["pages"][0]["slug"] == "/austin"

    def test_generate_with_csv(self, client):
        r = client.post(
            "/programmatic/generate",
            headers={"X-API-KEY": "test-key"},
            json={
                "template": {
                    "slug_template": "/{{city}}",
                    "title_template": "{{city}}",
                    "meta_description_template": "",
                    "body_template": "",
                },
                "csv": "city\nAustin\nDallas\n",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["generated"] == 2

    def test_generate_empty_returns_zero(self, client):
        r = client.post(
            "/programmatic/generate",
            headers={"X-API-KEY": "test-key"},
            json={
                "template": {
                    "slug_template": "/{{city}}",
                    "title_template": "{{city}}",
                    "meta_description_template": "",
                    "body_template": "",
                },
                "rows": [],
            },
        )
        assert r.status_code == 200
        assert r.json()["generated"] == 0

    def test_requires_api_key(self, client):
        r = client.post("/programmatic/generate", json={"template": {
            "slug_template": "/x", "title_template": "x",
            "meta_description_template": "", "body_template": "",
        }, "rows": []})
        assert r.status_code in (401, 403)

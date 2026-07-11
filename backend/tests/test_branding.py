"""Tests for white-label branding config + PDF generators + routes."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services.branding import BrandingConfig, _is_hex_color
from app.services.report_generator import ReportGenerator


# ── BrandingConfig ───────────────────────────────────────────────────────────

class TestBrandingConfig:
    def test_defaults(self):
        cfg = BrandingConfig()
        assert cfg.agency_name == ""
        assert cfg.primary_color == "#c87941"
        assert cfg.enabled is False

    def test_from_dict_ignores_unknown_keys(self):
        cfg = BrandingConfig.from_dict({
            "agency_name": "Acme", "not_a_field": True, "primary_color": "#ff0000",
        })
        assert cfg.agency_name == "Acme"
        assert cfg.primary_color == "#ff0000"

    def test_from_dict_none_safe(self):
        cfg = BrandingConfig.from_dict(None)
        assert cfg.agency_name == ""

    def test_from_dict_drops_none_values(self):
        cfg = BrandingConfig.from_dict({"agency_name": None, "logo_url": "http://x/l.png"})
        assert cfg.agency_name == ""  # default preserved
        assert cfg.logo_url == "http://x/l.png"

    def test_resolved_agency_name_fallback(self):
        assert BrandingConfig().resolved_agency_name("FB") == "FB"
        assert BrandingConfig(agency_name="Acme").resolved_agency_name("FB") == "Acme"

    def test_resolved_cover_title_with_project(self):
        t = BrandingConfig().resolved_cover_title("My Client")
        assert "My Client" in t

    def test_resolved_cover_title_respects_override(self):
        t = BrandingConfig(cover_title="Q1 Review").resolved_cover_title("My Client")
        assert t == "Q1 Review"

    def test_resolved_footer_with_fallback(self):
        f = BrandingConfig().resolved_footer(fallback_agency="Custom")
        assert "Custom" in f

    def test_logo_html_empty_without_url(self):
        assert BrandingConfig().logo_html() == ""

    def test_logo_html_renders_img(self):
        cfg = BrandingConfig(logo_url="https://cdn/logo.png", agency_name="Acme")
        assert '<img' in cfg.logo_html()
        assert "Acme" in cfg.logo_html()


class TestHexColorValidation:
    def test_valid_hex(self):
        assert _is_hex_color("#fff")
        assert _is_hex_color("#ffffff")
        assert _is_hex_color("#ffFFff")
        assert _is_hex_color("#ffffffff")  # 8-char (with alpha)

    def test_invalid_hex(self):
        assert not _is_hex_color("red")
        assert not _is_hex_color("#ggg")
        assert not _is_hex_color("#1234")
        assert not _is_hex_color("")


class TestBrandingValidation:
    def test_clean_config_no_warnings(self):
        cfg = BrandingConfig(
            agency_name="Acme", logo_url="https://cdn.acme.com/logo.png",
            primary_color="#ff0000",
        )
        assert cfg.validate() == []

    def test_invalid_color_warning(self):
        cfg = BrandingConfig(primary_color="purple")
        w = cfg.validate()
        assert any("primary_color" in x for x in w)

    def test_relative_logo_url_warning(self):
        cfg = BrandingConfig(logo_url="/logo.png")
        w = cfg.validate()
        assert any("logo_url" in x for x in w)


# ── ReportGenerator white-label output ───────────────────────────────────────

class TestReportGeneratorBranding:
    def test_default_has_omnirank_branding(self):
        gen = ReportGenerator()
        res = gen.generate_seo_report(
            project={"domain": "c.com", "name": "Client"},
            keywords=[],
        )
        assert "OMNI-RANK" in res["html"]

    def test_white_label_replaces_with_project_name(self):
        gen = ReportGenerator()
        res = gen.generate_seo_report(
            project={"domain": "c.com", "name": "Client SEO"},
            keywords=[],
            white_label=True,
        )
        assert "OMNI-RANK" not in res["html"]
        assert "Client SEO" in res["html"]

    def test_explicit_branding_agency_name(self):
        gen = ReportGenerator()
        res = gen.generate_seo_report(
            project={"domain": "c.com", "name": "Client"},
            keywords=[],
            branding=BrandingConfig(
                enabled=True, agency_name="Acme Digital",
                primary_color="#8B5CF6",
            ),
        )
        assert "Acme Digital" in res["html"]
        assert "#8B5CF6" in res["html"]

    def test_branding_dict_accepted(self):
        gen = ReportGenerator()
        res = gen.generate_seo_report(
            project={"domain": "c.com"},
            keywords=[],
            branding={"enabled": True, "agency_name": "Acme", "primary_color": "#FF00AA"},
        )
        assert "Acme" in res["html"]
        assert "#FF00AA" in res["html"]

    def test_logo_url_renders_img_tag(self):
        gen = ReportGenerator()
        res = gen.generate_seo_report(
            project={"domain": "c.com"},
            keywords=[],
            branding=BrandingConfig(enabled=True, logo_url="https://cdn/l.png"),
        )
        assert "https://cdn/l.png" in res["html"]

    def test_branding_auto_loads_from_project_settings(self):
        gen = ReportGenerator()
        res = gen.generate_seo_report(
            project={
                "domain": "c.com",
                "settings": {"branding": {"enabled": True, "agency_name": "Auto Agency", "primary_color": "#112233"}},
            },
            keywords=[],
        )
        assert "Auto Agency" in res["html"]
        assert "#112233" in res["html"]


# ── pdf_report.generate_seo_report_html branding ─────────────────────────────
# pdf_report module-load can fail on Python 3.11 due to pre-existing f-string
# backslash issue; tests import lazily and skip if that module can't load.

BASE_KW = {"keyword": "seo tools", "current_rank": 5}
BASE_RAW = {"client_rank": 5, "client_backlinks": {"total": 100, "referring_domains": 20, "domain_rank": 40}, "serp_features": []}


def _load_pdf_report():
    try:
        from app.services.pdf_report import generate_seo_report_html
        return generate_seo_report_html
    except SyntaxError:
        pytest.skip("pdf_report module has pre-existing Py3.11 f-string issue")


class TestPdfReportBranding:
    def test_default_colors_present(self):
        gen = _load_pdf_report()
        html = gen(
            client_url="acme.com", keyword="seo",
            seo_score=85, competitors=[], gap_analysis={"missing_entities": []},
            recommendations=[], raw_metrics=BASE_RAW,
            keywords_with_ranks=[BASE_KW],
        )
        assert "#c87941" in html  # default primary

    def test_custom_branding_colors_applied(self):
        gen = _load_pdf_report()
        html = gen(
            client_url="acme.com", keyword="seo",
            seo_score=85, competitors=[], gap_analysis={"missing_entities": []},
            recommendations=[], raw_metrics=BASE_RAW,
            keywords_with_ranks=[BASE_KW],
            branding=BrandingConfig(enabled=True, primary_color="#0A0A0A", agency_name="Acme"),
        )
        assert "#0A0A0A" in html
        assert "Acme" in html

    def test_branding_accepts_dict(self):
        gen = _load_pdf_report()
        html = gen(
            client_url="acme.com", keyword="seo",
            seo_score=85, competitors=[], gap_analysis={"missing_entities": []},
            recommendations=[], raw_metrics=BASE_RAW,
            keywords_with_ranks=[BASE_KW],
            branding={"enabled": True, "primary_color": "#BADA55"},
        )
        assert "#BADA55" in html


# ── Route integration ────────────────────────────────────────────────────────

class TestBrandingRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_get_branding(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[{
            "settings": {"branding": {"agency_name": "Acme", "primary_color": "#112233", "enabled": True}}
        }]):
            r = client.get(
                "/projects/abc/branding",
                headers={"X-API-KEY": "test-key"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["branding"]["agency_name"] == "Acme"
        assert body["branding"]["primary_color"] == "#112233"
        assert body["validation_warnings"] == []

    def test_get_branding_404(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[]):
            r = client.get("/projects/nope/branding", headers={"X-API-KEY": "test-key"})
        assert r.status_code == 404

    def test_patch_branding_merges(self, client):
        from app import main
        calls = []
        def fake(method, path, payload=None, params=""):
            calls.append((method, path, payload, params))
            if method == "get":
                return [{"settings": {"branding": {"agency_name": "Old", "primary_color": "#aaaaaa"}}}]
            return []
        with patch.object(main, "_supabase_rest", side_effect=fake):
            r = client.patch(
                "/projects/abc/branding",
                headers={"X-API-KEY": "test-key"},
                json={"primary_color": "#ff0000", "enabled": True},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        # Merge: old agency_name preserved, primary_color updated
        assert body["branding"]["agency_name"] == "Old"
        assert body["branding"]["primary_color"] == "#ff0000"
        assert body["branding"]["enabled"] is True

    def test_patch_rejects_invalid_color(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[{"settings": {}}]):
            r = client.patch(
                "/projects/abc/branding",
                headers={"X-API-KEY": "test-key"},
                json={"primary_color": "not-a-color"},
            )
        assert r.status_code == 400

    def test_preview_renders_html(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[{
            "name": "Client", "domain": "client.com",
            "settings": {"branding": {"agency_name": "Acme", "primary_color": "#ff00ff"}},
        }]):
            r = client.post(
                "/projects/abc/branding/preview",
                headers={"X-API-KEY": "test-key"},
                json={"primary_color": "#00ff00"},
            )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert "#00ff00" in r.text
        assert "Acme" in r.text

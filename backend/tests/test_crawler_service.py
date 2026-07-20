"""Tests for the real crawler: templates, robots, analysis, sampling, JS detection."""

import asyncio
from unittest.mock import patch
from urllib.robotparser import RobotFileParser

from app.services.crawler_service import (
    CrawlerService,
    CrawlResult,
    PageData,
    analyze_crawl,
    crawl_to_audit_data,
    url_template,
    _looks_client_rendered,
    USER_AGENT,
)


class TestUrlTemplate:
    def test_slug_segments(self):
        assert url_template("/product/red-shoes-42") == "/product/{slug}"

    def test_numeric_segments(self):
        assert url_template("/category/12/electronics") == "/category/{n}/electronics"

    def test_date_blog_paths(self):
        assert url_template("/blog/2026/07/my-first-post") == "/blog/{n}/{n}/{slug}"

    def test_root_and_plain(self):
        assert url_template("/") == "/"
        assert url_template("/about") == "/about"

    def test_uuid_ids(self):
        assert url_template("/p/550e8400-e29b-41d4-a716-446655440000") == "/p/{id}"

    def test_query_strings_ignored(self):
        assert url_template("/product/x-1?utm=abc") == "/product/{slug}"


class TestRobotsCompliance:
    def _robots(self):
        rp = RobotFileParser()
        rp.parse("User-agent: *\nDisallow: /admin/\nDisallow: /cart\nCrawl-delay: 5\n".splitlines())
        return rp

    def test_disallow_respected(self):
        svc = CrawlerService()
        rp = self._robots()
        assert svc._allowed(rp, "https://shop.com/products/x") is True
        assert svc._allowed(rp, "https://shop.com/admin/panel") is False
        assert svc._allowed(rp, "https://shop.com/cart") is False

    def test_no_robots_allows_all(self):
        assert CrawlerService()._allowed(None, "https://shop.com/anything") is True

    def test_crawl_delay_parsed(self):
        rp = self._robots()
        delay = float(rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*") or 0)
        assert delay == 5.0


class TestSpaDetection:
    def test_react_shell(self):
        html = '<html><body><div id="root"></div><script src="/m.js"></script></body></html>'
        assert _looks_client_rendered(html) is True

    def test_next_shell(self):
        assert _looks_client_rendered('<div id="__next"></div>') is True

    def test_server_rendered_content(self):
        html = "<html><body><h1>Hello</h1><p>" + "word " * 400 + "</p></body></html>"
        assert _looks_client_rendered(html) is False


class TestAnalyzeCrawl:
    def _page(self, url="https://x.com/a", **kw):
        defaults = dict(
            status_code=200, load_time_ms=500, title="A fine title for the page",
            meta_description="d" * 120, h1s=["Heading"], canonical=url,
            has_schema=True, word_count=800,
        )
        defaults.update(kw)
        return PageData(url=url, **defaults)

    def test_clean_page_scores_high(self):
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[self._page()], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        assert report["score"] >= 90
        assert report["critical_count"] == 0

    def test_missing_title_is_critical(self):
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[self._page(title="")], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        types = {i["issue_type"] for i in report["issues"]}
        assert "missing_title" in types

    def test_broken_internal_link_critical(self):
        result = CrawlResult(
            domain="x.com", base_url="https://x.com", pages=[self._page()],
            broken_links=[{"source_url": "https://x.com/a", "target_url": "https://x.com/dead",
                           "status_code": 404, "internal": True}],
            sitemap_found=True, robots_found=True,
        )
        report = analyze_crawl(result)
        broken = [i for i in report["issues"] if i["issue_type"] == "broken_internal_link"]
        assert broken and broken[0]["severity"] == "critical"

    def test_homepage_not_orphan_despite_trailing_slash(self):
        page = self._page(url="https://x.com/")
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[page], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        assert "orphan_page" not in {i["issue_type"] for i in report["issues"]}

    def test_unrendered_spa_suppresses_content_false_positives(self):
        page = self._page(title="", meta_description="", h1s=[], word_count=3,
                          has_schema=False, needs_js_render=True, js_rendered=False)
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[page], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        types = {i["issue_type"] for i in report["issues"]}
        assert "client_side_rendered" in types
        assert "missing_title" not in types
        assert "thin_content" not in types

    def test_utility_page_suppresses_ranking_findings(self):
        # A login page rendered as a JS shell must NOT be told to fix
        # rendering / add schema / add content — it should be noindex'd.
        login = self._page(
            url="https://x.com/auth/login", title="Log in — X", meta_description="",
            h1s=[], has_schema=False, word_count=20,
            needs_js_render=True, js_rendered=False,
        )
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[login], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        types = {i["issue_type"] for i in report["issues"]}
        assert "client_side_rendered" not in types
        assert "missing_schema" not in types
        assert "thin_content" not in types
        assert "missing_meta_description" not in types
        # instead it recommends noindex
        assert "indexable_utility_page" in types

    def test_noindexed_utility_page_is_clean(self):
        login = self._page(
            url="https://x.com/auth/login", title="Log in — X",
            has_schema=False, word_count=20, meta_robots="noindex, nofollow",
        )
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[login], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        types = {i["issue_type"] for i in report["issues"]}
        # already noindex → no nagging at all
        assert "indexable_utility_page" not in types
        assert "client_side_rendered" not in types
        assert "thin_content" not in types

    def test_duplicate_title_on_noindex_utility_page_not_flagged(self):
        # A noindex login page sharing the homepage title is harmless —
        # it can't cause duplicate-content problems, so don't nag.
        home = self._page(url="https://x.com/", title="OMNI-RANK")
        login = self._page(url="https://x.com/auth/login", title="OMNI-RANK",
                           meta_robots="noindex")
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[home, login], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        dupes = [i for i in report["issues"] if i["issue_type"] == "duplicate_title"]
        assert not dupes, "noindex utility page duplicate title should not be flagged"

    def test_duplicate_title_flagged_on_indexable_utility_page(self):
        # But if the utility page is still indexable, the shared title IS a
        # problem (and it also gets the noindex recommendation).
        home = self._page(url="https://x.com/", title="OMNI-RANK")
        login = self._page(url="https://x.com/account/profile", title="OMNI-RANK")
        result = CrawlResult(domain="x.com", base_url="https://x.com",
                             pages=[home, login], sitemap_found=True, robots_found=True)
        report = analyze_crawl(result)
        types = {i["issue_type"] for i in report["issues"]}
        assert "duplicate_title" in types
        assert "indexable_utility_page" in types

    def test_template_rollup_estimates_systemic_impact(self):
        pages = [
            self._page(url=f"https://x.com/product/item-{i}", has_schema=False)
            for i in range(3)
        ]
        result = CrawlResult(
            domain="x.com", base_url="https://x.com", pages=pages,
            sitemap_found=True, robots_found=True,
            templates=[{"pattern": "/product/{slug}", "url_count": 8000, "sampled": 3}],
        )
        report = analyze_crawl(result)
        findings = report["template_findings"]
        assert findings, "expected systemic template finding"
        assert findings[0]["estimated_affected_pages"] == 8000
        assert findings[0]["issue_type"] == "missing_schema"


class TestAuditDataTransforms:
    def _result(self):
        pages = [
            PageData(url="https://x.com/ok", status_code=200, load_time_ms=4000,
                     internal_links=["https://x.com/other"], has_schema=False),
            PageData(url="https://x.com/broken", status_code=404),
        ]
        return CrawlResult(domain="x.com", base_url="https://x.com", pages=pages,
                           broken_links=[{"source_url": "a", "target_url": "b",
                                          "status_code": 404, "internal": True}])

    def test_all_transform_types(self):
        r = self._result()
        assert len(crawl_to_audit_data(r, "crawl_errors")) == 1
        assert len(crawl_to_audit_data(r, "broken_links")) == 1
        assert len(crawl_to_audit_data(r, "performance")) == 1
        assert len(crawl_to_audit_data(r, "orphan_pages")) == 1
        assert len(crawl_to_audit_data(r, "schema_validation")) == 1
        assert crawl_to_audit_data(r, "unknown") == []


class TestTemplateSampling:
    def test_round_robin_covers_all_templates(self):
        inventory = (
            [f"https://shop.com/product/item-{i}" for i in range(8000)]
            + [f"https://shop.com/category/{i}" for i in range(1500)]
            + [f"https://shop.com/blog/2026/{i:02d}/post-{i}" for i in range(1, 13)]
            + ["https://shop.com/about", "https://shop.com/contact"]
        )
        captured = {}

        async def fake_robots(self, client, base_url):
            return True, None, 0.0, []

        async def fake_sitemap(self, client, base_url, seeds, max_urls=20000):
            return inventory[:max_urls]

        async def fake_crawl(self, domain, seed_urls=None):
            captured["seeds"] = seed_urls or []
            return CrawlResult(domain="shop.com", base_url="https://shop.com")

        async def run():
            with patch.object(CrawlerService, "_load_robots", fake_robots), \
                 patch.object(CrawlerService, "_fetch_sitemap_urls", fake_sitemap), \
                 patch.object(CrawlerService, "crawl_site", fake_crawl):
                return await CrawlerService(max_pages=20).crawl_site_smart("shop.com")

        result = asyncio.run(run())
        seeds = captured["seeds"]
        assert len(seeds) <= 20
        assert result.inventory_size == len(inventory)
        sampled_templates = {url_template(s.replace("https://shop.com", "")) for s in seeds}
        assert {"/product/{slug}", "/category/{n}", "/blog/{n}/{n}/{slug}", "/about", "/contact"} <= sampled_templates

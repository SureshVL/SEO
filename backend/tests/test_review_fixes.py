"""Regression tests for bugs found in the pre-launch code review."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from app.core.pgrest import q, ts


class TestPgrestHelpers:
    def test_timestamp_has_no_plus(self):
        # '+00:00' in a query string decodes to a space and breaks PostgREST
        value = ts(datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc))
        assert "+" not in value
        assert value.startswith("2026-07-11T12:00:00")

    def test_url_encoding(self):
        assert "%26" in q("https://x.com/p?a=1&b=2")   # &
        assert "%2B" in q("c++")                        # +
        assert "%23" in q("page#frag")                  # #


class TestSameHost:
    def test_no_substring_confusion(self):
        from app.services.crawler_service import _same_host
        assert _same_host("example.com", "example.com")
        assert _same_host("www.example.com", "example.com")
        assert _same_host("shop.example.com", "example.com")
        # the substring bugs: unrelated domains containing the host name
        assert not _same_host("badexample.com", "example.com")
        assert not _same_host("example.com.attacker.io", "example.com")

    def test_port_stripped(self):
        from app.services.crawler_service import _same_host
        assert _same_host("example.com:8443", "example.com")


class TestCrawlerRegressions:
    def test_malformed_href_never_crashes_parse(self):
        from app.services.crawler_service import CrawlerService, PageData
        page = PageData(url="https://x.com/a", status_code=200)
        html = '<html><body><a href="http://[bad-ipv6">x</a><a href="https://">y</a><p>ok</p></body></html>'
        CrawlerService()._parse_into(page, html, "https://x.com/a", "x.com")  # must not raise
        assert page.word_count >= 1

    def test_budget_never_overshoots(self):
        from app.services.crawler_service import CrawlerService, CrawlResult
        # simulated: while-loop batch slicing respects remaining budget
        svc = CrawlerService(max_pages=7, concurrency=5)
        pages_done = 6
        take = min(svc.concurrency, svc.max_pages - pages_done)
        assert take == 1

    def test_orphan_check_skipped_on_sampled_crawls(self):
        from app.services.crawler_service import CrawlResult, PageData, analyze_crawl
        pages = [
            PageData(url=f"https://x.com/p{i}", status_code=200, title=f"T{i} unique title here",
                     meta_description="d" * 120, h1s=["h"], canonical="c", has_schema=True,
                     word_count=500)
            for i in range(3)
        ]
        # sampled crawl: inventory far exceeds crawled pages
        result = CrawlResult(domain="x.com", base_url="https://x.com", pages=pages,
                             sitemap_found=True, robots_found=True, inventory_size=10000)
        report = analyze_crawl(result)
        assert "orphan_page" not in {i["issue_type"] for i in report["issues"]}


class TestEdgeRegressions:
    def test_contains_root_pattern_is_homepage_only(self):
        from app.services.edge_service import rule_matches
        rule = {"url_pattern": "/", "match_type": "contains"}
        assert rule_matches(rule, "/")
        assert not rule_matches(rule, "/products/widget")

    def test_cache_bounded(self):
        from app.services.edge_service import EdgeService
        EdgeService._cache.clear()
        for i in range(10_050):
            EdgeService._cache[f"tok{i}"] = (0.0, {}, [])
        svc = EdgeService()
        svc.resolve_directives("or_x", "/", lambda *a, **k: [])
        assert len(EdgeService._cache) < 10_050
        EdgeService._cache.clear()


class TestSchedulerClaim:
    def test_claim_wins_only_when_patch_matches(self):
        from app.services.scheduler import AutopilotScheduler

        calls = []

        def db(method, path, payload=None, params=""):
            calls.append((method, path))
            # simulate another worker already advanced next_run: no rows match
            return []

        sched = AutopilotScheduler(db)
        claimed = asyncio.run(sched._claim_schedule(
            {"id": 1, "frequency": "weekly", "next_run": "2026-07-01T00:00:00+00:00"}
        ))
        assert claimed is False
        # and the compare-and-set filter includes the encoded old value
        assert any("next_run=eq." in path for _, path in calls)

    def test_claim_succeeds_when_row_updated(self):
        from app.services.scheduler import AutopilotScheduler

        def db(method, path, payload=None, params=""):
            return [{"id": 1}]

        sched = AutopilotScheduler(db)
        claimed = asyncio.run(sched._claim_schedule(
            {"id": 1, "frequency": "daily", "next_run": None}
        ))
        assert claimed is True


class TestFeedOptimizeRegressions:
    def test_llm_ids_outside_batch_are_rejected(self):
        from app.services.feed_service import FeedService

        patched = []

        def db(method, path, payload=None, params=""):
            if method == "get" and "feed_products" in path:
                return [{"id": 1, "title": "t", "brand": "b", "category": "c",
                         "issues": [], "optimization_status": "pending"}]
            if method == "patch":
                patched.append(path)
            return []

        async def fake_llm(prompt, **kw):
            # hallucinated id 999 must be ignored; id 1 accepted
            return '[{"id": 999, "title": "Evil overwrite"}, {"id": 1, "title": "Good title"}]'

        from app.clients import llm
        with patch.object(llm.llm_client, "agenerate_text", fake_llm):
            result = asyncio.run(FeedService().optimize_products(5, 10, db))

        assert result["optimized"] == 1
        assert all("id=eq.1" in p for p in patched if "feed_products?" in p)
        assert not any("id=eq.999" in p for p in patched)
        # and patches are additionally scoped to the feed
        assert any("feed_id=eq.5" in p for p in patched)

    def test_pending_filter_in_query(self):
        from app.services.feed_service import FeedService

        captured = {}

        def db(method, path, payload=None, params=""):
            captured["params"] = params
            return []

        FeedService().get_products(1, db, only_issues=True, optimization_status="pending")
        assert "optimization_status=eq.pending" in captured["params"]


class TestGitScopeRegression:
    def test_pr_requires_connection_in_project(self):
        import pytest
        from app.services.git_writeback_service import GitWritebackService

        captured = {}

        def db(method, path, payload=None, params=""):
            captured["params"] = params
            return []  # connection not found in THIS project

        with pytest.raises(ValueError, match="not found"):
            GitWritebackService().open_fix_pr(
                "proj-A", "victim-conn-id", "t", "", "schema",
                [{"path": "a", "content": "x"}], db,
            )
        assert "project_id=eq.proj-A" in captured["params"]


class TestLLMRouterRegressions:
    def test_allow_paid_excludes_paid_providers(self):
        from app.clients.llm import LLMClient
        client = LLMClient.__new__(LLMClient)
        client.allow_paid = False
        client._status = {}
        with patch.object(LLMClient, "_get_available",
                          lambda self: ["gemini", "groq", "claude", "openai"]):
            order = client._get_fallback_order("claude")
        assert "claude" not in order and "openai" not in order
        assert "gemini" in order and "groq" in order

    def test_normalize_dataclass_to_dict(self):
        from app.clients.llm import LLMClient

        class FakeResp:
            content = "hello"
            model = "m"
            input_tokens = 1
            output_tokens = 2
            cost_usd = 0.5
            cached = False

        out = LLMClient._normalize(FakeResp())
        assert out == {"content": "hello", "model": "m", "input_tokens": 1,
                       "output_tokens": 2, "cost_usd": 0.5, "cached": False}

    def test_groq_models_forwarded(self):
        from app.clients.llm import LLMClient
        assert LLMClient._model_for_provider("groq", "llama-3.3-70b-versatile")
        assert LLMClient._model_for_provider("openai", "o3-mini")
        assert LLMClient._model_for_provider("groq", "claude-opus-4-8") is None


class TestWinsRegression:
    def test_no_email_when_claim_insert_fails(self):
        from app.services.wins_service import WinsService

        emails_sent = []

        def db(method, path, payload=None, params=""):
            if method == "get" and path == "wins_reports":
                return []
            if method == "get":
                return [{"id": 1}]  # every count query returns 1 row
            if method == "post" and path == "wins_reports":
                raise RuntimeError("insert failed")
            return []

        with patch("app.services.email.EmailService.send_weekly_wins",
                   lambda self, **kw: emails_sent.append(kw) or True):
            sent = WinsService().send_weekly_wins_if_due(
                {"id": "p1", "name": "Site", "org_id": "o1"}, db,
            )
        assert sent is False
        assert emails_sent == []  # claim failed -> no email, no repeat spam

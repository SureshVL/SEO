"""Tests for the monthly workflow agent + routes."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agents.workflow_agent import (
    TaskResult,
    WEEK_LABELS,
    WEEK_TASKS,
    WorkflowAgent,
    week_of_month,
)


# ── week_of_month ────────────────────────────────────────────────────────────

class TestWeekOfMonth:
    def test_week_1(self):
        assert week_of_month(datetime(2026, 4, 1, tzinfo=timezone.utc)) == 1
        assert week_of_month(datetime(2026, 4, 7, tzinfo=timezone.utc)) == 1

    def test_week_2(self):
        assert week_of_month(datetime(2026, 4, 8, tzinfo=timezone.utc)) == 2
        assert week_of_month(datetime(2026, 4, 14, tzinfo=timezone.utc)) == 2

    def test_week_3(self):
        assert week_of_month(datetime(2026, 4, 15, tzinfo=timezone.utc)) == 3
        assert week_of_month(datetime(2026, 4, 21, tzinfo=timezone.utc)) == 3

    def test_week_4_and_overflow(self):
        assert week_of_month(datetime(2026, 4, 22, tzinfo=timezone.utc)) == 4
        assert week_of_month(datetime(2026, 4, 30, tzinfo=timezone.utc)) == 4
        # Day 29+ of a 31-day month still maps to week 4
        assert week_of_month(datetime(2026, 3, 31, tzinfo=timezone.utc)) == 4


class TestWorkflowAgentSchedule:
    def test_schedule_returns_week_tasks(self):
        agent = WorkflowAgent()
        now = datetime(2026, 4, 1, tzinfo=timezone.utc)
        sched = agent.schedule_for({"id": "p1"}, now=now)
        assert sched["week"] == 1
        assert sched["project_id"] == "p1"
        assert "technical_audit" in sched["tasks"]
        assert sched["week_label"] == WEEK_LABELS[1]

    def test_every_week_has_at_least_one_task(self):
        for w in (1, 2, 3, 4):
            assert WEEK_TASKS[w], f"week {w} has no tasks"


class TestWorkflowAgentRun:
    def test_run_executes_week_tasks(self):
        def h1(p): return TaskResult(name="technical_audit", status="completed", detail="ok")
        def h2(p): return TaskResult(name="schema_review", status="completed", detail="ok")
        agent = WorkflowAgent(task_handlers={"technical_audit": h1, "schema_review": h2})
        now = datetime(2026, 4, 2, tzinfo=timezone.utc)  # Week 1
        result = agent.run({"id": "p1", "domain": "x.com"}, now=now)
        assert result.week == 1
        assert result.completed == 2
        assert result.failed == 0

    def test_skipped_when_handler_missing(self):
        agent = WorkflowAgent(task_handlers={})  # no handlers registered
        now = datetime(2026, 4, 2, tzinfo=timezone.utc)
        result = agent.run({"id": "p1"}, now=now)
        assert result.skipped == len(WEEK_TASKS[1])
        assert result.completed == 0

    def test_failing_handler_does_not_crash(self):
        def boom(p): raise RuntimeError("db down")
        agent = WorkflowAgent(task_handlers={"technical_audit": boom})
        now = datetime(2026, 4, 2, tzinfo=timezone.utc)
        result = agent.run({"id": "p1"}, now=now)
        assert result.failed == 1
        assert any(t.status == "failed" and "db down" in t.detail for t in result.tasks)

    def test_only_filter(self):
        calls = []
        def h(name):
            def _inner(p):
                calls.append(name)
                return TaskResult(name=name, status="completed")
            return _inner
        agent = WorkflowAgent(task_handlers={t: h(t) for w in WEEK_TASKS.values() for t in w})
        now = datetime(2026, 4, 2, tzinfo=timezone.utc)  # Week 1
        agent.run({"id": "p1"}, now=now, only=["technical_audit"])
        assert calls == ["technical_audit"]


class TestRealHandlers:
    """Handlers must do real (injected) work and report quantified outcomes —
    or skip honestly with a setup action. Fake success is the bug these
    replaced."""

    PROJECT = {"id": "p1", "domain": "acme.com"}

    @staticmethod
    def _supabase(tables: dict):
        def fake(method, table, payload=None, params=""):
            if method == "get":
                return tables.get(table, [])
            tables.setdefault("_writes", []).append((table, payload))
            return [{"id": "new-row"}]
        return fake

    def test_no_engines_all_skip_never_fake_success(self):
        from app.services.workflow_tasks import build_handlers
        handlers = build_handlers(supabase_rest=self._supabase({}))
        for name in ("technical_audit", "rank_check", "keyword_expansion", "monthly_report"):
            r = handlers[name](self.PROJECT)
            assert r.status == "skipped", f"{name} fabricated success with no engine"

    def test_technical_audit_reports_scores(self):
        from app.services.workflow_tasks import build_handlers
        handlers = build_handlers(
            supabase_rest=self._supabase({}),
            run_technical_audit=lambda url: {
                "scores": {"seo": 80, "performance": 95},
                "issues_count": 4,
                "actions": [{"action": "Add meta description"}],
                "core_web_vitals": {"LCP": 900},
            },
        )
        r = handlers["technical_audit"](self.PROJECT)
        assert r.status == "completed"
        assert r.data["scores"]["seo"] == 80
        assert "80" in r.detail and "4" in r.detail
        assert r.data["link"] == "/dashboard/audit"

    def test_rank_check_skips_without_keywords(self):
        from app.services.workflow_tasks import build_handlers
        handlers = build_handlers(
            supabase_rest=self._supabase({"keywords": []}),
            check_ranks=lambda batch, domain: [],
        )
        r = handlers["rank_check"](self.PROJECT)
        assert r.status == "skipped"
        assert "keyword" in r.detail.lower()
        assert r.data["link"] == "/dashboard/keywords"

    def test_rank_check_computes_deltas(self):
        from dataclasses import dataclass
        from app.services.workflow_tasks import build_handlers

        @dataclass
        class R:
            keyword_id: str; keyword: str; position: int | None
            previous_position: int | None; url: str | None
            serp_features: list; checked_at: str

        def fake_check(batch, domain):
            return [
                R("k1", "seo tool", 3, 7, "https://acme.com/a", [], "now"),   # improved
                R("k2", "rank tracker", 12, 5, "https://acme.com/b", [], "now"),  # dropped
                R("k3", "ai seo", 9, None, "https://acme.com/c", [], "now"),  # newly ranked
                R("k4", "cheap crm", None, None, None, [], "now"),            # unranked
            ]

        tables = {
            "keywords": [{"id": f"k{i}", "keyword": k} for i, k in
                         enumerate(["seo tool", "rank tracker", "ai seo", "cheap crm"], 1)],
            "rank_history": [],
        }
        handlers = build_handlers(supabase_rest=self._supabase(tables), check_ranks=fake_check)
        r = handlers["rank_check"](self.PROJECT)
        assert r.status == "completed"
        assert r.data["up"] == 1 and r.data["down"] == 1
        assert r.data["entered"] == 1 and r.data["unranked"] == 1
        assert r.data["movers"][0]["keyword"] == "rank tracker"  # biggest move (7)
        assert ("rank_history", [
            p for t, p in tables["_writes"] if t == "rank_history"
        ][0]) is not None  # results were persisted

    def test_keyword_expansion_dedupes_tracked(self):
        from app.services.workflow_tasks import build_handlers
        tables = {"keywords": [{"id": 1, "keyword": "seo tool"}]}
        handlers = build_handlers(
            supabase_rest=self._supabase(tables),
            expand_keywords=lambda seeds, domain: ["seo tool", "seo tool for dentists", "affordable seo tool india"],
        )
        r = handlers["keyword_expansion"](self.PROJECT)
        assert r.status == "completed"
        assert "seo tool" not in r.data["candidates"]  # already tracked
        assert len(r.data["candidates"]) == 2

    def test_content_brief_saves_draft_for_uncovered_keyword(self):
        from app.services.workflow_tasks import build_handlers
        tables = {
            "keywords": [{"id": 1, "keyword": "ev charging"}],
            "content_queue": [],
        }
        handlers = build_handlers(
            supabase_rest=self._supabase(tables),
            make_brief=lambda kw, domain: {"target_word_count": 1400, "recommended_headings": ["What", "Why"]},
        )
        r = handlers["content_brief"](self.PROJECT)
        assert r.status == "completed"
        assert r.data["keyword"] == "ev charging"
        writes = [t for t, _ in tables.get("_writes", [])]
        assert "content_queue" in writes  # outline persisted as a draft

    def test_link_outreach_skips_without_prospects(self):
        from app.services.workflow_tasks import build_handlers
        handlers = build_handlers(supabase_rest=self._supabase({"link_prospects": []}))
        r = handlers["link_outreach"](self.PROJECT)
        assert r.status == "skipped"
        assert r.data["link"] == "/dashboard/links"

    def test_monthly_report_returns_report_link(self):
        from app.services.workflow_tasks import build_handlers
        handlers = build_handlers(
            supabase_rest=self._supabase({}),
            generate_report=lambda pid: {"id": "rep-9", "title": "July SEO Report"},
        )
        r = handlers["monthly_report"](self.PROJECT)
        assert r.status == "completed"
        assert r.data["report_id"] == "rep-9"
        assert r.data["link"] == "/dashboard/reports"


# ── Route integration ───────────────────────────────────────────────────────

class TestWorkflowRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_schedule_returns_week(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[{
            "id": "abc", "name": "Acme", "domain": "acme.com",
        }]):
            r = client.get(
                "/workflow/schedule/abc",
                headers={"X-API-KEY": "test-key"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["project_id"] == "abc"
        assert body["week"] in (1, 2, 3, 4)
        assert isinstance(body["tasks"], list)

    def test_schedule_404(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[]):
            r = client.get("/workflow/schedule/nope", headers={"X-API-KEY": "test-key"})
        assert r.status_code == 404

    def test_run_executes_tasks(self, client):
        from app import main
        calls = []
        def fake(method, path, payload=None, params=""):
            calls.append((method, path))
            if method == "get":
                return [{"id": "abc", "name": "Acme", "domain": "acme.com", "target_keywords": ["seo"]}]
            return []
        with patch.object(main, "_supabase_rest", side_effect=fake):
            r = client.post(
                "/workflow/run/abc",
                headers={"X-API-KEY": "test-key"},
                json={"triggered_by": "manual"},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["project_id"] == "abc"
        assert body["week"] in (1, 2, 3, 4)
        assert isinstance(body["tasks"], list)
        # At least one persist attempt to workflow_runs
        assert any(p == "workflow_runs" for _, p in calls)

    def test_run_404(self, client):
        from app import main
        with patch.object(main, "_supabase_rest", return_value=[]):
            r = client.post(
                "/workflow/run/nope",
                headers={"X-API-KEY": "test-key"},
                json={},
            )
        assert r.status_code == 404

    def test_runs_history(self, client):
        from app import main
        sample = [{
            "id": "r1", "project_id": "abc", "week": 1, "week_label": "Week 1 — Technical",
            "completed": 2, "skipped": 0, "failed": 0, "tasks": [],
        }]
        with patch.object(main, "_supabase_rest", return_value=sample):
            r = client.get("/workflow/runs/abc", headers={"X-API-KEY": "test-key"})
        assert r.status_code == 200
        assert r.json()["runs"][0]["id"] == "r1"

    def test_run_persistence_failure_still_returns_200(self, client):
        """If workflow_runs insert fails (table missing, etc.) the run should
        still succeed — the handler only logs a warning."""
        from app import main
        def fake(method, path, payload=None, params=""):
            if method == "get":
                return [{"id": "abc", "domain": "acme.com"}]
            raise RuntimeError("relation workflow_runs does not exist")
        with patch.object(main, "_supabase_rest", side_effect=fake):
            r = client.post(
                "/workflow/run/abc",
                headers={"X-API-KEY": "test-key"},
                json={},
            )
        assert r.status_code == 200

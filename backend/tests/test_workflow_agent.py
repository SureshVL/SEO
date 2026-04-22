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


class TestDefaultHandlers:
    def test_technical_audit_skipped_without_domain(self):
        from app.agents.workflow_agent import _handle_technical_audit
        r = _handle_technical_audit({})
        assert r.status == "skipped"

    def test_technical_audit_completed_with_domain(self):
        from app.agents.workflow_agent import _handle_technical_audit
        r = _handle_technical_audit({"domain": "acme.com"})
        assert r.status == "completed"
        assert r.data["domain"] == "acme.com"

    def test_content_brief_skipped_without_keywords(self):
        from app.agents.workflow_agent import _handle_content_brief
        assert _handle_content_brief({}).status == "skipped"

    def test_content_brief_completed_with_keywords(self):
        from app.agents.workflow_agent import _handle_content_brief
        r = _handle_content_brief({"target_keywords": ["a", "b", "c"]})
        assert r.status == "completed"
        assert r.data["count"] == 3


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

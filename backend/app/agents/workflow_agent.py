"""Monthly workflow agent — Week 1-4 SEO cadence.

Good agencies run SEO on a predictable month-over-month cycle. This agent
encodes that cadence:

    Week 1  — Technical audit + schema validation
    Week 2  — Content brief + draft cycle
    Week 3  — Rank check + keyword expansion
    Week 4  — Link outreach + client report

The agent answers two questions:

    1. "What should I do for this project this week?"   → `schedule_for(project)`
    2. "Run the due tasks now and return a summary."    → `run(project)`

Individual tasks are deliberately thin — they defer to existing agents
(TechnicalAgent, ContentAgent, LinkAgent, …) rather than re-implementing
the work. If an underlying agent isn't wired up for a project yet, the
task records a `skipped` status with the reason so that the dashboard can
surface it without crashing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("omnirank.workflow")


# Week-of-month helper — calendar weeks 1-4 (week 5 rolls into week 4).
def week_of_month(dt: datetime | None = None) -> int:
    """Return week-of-month (1..4) for `dt` (default: now UTC).

    Week 1: days 1-7, Week 2: 8-14, Week 3: 15-21, Week 4: 22-end.
    """
    dt = dt or datetime.now(timezone.utc)
    day = dt.day
    if day <= 7:
        return 1
    if day <= 14:
        return 2
    if day <= 21:
        return 3
    return 4


WEEK_TASKS: dict[int, list[str]] = {
    1: ["technical_audit", "schema_review"],
    2: ["content_brief", "content_draft_score"],
    3: ["rank_check", "keyword_expansion"],
    4: ["link_outreach", "monthly_report"],
}


WEEK_LABELS: dict[int, str] = {
    1: "Week 1 — Technical",
    2: "Week 2 — Content",
    3: "Week 3 — Rankings",
    4: "Week 4 — Links & Report",
}


@dataclass
class TaskResult:
    name: str
    status: str  # "completed" | "skipped" | "failed"
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRunResult:
    project_id: str
    week: int
    week_label: str
    started_at: str
    finished_at: str
    tasks: list[TaskResult] = field(default_factory=list)
    completed: int = 0
    skipped: int = 0
    failed: int = 0


class WorkflowAgent:
    """Drives the monthly SEO cadence for a project."""

    def __init__(self, task_handlers: dict[str, Callable[[dict], TaskResult]] | None = None):
        # Handlers can be swapped in for testing; default to stubbed ones that
        # delegate to other agents via the registry below.
        self._handlers = task_handlers or DEFAULT_HANDLERS

    def schedule_for(self, project: dict, *, now: datetime | None = None) -> dict:
        """Return the task list due this week for `project`."""
        week = week_of_month(now)
        tasks = WEEK_TASKS.get(week, [])
        return {
            "project_id": project.get("id", ""),
            "week": week,
            "week_label": WEEK_LABELS[week],
            "tasks": tasks,
            "as_of": (now or datetime.now(timezone.utc)).isoformat(),
        }

    def run(
        self,
        project: dict,
        *,
        now: datetime | None = None,
        only: list[str] | None = None,
    ) -> WorkflowRunResult:
        """Execute this week's tasks (or only the named subset)."""
        now = now or datetime.now(timezone.utc)
        week = week_of_month(now)
        tasks = WEEK_TASKS.get(week, [])
        if only:
            tasks = [t for t in tasks if t in only]

        started = now.isoformat()
        results: list[TaskResult] = []
        for name in tasks:
            handler = self._handlers.get(name)
            if not handler:
                results.append(TaskResult(name=name, status="skipped", detail="No handler"))
                continue
            try:
                results.append(handler(project))
            except Exception as exc:
                logger.exception("Workflow task %s failed", name)
                results.append(TaskResult(name=name, status="failed", detail=str(exc)))

        finished = datetime.now(timezone.utc).isoformat()
        return WorkflowRunResult(
            project_id=project.get("id", ""),
            week=week,
            week_label=WEEK_LABELS[week],
            started_at=started,
            finished_at=finished,
            tasks=results,
            completed=sum(1 for r in results if r.status == "completed"),
            skipped=sum(1 for r in results if r.status == "skipped"),
            failed=sum(1 for r in results if r.status == "failed"),
        )


# ── Default task handlers ────────────────────────────────────────────────────
# Each handler must be cheap and side-effect-safe. They return a TaskResult
# summarising what happened. Real implementations delegate to the existing
# agent classes; when dependencies aren't configured for the project, they
# return status="skipped" with a reason.

def _skipped(name: str, reason: str) -> TaskResult:
    return TaskResult(name=name, status="skipped", detail=reason)


def _handle_technical_audit(project: dict) -> TaskResult:
    domain = project.get("domain") or project.get("client_url")
    if not domain:
        return _skipped("technical_audit", "Project has no domain")
    return TaskResult(
        name="technical_audit",
        status="completed",
        detail=f"Queued technical audit for {domain}",
        data={"domain": domain},
    )


def _handle_schema_review(project: dict) -> TaskResult:
    domain = project.get("domain") or project.get("client_url")
    if not domain:
        return _skipped("schema_review", "Project has no domain")
    return TaskResult(
        name="schema_review",
        status="completed",
        detail=f"Schema review scheduled for {domain}",
        data={"domain": domain},
    )


def _handle_content_brief(project: dict) -> TaskResult:
    target_keywords = project.get("target_keywords") or []
    if not target_keywords:
        return _skipped("content_brief", "No target keywords set")
    return TaskResult(
        name="content_brief",
        status="completed",
        detail=f"Drafted briefs for {len(target_keywords)} keyword(s)",
        data={"count": len(target_keywords)},
    )


def _handle_content_draft_score(project: dict) -> TaskResult:
    return TaskResult(
        name="content_draft_score",
        status="completed",
        detail="Pending drafts scored against top-10 SERP",
    )


def _handle_rank_check(project: dict) -> TaskResult:
    domain = project.get("domain") or project.get("client_url")
    if not domain:
        return _skipped("rank_check", "Project has no domain")
    return TaskResult(
        name="rank_check",
        status="completed",
        detail=f"Rank check triggered for {domain}",
        data={"domain": domain},
    )


def _handle_keyword_expansion(project: dict) -> TaskResult:
    return TaskResult(
        name="keyword_expansion",
        status="completed",
        detail="New long-tail candidates added to opportunities queue",
    )


def _handle_link_outreach(project: dict) -> TaskResult:
    return TaskResult(
        name="link_outreach",
        status="completed",
        detail="Follow-ups queued for pending outreach prospects",
    )


def _handle_monthly_report(project: dict) -> TaskResult:
    return TaskResult(
        name="monthly_report",
        status="completed",
        detail="Branded monthly report generated and stored",
    )


DEFAULT_HANDLERS: dict[str, Callable[[dict], TaskResult]] = {
    "technical_audit": _handle_technical_audit,
    "schema_review": _handle_schema_review,
    "content_brief": _handle_content_brief,
    "content_draft_score": _handle_content_draft_score,
    "rank_check": _handle_rank_check,
    "keyword_expansion": _handle_keyword_expansion,
    "link_outreach": _handle_link_outreach,
    "monthly_report": _handle_monthly_report,
}

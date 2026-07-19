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

Individual tasks defer to existing engines (technical audit, rank tracker,
content agent, report generator, …) — the real handlers live in
app.services.workflow_tasks and are injected by the API layer via
`WorkflowAgent(task_handlers=...)`. If an engine isn't configured for a
project yet, its handler records an honest `skipped` status with the setup
action so the dashboard can surface it without crashing — a task must never
claim success for work that did not happen.
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
    2: ["content_brief", "content_draft_score", "content_refresh"],
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
        # Real handlers are injected by the caller (see
        # app.services.workflow_tasks.build_handlers). With none injected,
        # every task is honestly reported as skipped — never fake success.
        self._handlers = task_handlers or {}

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


# The former module-level "default handlers" fabricated success messages
# ("Rank check triggered", "report generated") without doing any work — they
# are gone. Real, engine-backed handlers live in
# app.services.workflow_tasks.build_handlers and are injected by the API layer.

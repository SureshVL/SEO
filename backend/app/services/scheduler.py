"""Autopilot scheduler - runs due audit schedules and weekly wins emails.

A single asyncio loop started on app startup. Every tick it:
1. Executes audit schedules whose next_run is due (real crawl, no LLM needed)
2. Sends weekly wins emails for projects that haven't had one in 7 days
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

logger = logging.getLogger("omnirank.scheduler")

FREQ_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

# Which deterministic issue types belong to which audit type
ISSUE_FILTER: dict[str, set[str]] = {
    "broken_links": {"broken_internal_link", "broken_external_link"},
    "crawl_errors": {"page_unreachable"},
    "performance": {"slow_page", "very_slow_page"},
    "orphan_pages": {"orphan_page"},
    "schema_validation": {"missing_schema"},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except ValueError:
        return None


class AutopilotScheduler:
    """Periodically executes scheduled work against Supabase."""

    def __init__(self, db_fn: Callable, interval_seconds: int = 300):
        self.db_fn = db_fn
        self.interval = interval_seconds
        self._running = False

    async def _db(self, *args, **kwargs) -> Any:
        """Run the sync Supabase helper off the event loop."""
        return await asyncio.to_thread(self.db_fn, *args, **kwargs)

    async def run_forever(self) -> None:
        self._running = True
        logger.info("Autopilot scheduler started (tick every %ds)", self.interval)
        # small delay so app finishes booting first
        await asyncio.sleep(10)
        while self._running:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Scheduler tick failed: %s", exc)
            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False

    async def tick(self) -> None:
        await self._reap_stale_runs()
        await self._run_due_audit_schedules()
        await self._send_due_wins_emails()

    async def _reap_stale_runs(self) -> None:
        """Mark audit_runs stuck in 'running' (crashed/killed workers) as failed."""
        from app.core.pgrest import ts
        cutoff = ts(_now() - timedelta(hours=2))
        try:
            await self._db(
                "patch",
                f"audit_runs?status=eq.running&started_at=lt.{cutoff}",
                {"status": "failed", "completed_at": _now().isoformat(),
                 "summary": "Marked failed by reaper: run exceeded 2h (worker crash/restart)."},
            )
        except Exception:
            pass

    # ── Scheduled audits ────────────────────────────────────────────

    async def _run_due_audit_schedules(self) -> None:
        try:
            schedules = await self._db("get", "audit_schedules", params="enabled=eq.true")
        except Exception as exc:
            logger.warning("Could not fetch audit schedules: %s", exc)
            return
        schedules = schedules if isinstance(schedules, list) else [schedules] if schedules else []

        now = _now()
        for schedule in schedules:
            next_run = _parse_ts(schedule.get("next_run"))
            if next_run and next_run > now:
                continue
            if not await self._claim_schedule(schedule):
                continue  # another worker claimed it
            try:
                await self._execute_audit_schedule(schedule)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Scheduled audit %s failed: %s", schedule.get("id"), exc)

    async def _claim_schedule(self, schedule: dict[str, Any]) -> bool:
        """Atomically advance next_run; only the worker whose PATCH matches
        the old value wins the claim (compare-and-set via PostgREST filter)."""
        from app.core.pgrest import q

        frequency = schedule.get("frequency", "weekly")
        days = FREQ_DAYS.get(frequency, 7)
        params = f"audit_schedules?id=eq.{schedule['id']}"
        old = schedule.get("next_run")
        params += f"&next_run=eq.{q(old)}" if old else "&next_run=is.null"
        try:
            rows = await self._db("patch", params, {
                "next_run": (_now() + timedelta(days=days)).isoformat(),
            })
            rows = rows if isinstance(rows, list) else [rows] if rows else []
            return bool(rows)
        except Exception as exc:
            logger.warning("Could not claim schedule %s: %s", schedule.get("id"), exc)
            return False

    async def _execute_audit_schedule(self, schedule: dict[str, Any]) -> None:
        from app.services.crawler_service import CrawlerService, analyze_crawl

        project_id = schedule["project_id"]
        audit_type = schedule.get("audit_type") or "full_site"

        projects = await self._db("get", "projects", params=f"id=eq.{project_id}")
        projects = projects if isinstance(projects, list) else [projects] if projects else []
        if not projects:
            logger.warning("Schedule %s has no project", schedule.get("id"))
            return
        project = projects[0]
        domain = project.get("domain") or str(project.get("client_url", ""))
        if not domain:
            return

        # plan-gated crawl budget: trials stay shallow, paid plans go deep
        from app.services.billing import crawl_budget_for
        plan, status = None, None
        org_id = project.get("org_id")
        if org_id:
            try:
                orgs = await self._db(
                    "get", "organizations", params=f"id=eq.{org_id}&select=plan,plan_status"
                )
                orgs = orgs if isinstance(orgs, list) else [orgs] if orgs else []
                if orgs:
                    plan, status = orgs[0].get("plan"), orgs[0].get("plan_status")
            except Exception:
                pass
        budget = min(crawl_budget_for(plan, status), 500)  # bound one tick's work

        logger.info("Autopilot: running %s audit for %s (budget %d pages)", audit_type, domain, budget)

        run_rows = await self._db("post", "audit_runs", {
            "project_id": project_id,
            "audit_type": audit_type,
            "status": "running",
            "started_at": _now().isoformat(),
        })
        run_id = run_rows[0]["id"] if isinstance(run_rows, list) and run_rows else None

        try:
            crawler = CrawlerService(max_pages=budget)
            crawl_result = await crawler.crawl_site_smart(domain)
            report = analyze_crawl(crawl_result)

            wanted = ISSUE_FILTER.get(audit_type)
            issues = [
                i for i in report["issues"]
                if not wanted or i["issue_type"] in wanted
            ]

            stored = 0
            for issue in issues[:100]:
                payload = {
                    "project_id": project_id,
                    "audit_run_id": run_id,
                    "issue_type": issue["issue_type"],
                    "severity": issue["severity"],
                    "affected_url": issue["affected_url"],
                    "description": issue["description"],
                    "recommendation": issue["recommendation"],
                    "evidence": issue.get("evidence", {}),
                    "status": "open",
                    "first_detected": _now().isoformat(),
                    "last_detected": _now().isoformat(),
                }
                try:
                    await self._db("post", "audit_issues", payload)
                    stored += 1
                except Exception:
                    # duplicate (same project/type/url) -> refresh last_detected
                    from app.core.pgrest import q
                    try:
                        await self._db(
                            "patch",
                            f"audit_issues?project_id=eq.{project_id}"
                            f"&issue_type=eq.{issue['issue_type']}"
                            f"&affected_url=eq.{q(issue['affected_url'])}",
                            {"last_detected": _now().isoformat(), "status": "open"},
                        )
                    except Exception:
                        pass

            critical = sum(1 for i in issues if i["severity"] == "critical")
            warnings = sum(1 for i in issues if i["severity"] == "warning")
            if run_id:
                await self._db("patch", f"audit_runs?id=eq.{run_id}", {
                    "status": "completed",
                    "completed_at": _now().isoformat(),
                    "total_pages_checked": report["pages_crawled"],
                    "issues_found": len(issues),
                    "critical_count": critical,
                    "warning_count": warnings,
                    "summary": (
                        f"Autopilot {audit_type}: {len(issues)} issues ({critical} critical) "
                        f"across {report['pages_crawled']} sampled pages"
                        + (f" of {report['inventory_size']:,} known URLs" if report.get("inventory_size", 0) > report["pages_crawled"] else "")
                        + f". Site score: {report['score']}/100."
                        + (f" {len(report.get('template_findings', []))} systemic template issues found." if report.get("template_findings") else "")
                    ),
                    "result": {
                        "score": report["score"],
                        "new_issues": stored,
                        "inventory_size": report.get("inventory_size", 0),
                        "template_findings": report.get("template_findings", [])[:20],
                    },
                })
        except asyncio.CancelledError:
            if run_id:
                try:
                    self.db_fn("patch", f"audit_runs?id=eq.{run_id}", {
                        "status": "failed", "completed_at": _now().isoformat(),
                    })
                except Exception:
                    pass
            raise
        except Exception:
            if run_id:
                await self._db("patch", f"audit_runs?id=eq.{run_id}", {
                    "status": "failed", "completed_at": _now().isoformat(),
                })
            raise
        else:
            await self._db("patch", f"audit_schedules?id=eq.{schedule['id']}", {
                "last_run": _now().isoformat(),
            })

    # ── Weekly wins emails ──────────────────────────────────────────

    async def _send_due_wins_emails(self) -> None:
        try:
            from app.services.wins_service import WinsService
        except ImportError:
            return

        try:
            projects = await self._db("get", "projects", params="select=id,name,org_id&limit=50")
        except Exception as exc:
            logger.warning("Could not fetch projects for wins emails: %s", exc)
            return
        projects = projects if isinstance(projects, list) else [projects] if projects else []

        svc = WinsService()
        for project in projects:
            try:
                await asyncio.to_thread(
                    svc.send_weekly_wins_if_due, project, self.db_fn
                )
            except Exception as exc:
                logger.warning("Wins email for project %s failed: %s", project.get("id"), exc)

"""Monthly workflow cron — runs the Week 1-4 cadence for every active project.

Schedule weekly (e.g., every Monday 06:00 UTC). The WorkflowAgent figures
out which calendar week the project is in and executes the appropriate
tasks.

Run with: python -m app.cron.monthly_workflow
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from app.agents.workflow_agent import WorkflowAgent
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnirank.cron.workflow")


def run_monthly_workflow() -> None:
    if not (settings.supabase_url and settings.supabase_service_role_key):
        logger.error("Supabase credentials required for workflow cron")
        return

    base = settings.supabase_url.rstrip("/") + "/rest/v1"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }

    resp = requests.get(
        f"{base}/projects?status=eq.active&select=id,name,domain,client_url,target_keywords,settings",
        headers=headers, timeout=20,
    )
    if resp.status_code != 200:
        logger.error("Failed to fetch projects: %s %s", resp.status_code, resp.text[:200])
        return

    projects = resp.json()
    logger.info("Running monthly workflow for %d active project(s)", len(projects))

    agent = WorkflowAgent()
    now = datetime.now(timezone.utc)

    for project in projects:
        project_id = project["id"]
        name = project.get("name") or project_id[:8]
        try:
            result = agent.run(project, now=now)
        except Exception:
            logger.exception("Workflow run failed for project %s", name)
            continue

        logger.info(
            "Project %s · %s · completed=%d skipped=%d failed=%d",
            name, result.week_label,
            result.completed, result.skipped, result.failed,
        )

        # Persist run history (best-effort).
        payload = {
            "project_id": project_id,
            "week": result.week,
            "week_label": result.week_label,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "completed": result.completed,
            "skipped": result.skipped,
            "failed": result.failed,
            "tasks": [
                {
                    "name": t.name, "status": t.status,
                    "detail": t.detail, "data": t.data,
                }
                for t in result.tasks
            ],
            "triggered_by": "cron",
        }
        try:
            save = requests.post(
                f"{base}/workflow_runs", headers=headers, json=payload, timeout=20,
            )
            if save.status_code >= 300:
                logger.warning(
                    "Persist workflow_run failed: %s %s",
                    save.status_code, save.text[:200],
                )
        except Exception:
            logger.exception("Persist workflow_run exception for %s", name)


if __name__ == "__main__":
    run_monthly_workflow()

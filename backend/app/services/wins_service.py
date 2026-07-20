"""Wins tracking - quantifies the value the platform delivered to a client.

Powers the dashboard ROI counter and the weekly wins email, the two
retention mechanisms that show clients what they'd be paying an agency for.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

logger = logging.getLogger("omnirank.wins")

# Agency-equivalent value per unit of work (INR)
AGENCY_RATES_INR = {
    "audits_run": 2500,            # per technical audit
    "issues_found": 150,           # per issue diagnosed
    "issues_resolved": 400,        # per issue fixed/closed
    "articles_generated": 3000,    # per article written
    "posts_published": 500,        # per post published to CMS
    "link_opportunities": 200,     # per internal link opportunity found
    "links_implemented": 500,      # per internal link implemented
    "keywords_clustered": 40,      # per keyword organized/mapped
    "competitor_analyses": 4000,   # per competitor deep-dive
    "outrank_strategies": 800,     # per strategy generated
    "content_localized": 2000,     # per page translated/localized
}
INR_PER_USD = 84


class WinsService:
    """Computes and reports value delivered per project."""

    def compute_wins(
        self,
        project_id: str,
        days: int = 7,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Count work done for a project in the window and price it."""
        if not db_fn:
            return {}

        from app.core.pgrest import ts
        since = ts(datetime.now(timezone.utc) - timedelta(days=days))

        def count(table: str, extra: str = "", ts_col: str = "created_at") -> int:
            try:
                rows = db_fn(
                    "get", table,
                    params=f"project_id=eq.{project_id}&{ts_col}=gte.{since}&select=id{extra}",
                )
                if isinstance(rows, list):
                    return len(rows)
                return 1 if rows else 0
            except Exception:
                return 0

        stats = {
            "audits_run": count("audit_runs", "&status=eq.completed"),
            "issues_found": count("audit_issues", ts_col="first_detected"),
            "issues_resolved": count("audit_issues", "&status=eq.resolved", ts_col="resolved_at"),
            "articles_generated": count("bulk_content_articles"),
            "posts_published": count("publishing_logs"),
            "link_opportunities": count("internal_link_opportunities"),
            "links_implemented": count("internal_link_opportunities", "&status=eq.implemented"),
            "keywords_clustered": count("keyword_mappings"),
            "competitor_analyses": count("competitor_analysis"),
            "outrank_strategies": count("outrank_strategies"),
            "content_localized": count("localized_content"),
        }

        value_inr = sum(
            stats[key] * rate for key, rate in AGENCY_RATES_INR.items() if stats.get(key)
        )

        return {
            "project_id": project_id,
            "period_days": days,
            "stats": stats,
            "total_actions": sum(stats.values()),
            "value_inr": value_inr,
            "value_usd": round(value_inr / INR_PER_USD),
        }

    def send_weekly_wins_if_due(
        self,
        project: dict[str, Any],
        db_fn: Callable,
    ) -> bool:
        """Send the weekly wins email if none was sent in the last 7 days."""
        project_id = project["id"]

        # Already reported this week?
        try:
            recent = db_fn(
                "get", "wins_reports",
                params=f"project_id=eq.{project_id}&order=created_at.desc&limit=1",
            )
            recent = recent if isinstance(recent, list) else [recent] if recent else []
            if recent:
                last = recent[0].get("created_at", "")
                last_ts = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - last_ts < timedelta(days=7):
                    return False
        except Exception:
            # wins_reports table missing -> skip silently until migration runs
            return False

        wins = self.compute_wins(project_id, days=7, db_fn=db_fn)
        if not wins or wins["total_actions"] == 0:
            return False  # nothing to brag about; don't send empty emails

        # Find a recipient: first user of the project's org
        recipient = None
        org_id = project.get("org_id")
        if org_id:
            try:
                users = db_fn("get", "users", params=f"org_id=eq.{org_id}&select=email&limit=1")
                users = users if isinstance(users, list) else [users] if users else []
                if users:
                    recipient = users[0].get("email")
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        report_row = {
            "project_id": project_id,
            "period_start": (now - timedelta(days=7)).isoformat(),
            "period_end": now.isoformat(),
            "stats": wins["stats"],
            "value_inr": wins["value_inr"],
            "value_usd": wins["value_usd"],
        }

        # claim first: if this insert fails we do NOT send, so a broken table
        # can never cause the same email to fire on every scheduler tick
        try:
            created = db_fn("post", "wins_reports", report_row)
            report_id = created[0].get("id") if isinstance(created, list) and created else None
        except Exception as exc:
            logger.warning("Could not store wins report (email skipped): %s", exc)
            return False

        sent = False
        if recipient:
            from app.services.email import EmailService
            email_svc = EmailService()
            sent = email_svc.send_weekly_wins(
                to=recipient,
                project_name=project.get("name", "your site"),
                wins=wins,
            )
            if sent and report_id:
                try:
                    db_fn("patch", f"wins_reports?id=eq.{report_id}", {
                        "sent_to": recipient,
                        "sent_at": now.isoformat(),
                    })
                except Exception:
                    pass

        logger.info(
            "Weekly wins for %s: %d actions, ₹%d value%s",
            project_id, wins["total_actions"], wins["value_inr"],
            f", emailed {recipient}" if sent else " (no email sent)",
        )
        return sent

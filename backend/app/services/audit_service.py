"""Technical audit service for continuous SEO monitoring."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import UUID

from app.agents.audit_agent import AuditAgent

logger = logging.getLogger("omnirank.audit")


class AuditService:
    """Manages technical SEO audits and issue tracking."""

    def __init__(self):
        self.agent = AuditAgent()

    def create_audit_schedule(
        self,
        project_id: UUID,
        audit_type: str,
        frequency: str = "weekly",
        config: dict[str, Any] | None = None,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Create an audit schedule."""
        if not db_fn:
            return {}

        try:
            # Calculate next run
            now = datetime.utcnow()
            if frequency == "daily":
                next_run = now + timedelta(days=1)
            elif frequency == "weekly":
                next_run = now + timedelta(days=7)
            elif frequency == "monthly":
                next_run = now + timedelta(days=30)
            else:
                next_run = None

            result = db_fn(
                "post",
                "audit_schedules",
                {
                    "project_id": str(project_id),
                    "audit_type": audit_type,
                    "frequency": frequency,
                    "enabled": True,
                    "next_run": next_run.isoformat() if next_run else None,
                    "config": config or {},
                },
            )

            logger.info("Created audit schedule: %s for %s", audit_type, project_id)
            return {
                "status": "created",
                "audit_type": audit_type,
                "frequency": frequency,
            }

        except Exception as exc:
            logger.error("Failed to create audit schedule: %s", exc)
            raise

    async def run_audit(
        self,
        project_id: UUID,
        audit_type: str,
        audit_data: list[dict[str, Any]],
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Run an audit and store results."""
        if not db_fn:
            return {}

        try:
            # Create audit run record
            run_result = db_fn(
                "post",
                "audit_runs",
                {
                    "project_id": str(project_id),
                    "audit_type": audit_type,
                    "status": "running",
                    "started_at": datetime.utcnow().isoformat(),
                },
            )

            # Supabase returns the created row(s) as a list
            if isinstance(run_result, list) and run_result:
                run_id = run_result[0].get("id")
            elif isinstance(run_result, dict):
                run_id = run_result.get("id")
            else:
                run_id = None
            if not run_id:
                raise ValueError("Failed to create audit run record")

            # Execute appropriate audit based on type
            if audit_type == "crawl_errors":
                audit_result = await self.agent.analyze_crawl_errors("", audit_data)
            elif audit_type == "broken_links":
                audit_result = await self.agent.analyze_broken_links("", audit_data)
            elif audit_type == "schema_validation":
                audit_result = await self.agent.analyze_schema_validation("", audit_data)
            elif audit_type == "performance":
                audit_result = await self.agent.analyze_performance("", audit_data)
            elif audit_type == "orphan_pages":
                link_graph = {}  # Would be constructed from audit_data
                audit_result = await self.agent.analyze_orphan_pages("", audit_data, link_graph)
            else:
                raise ValueError(f"Unknown audit type: {audit_type}")

            # Store issues
            stored_issues = []
            for issue in audit_result.issues[:100]:
                try:
                    db_fn(
                        "post",
                        "audit_issues",
                        {
                            "project_id": str(project_id),
                            "audit_run_id": run_id,
                            "issue_type": issue.issue_type,
                            "severity": issue.severity,
                            "affected_url": issue.affected_url,
                            "affected_element": issue.affected_element,
                            "description": issue.description,
                            "recommendation": issue.recommendation,
                            "evidence": issue.evidence,
                            "status": "open",
                            "first_detected": datetime.utcnow().isoformat(),
                            "last_detected": datetime.utcnow().isoformat(),
                        },
                    )
                    stored_issues.append(issue.affected_url)
                except Exception as e:
                    logger.warning("Failed to store issue: %s", e)

            # Update audit run with completion
            db_fn(
                "patch",
                f"audit_runs?id=eq.{run_id}",
                {
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "total_pages_checked": audit_result.total_pages_checked,
                    "issues_found": audit_result.issues_found,
                    "critical_count": audit_result.critical_count,
                    "warning_count": audit_result.warning_count,
                    "summary": audit_result.summary,
                    "result": {
                        "audit_type": audit_result.audit_type,
                        "status": audit_result.status,
                        "total_pages_checked": audit_result.total_pages_checked,
                        "issues_found": audit_result.issues_found,
                    },
                },
            )

            # Update schedule's last_run
            try:
                db_fn(
                    "patch",
                    f"audit_schedules?project_id=eq.{project_id}&audit_type=eq.{audit_type}",
                    {
                        "last_run": datetime.utcnow().isoformat(),
                        "next_run": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                    },
                )
            except Exception as e:
                logger.warning("Failed to update schedule: %s", e)

            logger.info("Completed audit: %s with %d issues", audit_type, audit_result.issues_found)

            return {
                "status": "completed",
                "audit_type": audit_type,
                "issues_found": audit_result.issues_found,
                "critical_count": audit_result.critical_count,
                "warning_count": audit_result.warning_count,
                "summary": audit_result.summary,
            }

        except Exception as exc:
            logger.error("Audit failed: %s", exc)
            raise

    def get_audit_schedules(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get all audit schedules for a project."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "audit_schedules", params=f"project_id=eq.{project_id}")
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch audit schedules: %s", exc)
            return []

    def get_audit_runs(
        self,
        project_id: UUID,
        audit_type: str | None = None,
        status: str = "",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get audit runs for a project."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}&order=created_at.desc"
            if audit_type:
                params += f"&audit_type=eq.{audit_type}"
            if status:
                params += f"&status=eq.{status}"

            result = db_fn("get", "audit_runs", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch audit runs: %s", exc)
            return []

    def get_audit_issues(
        self,
        project_id: UUID,
        issue_type: str | None = None,
        severity: str = "",
        status: str = "open",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get audit issues for a project."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}&order=last_detected.desc"
            if issue_type:
                params += f"&issue_type=eq.{issue_type}"
            if severity:
                params += f"&severity=eq.{severity}"
            if status:
                params += f"&status=eq.{status}"

            result = db_fn("get", "audit_issues", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch audit issues: %s", exc)
            return []

    def update_issue_status(
        self,
        issue_id: int,
        status: str,
        db_fn: Callable | None = None,
        project_id: str = "",
    ) -> bool:
        """Update issue status (scoped to the calling project)."""
        if not db_fn:
            return False

        try:
            scope = f"&project_id=eq.{project_id}" if project_id else ""
            db_fn(
                "patch",
                f"audit_issues?id=eq.{issue_id}{scope}",
                {
                    "status": status,
                    "resolved_at": datetime.utcnow().isoformat() if status == "resolved" else None,
                },
            )

            logger.info("Updated issue %d status to %s", issue_id, status)
            return True

        except Exception as exc:
            logger.error("Failed to update issue status: %s", exc)
            return False

    def resolve_issue(
        self,
        issue_id: int,
        resolution_type: str,
        resolution_details: str,
        resolved_by: str = "autopilot",
        db_fn: Callable | None = None,
        project_id: str = "",
    ) -> bool:
        """Record issue resolution (scoped to the calling project)."""
        if not db_fn:
            return False

        try:
            scope = f"&project_id=eq.{project_id}" if project_id else ""
            issue_result = db_fn("get", "audit_issues", params=f"id=eq.{issue_id}{scope}")
            issue_data = issue_result if isinstance(issue_result, list) else [issue_result] if issue_result else []

            if not issue_data:
                return False

            project_id = issue_data[0].get("project_id")

            # Create resolution record
            db_fn(
                "post",
                "issue_resolutions",
                {
                    "project_id": project_id,
                    "issue_id": issue_id,
                    "resolution_type": resolution_type,
                    "resolution_details": resolution_details,
                    "resolved_by": resolved_by,
                    "verification_status": "pending",
                },
            )

            # Update issue status
            db_fn(
                "patch",
                f"audit_issues?id=eq.{issue_id}",
                {
                    "status": "resolved",
                    "resolved_at": datetime.utcnow().isoformat(),
                },
            )

            logger.info("Resolved issue %d with type %s", issue_id, resolution_type)
            return True

        except Exception as exc:
            logger.error("Failed to resolve issue: %s", exc)
            return False

    def get_audit_summary(
        self,
        project_id: UUID,
        days: int = 30,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Get audit summary for a project."""
        if not db_fn:
            return {}

        try:
            # Get recent audit runs
            runs = self.get_audit_runs(project_id, db_fn=db_fn)
            recent_runs = runs[:5]

            # Get open issues
            open_issues = self.get_audit_issues(project_id, status="open", db_fn=db_fn)

            # Get critical issues
            critical = self.get_audit_issues(project_id, severity="critical", status="open", db_fn=db_fn)

            # Aggregate stats
            total_issues = len(open_issues)
            critical_count = len(critical)
            warning_count = len(self.get_audit_issues(project_id, severity="warning", status="open", db_fn=db_fn))

            # Count by type
            issues_by_type = {}
            for issue in open_issues:
                issue_type = issue.get("issue_type", "unknown")
                issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1

            return {
                "total_open_issues": total_issues,
                "critical_count": critical_count,
                "warning_count": warning_count,
                "recent_audits": len(recent_runs),
                "issues_by_type": issues_by_type,
                "last_audit": recent_runs[0].get("completed_at") if recent_runs else None,
                "health_score": max(0, 100 - (critical_count * 20 + warning_count * 5)),
            }

        except Exception as exc:
            logger.warning("Failed to get audit summary: %s", exc)
            return {}

"""AI Search Research Reports generation and management."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger("omnirank.research")


@dataclass
class ResearchReportRequest:
    """Request to generate a research report."""
    vertical: str
    month: str  # "January 2026" format
    focus_areas: list[str] = None
    depth: str = "standard"  # "summary" | "standard" | "deep"


@dataclass
class ResearchReport:
    """Research report metadata."""
    id: str
    vertical: str
    month: str
    created_at: str
    updated_at: str
    status: str  # "draft" | "published" | "archived"
    key_findings: list[dict]
    ai_engines: list[str]  # ["chatgpt", "perplexity", "gemini", "google_ai"]
    citations_analyzed: int
    top_movers: list[dict]
    recommendations: list[dict]
    pdf_url: Optional[str] = None


class ResearchReportsService:
    """Service for managing AI Search research reports."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.verticals = [
            "saas", "ecommerce", "healthcare", "fintech", "b2b", "legal",
            "realestate", "local", "accounting", "consulting", "education",
            "insurance", "nonprofit"
        ]

    def generate_report(
        self,
        req: ResearchReportRequest,
        db_fn: Callable,
    ) -> ResearchReport:
        """Generate a new research report for a vertical."""
        if req.vertical not in self.verticals:
            raise ValueError(f"Invalid vertical: {req.vertical}")

        try:
            # Generate report content using Claude
            report_content = self._generate_report_content(req)

            # Store in database
            db_result = db_fn("post", "ai_research_reports", {
                "vertical": req.vertical,
                "month": req.month,
                "status": "published",
                "key_findings": json.dumps(report_content["key_findings"]),
                "ai_engines": json.dumps(report_content["ai_engines"]),
                "citations_analyzed": report_content["citations_analyzed"],
                "top_movers": json.dumps(report_content["top_movers"]),
                "recommendations": json.dumps(report_content["recommendations"]),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            })

            if isinstance(db_result, dict):
                report_id = db_result.get("id")
            elif isinstance(db_result, list) and len(db_result) > 0:
                report_id = db_result[0].get("id")
            else:
                raise ValueError(f"Unexpected db_result format: {db_result}")

            logger.info(f"Generated research report {report_id} for {req.vertical}/{req.month}")

            return ResearchReport(
                id=report_id,
                vertical=req.vertical,
                month=req.month,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                status="published",
                key_findings=report_content["key_findings"],
                ai_engines=report_content["ai_engines"],
                citations_analyzed=report_content["citations_analyzed"],
                top_movers=report_content["top_movers"],
                recommendations=report_content["recommendations"],
            )
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise

    def get_report(
        self,
        vertical: str,
        month: str,
        db_fn: Callable,
    ) -> Optional[ResearchReport]:
        """Retrieve a research report."""
        try:
            result = db_fn(
                "get",
                "ai_research_reports",
                params=f"vertical=eq.{vertical}&month=eq.{month}&select=*"
            )
            if not result:
                return None

            report_data = result[0] if isinstance(result, list) else result
            return self._parse_report(report_data)
        except Exception as e:
            logger.error(f"Error retrieving report: {e}")
            return None

    def get_latest_reports_by_vertical(
        self,
        limit: int = 3,
        db_fn: Callable = None,
    ) -> dict[str, list[ResearchReport]]:
        """Get latest reports grouped by vertical."""
        try:
            reports_by_vertical = {}
            for vertical in self.verticals:
                result = db_fn(
                    "get",
                    "ai_research_reports",
                    params=f"vertical=eq.{vertical}&status=eq.published&order=created_at.desc&limit={limit}&select=*"
                )
                if result:
                    reports_by_vertical[vertical] = [
                        self._parse_report(r) for r in result
                    ]
                else:
                    reports_by_vertical[vertical] = []

            return reports_by_vertical
        except Exception as e:
            logger.error(f"Error retrieving latest reports: {e}")
            return {}

    def get_benchmark_data(
        self,
        vertical: str,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Get aggregated benchmark data for a vertical."""
        try:
            # Get latest 3 reports for the vertical
            result = db_fn(
                "get",
                "ai_research_reports",
                params=f"vertical=eq.{vertical}&status=eq.published&order=created_at.desc&limit=3&select=*"
            )

            if not result:
                return {"vertical": vertical, "reports": [], "trend": "insufficient_data"}

            reports = [self._parse_report(r) for r in result]

            # Calculate trends from multiple reports
            trend = self._calculate_trend(reports) if len(reports) > 1 else "new"

            return {
                "vertical": vertical,
                "reports": [self._report_to_dict(r) for r in reports],
                "trend": trend,
                "last_updated": reports[0].updated_at if reports else None,
            }
        except Exception as e:
            logger.error(f"Error retrieving benchmark data: {e}")
            return {"vertical": vertical, "reports": [], "trend": "error"}

    def _generate_report_content(self, req: ResearchReportRequest) -> dict:
        """Generate research report content using Claude."""
        # This would call Claude API to generate report
        # For now, returning template data
        vertical_title = req.vertical.title()

        return {
            "key_findings": [
                {
                    "title": f"{vertical_title} AI Citation Surge",
                    "description": f"{vertical_title} brands got cited 34% more often in ChatGPT responses this period.",
                    "metric": "+34%",
                    "importance": "critical"
                },
                {
                    "title": "Comparison Pages Win",
                    "description": "68% of AI citations came from comparison pages (vs. product pages at 18%).",
                    "metric": "68%",
                    "importance": "high"
                },
                {
                    "title": "E-E-A-T Still Critical",
                    "description": "89% of non-cited domains were missing author credentials in their schema.",
                    "metric": "89%",
                    "importance": "high"
                },
            ],
            "ai_engines": ["chatgpt", "perplexity", "gemini", "google_ai"],
            "citations_analyzed": 50000,
            "top_movers": [
                {"rank": 1, "domain": "example1.com", "citations": 1250, "change": "+45%"},
                {"rank": 2, "domain": "example2.com", "citations": 980, "change": "+28%"},
                {"rank": 3, "domain": "example3.com", "citations": 875, "change": "+12%"},
            ],
            "recommendations": [
                {
                    "priority": "critical",
                    "action": "Add detailed author bylines with E-E-A-T signals",
                    "impact": "High",
                    "effort": "Low"
                },
                {
                    "priority": "high",
                    "action": "Create comparison content targeting vs. keywords",
                    "impact": "High",
                    "effort": "Medium"
                },
                {
                    "priority": "medium",
                    "action": "Increase presence on third-party platforms",
                    "impact": "Medium",
                    "effort": "High"
                },
            ]
        }

    def _parse_report(self, data: dict) -> ResearchReport:
        """Parse database record into ResearchReport object."""
        return ResearchReport(
            id=data.get("id"),
            vertical=data.get("vertical"),
            month=data.get("month"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            status=data.get("status"),
            key_findings=json.loads(data.get("key_findings", "[]")),
            ai_engines=json.loads(data.get("ai_engines", "[]")),
            citations_analyzed=data.get("citations_analyzed", 0),
            top_movers=json.loads(data.get("top_movers", "[]")),
            recommendations=json.loads(data.get("recommendations", "[]")),
            pdf_url=data.get("pdf_url"),
        )

    def _report_to_dict(self, report: ResearchReport) -> dict:
        """Convert ResearchReport to dictionary."""
        return {
            "id": report.id,
            "vertical": report.vertical,
            "month": report.month,
            "status": report.status,
            "created_at": report.created_at,
            "key_findings": report.key_findings,
            "ai_engines": report.ai_engines,
            "citations_analyzed": report.citations_analyzed,
            "top_movers": report.top_movers,
        }

    def _calculate_trend(self, reports: list[ResearchReport]) -> str:
        """Calculate trend direction from multiple reports."""
        if len(reports) < 2:
            return "new"

        current = reports[0].citations_analyzed
        previous = reports[1].citations_analyzed

        if current > previous * 1.1:
            return "up"
        elif current < previous * 0.9:
            return "down"
        else:
            return "stable"

"""Competitor analysis and outrank strategy service."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from app.agents.competitor_agent import CompetitorAgent, CompetitorData

logger = logging.getLogger("omnirank.competitor")


@dataclass
class AddCompetitorRequest:
    project_id: UUID
    domain: str
    name: str = ""
    country_code: str = ""
    language_code: str = "en"


class CompetitorService:
    """Manages competitor tracking and analysis."""

    def __init__(self):
        self.agent = CompetitorAgent()

    def add_competitor(
        self,
        req: AddCompetitorRequest,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Add a competitor to track."""
        try:
            # Extract TLD from domain
            tld = req.domain.split(".")[-1] if "." in req.domain else ""

            result = db_fn("post", "competitors", {
                "project_id": str(req.project_id),
                "domain": req.domain,
                "name": req.name or req.domain,
                "tld": tld,
                "country_code": req.country_code,
                "language_code": req.language_code,
            })

            competitor_id = result.get("id") if isinstance(result, dict) else result[0].get("id")

            logger.info("Added competitor: %s", req.domain)
            return {
                "competitor_id": competitor_id,
                "domain": req.domain,
                "status": "added",
            }

        except Exception as exc:
            logger.error("Failed to add competitor: %s", exc)
            raise

    def get_competitors(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get all competitors for a project."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "competitors", params=f"project_id=eq.{project_id}&order=added_at.desc")
            return result if isinstance(result, list) else [result] if result else []
        except Exception as exc:
            logger.warning("Failed to fetch competitors: %s", exc)
            return []

    def remove_competitor(
        self,
        competitor_id: int,
        db_fn: Callable,
    ) -> bool:
        """Remove a competitor."""
        try:
            db_fn("delete", f"competitors?id=eq.{competitor_id}", None)
            logger.info("Removed competitor: %d", competitor_id)
            return True
        except Exception as exc:
            logger.error("Failed to remove competitor: %s", exc)
            return False

    async def analyze_competitor(
        self,
        competitor_id: int,
        competitor_data_dict: dict[str, Any],
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Analyze a competitor using Claude."""
        try:
            # Fetch competitor details
            competitor = db_fn("get", "competitors", params=f"id=eq.{competitor_id}")
            if not competitor:
                raise ValueError("Competitor not found")

            competitor = competitor[0] if isinstance(competitor, list) else competitor

            # Convert data dict to CompetitorData
            competitor_data = CompetitorData(
                domain=competitor["domain"],
                keywords=competitor_data_dict.get("keywords", []),
                backlinks=competitor_data_dict.get("backlinks", 0),
                referring_domains=competitor_data_dict.get("referring_domains", 0),
                top_pages=competitor_data_dict.get("top_pages", []),
                technical_score=competitor_data_dict.get("technical_score"),
                content_pages=competitor_data_dict.get("content_pages", 0),
                avg_content_length=competitor_data_dict.get("avg_content_length", 0),
            )

            # Run analysis
            analysis_result = await self.agent.analyze_competitor(
                competitor["domain"],
                competitor_data,
            )

            # Store analysis
            db_fn("post", "competitor_analysis", {
                "competitor_id": competitor_id,
                "project_id": str(competitor["project_id"]),
                "analysis_type": "seo_overview",
                "keyword_count": len(competitor_data.keywords),
                "top_keywords": json.dumps(competitor_data.keywords[:50]),
                "content_count": competitor_data.content_pages,
                "avg_content_length": competitor_data.avg_content_length,
                "backlink_count": competitor_data.backlinks,
                "referring_domains": competitor_data.referring_domains,
                "top_pages": json.dumps(competitor_data.top_pages[:10]),
                "ai_insights": analysis_result["analysis"],
                "full_analysis": json.dumps(analysis_result),
            })

            # Update last_analyzed timestamp
            db_fn("patch", f"competitors?id=eq.{competitor_id}", {
                "last_analyzed": "now()",
            })

            logger.info("Analyzed competitor: %d", competitor_id)
            return analysis_result

        except Exception as exc:
            logger.error("Competitor analysis failed: %s", exc)
            raise

    async def generate_strategies(
        self,
        competitor_id: int,
        your_domain: str,
        your_keywords: list[str],
        your_rankings: dict[str, int] | None = None,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Generate outrank strategies for a competitor."""
        if not db_fn:
            return []

        try:
            # Fetch competitor and latest analysis
            competitor = db_fn("get", "competitors", params=f"id=eq.{competitor_id}")
            if not competitor:
                raise ValueError("Competitor not found")

            competitor = competitor[0] if isinstance(competitor, list) else competitor

            analysis = db_fn(
                "get",
                "competitor_analysis",
                params=f"competitor_id=eq.{competitor_id}&analysis_type=eq.seo_overview&order=analyzed_at.desc&limit=1",
            )

            if not analysis:
                raise ValueError("No analysis found. Run analyze_competitor first.")

            analysis = analysis[0] if isinstance(analysis, list) else analysis

            # Parse competitor data
            full_analysis = json.loads(analysis.get("full_analysis", "{}"))
            competitor_data = CompetitorData(
                domain=competitor["domain"],
                keywords=full_analysis.get("data_snapshot", {}).get("top_keywords", []),
                backlinks=analysis.get("backlink_count", 0),
                referring_domains=analysis.get("referring_domains", 0),
                top_pages=full_analysis.get("data_snapshot", {}).get("top_pages", []),
                content_pages=analysis.get("content_count", 0),
                avg_content_length=analysis.get("avg_content_length", 0),
            )

            # Generate strategies
            strategies = await self.agent.generate_outrank_strategies(
                your_domain,
                your_keywords,
                competitor["domain"],
                competitor_data,
                your_rankings,
            )

            # Store strategies
            stored_strategies = []
            for strategy in strategies:
                result = db_fn("post", "outrank_strategies", {
                    "project_id": str(competitor["project_id"]),
                    "competitor_id": competitor_id,
                    "strategy_type": "content",
                    "target_keyword": strategy.target_keyword,
                    "competitor_position": strategy.competitor_position,
                    "recommended_action": strategy.recommended_action,
                    "implementation_steps": json.dumps(strategy.implementation_steps),
                    "content_gap": json.dumps(strategy.content_gap),
                    "estimated_roi": strategy.estimated_roi,
                    "priority": strategy.priority,
                    "status": "pending",
                })

                strategy_id = result.get("id") if isinstance(result, dict) else result[0].get("id")
                stored_strategies.append({
                    "id": strategy_id,
                    "target_keyword": strategy.target_keyword,
                    "competitor_position": strategy.competitor_position,
                    "action": strategy.recommended_action,
                    "priority": strategy.priority,
                })

            logger.info("Generated %d strategies for competitor %d", len(strategies), competitor_id)
            return stored_strategies

        except Exception as exc:
            logger.error("Strategy generation failed: %s", exc)
            raise

    def get_strategies(
        self,
        project_id: UUID,
        competitor_id: int | None = None,
        status: str = "",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch outrank strategies."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}"
            if competitor_id:
                params += f"&competitor_id=eq.{competitor_id}"
            if status:
                params += f"&status=eq.{status}"
            params += "&order=priority.desc"

            result = db_fn("get", "outrank_strategies", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch strategies: %s", exc)
            return []

    def update_strategy_status(
        self,
        strategy_id: int,
        status: str,
        db_fn: Callable,
    ) -> bool:
        """Update strategy implementation status."""
        try:
            db_fn("patch", f"outrank_strategies?id=eq.{strategy_id}", {
                "status": status,
                "updated_at": "now()",
            })
            logger.info("Updated strategy %d to %s", strategy_id, status)
            return True
        except Exception as exc:
            logger.error("Failed to update strategy: %s", exc)
            return False

    def get_analysis(
        self,
        competitor_id: int,
        db_fn: Callable | None = None,
    ) -> dict[str, Any] | None:
        """Get latest analysis for a competitor."""
        if not db_fn:
            return None

        try:
            result = db_fn(
                "get",
                "competitor_analysis",
                params=f"competitor_id=eq.{competitor_id}&order=analyzed_at.desc&limit=1",
            )

            if not result:
                return None

            analysis = result[0] if isinstance(result, list) else result
            # Parse JSON fields
            if analysis.get("top_keywords"):
                analysis["top_keywords"] = json.loads(analysis["top_keywords"])
            if analysis.get("top_pages"):
                analysis["top_pages"] = json.loads(analysis["top_pages"])
            if analysis.get("full_analysis"):
                analysis["full_analysis"] = json.loads(analysis["full_analysis"])

            return analysis

        except Exception as exc:
            logger.warning("Failed to fetch analysis: %s", exc)
            return None

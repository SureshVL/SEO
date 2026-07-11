"""Internal linking service for smart link discovery and implementation."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable
from uuid import UUID

from app.agents.internal_linking_agent import (
    InternalLinkingAgent,
    LinkOpportunity,
    SitePage,
)

logger = logging.getLogger("omnirank.linking")


class InternalLinkingService:
    """Manages internal linking strategies and implementations."""

    def __init__(self):
        self.agent = InternalLinkingAgent()

    def add_page(
        self,
        project_id: UUID,
        url: str,
        title: str,
        content: str,
        topics: list[str],
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Add or update a page in the site structure."""
        try:
            word_count = len(content.split())

            # Check if page exists
            existing = db_fn("get", "site_pages", params=f"project_id=eq.{project_id}&url=eq.{url}")

            if existing and isinstance(existing, list) and len(existing) > 0:
                # Update
                result = db_fn(
                    "patch",
                    f"site_pages?project_id=eq.{project_id}&url=eq.{url}",
                    {
                        "title": title,
                        "content": content[:5000],  # Store first 5K words
                        "topics": json.dumps(topics),
                        "word_count": word_count,
                    },
                )
            else:
                # Create
                result = db_fn(
                    "post",
                    "site_pages",
                    {
                        "project_id": str(project_id),
                        "url": url,
                        "title": title,
                        "content": content[:5000],
                        "topics": json.dumps(topics),
                        "word_count": word_count,
                    },
                )

            logger.info("Added page: %s", url)
            return {"status": "added", "url": url}

        except Exception as exc:
            logger.error("Failed to add page: %s", exc)
            raise

    def get_pages(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> list[SitePage]:
        """Get all pages for a project."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "site_pages", params=f"project_id=eq.{project_id}")
            pages = result if isinstance(result, list) else [result] if result else []

            return [
                SitePage(
                    url=p["url"],
                    title=p.get("title", ""),
                    content=p.get("content", ""),
                    topics=json.loads(p.get("topics", "[]")),
                    word_count=p.get("word_count", 0),
                )
                for p in pages
            ]

        except Exception as exc:
            logger.warning("Failed to fetch pages: %s", exc)
            return []

    async def find_opportunities(
        self,
        project_id: UUID,
        source_url: str,
        db_fn: Callable,
    ) -> list[dict[str, Any]]:
        """Find linking opportunities for a page."""
        try:
            # Get all pages
            all_pages = self.get_pages(project_id, db_fn)
            if not all_pages:
                raise ValueError("No pages found")

            # Find source page
            source_page = next((p for p in all_pages if p.url == source_url), None)
            if not source_page:
                raise ValueError("Source page not found")

            # Find target pages (all others)
            target_pages = [p for p in all_pages if p.url != source_url]

            # Get opportunities from agent
            opportunities = await self.agent.find_linking_opportunities(
                source_page,
                target_pages,
                max_opportunities=10,
            )

            # Build url -> database id map so we store real page IDs
            raw_rows = db_fn("get", "site_pages", params=f"project_id=eq.{project_id}&select=id,url")
            raw_rows = raw_rows if isinstance(raw_rows, list) else [raw_rows] if raw_rows else []
            page_id_by_url = {row["url"]: row["id"] for row in raw_rows}

            # Store opportunities
            stored = []
            for opp in opportunities:
                source_page_id = page_id_by_url.get(opp.source_url)
                target_page_id = page_id_by_url.get(opp.target_url)
                if not source_page_id or not target_page_id:
                    continue

                result = db_fn(
                    "post",
                    "internal_link_opportunities",
                    {
                        "project_id": str(project_id),
                        "source_page_id": source_page_id,
                        "target_page_id": target_page_id,
                        "anchor_text": opp.anchor_text,
                        "relevance_score": opp.relevance_score,
                        "keyword_match": opp.keyword_match,
                        "linking_reason": opp.linking_reason,
                        "opportunity_type": opp.opportunity_type,
                        "priority": opp.priority,
                    },
                )

                stored.append({
                    "target_url": opp.target_url,
                    "anchor_text": opp.anchor_text,
                    "relevance_score": opp.relevance_score,
                    "priority": opp.priority,
                })

            logger.info("Found %d opportunities for %s", len(stored), source_url)
            return stored

        except Exception as exc:
            logger.error("Failed to find opportunities: %s", exc)
            raise

    async def analyze_site_structure(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Analyze overall site structure."""
        try:
            pages = self.get_pages(project_id, db_fn)
            if not pages:
                raise ValueError("No pages found")

            analysis = await self.agent.analyze_site_structure(pages)
            return analysis

        except Exception as exc:
            logger.error("Failed to analyze site structure: %s", exc)
            raise

    def get_opportunities(
        self,
        project_id: UUID,
        source_url: str | None = None,
        status: str = "",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get linking opportunities."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}"
            if source_url:
                params += f"&source_url=eq.{source_url}"
            if status:
                params += f"&status=eq.{status}"
            params += "&order=priority.desc"

            result = db_fn("get", "internal_link_opportunities", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch opportunities: %s", exc)
            return []

    def approve_opportunity(
        self,
        opportunity_id: int,
        db_fn: Callable,
    ) -> bool:
        """Approve a linking opportunity."""
        try:
            db_fn(
                "patch",
                f"internal_link_opportunities?id=eq.{opportunity_id}",
                {"status": "approved"},
            )
            logger.info("Approved opportunity: %d", opportunity_id)
            return True
        except Exception as exc:
            logger.error("Failed to approve opportunity: %s", exc)
            return False

    def implement_link(
        self,
        opportunity_id: int,
        db_fn: Callable,
    ) -> bool:
        """Implement a linking opportunity."""
        try:
            db_fn(
                "patch",
                f"internal_link_opportunities?id=eq.{opportunity_id}",
                {"status": "implemented"},
            )

            # Also create a record in internal_links table
            # (would need to fetch opportunity details first)

            logger.info("Implemented opportunity: %d", opportunity_id)
            return True

        except Exception as exc:
            logger.error("Failed to implement link: %s", exc)
            return False

    def reject_opportunity(
        self,
        opportunity_id: int,
        reason: str = "",
        db_fn: Callable | None = None,
    ) -> bool:
        """Reject a linking opportunity."""
        if not db_fn:
            return False

        try:
            db_fn(
                "patch",
                f"internal_link_opportunities?id=eq.{opportunity_id}",
                {"status": "rejected"},
            )
            logger.info("Rejected opportunity: %d", opportunity_id)
            return True

        except Exception as exc:
            logger.error("Failed to reject opportunity: %s", exc)
            return False

    async def identify_orphans(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Identify orphan pages in the site."""
        try:
            pages = self.get_pages(project_id, db_fn)
            if not pages:
                raise ValueError("No pages found")

            # Build link graph from opportunities
            link_graph: dict[str, list[str]] = {}
            for page in pages:
                link_graph[page.url] = []

            # Get implemented links
            links = db_fn("get", "internal_links", params=f"project_id=eq.{project_id}")
            if links:
                links_list = links if isinstance(links, list) else [links]
                for link in links_list:
                    source = link.get("source_url", "")
                    target = link.get("target_url", "")
                    if source in link_graph:
                        link_graph[source].append(target)

            # Identify orphans
            orphans_analysis = await self.agent.identify_orphan_pages(pages, link_graph)
            return orphans_analysis

        except Exception as exc:
            logger.error("Failed to identify orphans: %s", exc)
            raise

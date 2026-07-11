"""Keyword clustering and mapping service for organizing keywords and assigning to URLs."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable
from uuid import UUID

from app.core.pgrest import q
from app.agents.keyword_mapping_agent import (
    KeywordMappingAgent,
    Keyword,
    KeywordCluster,
    URLAssignment,
)

logger = logging.getLogger("omnirank.keyword_mapping")


def _json_list(raw) -> list:
    """jsonb columns may arrive native (list), as a legacy string, or NULL."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return []
    return []


class KeywordMappingService:
    """Manages keyword clustering and URL assignment workflows."""

    def __init__(self):
        self.agent = KeywordMappingAgent()

    def import_keywords(
        self,
        project_id: UUID,
        keywords_data: list[dict[str, Any]],
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Import keywords into the project."""
        try:
            imported_count = 0
            failed_count = 0

            for kw_data in keywords_data:
                try:
                    # Check if keyword exists
                    existing = db_fn(
                        "get",
                        "keywords",
                        params=f"project_id=eq.{project_id}&keyword=eq.{q(kw_data.get('keyword', ''))}",
                    )

                    if existing and isinstance(existing, list) and len(existing) > 0:
                        # Update existing
                        db_fn(
                            "patch",
                            f"keywords?project_id=eq.{project_id}&keyword=eq.{q(kw_data.get('keyword', ''))}",
                            {
                                "search_volume": kw_data.get("search_volume", 0),
                                "keyword_difficulty": kw_data.get("difficulty", 0),
                                "search_intent": kw_data.get("intent", "informational"),
                                "cpc": kw_data.get("cpc", 0.0),
                                "trend": kw_data.get("trend", "stable"),
                                "source": kw_data.get("source", "imported"),
                            },
                        )
                    else:
                        # Create new
                        db_fn(
                            "post",
                            "keywords",
                            {
                                "project_id": str(project_id),
                                "keyword": kw_data.get("keyword", ""),
                                "search_volume": kw_data.get("search_volume", 0),
                                "keyword_difficulty": kw_data.get("difficulty", 0),
                                "search_intent": kw_data.get("intent", "informational"),
                                "cpc": kw_data.get("cpc", 0.0),
                                "trend": kw_data.get("trend", "stable"),
                                "source": kw_data.get("source", "imported"),
                            },
                        )

                    imported_count += 1

                except Exception as e:
                    logger.warning("Failed to import keyword %s: %s", kw_data.get("keyword"), e)
                    failed_count += 1

            logger.info("Imported %d keywords, %d failed", imported_count, failed_count)
            return {
                "status": "imported",
                "imported_count": imported_count,
                "failed_count": failed_count,
            }

        except Exception as exc:
            logger.error("Keyword import failed: %s", exc)
            raise

    def get_keywords(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> list[Keyword]:
        """Get all keywords for a project."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "keywords", params=f"project_id=eq.{project_id}")
            keywords_list = result if isinstance(result, list) else [result] if result else []

            return [
                Keyword(
                    keyword=k.get("keyword", ""),
                    search_volume=k.get("search_volume", 0),
                    difficulty=k.get("keyword_difficulty", 0),
                    intent=k.get("search_intent", "informational"),
                    cpc=k.get("cpc", 0.0),
                )
                for k in keywords_list
            ]

        except Exception as exc:
            logger.warning("Failed to fetch keywords: %s", exc)
            return []

    async def cluster_keywords(
        self,
        project_id: UUID,
        db_fn: Callable,
    ) -> list[dict[str, Any]]:
        """Cluster keywords by semantic similarity and intent."""
        try:
            # Get all keywords
            keywords = self.get_keywords(project_id, db_fn)
            if not keywords:
                raise ValueError("No keywords found")

            # Run clustering
            clusters = await self.agent.cluster_keywords(keywords)

            # Store clusters
            stored = []
            for cluster in clusters:
                result = db_fn(
                    "post",
                    "keyword_clusters",
                    {
                        "project_id": str(project_id),
                        "cluster_name": cluster.cluster_name,
                        "seed_keyword": cluster.seed_keyword,
                        "keywords": cluster.keywords,
                        "intent": cluster.intent,
                        "volume": cluster.total_volume,
                        "difficulty": cluster.avg_difficulty,
                    },
                )

                stored.append({
                    "cluster_name": cluster.cluster_name,
                    "seed_keyword": cluster.seed_keyword,
                    "keywords": cluster.keywords,
                    "intent": cluster.intent,
                    "volume": cluster.total_volume,
                    "difficulty": cluster.avg_difficulty,
                })

            logger.info("Created %d clusters", len(stored))
            return stored

        except Exception as exc:
            logger.error("Keyword clustering failed: %s", exc)
            raise

    async def assign_keywords_to_urls(
        self,
        project_id: UUID,
        db_fn: Callable,
    ) -> list[dict[str, Any]]:
        """Assign keyword clusters to best-matching URLs."""
        try:
            # Get clusters
            clusters_result = db_fn("get", "keyword_clusters", params=f"project_id=eq.{project_id}")
            clusters_list = clusters_result if isinstance(clusters_result, list) else [clusters_result] if clusters_result else []

            if not clusters_list:
                raise ValueError("No clusters found")

            clusters = [
                KeywordCluster(
                    cluster_name=c.get("cluster_name", ""),
                    seed_keyword=c.get("seed_keyword", ""),
                    keywords=_json_list(c.get("keywords")),
                    intent=c.get("intent", "informational"),
                    total_volume=c.get("volume", 0),
                    avg_difficulty=c.get("difficulty", 0),
                )
                for c in clusters_list
            ]

            # Get existing URLs
            pages_result = db_fn("get", "site_pages", params=f"project_id=eq.{project_id}")
            pages_list = pages_result if isinstance(pages_result, list) else [pages_result] if pages_result else []

            existing_urls = {p.get("url", ""): p.get("title", "") for p in pages_list}

            # Run assignment
            assignments = await self.agent.assign_keywords_to_urls(clusters, existing_urls)

            # Store assignments
            stored = []
            for assignment in assignments:
                result = db_fn(
                    "post",
                    "url_assignments",
                    {
                        "project_id": str(project_id),
                        "url": assignment.url,
                        "primary_keyword": assignment.primary_keyword,
                        "secondary_keywords": assignment.secondary_keywords,
                        "target_volume": assignment.target_volume,
                        "optimization_score": 0,  # To be calculated
                    },
                )

                stored.append({
                    "url": assignment.url,
                    "primary_keyword": assignment.primary_keyword,
                    "secondary_keywords": assignment.secondary_keywords,
                    "target_volume": assignment.target_volume,
                    "priority": assignment.priority,
                })

            # also persist per-keyword mappings so /keywords/mappings has data
            id_rows = db_fn("get", "keywords", params=f"project_id=eq.{project_id}&select=id,keyword")
            id_rows = id_rows if isinstance(id_rows, list) else [id_rows] if id_rows else []
            keyword_ids = {r.get("keyword", "").lower(): r.get("id") for r in id_rows}
            for assignment in assignments:
                names = [assignment.primary_keyword] + list(assignment.secondary_keywords or [])
                for name in names:
                    keyword_id = keyword_ids.get((name or "").lower())
                    if not keyword_id or not assignment.url:
                        continue
                    try:
                        db_fn("post", "keyword_mappings", {
                            "project_id": str(project_id),
                            "keyword_id": keyword_id,
                            "url": assignment.url,
                            "recommendation": "target" if name == assignment.primary_keyword else "optimize",
                            "priority": assignment.priority,
                        })
                    except Exception:
                        pass  # duplicate mapping (unique project/keyword/url)

            logger.info("Assigned %d keyword clusters to URLs", len(stored))
            return stored

        except Exception as exc:
            logger.error("Keyword assignment failed: %s", exc)
            raise

    async def identify_gaps(
        self,
        project_id: UUID,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Identify keyword gaps and content opportunities."""
        try:
            # Get keywords and existing mappings
            keywords = self.get_keywords(project_id, db_fn)
            if not keywords:
                raise ValueError("No keywords found")

            # Get existing mappings
            mappings_result = db_fn("get", "keyword_mappings", params=f"project_id=eq.{project_id}")
            mappings_list = mappings_result if isinstance(mappings_result, list) else [mappings_result] if mappings_result else []

            existing_mappings = {}
            for mapping in mappings_list:
                keyword = mapping.get("keyword_id")
                if keyword not in existing_mappings:
                    existing_mappings[keyword] = []

            # Identify gaps
            gaps = await self.agent.identify_gaps(keywords, existing_mappings)

            # Store gaps with real keyword ids (the FK requires one)
            id_rows = db_fn("get", "keywords", params=f"project_id=eq.{project_id}&select=id,keyword")
            id_rows = id_rows if isinstance(id_rows, list) else [id_rows] if id_rows else []
            keyword_ids = {r.get("keyword", "").lower(): r.get("id") for r in id_rows}

            for gap in gaps.get("opportunities", []):
                keyword_id = keyword_ids.get((gap.get("keyword") or "").lower())
                if not keyword_id:
                    continue
                try:
                    db_fn(
                        "post",
                        "keyword_gaps",
                        {
                            "project_id": str(project_id),
                            "keyword_id": keyword_id,
                            "gap_type": gap.get("gap_type", "new_content_needed"),
                            "volume": gap.get("volume", 0),
                            "difficulty": 0,
                            "recommendation": gap.get("recommendation", ""),
                            "priority": gap.get("priority", 5),
                        },
                    )
                except Exception as e:
                    logger.warning("Failed to store gap: %s", e)

            return gaps

        except Exception as exc:
            logger.error("Gap identification failed: %s", exc)
            raise

    def get_clusters(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get all keyword clusters for a project."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "keyword_clusters", params=f"project_id=eq.{project_id}&order=volume.desc")
            clusters = result if isinstance(result, list) else [result] if result else []

            return [
                {
                    "cluster_name": c.get("cluster_name", ""),
                    "seed_keyword": c.get("seed_keyword", ""),
                    "keywords": json.loads(c.get("keywords", "[]")),
                    "intent": c.get("intent", "informational"),
                    "volume": c.get("volume", 0),
                    "difficulty": c.get("difficulty", 0),
                }
                for c in clusters
            ]

        except Exception as exc:
            logger.warning("Failed to fetch clusters: %s", exc)
            return []

    def get_mappings(
        self,
        project_id: UUID,
        url: str | None = None,
        status: str = "",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get keyword-URL mappings."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}"
            if url:
                params += f"&url=eq.{url}"
            if status:
                params += f"&status=eq.{status}"
            params += "&order=priority.desc"

            result = db_fn("get", "keyword_mappings", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch mappings: %s", exc)
            return []

    def get_gaps(
        self,
        project_id: UUID,
        gap_type: str = "",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get keyword gaps."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}&order=priority.desc"
            if gap_type:
                params += f"&gap_type=eq.{gap_type}"

            result = db_fn("get", "keyword_gaps", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch gaps: %s", exc)
            return []

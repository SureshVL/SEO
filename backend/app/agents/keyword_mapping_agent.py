"""Keyword clustering and mapping - organize keywords by intent and assign to URLs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.clients.llm import llm_client

logger = logging.getLogger("omnirank.keyword_mapping")


@dataclass
class Keyword:
    """A single keyword with metadata."""
    keyword: str
    search_volume: int = 0
    difficulty: int = 0
    intent: str = "informational"
    cpc: float = 0.0


@dataclass
class KeywordCluster:
    """A group of semantically related keywords."""
    cluster_name: str
    seed_keyword: str
    keywords: list[str]
    intent: str
    total_volume: int
    avg_difficulty: int


@dataclass
class URLAssignment:
    """Assignment of keywords to a URL."""
    url: str
    primary_keyword: str
    secondary_keywords: list[str]
    target_volume: int
    priority: int


class KeywordMappingAgent:
    """Groups keywords by semantic similarity and assigns to URLs."""

    def __init__(self):
        self.llm = llm_client

    async def cluster_keywords(
        self,
        keywords: list[Keyword],
    ) -> list[KeywordCluster]:
        """Group keywords into semantic clusters."""
        try:
            if not keywords:
                return []

            # Prepare keyword list for Claude
            keyword_list = "\n".join(
                f"- {k.keyword}: vol={k.search_volume}, difficulty={k.difficulty}, intent={k.intent}"
                for k in keywords[:100]
            )

            prompt = f"""Group these keywords into semantic clusters based on:
1. Search intent (informational, commercial, transactional, navigational)
2. Topic relevance (keywords about same topic)
3. User search behavior (synonyms, variations)
4. Search volume and opportunity

Keywords:
{keyword_list}

For each cluster, provide:
- Cluster name (thematic description)
- Seed keyword (most important/highest volume)
- All keywords in cluster
- Dominant intent
- Total volume
- Average difficulty

Format as JSON array:
[
  {{
    "cluster_name": "SEO Basics",
    "seed_keyword": "how to do seo",
    "keywords": ["seo", "seo basics", "seo guide", "what is seo"],
    "intent": "informational",
    "total_volume": 50000,
    "avg_difficulty": 25
  }}
]"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2000,
            )

            # Parse clusters from response
            clusters = self._parse_clusters(response)
            return clusters

        except Exception as exc:
            logger.error("Keyword clustering failed: %s", exc)
            raise

    async def assign_keywords_to_urls(
        self,
        clusters: list[KeywordCluster],
        existing_urls: dict[str, str],
    ) -> list[URLAssignment]:
        """Assign keywords to best-matching URLs."""
        try:
            # Prepare cluster and URL data for Claude
            cluster_list = "\n".join(
                f"- {c.cluster_name} ({c.seed_keyword}): {', '.join(c.keywords[:5])}..."
                for c in clusters[:50]
            )

            url_list = "\n".join(
                f"- {url}: {title}"
                for url, title in list(existing_urls.items())[:30]
            )

            prompt = f"""Assign keyword clusters to URLs that would rank best for them:

Keyword Clusters:
{cluster_list}

Existing URLs:
{url_list}

For each cluster, determine:
1. Best-matching URL (or recommend creating new content)
2. Primary keyword to target
3. Secondary keywords to support
4. Optimization priority (1-10)

Consider:
- URL relevance to keyword intent
- Page authority needed vs keyword difficulty
- Content gaps (keywords with no good URL match)
- Ranking potential

Format as JSON array:
[
  {{
    "cluster_name": "SEO Basics",
    "seed_keyword": "how to do seo",
    "assigned_url": "/guides/seo-tutorial/",
    "secondary_keywords": ["seo basics", "seo guide"],
    "target_volume": 50000,
    "priority": 9,
    "recommendation": "optimize"
  }}
]"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2000,
            )

            assignments = self._parse_assignments(response)
            return assignments

        except Exception as exc:
            logger.error("Keyword assignment failed: %s", exc)
            raise

    async def identify_gaps(
        self,
        keywords: list[Keyword],
        existing_mappings: dict[str, list[str]],
    ) -> dict[str, Any]:
        """Identify keyword gaps and content opportunities."""
        try:
            unmapped_keywords = [
                k for k in keywords
                if k.keyword not in existing_mappings
            ]

            if not unmapped_keywords:
                return {
                    "gap_count": 0,
                    "total_volume": 0,
                    "opportunities": [],
                }

            # Prioritize high-volume unmapped keywords
            unmapped_keywords.sort(key=lambda k: k.search_volume, reverse=True)

            keyword_list = "\n".join(
                f"- {k.keyword}: vol={k.search_volume}, diff={k.difficulty}"
                for k in unmapped_keywords[:50]
            )

            prompt = f"""Analyze these unmapped keywords and recommend content strategy:

Unmapped Keywords (highest volume first):
{keyword_list}

For each keyword, determine:
1. Gap type: new_content_needed, orphan_keyword, poor_match, opportunity
2. Content recommendation: guide, tool, comparison, case_study, etc.
3. Estimated impact: traffic potential
4. Priority: 1-10 for implementation

Format as JSON:
[
  {{
    "keyword": "keyword name",
    "volume": 1000,
    "gap_type": "new_content_needed",
    "recommendation": "Create comprehensive guide",
    "impact": 850,
    "priority": 9
  }}
]"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=1500,
            )

            gaps = self._parse_gaps(response)
            total_volume = sum(g["volume"] for g in gaps)

            return {
                "gap_count": len(gaps),
                "total_volume": total_volume,
                "opportunities": gaps[:20],  # Top 20 opportunities
                "analysis": response,
            }

        except Exception as exc:
            logger.error("Gap identification failed: %s", exc)
            raise

    def _parse_clusters(self, response: str) -> list[KeywordCluster]:
        """Parse clusters from Claude response."""
        clusters = []
        try:
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())

            for item in data[:50]:  # Limit to 50 clusters
                cluster = KeywordCluster(
                    cluster_name=item.get("cluster_name", ""),
                    seed_keyword=item.get("seed_keyword", ""),
                    keywords=item.get("keywords", []),
                    intent=item.get("intent", "informational"),
                    total_volume=item.get("total_volume", 0),
                    avg_difficulty=item.get("avg_difficulty", 0),
                )
                clusters.append(cluster)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse clusters: %s", exc)

        return clusters

    def _parse_assignments(self, response: str) -> list[URLAssignment]:
        """Parse URL assignments from Claude response."""
        assignments = []
        try:
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())

            for item in data[:50]:
                assignment = URLAssignment(
                    url=item.get("assigned_url", ""),
                    primary_keyword=item.get("seed_keyword", ""),
                    secondary_keywords=item.get("secondary_keywords", []),
                    target_volume=item.get("target_volume", 0),
                    priority=item.get("priority", 5),
                )
                assignments.append(assignment)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse assignments: %s", exc)

        return assignments

    def _parse_gaps(self, response: str) -> list[dict[str, Any]]:
        """Parse gaps from Claude response."""
        gaps = []
        try:
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            gaps = data[:50]

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse gaps: %s", exc)

        return gaps

"""Smart internal linking - identify and implement linking opportunities."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.clients.llm import llm_client

logger = logging.getLogger("omnirank.linking")


@dataclass
class SitePage:
    """Represents a page in the site structure."""
    url: str
    title: str
    content: str
    topics: list[str]
    word_count: int


@dataclass
class LinkOpportunity:
    """A candidate internal link to implement."""
    source_url: str
    target_url: str
    anchor_text: str
    relevance_score: float  # 0-1
    keyword_match: str
    linking_reason: str
    opportunity_type: str  # keyword_relevant, semantic, topic_cluster, orphan_rescue
    priority: int  # 1-10


class InternalLinkingAgent:
    """Identifies and manages internal linking opportunities."""

    def __init__(self):
        self.llm = llm_client

    async def analyze_site_structure(
        self,
        pages: list[SitePage],
    ) -> dict[str, Any]:
        """Analyze overall site structure and linking patterns."""
        try:
            # Extract basic metrics
            total_pages = len(pages)
            avg_word_count = sum(p.word_count for p in pages) // max(1, len(pages))

            # Identify topic clusters
            topic_map = self._build_topic_map(pages)

            prompt = f"""Analyze this site structure and linking strategy:

Total Pages: {total_pages}
Average Page Length: {avg_word_count} words
Topic Clusters: {len(topic_map)}

Pages by Topic:
{chr(10).join(f"- {topic}: {len(urls)} pages - {', '.join(urls[:3])}{'...' if len(urls) > 3 else ''}" for topic, urls in list(topic_map.items())[:10])}

Provide:
1. Overall site architecture assessment
2. Content siloing opportunities
3. Topic cluster analysis
4. Orphan page identification
5. Internal link depth analysis
6. Recommendations for improvement"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=1500,
            )

            return {
                "total_pages": total_pages,
                "topic_clusters": len(topic_map),
                "analysis": response,
                "topic_map": topic_map,
            }

        except Exception as exc:
            logger.error("Site structure analysis failed: %s", exc)
            raise

    async def find_linking_opportunities(
        self,
        source_page: SitePage,
        target_pages: list[SitePage],
        max_opportunities: int = 5,
    ) -> list[LinkOpportunity]:
        """Find linking opportunities from source to target pages."""
        try:
            opportunities = []

            # Build candidate list with relevance scoring
            candidates = self._score_relevance(source_page, target_pages)

            # Use Claude to validate and enhance opportunities
            top_candidates = candidates[:max_opportunities * 2]

            if not top_candidates:
                return []

            candidate_list = "\n".join(
                f"- {c['target']}: relevance={c['score']:.2f}, keywords={', '.join(c['keywords'][:3])}"
                for c in top_candidates[:10]
            )

            prompt = f"""Generate internal linking recommendations:

Source Page: {source_page.title}
URL: {source_page.url}
Content Focus: {', '.join(source_page.topics[:5])}

Target Pages (ranked by relevance):
{candidate_list}

For the top {min(5, len(top_candidates))} opportunities:
1. Rank by strategic value (not just relevance)
2. Suggest specific anchor text that's natural and SEO-friendly
3. Explain why each link strengthens the overall site structure
4. Identify opportunity type: keyword_relevant, semantic, topic_cluster, orphan_rescue

Format response as JSON array:
[
  {{
    "target_url": "url",
    "anchor_text": "natural anchor text",
    "relevance_score": 0.85,
    "reason": "why this link helps",
    "type": "opportunity_type",
    "priority": 8
  }}
]"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=1500,
            )

            # Parse opportunities from response
            opportunities = self._parse_opportunities(
                response,
                source_page.url,
                target_pages,
            )

            return opportunities

        except Exception as exc:
            logger.error("Linking opportunity detection failed: %s", exc)
            raise

    async def identify_orphan_pages(
        self,
        pages: list[SitePage],
        link_graph: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        """Identify pages that are hard to reach or have no internal links."""
        try:
            orphans = []

            for page in pages:
                # Check if page is linked to
                inbound_links = sum(
                    1 for targets in link_graph.values() if page.url in targets
                )

                # Check if page links out
                outbound_links = len(link_graph.get(page.url, []))

                if inbound_links == 0 or (outbound_links == 0 and page.word_count > 500):
                    orphans.append({
                        "url": page.url,
                        "title": page.title,
                        "inbound_links": inbound_links,
                        "outbound_links": outbound_links,
                        "word_count": page.word_count,
                        "issues": (
                            ["orphan_page"] if inbound_links == 0 else [] +
                            ["no_outbound_links"] if outbound_links == 0 else []
                        ),
                    })

            # Prompt Claude for rescue strategies
            if orphans:
                orphan_list = "\n".join(
                    f"- {o['url']}: {o['inbound_links']} inbound, {o['outbound_links']} outbound"
                    for o in orphans[:10]
                )

                prompt = f"""Recommend internal linking strategies to rescue orphan pages:

Orphan Pages ({len(orphans)} total):
{orphan_list}

For each, suggest:
1. Which pages should link to it (and why)
2. Natural anchor text options
3. Expected impact on crawlability and authority
4. Priority (1-10) for implementation"""

                response = await self.llm.agenerate_text(
                    prompt,
                    model="claude-opus-4-8",
                    max_tokens=1500,
                )

                return {
                    "orphan_count": len(orphans),
                    "pages": orphans,
                    "rescue_strategy": response,
                }

            return {"orphan_count": 0, "pages": []}

        except Exception as exc:
            logger.error("Orphan page identification failed: %s", exc)
            raise

    def _build_topic_map(self, pages: list[SitePage]) -> dict[str, list[str]]:
        """Build a map of topics to pages."""
        topic_map: dict[str, list[str]] = {}

        for page in pages:
            for topic in page.topics[:3]:  # Top 3 topics per page
                if topic not in topic_map:
                    topic_map[topic] = []
                topic_map[topic].append(page.url)

        return topic_map

    def _score_relevance(
        self,
        source: SitePage,
        targets: list[SitePage],
    ) -> list[dict[str, Any]]:
        """Score relevance of target pages to source page."""
        scored = []

        for target in targets:
            if target.url == source.url:
                continue

            # Calculate relevance based on topic overlap
            source_topics = set(source.topics)
            target_topics = set(target.topics)
            overlap = source_topics & target_topics

            relevance_score = len(overlap) / max(len(source_topics), 1) * 0.7
            relevance_score += min(len(overlap), 1) * 0.3

            # Find matching keywords
            source_content_lower = source.content.lower()
            matching_keywords = [
                topic for topic in target.topics
                if topic.lower() in source_content_lower
            ]

            if relevance_score > 0 or matching_keywords:
                scored.append({
                    "target": target.url,
                    "title": target.title,
                    "score": min(relevance_score, 1.0),
                    "keywords": matching_keywords or target.topics[:3],
                })

        return sorted(scored, key=lambda x: x["score"], reverse=True)

    def _parse_opportunities(
        self,
        response: str,
        source_url: str,
        target_pages: list[SitePage],
    ) -> list[LinkOpportunity]:
        """Parse opportunities from Claude response."""
        opportunities = []

        try:
            import re

            # Extract JSON from response
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())

            # Create a URL map for quick lookup
            url_map = {p.url: p for p in target_pages}

            for item in data[:5]:
                target_url = item.get("target_url", "")
                if target_url in url_map:
                    opportunity = LinkOpportunity(
                        source_url=source_url,
                        target_url=target_url,
                        anchor_text=item.get("anchor_text", ""),
                        relevance_score=item.get("relevance_score", 0.5),
                        keyword_match=item.get("keyword", ""),
                        linking_reason=item.get("reason", ""),
                        opportunity_type=item.get("type", "keyword_relevant"),
                        priority=item.get("priority", 5),
                    )
                    opportunities.append(opportunity)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse opportunities: %s", exc)

        return opportunities

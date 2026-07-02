"""Competitor analysis and outrank strategy generation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.clients.llm import llm_client

logger = logging.getLogger("omnirank.competitor")


@dataclass
class CompetitorData:
    """Raw competitor data from external sources."""
    domain: str
    keywords: list[dict[str, Any]]  # {keyword, volume, position, url}
    backlinks: int
    referring_domains: int
    top_pages: list[dict[str, Any]]  # {url, estimated_traffic, keywords}
    technical_score: int | None = None
    content_pages: int = 0
    avg_content_length: int = 0


@dataclass
class OutrankStrategy:
    """Generated strategy to outrank competitor."""
    target_keyword: str
    competitor_position: int
    recommended_action: str
    implementation_steps: list[str]
    content_gap: dict[str, Any]  # {topics_missing, format_opportunities, length_gap}
    estimated_roi: str
    priority: int  # 1-10, higher = more important


class CompetitorAgent:
    """Analyzes competitors and generates outrank strategies."""

    def __init__(self):
        self.llm = llm_client

    async def analyze_competitor(
        self,
        domain: str,
        competitor_data: CompetitorData,
        your_domain: str = "",
        your_keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze a competitor and generate insights."""
        try:
            # Prepare context for Claude
            context = self._prepare_analysis_context(
                domain,
                competitor_data,
                your_domain,
                your_keywords or [],
            )

            # Call Claude for deep analysis
            prompt = f"""Analyze this competitor and provide strategic insights:

Domain: {domain}
Top Keywords: {len(competitor_data.keywords)} keywords tracked
Top Positions: {', '.join(str(k.get('position', 'N/A')) for k in competitor_data.keywords[:5])}
Backlinks: {competitor_data.backlinks:,}
Referring Domains: {competitor_data.referring_domains}
Content Pages: {competitor_data.content_pages}
Avg Content Length: {competitor_data.avg_content_length} words

Top Pages:
{chr(10).join(f"- {p['url']}: ~{p.get('estimated_traffic', '?')} traffic" for p in competitor_data.top_pages[:5])}

Top Keywords:
{chr(10).join(f"- {k['keyword']}: vol={k.get('volume', '?')}, pos={k.get('position', '?')}" for k in competitor_data.keywords[:10])}

Provide:
1. Overall SEO strategy assessment
2. Content strategy analysis
3. Keyword targeting approach
4. Link building patterns
5. Technical SEO strengths/weaknesses
6. Competitive moats (defensibility)
7. Exploitable gaps in their strategy"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2000,
            )

            return {
                "domain": domain,
                "analysis": response,
                "data_snapshot": {
                    "keyword_count": len(competitor_data.keywords),
                    "backlink_count": competitor_data.backlinks,
                    "referring_domains": competitor_data.referring_domains,
                    "top_keywords": competitor_data.keywords[:20],
                    "top_pages": competitor_data.top_pages[:10],
                },
            }

        except Exception as exc:
            logger.error("Competitor analysis failed: %s", exc)
            raise

    async def generate_outrank_strategies(
        self,
        your_domain: str,
        your_keywords: list[str],
        competitor_domain: str,
        competitor_data: CompetitorData,
        your_rankings: dict[str, int] | None = None,
    ) -> list[OutrankStrategy]:
        """Generate specific strategies to outrank competitor."""
        try:
            your_rankings = your_rankings or {}

            # Find keyword gaps
            competitor_keywords = {k["keyword"] for k in competitor_data.keywords}
            shared_keywords = set(your_keywords) & competitor_keywords
            competitor_only = competitor_keywords - set(your_keywords)

            prompt = f"""Generate specific outrank strategies:

Your Domain: {your_domain}
Competitor: {competitor_domain}

Your Keywords: {len(your_keywords)} tracked
Shared Keywords: {len(shared_keywords)}
Competitor-Only Keywords: {len(competitor_only)}

Top Shared Keywords:
{chr(10).join(f"- {kw}: your_pos={your_rankings.get(kw, 'unranked')}, comp_pos={next((k['position'] for k in competitor_data.keywords if k['keyword'] == kw), 'N/A')}" for kw in list(shared_keywords)[:10])}

Competitor's Top Keywords:
{chr(10).join(f"- {k['keyword']}: pos={k.get('position', '?')}, vol={k.get('volume', '?')}" for k in competitor_data.keywords[:15])}

For each of these categories, provide 3-5 specific, actionable strategies:

1. QUICK WINS (keywords where competitor ranks 5+, you're unranked or 10+)
2. CONTENT UPGRADES (keywords you both rank for, but they're higher)
3. NEW OPPORTUNITIES (keywords only they rank for, high volume)
4. TECHNICAL ADVANTAGES (where to improve technical SEO vs them)
5. LINK BUILDING TARGETS (their best pages to benchmark against)

Format each strategy as JSON:
{{
  "target_keyword": "keyword",
  "competitor_position": X,
  "your_current_position": Y,
  "action": "brief description",
  "steps": ["step 1", "step 2", "step 3"],
  "content_gap": {{"topics": ["topic1"], "formats": ["format"], "length_gap": "XXX words"}},
  "roi": "estimated_timeline_and_impact",
  "priority": 1-10
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=3000,
            )

            # Parse strategies from response
            strategies = self._parse_strategy_response(response)
            return strategies

        except Exception as exc:
            logger.error("Strategy generation failed: %s", exc)
            raise

    async def generate_content_gaps(
        self,
        competitor_data: CompetitorData,
        your_keywords: list[str],
    ) -> dict[str, Any]:
        """Identify content gaps in competitor's coverage."""
        try:
            competitor_keywords = {k["keyword"] for k in competitor_data.keywords}
            missing_keywords = [k for k in your_keywords if k not in competitor_keywords]

            prompt = f"""Identify content gaps for competitor coverage:

Your Keywords: {len(your_keywords)} total
Missing from Competitor: {len(missing_keywords)}

Missing Keywords Sample:
{chr(10).join(missing_keywords[:20])}

Competitor's Content Strategy:
- Avg article length: {competitor_data.avg_content_length} words
- Total pages indexed: {competitor_data.content_pages}
- Top content topics: {', '.join(set(p.get('title', '') for p in competitor_data.top_pages[:5]))}

Identify:
1. Topic areas they haven't covered
2. Content formats they're missing (guides, tools, comparisons, case studies)
3. Long-tail keyword opportunities
4. Semantic clusters they haven't addressed
5. Geographic or intent-based angles they're ignoring
6. Trending topics in their space they're slow to cover

Provide as JSON with exploitable_gaps array."""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=1500,
            )

            return {
                "analysis": response,
                "missing_keyword_count": len(missing_keywords),
                "coverage_gap": round((len(missing_keywords) / len(your_keywords)) * 100, 1),
            }

        except Exception as exc:
            logger.error("Content gap analysis failed: %s", exc)
            raise

    def _prepare_analysis_context(
        self,
        domain: str,
        data: CompetitorData,
        your_domain: str,
        your_keywords: list[str],
    ) -> str:
        """Prepare context for Claude analysis."""
        return f"""
Competitor: {domain}
Your Domain: {your_domain}

Their Strategy:
- Ranking for {len(data.keywords)} keywords
- {data.backlinks:,} backlinks from {data.referring_domains} domains
- {data.content_pages} pages published
- Average content depth: {data.avg_content_length} words

Your Current State:
- Tracking {len(your_keywords)} keywords
- Need to analyze positioning
"""

    def _parse_strategy_response(self, response: str) -> list[OutrankStrategy]:
        """Parse Claude's strategy response into objects."""
        strategies = []
        try:
            # Try to extract JSON blocks from response
            import re
            json_blocks = re.findall(r'\{[^{}]*\}', response)

            for block in json_blocks[:10]:  # Top 10 strategies
                try:
                    data = json.loads(block)
                    strategy = OutrankStrategy(
                        target_keyword=data.get("target_keyword", ""),
                        competitor_position=data.get("competitor_position", 0),
                        recommended_action=data.get("action", ""),
                        implementation_steps=data.get("steps", []),
                        content_gap=data.get("content_gap", {}),
                        estimated_roi=data.get("roi", ""),
                        priority=data.get("priority", 5),
                    )
                    strategies.append(strategy)
                except (json.JSONDecodeError, KeyError):
                    continue

        except Exception as exc:
            logger.warning("Strategy parsing failed: %s", exc)

        return strategies

"""AI-Powered Keyword Strategy Agent.

Uses Claude for keyword research, clustering, difficulty assessment,
and content planning from seed keywords.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.clients.claude_client import HAIKU, SONNET, AIUsageAccumulator, ClaudeClient
from app.clients.http_clients import SerperHTTPClient

logger = logging.getLogger("omnirank.keyword")


@dataclass
class KeywordOpportunity:
    keyword: str
    search_volume_est: str  # "high", "medium", "low"
    difficulty_est: str  # "easy", "medium", "hard"
    intent: str  # informational, transactional, navigational, commercial
    content_type: str  # blog, landing, product, faq
    priority_score: float  # 0-100
    cluster: str  # topic cluster name
    notes: str = ""


@dataclass
class KeywordStrategyResult:
    primary_keyword: str
    opportunities: list[KeywordOpportunity] = field(default_factory=list)
    clusters: dict[str, list[str]] = field(default_factory=dict)
    content_plan: list[dict[str, str]] = field(default_factory=list)
    competitor_keywords: list[str] = field(default_factory=list)


class KeywordStrategyAgent:
    """AI-powered keyword research and strategy generation."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        serper_client: SerperHTTPClient | None = None,
    ):
        self.claude = claude_client
        self.serper = serper_client
        self.usage = AIUsageAccumulator()

    def research(
        self,
        seed_keyword: str,
        domain: str,
        locale: str = "en-US",
        region: str = "IN",
        industry: str = "",
    ) -> KeywordStrategyResult:
        """Full keyword research from a seed keyword."""

        # 1. Get SERP context if serper is available
        serp_context = ""
        if self.serper:
            try:
                results = self.serper.search_top_results(seed_keyword, locale, region, limit=5)
                serp_titles = [r.get("title", "") for r in results]
                serp_snippets = [r.get("snippet", "") for r in results[:3]]
                serp_context = f"""
Current SERP titles for "{seed_keyword}":
{chr(10).join(f'- {t}' for t in serp_titles)}

Top snippets:
{chr(10).join(f'- {s}' for s in serp_snippets)}"""
            except Exception as exc:
                logger.warning("Serper failed for keyword research: %s", exc)

        # 2. AI keyword expansion and analysis
        system = """You are an expert SEO keyword strategist specializing in the Indian market.
Given a seed keyword, generate a comprehensive keyword strategy.

For each keyword opportunity:
- Estimate search volume tier (high/medium/low)
- Estimate ranking difficulty (easy/medium/hard)
- Classify intent (informational/transactional/navigational/commercial)
- Suggest content type (blog/landing/product/faq/comparison/guide)
- Assign priority score (0-100)
- Group into topic clusters

Also provide:
- A content plan (which pages to create in what order)
- Keywords competitors are likely targeting

Focus on keywords relevant to the Indian market where applicable.

Respond ONLY with JSON:
{
  "opportunities": [
    {"keyword":"...","search_volume_est":"high|medium|low","difficulty_est":"easy|medium|hard","intent":"...","content_type":"...","priority_score":<0-100>,"cluster":"...","notes":"..."}
  ],
  "clusters": {"cluster_name": ["kw1","kw2"]},
  "content_plan": [{"order":1,"keyword":"...","content_type":"...","title":"...","rationale":"..."}],
  "competitor_keywords": ["kw1","kw2"]
}"""

        user_msg = f"""Seed keyword: "{seed_keyword}"
Domain: {domain}
Target market: {region} ({locale})
Industry: {industry or 'General'}
{serp_context}

Generate 20-30 keyword opportunities with clustering and a content plan."""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": user_msg}],
            system=system, model=SONNET, max_tokens=4096, temperature=0.3,
        )
        self.usage.record(resp)

        opportunities = []
        for opp in parsed.get("opportunities", []):
            if isinstance(opp, dict):
                opportunities.append(KeywordOpportunity(
                    keyword=opp.get("keyword", ""),
                    search_volume_est=opp.get("search_volume_est", "medium"),
                    difficulty_est=opp.get("difficulty_est", "medium"),
                    intent=opp.get("intent", "informational"),
                    content_type=opp.get("content_type", "blog"),
                    priority_score=float(opp.get("priority_score", 50)),
                    cluster=opp.get("cluster", "general"),
                    notes=opp.get("notes", ""),
                ))

        return KeywordStrategyResult(
            primary_keyword=seed_keyword,
            opportunities=sorted(opportunities, key=lambda x: x.priority_score, reverse=True),
            clusters=parsed.get("clusters", {}),
            content_plan=parsed.get("content_plan", []),
            competitor_keywords=parsed.get("competitor_keywords", []),
        )

    def classify_intent(self, keywords: list[str]) -> dict[str, str]:
        """Classify search intent for a batch of keywords using Haiku (cheap + fast)."""
        system = """Classify search intent for each keyword. Categories:
- informational: user wants to learn
- transactional: user wants to buy/sign up
- navigational: user looking for specific site
- commercial: user comparing options before buying

Respond ONLY with JSON: {"keyword": "intent", ...}"""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": f"Keywords: {', '.join(keywords)}"}],
            system=system, model=HAIKU, max_tokens=1024,
        )
        self.usage.record(resp)
        return {k: v for k, v in parsed.items() if isinstance(v, str)}

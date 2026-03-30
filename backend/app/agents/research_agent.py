"""Algorithmic Reverse-Engineer Research Agent (Phase 1).

This module provides deterministic SEO competitor analysis with pluggable API clients.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Protocol

from app.schemas.research import (
    CompetitorPageProfile,
    GapAnalysis,
    ResearchRequest,
    ResearchResponse,
)

STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "from",
    "this",
    "your",
    "into",
    "about",
    "when",
    "what",
    "where",
    "which",
    "their",
    "have",
}


class SerperClient(Protocol):
    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3) -> list[dict]:
        ...


class FirecrawlClient(Protocol):
    def scrape_markdown(self, url: str) -> str:
        ...


@dataclass
class RawPageSignals:
    title: str
    h1: str | None
    h2: list[str]
    questions: list[str]
    entities: list[str]
    words: list[str]


class AlgorithmicReverseEngineerAgent:
    """Research agent that reverse engineers top-ranking pages for ranking patterns."""

    def __init__(self, serper_client: SerperClient, firecrawl_client: FirecrawlClient):
        self.serper = serper_client
        self.firecrawl = firecrawl_client

    def run(self, request: ResearchRequest) -> ResearchResponse:
        serp_results = self.serper.search_top_results(
            keyword=request.primary_keyword,
            locale=request.locale,
            region=request.target_region,
            limit=3,
        )

        competitor_profiles = [
            self._build_profile(item["link"], request.primary_keyword) for item in serp_results[:3]
        ]
        client_profile = self._build_profile(str(request.client_url), request.primary_keyword)

        gap_analysis = self._build_gap_analysis(client_profile, competitor_profiles)
        seo_score = self._score(client_profile, competitor_profiles, gap_analysis)
        recommendations = self._recommend(gap_analysis, client_profile, competitor_profiles)

        return ResearchResponse(
            seo_score=seo_score,
            competitor_profiles=competitor_profiles,
            client_profile=client_profile,
            gap_analysis=gap_analysis,
            recommendations=recommendations,
            raw_metrics={
                "avg_competitor_word_count": sum(c.word_count for c in competitor_profiles)
                / max(len(competitor_profiles), 1),
                "avg_competitor_density": sum(c.keyword_density for c in competitor_profiles)
                / max(len(competitor_profiles), 1),
            },
        )

    def _build_profile(self, url: str, keyword: str) -> CompetitorPageProfile:
        markdown = self.firecrawl.scrape_markdown(url)
        signals = self._extract_signals(markdown)

        keyword_density = self._keyword_density(signals.words, keyword)

        return CompetitorPageProfile(
            url=url,
            title=signals.title,
            h1=signals.h1,
            h2=signals.h2[:10],
            top_entities=signals.entities[:20],
            top_questions=signals.questions[:10],
            word_count=len(signals.words),
            keyword_density=keyword_density,
        )

    def _extract_signals(self, markdown: str) -> RawPageSignals:
        lines = [line.strip() for line in markdown.splitlines() if line.strip()]

        title = next((line.replace("# ", "") for line in lines if line.startswith("# ")), "Untitled")
        h1 = next((line.replace("# ", "") for line in lines if line.startswith("# ")), None)
        h2 = [line.replace("## ", "") for line in lines if line.startswith("## ")]

        full_text = " ".join(lines)
        words = re.findall(r"[A-Za-z][A-Za-z\-']+", full_text.lower())

        entity_matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", markdown)
        entity_counts = Counter(e.strip() for e in entity_matches)
        entities = [entity for entity, _ in entity_counts.most_common() if entity.lower() not in STOPWORDS]

        questions = [line for line in lines if line.endswith("?")]
        if not questions:
            questions = re.findall(r"([^.!?]*\?)", full_text)
            questions = [q.strip() for q in questions if 30 <= len(q.strip()) <= 140]

        return RawPageSignals(
            title=title,
            h1=h1,
            h2=h2,
            questions=questions,
            entities=entities,
            words=[w for w in words if w not in STOPWORDS],
        )

    def _keyword_density(self, words: list[str], keyword: str) -> float:
        if not words:
            return 0.0
        keyword_terms = keyword.lower().split()
        hits = sum(1 for word in words if word in keyword_terms)
        return round((hits / len(words)) * 100, 3)

    def _build_gap_analysis(
        self,
        client: CompetitorPageProfile,
        competitors: list[CompetitorPageProfile],
    ) -> GapAnalysis:
        competitor_entities = Counter()
        competitor_questions: set[str] = set()
        competitor_h2: set[str] = set()

        for c in competitors:
            competitor_entities.update(c.top_entities)
            competitor_questions.update(c.top_questions)
            competitor_h2.update(c.h2)

        missing_entities = [
            entity for entity, _ in competitor_entities.most_common(25) if entity not in client.top_entities
        ][:10]

        missing_questions = [q for q in competitor_questions if q not in client.top_questions][:10]
        heading_gaps = [h for h in competitor_h2 if h not in client.h2][:10]

        avg_comp_density = (
            sum(c.keyword_density for c in competitors) / max(len(competitors), 1) if competitors else 0.0
        )
        density_gap = round(avg_comp_density - client.keyword_density, 3)

        return GapAnalysis(
            missing_entities=missing_entities,
            missing_questions=missing_questions,
            heading_gaps=heading_gaps,
            density_gap=density_gap,
        )

    def _score(
        self,
        client: CompetitorPageProfile,
        competitors: list[CompetitorPageProfile],
        gap: GapAnalysis,
    ) -> float:
        if not competitors:
            return 0.0

        avg_words = sum(c.word_count for c in competitors) / len(competitors)
        content_depth = min((client.word_count / max(avg_words, 1)) * 35, 35)

        entity_alignment = max(0, 30 - (len(gap.missing_entities) * 2.5))
        snippet_readiness = max(0, 20 - (len(gap.missing_questions) * 2.0))

        density_penalty = abs(gap.density_gap) * 5
        density_score = max(0, 15 - density_penalty)

        total = content_depth + entity_alignment + snippet_readiness + density_score
        return round(min(100, total), 2)

    def _recommend(
        self,
        gap: GapAnalysis,
        client: CompetitorPageProfile,
        competitors: list[CompetitorPageProfile],
    ) -> list[str]:
        avg_words = sum(c.word_count for c in competitors) / max(len(competitors), 1)
        recommendations: list[str] = []

        if client.word_count < avg_words:
            recommendations.append(
                f"Expand page depth by ~{int(avg_words - client.word_count)} words to match top competitors."
            )

        if gap.missing_entities:
            recommendations.append(
                "Add semantic entity coverage for: " + ", ".join(gap.missing_entities[:5])
            )

        if gap.heading_gaps:
            recommendations.append(
                "Add section headings for uncovered topics: " + ", ".join(gap.heading_gaps[:4])
            )

        if gap.missing_questions:
            recommendations.append(
                "Create Position Zero FAQ block answering: " + " | ".join(gap.missing_questions[:3])
            )

        if gap.density_gap > 0.4:
            recommendations.append(
                "Increase natural keyword usage in introductions/subheadings while preserving readability."
            )

        if not recommendations:
            recommendations.append("Content is benchmark-aligned; proceed to technical and backlink optimization.")

        return recommendations

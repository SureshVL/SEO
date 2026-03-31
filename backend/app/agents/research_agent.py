"""Algorithmic Reverse-Engineer Research Agent (Phase 1).

Deterministic competitor benchmarking with pluggable data providers.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
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
    "they",
    "them",
    "then",
    "than",
    "will",
}


class SerperClient(Protocol):
    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3) -> list[dict]:
        """Return search results where each item includes at least a `link` key."""


class FirecrawlClient(Protocol):
    def scrape_markdown(self, url: str) -> str:
        """Return cleaned markdown content for a URL."""


@dataclass
class RawPageSignals:
    title: str
    h1: str | None
    h2: list[str]
    questions: list[str]
    entities: list[str]
    words: list[str]


class AlgorithmicReverseEngineerAgent:
    """Reverse engineer top-ranked pages to compute ranking opportunities."""

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
        if not serp_results:
            raise ValueError("No SERP results returned by Serper client.")

        competitor_links = [item.get("link", "").strip() for item in serp_results[:3]]
        competitor_links = [link for link in competitor_links if link]
        if not competitor_links:
            raise ValueError("SERP response did not include valid competitor links.")

        competitor_profiles = [self._build_profile(link, request.primary_keyword) for link in competitor_links]
        client_profile = self._build_profile(str(request.client_url), request.primary_keyword)

        competitor_markdown = {c.url: self.firecrawl.scrape_markdown(c.url) for c in competitor_profiles}

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
                "avg_competitor_word_count": self._mean([c.word_count for c in competitor_profiles]),
                "avg_competitor_density": self._mean([c.keyword_density for c in competitor_profiles]),
                "avg_competitor_question_count": self._mean([len(c.top_questions) for c in competitor_profiles]),
                "avg_competitor_entity_count": self._mean([len(c.top_entities) for c in competitor_profiles]),
                "scraped_content": competitor_markdown,
            },
        )

    def _build_profile(self, url: str, keyword: str) -> CompetitorPageProfile:
        markdown = self.firecrawl.scrape_markdown(url)
        signals = self._extract_signals(markdown)

        return CompetitorPageProfile(
            url=url,
            title=signals.title,
            h1=signals.h1,
            h2=signals.h2[:15],
            top_entities=signals.entities[:25],
            top_questions=signals.questions[:12],
            word_count=len(signals.words),
            keyword_density=self._keyword_density(signals.words, keyword),
        )

    def _extract_signals(self, markdown: str) -> RawPageSignals:
        lines = [line.strip() for line in markdown.splitlines() if line.strip()]

        h1_candidates = [line.replace("# ", "").strip() for line in lines if line.startswith("# ")]
        title = h1_candidates[0] if h1_candidates else "Untitled"
        h1 = h1_candidates[0] if h1_candidates else None
        h2 = [line.replace("## ", "").strip() for line in lines if line.startswith("## ")]

        full_text = " ".join(lines)
        words = re.findall(r"[A-Za-z][A-Za-z\-']+", full_text.lower())
        words = [w for w in words if w not in STOPWORDS and len(w) > 2]

        entity_matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", markdown)
        entity_counts = Counter(entity_matches)
        entities = [e for e, _ in entity_counts.most_common()]

        questions = [line for line in lines if line.endswith("?")]
        if not questions:
            questions = re.findall(r"([^.!?]*\?)", full_text)
            questions = [q.strip() for q in questions if 30 <= len(q.strip()) <= 180]

        return RawPageSignals(
            title=title,
            h1=h1,
            h2=h2,
            questions=self._unique_preserve_order(questions),
            entities=self._unique_preserve_order(entities),
            words=words,
        )

    def _keyword_density(self, words: list[str], keyword: str) -> float:
        if not words:
            return 0.0
        keyword_terms = [term for term in re.findall(r"[A-Za-z0-9]+", keyword.lower()) if len(term) > 1]
        if not keyword_terms:
            return 0.0
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

        for comp in competitors:
            competitor_entities.update(comp.top_entities)
            competitor_questions.update(comp.top_questions)
            competitor_h2.update(comp.h2)

        missing_entities = [entity for entity, _ in competitor_entities.most_common(30) if entity not in client.top_entities][:12]
        missing_questions = [q for q in competitor_questions if q not in client.top_questions][:12]
        heading_gaps = [h for h in competitor_h2 if h not in client.h2][:12]

        avg_comp_density = self._mean([c.keyword_density for c in competitors])
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

        avg_words = self._mean([c.word_count for c in competitors])
        avg_questions = self._mean([len(c.top_questions) for c in competitors])

        content_depth_score = min(35.0, (client.word_count / max(avg_words, 1.0)) * 35.0)

        entity_score = max(0.0, 30.0 - (len(gap.missing_entities) * 2.2))
        snippet_score = min(20.0, (len(client.top_questions) / max(avg_questions, 1.0)) * 20.0)

        density_penalty = min(15.0, math.fabs(gap.density_gap) * 4.0)
        density_score = max(0.0, 15.0 - density_penalty)

        total = content_depth_score + entity_score + snippet_score + density_score
        return round(min(100.0, total), 2)

    def _recommend(
        self,
        gap: GapAnalysis,
        client: CompetitorPageProfile,
        competitors: list[CompetitorPageProfile],
    ) -> list[str]:
        avg_words = self._mean([c.word_count for c in competitors])
        recommendations: list[str] = []

        if client.word_count < avg_words:
            recommendations.append(f"Expand page depth by ~{int(avg_words - client.word_count)} words to match top competitors.")
        if gap.missing_entities:
            recommendations.append("Add semantic entity coverage for: " + ", ".join(gap.missing_entities[:6]))
        if gap.heading_gaps:
            recommendations.append("Add section headings for uncovered topics: " + ", ".join(gap.heading_gaps[:5]))
        if gap.missing_questions:
            recommendations.append("Create Position Zero FAQ block answering: " + " | ".join(gap.missing_questions[:4]))
        if gap.density_gap > 0.4:
            recommendations.append("Increase natural keyword usage in intros/subheadings while preserving readability.")
        if not recommendations:
            recommendations.append("Content is benchmark-aligned; proceed to technical and backlink optimization.")
        return recommendations

    @staticmethod
    def _unique_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    @staticmethod
    def _mean(values: list[float | int]) -> float:
        if not values:
            return 0.0
        return float(sum(values) / len(values))

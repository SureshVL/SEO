"""AI-Powered SEO Research Agent.

Replaces the heuristic-only approach with Claude-powered analysis
while keeping deterministic data collection via Serper + Firecrawl.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Protocol

from app.clients.claude_client import SONNET, AIUsageAccumulator, ClaudeClient
from app.schemas.research import (
    CompetitorPageProfile,
    GapAnalysis,
    ResearchRequest,
    ResearchResponse,
)

logger = logging.getLogger("omnirank.research")

STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "your", "into",
    "about", "when", "what", "where", "which", "their", "have", "they",
    "them", "then", "than", "will", "are", "was", "were", "been", "being",
    "has", "had", "does", "did", "not", "but", "can", "could", "would",
    "should", "may", "might", "shall", "must", "its", "also", "each",
    "more", "most", "other", "some", "such", "only", "very", "just",
}


class SerperClient(Protocol):
    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3) -> list[dict]: ...


class FirecrawlClient(Protocol):
    def scrape_markdown(self, url: str) -> str: ...


class AlgorithmicReverseEngineerAgent:
    """AI-augmented SEO research: deterministic data collection + Claude analysis."""

    def __init__(
        self,
        serper_client: SerperClient,
        firecrawl_client: FirecrawlClient,
        claude_client: ClaudeClient | None = None,
    ):
        self.serper = serper_client
        self.firecrawl = firecrawl_client
        self.claude = claude_client
        self.usage = AIUsageAccumulator()

    def run(self, request: ResearchRequest) -> ResearchResponse:
        serp_results = self.serper.search_top_results(
            keyword=request.primary_keyword,
            locale=request.locale,
            region=request.target_region,
            limit=5,
        )
        if not serp_results:
            raise ValueError("No SERP results returned by Serper client.")

        competitor_links = [item.get("link", "").strip() for item in serp_results[:5]]
        competitor_links = [link for link in competitor_links if link]
        if not competitor_links:
            raise ValueError("SERP response did not include valid competitor links.")

        competitor_profiles = []
        competitor_markdown: dict[str, str] = {}
        for link in competitor_links[:5]:
            try:
                md = self.firecrawl.scrape_markdown(link)
                competitor_markdown[link] = md
                profile = self._build_profile(link, request.primary_keyword, md)
                competitor_profiles.append(profile)
            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", link, exc)

        if not competitor_profiles:
            raise ValueError("Could not scrape any competitor pages.")

        client_md = self.firecrawl.scrape_markdown(str(request.client_url))
        client_profile = self._build_profile(str(request.client_url), request.primary_keyword, client_md)

        gap_analysis = self._build_gap_analysis(client_profile, competitor_profiles)

        if self.claude:
            seo_score, recommendations = self._ai_analyze(
                client_profile, competitor_profiles, gap_analysis,
                request.primary_keyword, client_md, competitor_markdown,
            )
        else:
            seo_score = self._deterministic_score(client_profile, competitor_profiles, gap_analysis)
            recommendations = self._deterministic_recommend(gap_analysis, client_profile, competitor_profiles)

        return ResearchResponse(
            seo_score=seo_score,
            competitor_profiles=competitor_profiles,
            client_profile=client_profile,
            gap_analysis=gap_analysis,
            recommendations=recommendations,
            raw_metrics={
                "avg_competitor_word_count": self._mean([c.word_count for c in competitor_profiles]),
                "avg_competitor_density": self._mean([c.keyword_density for c in competitor_profiles]),
                "scraped_content": competitor_markdown,
                "ai_usage": {
                    "total_input_tokens": self.usage.total_input_tokens,
                    "total_output_tokens": self.usage.total_output_tokens,
                    "total_cost_usd": self.usage.total_cost_usd,
                },
            },
        )

    def _ai_analyze(
        self,
        client: CompetitorPageProfile,
        competitors: list[CompetitorPageProfile],
        gap: GapAnalysis,
        keyword: str,
        client_md: str,
        competitor_md: dict[str, str],
    ) -> tuple[float, list[str]]:
        client_excerpt = client_md[:3000]
        comp_excerpts = {url: md[:2000] for url, md in list(competitor_md.items())[:3]}

        system = """You are an expert SEO analyst. Analyze the client page vs competitors
for the target keyword. Provide an honest SEO readiness score (0-100) and
5-8 specific, actionable recommendations ranked by impact.

Score criteria (total 100):
- Content depth & quality (0-30): word count, coverage, expertise
- Entity & semantic coverage (0-25): named entities, LSI terms, completeness
- Technical SEO signals (0-20): heading structure, links, schema readiness
- Search intent alignment (0-15): does content match keyword intent?
- Competitive positioning (0-10): unique value vs competitors

Respond ONLY with valid JSON:
{
  "score": <number>,
  "score_breakdown": {"content_depth":<0-30>,"entity_coverage":<0-25>,"technical_signals":<0-20>,"intent_alignment":<0-15>,"competitive_edge":<0-10>},
  "recommendations": [{"priority":"critical|high|medium","action":"<specific>","impact":"<result>"}]
}"""

        comp_summary = "\n".join([
            f"Competitor {i+1} ({p.url}): {p.word_count} words, {len(p.top_entities)} entities, "
            f"density {p.keyword_density}%, H2s: {', '.join(p.h2[:5])}"
            for i, p in enumerate(competitors[:3])
        ])

        user_msg = f"""Target keyword: "{keyword}"

CLIENT PAGE ({client.url}):
- Words: {client.word_count}, Density: {client.keyword_density}%
- H1: {client.h1}
- H2s: {', '.join(client.h2[:10])}
- Entities: {', '.join(client.top_entities[:15])}
- Questions: {', '.join(client.top_questions[:5])}
Content excerpt:
{client_excerpt}

COMPETITORS:
{comp_summary}

GAPS:
- Missing entities: {', '.join(gap.missing_entities[:10])}
- Missing questions: {', '.join(gap.missing_questions[:5])}
- Heading gaps: {', '.join(gap.heading_gaps[:5])}
- Density gap: {gap.density_gap}

Competitor excerpts:
{chr(10).join(f"--- {url} ---{chr(10)}{ex}" for url, ex in list(comp_excerpts.items())[:2])}"""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": user_msg}],
            system=system, model=SONNET, max_tokens=2048, temperature=0.2,
        )
        self.usage.record(resp)

        score = float(parsed.get("score", 50))
        recs_raw = parsed.get("recommendations", [])
        recommendations = []
        for r in recs_raw:
            if isinstance(r, dict):
                pri = r.get("priority", "medium")
                act = r.get("action", "")
                imp = r.get("impact", "")
                recommendations.append(f"[{pri.upper()}] {act} → {imp}")
            elif isinstance(r, str):
                recommendations.append(r)

        return score, recommendations or ["Review gap analysis manually."]

    def _build_profile(self, url: str, keyword: str, markdown: str) -> CompetitorPageProfile:
        lines = [l.strip() for l in markdown.splitlines() if l.strip()]
        h1_cands = [l.replace("# ", "").strip() for l in lines if l.startswith("# ")]
        title = h1_cands[0] if h1_cands else "Untitled"
        h1 = h1_cands[0] if h1_cands else None
        h2 = [l.replace("## ", "").strip() for l in lines if l.startswith("## ")]

        full_text = " ".join(lines)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-']+", full_text.lower()) if w not in STOPWORDS and len(w) > 2]

        entity_matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", markdown)
        entities = [e for e, _ in Counter(entity_matches).most_common()]

        questions = [l for l in lines if l.endswith("?")]
        if not questions:
            questions = [q.strip() for q in re.findall(r"([^.!?]*\?)", full_text) if 30 <= len(q.strip()) <= 180]

        return CompetitorPageProfile(
            url=url, title=title, h1=h1, h2=h2[:15],
            top_entities=self._unique(entities)[:25],
            top_questions=self._unique(questions)[:12],
            word_count=len(words),
            keyword_density=self._keyword_density(words, keyword),
        )

    def _keyword_density(self, words: list[str], keyword: str) -> float:
        if not words:
            return 0.0
        terms = [t for t in re.findall(r"[A-Za-z0-9]+", keyword.lower()) if len(t) > 1]
        if not terms:
            return 0.0
        return round((sum(1 for w in words if w in terms) / len(words)) * 100, 3)

    def _build_gap_analysis(self, client: CompetitorPageProfile, competitors: list[CompetitorPageProfile]) -> GapAnalysis:
        comp_entities: Counter[str] = Counter()
        comp_questions: set[str] = set()
        comp_h2: set[str] = set()
        for c in competitors:
            comp_entities.update(c.top_entities)
            comp_questions.update(c.top_questions)
            comp_h2.update(c.h2)

        return GapAnalysis(
            missing_entities=[e for e, _ in comp_entities.most_common(30) if e not in client.top_entities][:12],
            missing_questions=[q for q in comp_questions if q not in client.top_questions][:12],
            heading_gaps=[h for h in comp_h2 if h not in client.h2][:12],
            density_gap=round(self._mean([c.keyword_density for c in competitors]) - client.keyword_density, 3),
        )

    def _deterministic_score(self, client: CompetitorPageProfile, competitors: list[CompetitorPageProfile], gap: GapAnalysis) -> float:
        if not competitors:
            return 0.0
        avg_w = self._mean([c.word_count for c in competitors])
        avg_q = self._mean([len(c.top_questions) for c in competitors])
        cs = min(35.0, (client.word_count / max(avg_w, 1.0)) * 35.0)
        es = max(0.0, 30.0 - len(gap.missing_entities) * 2.2)
        ss = min(20.0, (len(client.top_questions) / max(avg_q, 1.0)) * 20.0)
        ds = max(0.0, 15.0 - min(15.0, math.fabs(gap.density_gap) * 4.0))
        return round(min(100.0, cs + es + ss + ds), 2)

    def _deterministic_recommend(self, gap: GapAnalysis, client: CompetitorPageProfile, competitors: list[CompetitorPageProfile]) -> list[str]:
        avg_w = self._mean([c.word_count for c in competitors])
        r: list[str] = []
        if client.word_count < avg_w:
            r.append(f"Expand content by ~{int(avg_w - client.word_count)} words.")
        if gap.missing_entities:
            r.append("Add entities: " + ", ".join(gap.missing_entities[:6]))
        if gap.heading_gaps:
            r.append("Add headings: " + ", ".join(gap.heading_gaps[:5]))
        if gap.missing_questions:
            r.append("Add FAQ: " + " | ".join(gap.missing_questions[:4]))
        return r or ["Content is benchmark-aligned."]

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        seen: set[str] = set()
        return [x for x in items if x not in seen and not seen.add(x)]  # type: ignore

    @staticmethod
    def _mean(values: list[float | int]) -> float:
        return float(sum(values) / len(values)) if values else 0.0

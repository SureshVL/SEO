"""AI-Powered SEO Research Agent — DataForSEO Edition."""

from __future__ import annotations
import logging
import math
import re
from collections import Counter
from typing import Any

from app.clients.dataforseo_client import DataForSEOClient
from app.clients.claude_client import AIUsageAccumulator
from app.schemas.research import (
    CompetitorPageProfile, GapAnalysis, ResearchRequest, ResearchResponse,
)

logger = logging.getLogger("omnirank.research")

STOPWORDS = {
    "the","and","for","that","with","from","this","your","into","about",
    "when","what","where","which","their","have","they","them","then",
    "than","will","are","was","were","been","being","has","had","does",
    "did","not","but","can","could","would","should","may","might",
    "shall","must","its","also","each","more","most","other","some",
    "such","only","very","just",
}


class AlgorithmicReverseEngineerAgent:
    """SEO research using DataForSEO for data + Gemini/Claude for analysis."""

    def __init__(self, serper_client=None, firecrawl_client=None, claude_client=None):
        self.dfs = DataForSEOClient()
        self.claude = claude_client
        self.usage = AIUsageAccumulator()
        # Keep old clients as fallback
        self.serper = serper_client
        self.firecrawl = firecrawl_client

    def run(self, request: ResearchRequest) -> ResearchResponse:
        keyword = request.primary_keyword
        client_url = str(request.client_url)
        client_domain = self._extract_domain(client_url)

        if self.dfs.enabled:
            return self._run_with_dataforseo(request, keyword, client_url, client_domain)
        elif self.serper and self.firecrawl:
            return self._run_with_serper(request)
        else:
            raise ValueError("No data provider configured. Add DATAFORSEO_LOGIN/PASSWORD or SERPER_API_KEY to .env")

    def _run_with_dataforseo(self, request, keyword, client_url, client_domain):
        # 1. Get SERP results
        serp_results = self.dfs.serp_competitors(
            keyword, location_code=2356, language_code="en"
        )
        if not serp_results:
            raise ValueError(f"No SERP results for '{keyword}'")

        # 2. Build competitor profiles from SERP
        competitor_profiles = []
        for item in serp_results[:5]:
            url = item.get("url", "")
            domain = item.get("domain", "")
            if domain == client_domain:
                continue
            profile = CompetitorPageProfile(
                url=url,
                title=item.get("title", ""),
                h1=item.get("title"),
                h2=[],
                top_entities=[],
                top_questions=[],
                word_count=0,
                keyword_density=0,
            )
            # Enrich with backlink data
            try:
                bl = self.dfs.backlink_summary(domain)
                profile.word_count = bl.referring_domains  # repurpose for display
            except Exception:
                pass
            competitor_profiles.append(profile)

        if not competitor_profiles:
            raise ValueError("No competitors found in SERP")

        # 3. Get client backlink profile
        try:
            client_bl = self.dfs.backlink_summary(client_domain)
        except Exception:
            client_bl = None

        # 4. Build client profile
        client_profile = CompetitorPageProfile(
            url=client_url,
            title=client_domain,
            h1=client_domain,
            h2=[],
            top_entities=[],
            top_questions=[],
            word_count=client_bl.referring_domains if client_bl else 0,
            keyword_density=0,
        )

        # 5. Get SERP features
        try:
            features = self.dfs.serp_features(keyword, location_code=2356)
        except Exception:
            features = []

        # 6. Gap analysis
        gap_analysis = GapAnalysis(
            missing_entities=[f.replace("_", " ") for f in features[:8]],
            missing_questions=[],
            heading_gaps=[item.get("title","") for item in serp_results[:3] if item.get("domain") != client_domain],
            density_gap=0,
        )

        # 7. AI Analysis
        if self.claude:
            seo_score, recommendations = self._ai_analyze_dfs(
                client_profile, competitor_profiles, gap_analysis,
                keyword, serp_results, client_bl, features,
            )
        else:
            seo_score = self._score_from_data(client_bl, serp_results, client_domain)
            recommendations = self._basic_recommendations(client_bl, serp_results, features, client_domain)

        return ResearchResponse(
            seo_score=seo_score,
            competitor_profiles=competitor_profiles,
            client_profile=client_profile,
            gap_analysis=gap_analysis,
            recommendations=recommendations,
            raw_metrics={
                "serp_features": features,
                "client_backlinks": {
                    "total": client_bl.total_backlinks if client_bl else 0,
                    "referring_domains": client_bl.referring_domains if client_bl else 0,
                    "domain_rank": client_bl.domain_rank if client_bl else 0,
                },
                "dataforseo_cost": self.dfs.get_cost_summary(),
                "ai_usage": {
                    "total_input_tokens": self.usage.total_input_tokens,
                    "total_output_tokens": self.usage.total_output_tokens,
                    "total_cost_usd": self.usage.total_cost_usd,
                },
            },
        )

    def _ai_analyze_dfs(self, client, competitors, gap, keyword, serp_results, client_bl, features):
        system = """You are an expert SEO analyst. Analyze the client vs SERP competitors.
Consider: backlink strength, SERP feature presence, content gaps, local SEO signals.
Score criteria (total 100):
- Content relevance (0-25)
- Backlink authority (0-25)
- Technical signals (0-20)
- Local/SERP features (0-15)
- Competitive positioning (0-15)
Respond ONLY with valid JSON:
{"score": <number>, "recommendations": [{"priority":"critical|high|medium","action":"<specific>","impact":"<result>"}]}"""

        comp_text = "\n".join([
            f"#{i+1} {c.url} (referring domains: {c.word_count})"
            for i, c in enumerate(competitors[:5])
        ])

        bl_text = "None"
        if client_bl:
            bl_text = f"Backlinks: {client_bl.total_backlinks}, Referring domains: {client_bl.referring_domains}, Domain rank: {client_bl.domain_rank}, Dofollow: {client_bl.dofollow_ratio}%"

        user_msg = f"""Keyword: "{keyword}"
Client: {client.url}
Client backlinks: {bl_text}
SERP features present: {', '.join(features) if features else 'none detected'}
Top competitors:
{comp_text}
Content gaps: {', '.join(gap.missing_entities[:8])}
Competitor titles: {', '.join(gap.heading_gaps[:5])}"""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": user_msg}],
            system=system, max_tokens=2048, temperature=0.2,
        )
        self.usage.record(resp)

        score = float(parsed.get("score", 50))
        recs = []
        for r in parsed.get("recommendations", []):
            if isinstance(r, dict):
                recs.append(f"[{r.get('priority','medium').upper()}] {r.get('action','')} -> {r.get('impact','')}")
            elif isinstance(r, str):
                recs.append(r)
        return score, recs or ["Review analysis manually."]

    def _score_from_data(self, client_bl, serp_results, client_domain):
        score = 30.0
        if client_bl:
            if client_bl.referring_domains > 100: score += 15
            elif client_bl.referring_domains > 30: score += 10
            elif client_bl.referring_domains > 10: score += 5
            if client_bl.domain_rank > 50: score += 15
            elif client_bl.domain_rank > 30: score += 10
            elif client_bl.domain_rank > 10: score += 5
        # Check if client appears in SERP
        for item in serp_results:
            if client_domain in item.get("domain", ""):
                pos = item.get("position", 100)
                if pos <= 3: score += 20
                elif pos <= 10: score += 10
                elif pos <= 20: score += 5
                break
        return min(100.0, round(score, 2))

    def _basic_recommendations(self, client_bl, serp_results, features, client_domain):
        recs = []
        if not client_bl or client_bl.referring_domains < 20:
            recs.append("[CRITICAL] Build backlinks - your referring domains are very low compared to competitors")
        if "local_pack" in features:
            recs.append("[HIGH] Optimize Google Business Profile - local pack appears for this keyword")
        if "featured_snippet" in features:
            recs.append("[HIGH] Target featured snippet with structured content and FAQ schema")
        if "people_also_ask" in features:
            recs.append("[MEDIUM] Add FAQ section targeting People Also Ask questions")
        in_serp = any(client_domain in item.get("domain","") for item in serp_results)
        if not in_serp:
            recs.append("[CRITICAL] Your site does not appear in top 20 results for this keyword")
        return recs or ["Site appears competitive - focus on content depth and backlink quality"]

    def _run_with_serper(self, request):
        """Fallback to old Serper+Firecrawl pipeline."""
        serp_results = self.serper.search_top_results(
            keyword=request.primary_keyword, locale=request.locale,
            region=request.target_region, limit=5)
        if not serp_results:
            raise ValueError("No SERP results returned.")
        competitor_links = [i.get("link","").strip() for i in serp_results[:5]]
        competitor_links = [l for l in competitor_links if l]
        if not competitor_links:
            raise ValueError("No valid competitor links.")
        competitor_profiles = []
        competitor_markdown = {}
        for link in competitor_links[:5]:
            try:
                md = self.firecrawl.scrape_markdown(link)
                competitor_markdown[link] = md
                competitor_profiles.append(self._build_profile(link, request.primary_keyword, md))
            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", link, exc)
        if not competitor_profiles:
            raise ValueError("Could not scrape any competitor pages.")
        client_md = self.firecrawl.scrape_markdown(str(request.client_url))
        client_profile = self._build_profile(str(request.client_url), request.primary_keyword, client_md)
        gap = self._build_gap_analysis(client_profile, competitor_profiles)
        seo_score = self._deterministic_score(client_profile, competitor_profiles, gap)
        recommendations = self._deterministic_recommend(gap, client_profile, competitor_profiles)
        return ResearchResponse(
            seo_score=seo_score, competitor_profiles=competitor_profiles,
            client_profile=client_profile, gap_analysis=gap,
            recommendations=recommendations, raw_metrics={})

    def _build_profile(self, url, keyword, markdown):
        lines = [l.strip() for l in markdown.splitlines() if l.strip()]
        h1_cands = [l.replace("# ","").strip() for l in lines if l.startswith("# ")]
        h1 = h1_cands[0] if h1_cands else None
        h2 = [l.replace("## ","").strip() for l in lines if l.startswith("## ")]
        full_text = " ".join(lines)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-']+", full_text.lower()) if w not in STOPWORDS and len(w)>2]
        entities = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", markdown)
        entities = [e for e,_ in Counter(entities).most_common()]
        questions = [l for l in lines if l.endswith("?")]
        return CompetitorPageProfile(url=url, title=h1 or "Untitled", h1=h1, h2=h2[:15],
            top_entities=entities[:25], top_questions=questions[:12],
            word_count=len(words), keyword_density=self._kw_density(words,keyword))

    def _kw_density(self, words, keyword):
        if not words: return 0.0
        terms = [t for t in re.findall(r"[A-Za-z0-9]+", keyword.lower()) if len(t)>1]
        if not terms: return 0.0
        return round((sum(1 for w in words if w in terms)/len(words))*100, 3)

    def _build_gap_analysis(self, client, competitors):
        ce=Counter(); cq=set(); ch=set()
        for c in competitors:
            ce.update(c.top_entities); cq.update(c.top_questions); ch.update(c.h2)
        return GapAnalysis(
            missing_entities=[e for e,_ in ce.most_common(30) if e not in client.top_entities][:12],
            missing_questions=[q for q in cq if q not in client.top_questions][:12],
            heading_gaps=[h for h in ch if h not in client.h2][:12],
            density_gap=round(self._mean([c.keyword_density for c in competitors])-client.keyword_density,3))

    def _deterministic_score(self, client, competitors, gap):
        if not competitors: return 0.0
        aw=self._mean([c.word_count for c in competitors])
        aq=self._mean([len(c.top_questions) for c in competitors])
        return round(min(100.0, min(35,(client.word_count/max(aw,1))*35)+
            max(0,30-len(gap.missing_entities)*2.2)+
            min(20,(len(client.top_questions)/max(aq,1))*20)+
            max(0,15-min(15,math.fabs(gap.density_gap)*4))),2)

    def _deterministic_recommend(self, gap, client, competitors):
        aw=self._mean([c.word_count for c in competitors]); r=[]
        if client.word_count<aw: r.append(f"Expand content by ~{int(aw-client.word_count)} words.")
        if gap.missing_entities: r.append("Add entities: "+", ".join(gap.missing_entities[:6]))
        if gap.heading_gaps: r.append("Add headings: "+", ".join(gap.heading_gaps[:5]))
        return r or ["Content is benchmark-aligned."]

    @staticmethod
    def _extract_domain(url):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        if domain.startswith("www."): domain = domain[4:]
        return domain

    @staticmethod
    def _mean(values):
        return float(sum(values)/len(values)) if values else 0.0

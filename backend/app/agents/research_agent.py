"""AI-Powered SEO Research Agent — DataForSEO + Enriched Competitors."""

from __future__ import annotations
import logging
import math
import re
import httpx
from collections import Counter
from typing import Any
from urllib.parse import urlparse

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


def _extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.hostname or ""
    if domain.startswith("www."): domain = domain[4:]
    return domain


def _scrape_page(url, timeout=10):
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 OmniRank/2.0"})
            if resp.status_code == 200:
                return resp.text[:50000]
    except Exception as exc:
        logger.debug("Scrape failed for %s: %s", url, exc)
    return ""


def _extract_from_html(html):
    title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else ""
    h1_m = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    h1 = re.sub(r'<[^>]+>', '', h1_m[0]).strip() if h1_m else None
    h2_m = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)
    h2s = [re.sub(r'<[^>]+>', '', h).strip() for h in h2_m[:15]]
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    words = [w for w in re.findall(r'[A-Za-z][A-Za-z\-\']+', text.lower()) if w not in STOPWORDS and len(w) > 2]
    entities = [e for e, _ in Counter(re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b', text)).most_common(25)]
    questions = [q.strip() for q in re.findall(r'([^.!?]{20,180}\?)', text)][:12]
    return {"title": title, "h1": h1, "h2s": h2s, "word_count": len(words), "entities": entities, "questions": questions, "words": words}


def _kw_density(words, keyword):
    if not words: return 0.0
    terms = [t for t in re.findall(r'[A-Za-z0-9]+', keyword.lower()) if len(t) > 1]
    if not terms: return 0.0
    return round((sum(1 for w in words if w in terms) / len(words)) * 100, 3)


class AlgorithmicReverseEngineerAgent:
    def __init__(self, serper_client=None, firecrawl_client=None, claude_client=None):
        self.dfs = DataForSEOClient()
        self.claude = claude_client
        self.usage = AIUsageAccumulator()
        self.serper = serper_client
        self.firecrawl = firecrawl_client

    def run(self, request):
        keyword = request.primary_keyword
        client_url = str(request.client_url)
        client_domain = _extract_domain(client_url)
        if self.dfs.enabled:
            return self._run_dfs(request, keyword, client_url, client_domain)
        elif self.serper and self.firecrawl:
            return self._run_legacy(request)
        else:
            raise ValueError("No data provider. Add DATAFORSEO or SERPER credentials.")

    def _run_dfs(self, request, keyword, client_url, client_domain):
        serp = self.dfs.serp_competitors(keyword, location_code=2356, language_code="en")
        if not serp:
            raise ValueError(f"No SERP results for '{keyword}'")

        competitor_profiles = []
        for item in serp[:5]:
            url = item.get("url", "")
            domain = item.get("domain", "")
            if domain == client_domain: continue
            html = _scrape_page(url)
            ex = _extract_from_html(html) if html else {}
            try:
                bl = self.dfs.backlink_summary(domain)
                ref_doms = bl.referring_domains
            except: ref_doms = 0
            competitor_profiles.append(CompetitorPageProfile(
                url=url, title=ex.get("title", item.get("title", "")),
                h1=ex.get("h1") or item.get("title"), h2=ex.get("h2s", []),
                top_entities=ex.get("entities", []), top_questions=ex.get("questions", []),
                word_count=ex.get("word_count", 0),
                keyword_density=_kw_density(ex.get("words", []), keyword),
            ))
        if not competitor_profiles:
            raise ValueError("No competitors found")

        client_html = _scrape_page(client_url)
        client_ex = _extract_from_html(client_html) if client_html else {}
        try: client_bl = self.dfs.backlink_summary(client_domain)
        except: client_bl = None

        client_profile = CompetitorPageProfile(
            url=client_url, title=client_ex.get("title", client_domain),
            h1=client_ex.get("h1", client_domain), h2=client_ex.get("h2s", []),
            top_entities=client_ex.get("entities", []), top_questions=client_ex.get("questions", []),
            word_count=client_ex.get("word_count", 0),
            keyword_density=_kw_density(client_ex.get("words", []), keyword),
        )

        try: features = self.dfs.serp_features(keyword, location_code=2356)
        except: features = []

        ce = Counter(); cq = set(); ch = set()
        for c in competitor_profiles:
            ce.update(c.top_entities); cq.update(c.top_questions); ch.update(c.h2)

        gap = GapAnalysis(
            missing_entities=[e for e, _ in ce.most_common(30) if e not in client_profile.top_entities][:12],
            missing_questions=[q for q in cq if q not in client_profile.top_questions][:12],
            heading_gaps=[h for h in ch if h not in client_profile.h2][:12],
            density_gap=round(sum(c.keyword_density for c in competitor_profiles) / max(len(competitor_profiles), 1) - client_profile.keyword_density, 3),
        )
        for f in features[:8]:
            clean = f.replace("_", " ")
            if clean not in gap.missing_entities: gap.missing_entities.append(clean)

        if self.claude:
            score, recs = self._ai_analyze(client_profile, competitor_profiles, gap, keyword, client_bl, features)
        else:
            score = self._calc_score(client_profile, competitor_profiles, gap, client_bl, serp, client_domain)
            recs = self._basic_recs(client_bl, serp, features, client_domain, gap, client_profile, competitor_profiles)

        return ResearchResponse(
            seo_score=score, competitor_profiles=competitor_profiles,
            client_profile=client_profile, gap_analysis=gap, recommendations=recs,
            raw_metrics={
                "serp_features": features,
                "client_backlinks": {"total": client_bl.total_backlinks if client_bl else 0, "referring_domains": client_bl.referring_domains if client_bl else 0, "domain_rank": client_bl.domain_rank if client_bl else 0},
                "dataforseo_cost": self.dfs.get_cost_summary(),
                "ai_usage": {"total_input_tokens": self.usage.total_input_tokens, "total_output_tokens": self.usage.total_output_tokens, "total_cost_usd": self.usage.total_cost_usd},
            },
        )

    def _ai_analyze(self, client, competitors, gap, keyword, client_bl, features):
        system = """You are an expert SEO analyst. Analyze client vs SERP competitors using real data.
Score (total 100): Content (0-25), Backlinks (0-25), Technical (0-20), Local/SERP (0-15), Competitive (0-15).
Be HONEST. Small local site vs Zomato/JustDial = score 10-30.
Respond ONLY with valid JSON:
{"score":<number>,"recommendations":[{"priority":"critical|high|medium","action":"<specific>","impact":"<result>"}]}"""
        comp_text = "\n".join([f"#{i+1} {c.url}: {c.word_count} words, {len(c.top_entities)} entities, density {c.keyword_density}%" for i, c in enumerate(competitors[:5])])
        bl_text = f"Backlinks: {client_bl.total_backlinks}, Referring domains: {client_bl.referring_domains}, Domain rank: {client_bl.domain_rank}" if client_bl else "None"
        user_msg = f"""Keyword: "{keyword}"
Client: {client.url} — {client.word_count} words, {len(client.top_entities)} entities, density {client.keyword_density}%
Client backlinks: {bl_text}
SERP features: {', '.join(features) if features else 'none'}
Competitors:
{comp_text}
Gaps: {', '.join(gap.missing_entities[:10])}
Heading gaps: {', '.join(gap.heading_gaps[:5])}"""
        parsed, resp = self.claude.complete_json(messages=[{"role": "user", "content": user_msg}], system=system, max_tokens=2048, temperature=0.2)
        self.usage.record(resp)
        score = float(parsed.get("score", 50))
        recs = []
        for r in parsed.get("recommendations", []):
            if isinstance(r, dict): recs.append(f"[{r.get('priority','medium').upper()}] {r.get('action','')} -> {r.get('impact','')}")
            elif isinstance(r, str): recs.append(r)
        return score, recs or ["Review analysis manually."]

    def _calc_score(self, client, comps, gap, client_bl, serp, client_domain):
        score = 10.0
        avg_wc = sum(c.word_count for c in comps) / max(len(comps), 1)
        if avg_wc > 0: score += min(20, (client.word_count / avg_wc) * 20)
        if client_bl:
            if client_bl.referring_domains > 100: score += 20
            elif client_bl.referring_domains > 30: score += 12
            elif client_bl.referring_domains > 10: score += 6
        score -= len(gap.missing_entities) * 1.5
        for item in serp:
            if client_domain in item.get("domain", ""):
                pos = item.get("position", 100)
                if pos <= 3: score += 20
                elif pos <= 10: score += 10
                break
        return max(5, min(100, round(score, 2)))

    def _basic_recs(self, client_bl, serp, features, client_domain, gap, client, comps):
        recs = []
        avg_wc = sum(c.word_count for c in comps) / max(len(comps), 1)
        if client.word_count < avg_wc * 0.5:
            recs.append(f"[CRITICAL] Content too thin ({client.word_count} words vs avg {int(avg_wc)}) -> 2-3x more traffic")
        if not client_bl or client_bl.referring_domains < 20:
            recs.append("[CRITICAL] Build backlinks — very low referring domains -> Improved authority")
        if "local_pack" in features:
            recs.append("[HIGH] Optimize Google Business Profile -> Local pack visibility")
        if "featured_snippet" in features:
            recs.append("[HIGH] Target featured snippet with FAQ schema -> Position zero")
        if gap.missing_entities:
            recs.append(f"[MEDIUM] Add entities: {', '.join(gap.missing_entities[:5])} -> Better coverage")
        if not any(client_domain in item.get("domain","") for item in serp):
            recs.append("[CRITICAL] Not in top 20 — needs full SEO strategy -> SERP visibility")
        return recs or ["Content is competitive"]

    def _run_legacy(self, request):
        serp = self.serper.search_top_results(keyword=request.primary_keyword, locale=request.locale, region=request.target_region, limit=5)
        if not serp: raise ValueError("No SERP results")
        profiles = []
        for item in serp[:5]:
            link = item.get("link","").strip()
            if not link: continue
            try:
                md = self.firecrawl.scrape_markdown(link)
                lines = [l.strip() for l in md.splitlines() if l.strip()]
                h1c = [l.replace("# ","").strip() for l in lines if l.startswith("# ")]
                h2 = [l.replace("## ","").strip() for l in lines if l.startswith("## ")]
                text = " ".join(lines)
                words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower()) if w not in STOPWORDS and len(w)>2]
                ents = [e for e,_ in Counter(re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", md)).most_common()]
                profiles.append(CompetitorPageProfile(url=link, title=h1c[0] if h1c else "Untitled", h1=h1c[0] if h1c else None, h2=h2[:15], top_entities=ents[:25], top_questions=[l for l in lines if l.endswith("?")][:12], word_count=len(words), keyword_density=_kw_density(words, request.primary_keyword)))
            except: pass
        if not profiles: raise ValueError("No competitors scraped")
        client_md = self.firecrawl.scrape_markdown(str(request.client_url))
        lines = [l.strip() for l in client_md.splitlines() if l.strip()]
        h1c = [l.replace("# ","").strip() for l in lines if l.startswith("# ")]
        text = " ".join(lines)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower()) if w not in STOPWORDS and len(w)>2]
        client_p = CompetitorPageProfile(url=str(request.client_url), title=h1c[0] if h1c else "Untitled", h1=h1c[0] if h1c else None, h2=[l.replace("## ","").strip() for l in lines if l.startswith("## ")][:15], top_entities=[e for e,_ in Counter(re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", client_md)).most_common()][:25], top_questions=[l for l in lines if l.endswith("?")][:12], word_count=len(words), keyword_density=_kw_density(words, request.primary_keyword))
        ce=Counter(); cq=set(); ch=set()
        for c in profiles: ce.update(c.top_entities); cq.update(c.top_questions); ch.update(c.h2)
        gap = GapAnalysis(missing_entities=[e for e,_ in ce.most_common(30) if e not in client_p.top_entities][:12], missing_questions=[q for q in cq if q not in client_p.top_questions][:12], heading_gaps=[h for h in ch if h not in client_p.h2][:12], density_gap=round(sum(c.keyword_density for c in profiles)/max(len(profiles),1)-client_p.keyword_density,3))
        aw=sum(c.word_count for c in profiles)/max(len(profiles),1)
        score = round(min(100, min(35,(client_p.word_count/max(aw,1))*35)+max(0,30-len(gap.missing_entities)*2.2)),2)
        recs = []
        if client_p.word_count<aw: recs.append(f"Expand content by ~{int(aw-client_p.word_count)} words")
        if gap.missing_entities: recs.append("Add entities: "+", ".join(gap.missing_entities[:6]))
        return ResearchResponse(seo_score=score, competitor_profiles=profiles, client_profile=client_p, gap_analysis=gap, recommendations=recs or ["Aligned"], raw_metrics={})

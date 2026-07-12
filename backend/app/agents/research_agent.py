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

# Common UI-chrome / navigation phrases scraped from pages that must never be
# surfaced as SEO "entities" (lowercased, exact-match after collapsing spaces).
UI_CHROME = frozenset({
    "view profile","read more","read less","learn more","see more","see all",
    "view more","view all","view details","show more","show less","load more",
    "sign in","sign up","log in","log out","get started","start free","try free",
    "contact us","about us","follow us","privacy policy","terms of service",
    "terms conditions","cookie policy","add to cart","buy now","shop now",
    "book now","get quote","quick view","free shipping","back to top",
    "skip to content","watch video","subscribe now","download now","menu close",
    "search results","get in touch","find out","click here","new arrivals",
    "my account","order now","join now","see details","explore more",
    "shop women","shop men","shop all","shop now","shop kids","quick add",
    "add to bag","view cart","best sellers","new in","gift cards",
})


def _clean_entities(raw: list[str], limit: int = 25) -> list[str]:
    """Drop scraped UI/navigation labels so they aren't surfaced as entities."""
    out: list[str] = []
    for e in raw:
        # entities spanning line breaks are scraping artifacts (two elements
        # captured together), not real named entities — drop them.
        if "\n" in e or "\r" in e or "\t" in e:
            continue
        key = re.sub(r"\s+", " ", e).strip().lower()
        if key in UI_CHROME or len(key) < 4 or key.startswith("shop "):
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def _extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.hostname or ""
    if domain.startswith("www."): domain = domain[4:]
    return domain


def _scrape_page(url, timeout=10):
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 OmniRank/2.0"})
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
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
    entities = _clean_entities([e for e, _ in Counter(re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b', text)).most_common(40)])
    questions = [q.strip() for q in re.findall(r'([^.!?]{20,180}\?)', text) if q.isprintable()][:12]
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
        self.claude = claude_client
        self.usage = AIUsageAccumulator()

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
        # ── Smart Location Targeting ──────────────────────────────
        # Hierarchy: City → State → Country → International
        # Based on business type detection from URL + keyword
        
        INDIA_CITIES = {
            "hyderabad": 1007768, "mumbai": 1007785, "delhi": 1007751, "new delhi": 1007751,
            "bangalore": 1007739, "bengaluru": 1007739, "chennai": 1007745, "kolkata": 1007776,
            "pune": 1007792, "ahmedabad": 1007737, "jaipur": 1007769, "lucknow": 1007782,
            "kochi": 1007775, "cochin": 1007775, "chandigarh": 1007744, "indore": 1007767,
            "bhopal": 1007741, "visakhapatnam": 1007800, "vizag": 1007800, "nagpur": 1007786,
            "coimbatore": 1007748, "goa": 1007756, "surat": 1007797, "vadodara": 1007799,
            "patna": 1007790, "ranchi": 1007793, "guwahati": 1007759, "bhubaneswar": 1007742,
            "thiruvananthapuram": 1007798, "trivandrum": 1007798, "mysore": 1007784, "mysuru": 1007784,
            "mangalore": 1007783, "mangaluru": 1007783, "madurai": 1007781, "varanasi": 1007800,
            "agra": 1007736, "noida": 1007751, "gurgaon": 1007758, "gurugram": 1007758,
            "faridabad": 1007754, "ghaziabad": 1007755, "dehradun": 1007750, "shimla": 1007796,
            "amritsar": 1007738, "ludhiana": 1007780, "jodhpur": 1007772, "udaipur": 1007799,
            "raipur": 1007793, "vijayawada": 1007800, "guntur": 1007757, "warangal": 1007800,
            "nellore": 1007787, "kakinada": 1007773, "tirupati": 1007798, "rajahmundry": 1007793,
            "secunderabad": 1007768, "kukatpally": 1007768, "gachibowli": 1007768, "hitech city": 1007768,
            "jubilee hills": 1007768, "banjara hills": 1007768, "ameerpet": 1007768, "kphb": 1007768,
        }
        
        # ── Business type categories ──
        # CITY-LEVEL: Serve customers who physically visit or are nearby
        LOCAL_SIGNALS = [
            # Food & Dining
            "restaurant", "hotel", "cafe", "dhaba", "mess", "bhojanam", "biryani",
            "bakery", "sweets", "mithai", "catering", "tiffin", "food court",
            "bar", "pub", "lounge", "ice cream", "juice", "chai", "coffee",
            # Health & Wellness
            "hospital", "clinic", "doctor", "dentist", "pharmacy", "medical",
            "ayurveda", "homeopathy", "physiotherapy", "lab", "diagnostic",
            "gym", "fitness", "yoga", "spa", "salon", "parlour", "parlor",
            "beauty", "barber", "tattoo", "massage", "wellness",
            # Retail & Shopping
            "shop", "store", "showroom", "boutique", "jewellery", "jewelry",
            "furniture", "electronics", "mobile", "optical", "florist",
            "supermarket", "kirana", "grocery", "mart", "bazaar", "market",
            # Services
            "plumber", "electrician", "carpenter", "painter", "mechanic",
            "tailor", "laundry", "dry clean", "pest control", "cleaning",
            "packers", "movers", "courier", "repair", "service center",
            "ac repair", "car wash", "garage", "tyre", "tire",
            # Education
            "school", "college", "university", "coaching", "tuition", "tutorial",
            "institute", "academy", "preschool", "playschool", "daycare", "creche",
            "library", "training", "certification",
            # Religious & Cultural
            "temple", "church", "mosque", "gurudwara", "ashram", "mandir",
            "havan", "puja", "pooja", "yagna", "mandal", "samaj", "seva",
            "math", "mutt", "dargah", "synagogue",
            # Real Estate & Property
            "pg", "paying guest", "hostel", "lodge", "guest house", "oyo",
            "apartment", "flat", "villa", "plot", "real estate", "property",
            "builder", "construction", "interior", "architect",
            # Legal & Financial (local offices)
            "advocate", "lawyer", "ca firm", "chartered accountant", "notary",
            "insurance agent", "loan", "chit fund",
            # Auto & Transport
            "driving school", "auto", "taxi", "cab", "car rental", "bike rental",
            "travel agent", "tour operator",
            # Events & Entertainment
            "wedding", "event", "banquet", "hall", "auditorium", "theatre", "theater",
            "cinema", "photographer", "videographer", "dj", "decorator", "florist",
            # Pet & Animal
            "vet", "veterinary", "pet shop", "pet care", "grooming",
        ]
        
        # STATE-LEVEL: Regional businesses, state government, regional brands
        STATE_SIGNALS = [
            "state government", "regional", "district", "mandal", "taluk",
            "wholesale", "distributor", "dealer", "franchise",
            "tourism", "heritage", "pilgrimage", "circuit",
            "state board", "regional office", "zonal",
        ]
        
        # NATIONAL-LEVEL: Pan-India brands, e-commerce, national services
        NATIONAL_SIGNALS = [
            "india", "pan india", "nationwide", "all india",
            "ecommerce", "e-commerce", "online store", "startup",
            "saas", "software", "app", "platform", "fintech",
            "insurance company", "bank", "nbfc", "mutual fund",
            "airline", "railway", "logistics", "shipping",
            "news", "media", "magazine", "publication",
            "brand", "manufacturer", "exporter", "importer",
        ]
        
        # INTERNATIONAL: Global companies, exports, multinational
        INTERNATIONAL_SIGNALS = [
            "global", "international", "worldwide", "export",
            "multinational", "offshore", "overseas", "foreign",
            ".com", ".io", ".ai", ".co",  # Generic TLDs suggest broader scope
        ]
        
        # ── Detection logic ──
        url_lower = client_url.lower() + " " + client_domain.lower()
        kw_lower = keyword.lower()
        search_context = url_lower + " " + kw_lower
        
        # Step 1: Try to detect city from URL/domain
        location_code = 2356  # India default
        detected_city = None
        detected_level = "country"  # city, state, country, international
        
        for city, code in INDIA_CITIES.items():
            if city in url_lower or city in kw_lower:
                location_code = code
                detected_city = city
                detected_level = "city"
                break
        
        # Step 2: If no city found, classify business type
        if not detected_city:
            is_local = any(s in search_context for s in LOCAL_SIGNALS)
            is_national = any(s in search_context for s in NATIONAL_SIGNALS)
            is_international = any(s in search_context for s in INTERNATIONAL_SIGNALS)
            
            if is_local and not is_national:
                # Local business but no city detected — use India-level
                # (user should add city to project settings for best results)
                detected_level = "city"
                location_code = 2356  # Will search India-wide but flag as local
            elif is_national:
                detected_level = "country"
                location_code = 2356  # India
            elif is_international:
                detected_level = "international"
                location_code = 2840  # US as global default
            else:
                detected_level = "country"
                location_code = 2356  # India default
        
        logger.info("Search targeting: level=%s, city=%s, location_code=%d", 
                     detected_level, detected_city or "none", location_code)
        
        serp = self.dfs.serp_competitors(keyword, location_code=location_code, language_code="en")
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
        return max(5, min(100, round(score)))

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
        score = round(min(100, min(35,(client_p.word_count/max(aw,1))*35)+max(0,30-len(gap.missing_entities)*2.2)))
        recs = []
        if client_p.word_count<aw: recs.append(f"Expand content by ~{int(round((aw-client_p.word_count)/50.0)*50)} words")
        if gap.missing_entities: recs.append("Add entities: "+", ".join(gap.missing_entities[:6]))
        return ResearchResponse(seo_score=score, competitor_profiles=profiles, client_profile=client_p, gap_analysis=gap, recommendations=recs or ["Aligned"], raw_metrics={"ai_usage": {"total_input_tokens": self.usage.total_input_tokens, "total_output_tokens": self.usage.total_output_tokens, "total_cost_usd": self.usage.total_cost_usd}})

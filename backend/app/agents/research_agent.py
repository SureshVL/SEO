"""AI-Powered SEO Research Agent — DataForSEO + Enriched Competitors."""

from __future__ import annotations
import logging
import math
import re
import statistics
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
    # cookie-banner / legal / footer boilerplate
    "privacy statement","cookie consent","cookie consent manager","cookies details",
    "cookie settings","cookie preferences","accept cookies","manage cookies",
    "accept all","reject all","strictly necessary","functional cookies",
    "performance cookies","targeting cookies","advertising cookies",
    "terms of use","all rights reserved","legal notice","privacy notice",
    "privacy choices","your privacy","do not sell","opt out",
    # CTA / marketing chrome
    "get started free","start free trial","free trial","request demo","request a demo",
    "watch demo","book a demo","contact sales","talk to sales","start now",
    "try it free","learn how","find out more","get the app","download app",
    "sign into","create account","join free","subscribe today","get pricing",
    # generic page furniture
    "email address","phone number","first name","last name","zip code",
    "united states","new york","san francisco","frequently asked","help center",
    "customer stories","case studies","press releases","investor relations",
    "media kit","site map","table of contents",
})

# Suffixes that mark an entity as some company's product/person page furniture
# rather than a topical concept ("Sales Cloud", "Marketing Hub", "Acme Suite").
_BRANDY_SUFFIXES = ("cloud", "hub", "suite", "labs", "inc", "llc", "ltd", "corp")


def _looks_like_person(entity: str) -> bool:
    """Heuristic: exactly two capitalised words, no digits/&, both alpha —
    'Marc Benioff' yes; 'Fleet Management' also matches shape, so only used
    together with the cross-competitor consensus filter (person names almost
    never repeat across unrelated competitor pages, concepts do)."""
    parts = entity.split()
    return (
        len(parts) == 2
        and all(p[:1].isupper() and p[1:].islower() and p.isalpha() for p in parts)
    )


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
        if any(key.endswith(" " + s) for s in _BRANDY_SUFFIXES):
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def _consensus_gap_entities(
    ce: Counter, client_entities: list[str], n_competitors: int, limit: int = 12
) -> list[str]:
    """Missing entities the client should actually cover.

    An entity mentioned by a single competitor is usually that company's own
    product, person, or page furniture ('Sales Cloud', 'Marc Benioff') — only
    concepts repeated across competitors are treated as topical gaps. Falls
    back to single-source entities (still cleaned) when consensus yields
    nothing, e.g. with only one scrapeable competitor.
    """
    client_set = set(client_entities)
    min_count = 2 if n_competitors >= 2 else 1
    # Consensus itself filters people/brands (they rarely repeat across
    # unrelated competitors), so repeated entities pass without the person
    # heuristic — otherwise it would kill concepts like "Machine Learning".
    # With a single competitor there is no consensus signal, so the person
    # heuristic applies there instead.
    picks = [
        e for e, c in ce.most_common(60)
        if c >= min_count and e not in client_set
        and (min_count >= 2 or not _looks_like_person(e))
    ]
    if not picks:
        # Single-source fallback has no consensus signal, so apply the
        # person-shape heuristic there to keep CEOs out of the gap list.
        picks = [
            e for e, _ in ce.most_common(60)
            if e not in client_set and not _looks_like_person(e)
        ]
    return _clean_entities(picks, limit=limit)


# A page with fewer visible words than this is effectively invisible to
# crawlers — typical of client-side-rendered apps with an empty HTML shell.
_THIN_PAGE_WORDS = 100


def _word_stats(comps) -> tuple[int, int, int]:
    """(median, typical_low, typical_high) of competitor word counts.

    A single encyclopedia-length page (Wikipedia at 35k words) makes the mean
    useless as a content target; the median and interquartile range describe
    what actually ranks.
    """
    counts = sorted(c.word_count for c in comps if c.word_count > 0)
    if not counts:
        return 0, 0, 0
    med = int(statistics.median(counts))
    if len(counts) >= 4:
        lo, hi = counts[len(counts) // 4], counts[(3 * len(counts)) // 4]
    else:
        lo, hi = counts[0], counts[-1]
    return med, lo, hi


# Reference/education sites whose presence marks a SERP as informational.
_INFORMATIONAL_AUTHORITIES = {
    "wikipedia.org", "britannica.com", "investopedia.com", "geeksforgeeks.org",
    "w3schools.com", "tutorialspoint.com", "javatpoint.com", "wikihow.com",
    "quora.com", "reddit.com", "medium.com", "stackoverflow.com",
    "stackexchange.com", "youtube.com", "coursera.org", "udemy.com", "edx.org",
    "techtarget.com", "sciencedirect.com", "springer.com", "nature.com",
    "forbes.com", "hbr.org", "mckinsey.com", "gartner.com", "ibm.com",
}

# Mega-brands whose domain authority a small site cannot realistically outrank
# on a head keyword.
_MEGA_BRANDS = {
    "google.com", "amazon.com", "microsoft.com", "oracle.com", "sap.com",
    "apple.com", "salesforce.com", "adobe.com", "nvidia.com", "intel.com",
    "tableau.com", "cisco.com", "dell.com", "hp.com", "meta.com",
}


def _domain_in(domain: str, group: frozenset | set) -> bool:
    return any(domain == a or domain.endswith("." + a) for a in group)


# Title/H1 shapes that mark a ranking page as informational content (listicle,
# encyclopedia, tutorial) rather than a commercial page a business competes with.
_INFO_TITLE_RE = re.compile(
    r"\b(best|top\s?\d+|what\s+is|what\s+are|how\s+to|guide|tutorial|examples?\s+of|"
    r"applications?\s+of|types?\s+of|introduction\s+to|explained|vs\.?|comparison)\b",
    re.IGNORECASE,
)


def _serp_strategy_rec(keyword: str, comps: list, client_domain: str, region: str = "") -> list[str]:
    """Warn when the SERP is dominated by pages a commercial site can't outrank
    head-on — high-authority domains and/or informational listicle content —
    and point at winnable long-tail variants instead. Deterministic — no LLM,
    no extra API calls. `comps` items need .url, and optionally .title/.h1."""
    comps = [c for c in comps[:5] if getattr(c, "url", "")]
    domains = [_extract_domain(c.url) for c in comps]
    if not domains or (client_domain and any(client_domain in d or d in client_domain for d in domains)):
        return []  # client already ranks here — the keyword is clearly winnable
    evidence: dict[str, str] = {}  # domain -> why it counts
    for c, d in zip(comps, domains):
        if _domain_in(d, _INFORMATIONAL_AUTHORITIES) or d.endswith((".edu", ".gov")):
            evidence[d] = "authority"
        elif _domain_in(d, _MEGA_BRANDS):
            evidence[d] = "mega-brand"
        else:
            page_head = f"{getattr(c, 'title', '') or ''} {getattr(c, 'h1', '') or ''}"
            if _INFO_TITLE_RE.search(page_head):
                evidence[d] = "informational article"
    if len(evidence) < 3:
        return []
    named = ", ".join(list(evidence)[:3])
    where = f" in {region}" if region else ""
    return [
        f'[STRATEGY] {len(evidence)} of the top {len(domains)} results for "{keyword}" are '
        f"high-authority sites or informational articles ({named}) — searchers here want "
        "reference content, not a vendor, and outranking these pages head-on is unrealistic "
        "for a commercial site. Target buyer-intent long-tail variants instead (e.g. "
        f'"{keyword} for [your industry]", "{keyword} services{where}", '
        f'"best {keyword} tools for [your niche]") and run this analysis on those keywords.'
    ]


def _site_health_recs(client_p, keyword: str) -> list[str]:
    """Prepended findings that outrank everything else when they apply."""
    recs: list[str] = []
    title = (client_p.title or "").strip().lower()
    if client_p.word_count < _THIN_PAGE_WORDS:
        recs.append(
            f"[CRITICAL] Your page exposes only ~{client_p.word_count} words of crawlable text"
            " — search engines and AI assistants see an almost empty page. This usually means"
            " the site renders via JavaScript (client-side React/Vue) with no server-side"
            " rendering. Fix rendering (SSR or prerendering) and add real titles/meta first;"
            " no other optimization matters until crawlers can read the site."
        )
    if title in {"react app", "vue app", "vite app", "untitled", "home", "index"}:
        recs.append(
            f'[CRITICAL] Your page title is "{client_p.title}" — a framework default.'
            " The title tag is the single strongest on-page signal and your headline in"
            " Google. Set a real title (e.g. brand + primary service)."
        )
    if client_p.word_count >= 200 and client_p.keyword_density == 0:
        recs.append(
            f'[WARNING] The keyword "{keyword}" does not appear anywhere on your page.'
            " Either the page needs content for this topic, or this keyword does not match"
            " your business — consider a keyword that reflects what the site actually offers."
        )
    return recs


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
            missing_entities=_consensus_gap_entities(ce, client_profile.top_entities, len(competitor_profiles)),
            missing_questions=[q for q in cq if q not in client_profile.top_questions][:12],
            heading_gaps=[h for h in ch if h not in client_profile.h2][:12],
            density_gap=round(sum(c.keyword_density for c in competitor_profiles) / max(len(competitor_profiles), 1) - client_profile.keyword_density, 3),
        )

        if self.claude:
            score, recs = self._ai_analyze(client_profile, competitor_profiles, gap, keyword, client_bl, features)
        else:
            score = self._calc_score(client_profile, competitor_profiles, gap, client_bl, serp, client_domain)
            recs = self._basic_recs(client_bl, serp, features, client_domain, gap, client_profile, competitor_profiles)

        strategy = _serp_strategy_rec(
            keyword, competitor_profiles, client_domain,
            getattr(request, "target_region", "") or "",
        )
        recs = _site_health_recs(client_profile, keyword) + strategy + recs
        summary = self._narrative(keyword, client_profile, competitor_profiles, score, recs)

        return ResearchResponse(
            seo_score=score, competitor_profiles=competitor_profiles,
            client_profile=client_profile, gap_analysis=gap, recommendations=recs,
            analyst_summary=summary,
            raw_metrics={
                "serp_features": features,
                "client_backlinks": {"total": client_bl.total_backlinks if client_bl else 0, "referring_domains": client_bl.referring_domains if client_bl else 0, "domain_rank": client_bl.domain_rank if client_bl else 0},
                "dataforseo_cost": self.dfs.get_cost_summary(),
                "ai_usage": {"total_input_tokens": self.usage.total_input_tokens, "total_output_tokens": self.usage.total_output_tokens, "total_cost_usd": self.usage.total_cost_usd},
            },
        )

    def _narrative(self, keyword, client_p, comps, score, recs) -> str:
        """Plain-language 'what this means and what to do first' for the owner."""
        med_wc, lo_wc, hi_wc = _word_stats(comps)
        comp_domains = ", ".join(_extract_domain(c.url) for c in comps[:5])
        typical = f"{lo_wc:,}–{hi_wc:,}" if lo_wc != hi_wc else f"about {med_wc:,}"
        if self.claude:
            try:
                prompt = f"""You are an SEO analyst explaining results to a business owner in 3-5 plain sentences (no jargon, no fluff).
DATA:
- Their page: {client_p.word_count} words visible to crawlers, page title "{client_p.title}", keyword "{keyword}" appears at {client_p.keyword_density}% density
- SEO score: {score}/100
- Pages currently ranking for "{keyword}": {comp_domains} (typically {typical} words of content, median {med_wc})
- Top findings already identified: {recs[:4]}
Explain: what the score means, the single most important problem, and the first thing to fix. Be direct and specific to THIS data. If a [STRATEGY] finding exists, reflect it honestly (don't tell them to out-write Wikipedia).
Return ONLY JSON: {{"summary": "<3-5 sentences>"}}"""
                parsed, resp = self.claude.complete_json(
                    messages=[{"role": "user", "content": prompt}], max_tokens=400, temperature=0.3
                )
                self.usage.record(resp)
                s = str(parsed.get("summary", "")).strip()
                if len(s) > 40:
                    return s
            except Exception as exc:
                logger.debug("Narrative generation failed: %s", exc)
        # Deterministic fallback so the summary never comes back empty.
        return (
            f'Your page scores {score}/100 for "{keyword}". Search engines can read about '
            f"{client_p.word_count} words on your page, while the pages currently ranking "
            f"({comp_domains}) typically have {typical} words. Work through the recommendations "
            "below in order — the top one is the highest-impact fix — then re-run this analysis "
            "to measure progress."
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
        med_wc, _, _ = _word_stats(comps)
        if med_wc > 0: score += min(20, (client.word_count / med_wc) * 20)
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
        med_wc, _, _ = _word_stats(comps)
        if client.word_count < med_wc * 0.5:
            recs.append(f"[CRITICAL] Content too thin ({client.word_count} words vs typical {med_wc}) -> 2-3x more traffic")
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
                ents = _clean_entities([e for e,_ in Counter(re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", md)).most_common(40)])
                profiles.append(CompetitorPageProfile(url=link, title=h1c[0] if h1c else "Untitled", h1=h1c[0] if h1c else None, h2=h2[:15], top_entities=ents[:25], top_questions=[l for l in lines if l.endswith("?")][:12], word_count=len(words), keyword_density=_kw_density(words, request.primary_keyword)))
            except: pass
        if not profiles: raise ValueError("No competitors scraped")
        client_md = self.firecrawl.scrape_markdown(str(request.client_url))
        lines = [l.strip() for l in client_md.splitlines() if l.strip()]
        h1c = [l.replace("# ","").strip() for l in lines if l.startswith("# ")]
        text = " ".join(lines)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower()) if w not in STOPWORDS and len(w)>2]
        client_p = CompetitorPageProfile(url=str(request.client_url), title=h1c[0] if h1c else "Untitled", h1=h1c[0] if h1c else None, h2=[l.replace("## ","").strip() for l in lines if l.startswith("## ")][:15], top_entities=_clean_entities([e for e,_ in Counter(re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", client_md)).most_common(40)]), top_questions=[l for l in lines if l.endswith("?")][:12], word_count=len(words), keyword_density=_kw_density(words, request.primary_keyword))
        ce=Counter(); cq=set(); ch=set()
        for c in profiles: ce.update(c.top_entities); cq.update(c.top_questions); ch.update(c.h2)
        gap = GapAnalysis(missing_entities=_consensus_gap_entities(ce, client_p.top_entities, len(profiles)), missing_questions=[q for q in cq if q not in client_p.top_questions][:12], heading_gaps=[h for h in ch if h not in client_p.h2][:12], density_gap=round(sum(c.keyword_density for c in profiles)/max(len(profiles),1)-client_p.keyword_density,3))
        med_wc, lo_wc, hi_wc = _word_stats(profiles)
        score = round(min(100, min(35,(client_p.word_count/max(med_wc,1))*35)+max(0,30-len(gap.missing_entities)*2.2)))
        recs = []
        if client_p.word_count < med_wc:
            comp_names = ", ".join(_extract_domain(c.url) for c in profiles[:3])
            typical = f"{lo_wc:,}–{hi_wc:,}" if lo_wc != hi_wc else f"~{med_wc:,}"
            recs.append(
                f"[HIGH] Top-ranking pages ({comp_names}) typically carry {typical} words of "
                f"content; crawlers can read only {client_p.word_count} on yours. Build the "
                "missing depth with sections covering the topic gaps below."
            )
        if gap.missing_entities:
            recs.append(
                "[MEDIUM] Topics competitors cover that your page doesn't: "
                + ", ".join(gap.missing_entities[:6])
                + ". Add a section (or FAQ answer) for each that fits your business."
            )
        strategy = _serp_strategy_rec(
            request.primary_keyword, profiles,
            _extract_domain(str(request.client_url)), request.target_region or "",
        )
        recs = _site_health_recs(client_p, request.primary_keyword) + strategy + recs
        summary = self._narrative(request.primary_keyword, client_p, profiles, score, recs)
        return ResearchResponse(seo_score=score, competitor_profiles=profiles, client_profile=client_p, gap_analysis=gap, recommendations=recs or ["Content depth and topical coverage are competitive for this keyword."], analyst_summary=summary, raw_metrics={"ai_usage": {"total_input_tokens": self.usage.total_input_tokens, "total_output_tokens": self.usage.total_output_tokens, "total_cost_usd": self.usage.total_cost_usd}})

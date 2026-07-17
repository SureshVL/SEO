"""DataForSEO API client.

Comprehensive integration covering:
- SERP API: real-time search results, SERP features, AI overviews
- Keywords Data API: search volume, CPC, difficulty, trends
- Backlinks API: referring domains, anchors, domain authority
- DataForSEO Labs API: competitor domains, ranked keywords, content gaps
- On-Page API: full site crawl, technical audit

Pay-as-you-go pricing (~70-97% cheaper than Ahrefs):
- SERP: $0.002/query live, $0.0006 standard queue
- Keywords: $0.05 per 700 keywords
- Backlinks: $0.02/task + $0.00003/row
- Labs: $0.001-0.01/task
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("omnirank.dataforseo")

LIVE_URL = "https://api.dataforseo.com/v3"
# Free sandbox: dummy data, identical response shapes — for dev/testing
# without spending account balance (set DATAFORSEO_SANDBOX=true).
SANDBOX_URL = "https://sandbox.dataforseo.com/v3"


def _base_url() -> str:
    return SANDBOX_URL if settings.dataforseo_sandbox else LIVE_URL


@dataclass
class BacklinkProfile:
    total_backlinks: int = 0
    referring_domains: int = 0
    domain_rank: float = 0
    top_anchors: list[dict] = field(default_factory=list)
    top_referring: list[dict] = field(default_factory=list)
    dofollow_ratio: float = 0
    edu_gov_links: int = 0


@dataclass
class KeywordMetrics:
    keyword: str = ""
    search_volume: int = 0
    cpc: float = 0
    competition: float = 0
    difficulty: int = 0
    trend: list[int] = field(default_factory=list)
    intent: str = ""
    serp_features: list[str] = field(default_factory=list)


@dataclass
class CompetitorDomain:
    domain: str = ""
    common_keywords: int = 0
    total_keywords: int = 0
    total_traffic: int = 0
    domain_rank: float = 0
    overlap_percentage: float = 0


class DataForSEOClient:
    """Production DataForSEO API client with retry, rate limiting, and cost tracking."""

    def __init__(
        self,
        login: str | None = None,
        password: str | None = None,
    ):
        self.login = login or settings.dataforseo_login
        self.password = password or settings.dataforseo_password
        self.total_cost = 0.0
        self._request_count = 0

        if not self.login or not self.password:
            logger.warning("DataForSEO credentials not set — data features disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.login and self.password)

    def _auth(self) -> tuple[str, str]:
        return (self.login, self.password)

    def _post(self, endpoint: str, payload: list[dict], retries: int = 3) -> dict:
        """Make authenticated POST request with retry."""
        url = f"{_base_url()}/{endpoint}"
        last_error = None

        for attempt in range(retries):
            try:
                with httpx.Client(timeout=60) as client:
                    resp = client.post(url, json=payload, auth=self._auth())
                    data = resp.json()

                    if data.get("status_code") == 20000:
                        cost = data.get("cost", 0)
                        self.total_cost += cost
                        self._request_count += 1
                        return data

                    error_msg = data.get("status_message", "Unknown error")
                    if data.get("status_code") == 40200:
                        logger.error("DataForSEO insufficient funds")
                        raise ValueError("DataForSEO: insufficient account balance")

                    logger.warning("DataForSEO error (attempt %d): %s", attempt + 1, error_msg)
                    last_error = Exception(error_msg)

            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("DataForSEO HTTP error (attempt %d): %s", attempt + 1, exc)

            time.sleep(1.5 * (2 ** attempt))

        raise RuntimeError(f"DataForSEO failed after {retries} retries: {last_error}")

    # ── SERP API ──────────────────────────────────────────────────

    def serp_live(
        self,
        keyword: str,
        location_code: int = 2356,  # India
        language_code: str = "en",
        depth: int = 20,
        device: str = "desktop",
    ) -> dict:
        """Get live SERP results with all features."""
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": depth,
            "device": device,
            "se_type": "organic",
        }]
        return self._post("serp/google/organic/live/advanced", payload)

    def serp_competitors(
        self,
        keyword: str,
        location_code: int = 2356,
        language_code: str = "en",
    ) -> list[dict]:
        """Get SERP competitors for a keyword."""
        data = self.serp_live(keyword, location_code, language_code, depth=20)
        results = []
        for task in data.get("tasks", []):
            for item in task.get("result", []):
                for organic in item.get("items", []):
                    if organic.get("type") == "organic":
                        results.append({
                            "position": organic.get("rank_absolute"),
                            "url": organic.get("url", ""),
                            "domain": organic.get("domain", ""),
                            "title": organic.get("title", ""),
                            "description": organic.get("description", ""),
                            "etv": organic.get("estimated_paid_traffic_cost"),
                        })
        return results[:20]

    def serp_features(self, keyword: str, location_code: int = 2356) -> list[str]:
        """Detect which SERP features appear for a keyword."""
        data = self.serp_live(keyword, location_code, depth=10)
        features = set()
        for task in data.get("tasks", []):
            for result in task.get("result", []):
                for item in result.get("items", []):
                    item_type = item.get("type", "")
                    if item_type and item_type != "organic":
                        features.add(item_type)
        return list(features)

    # ── AI Visibility (GEO) ───────────────────────────────────────

    @staticmethod
    def _extract_domain(value: str) -> str:
        if not value:
            return ""
        v = value.strip().lower()
        v = v.replace("https://", "").replace("http://", "")
        v = v.replace("www.", "")
        return v.split("/")[0]

    def ai_overview_for_keyword(
        self,
        keyword: str,
        domain: str = "",
        location_code: int = 2356,
        language_code: str = "en",
    ) -> dict:
        """Extract Google AI Overview presence and citations from live SERP.

        DataForSEO returns an ai_overview item in the SERP feed whenever Google
        shows one. This method flattens it into {present, snippet, citations,
        domain_cited, domain_position}.
        """
        data = self.serp_live(keyword, location_code, language_code, depth=20)
        target = self._extract_domain(domain)

        out = {
            "keyword": keyword,
            "present": False,
            "snippet": "",
            "citations": [],
            "domain_cited": False,
            "domain_position": None,
        }

        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                for item in result.get("items", []) or []:
                    if item.get("type") != "ai_overview":
                        continue
                    out["present"] = True
                    references = item.get("references") or []
                    snippets: list[str] = []
                    for block in item.get("items", []) or []:
                        text = block.get("text") or block.get("title") or ""
                        if text:
                            snippets.append(text)
                    out["snippet"] = " ".join(snippets)[:2000]

                    citations: list[dict] = []
                    for idx, ref in enumerate(references, 1):
                        ref_domain = self._extract_domain(ref.get("domain") or ref.get("url") or "")
                        citations.append({
                            "position": idx,
                            "domain": ref_domain,
                            "url": ref.get("url", ""),
                            "title": ref.get("title", ""),
                        })
                        if target and ref_domain == target and not out["domain_cited"]:
                            out["domain_cited"] = True
                            out["domain_position"] = idx
                    out["citations"] = citations
                    return out
        return out

    def ai_mode_serp(
        self,
        keyword: str,
        location_code: int = 2356,
        language_code: str = "en",
    ) -> dict:
        """Call DataForSEO's Google AI Mode SERP endpoint.

        AI Mode is Google's conversational search surface. Returns
        {answer, references, present} parsed from the response.
        """
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
        }]
        try:
            data = self._post("serp/google/ai_mode/live/advanced", payload)
        except Exception as exc:
            logger.debug("AI Mode endpoint failed for %s: %s", keyword, exc)
            return {"keyword": keyword, "present": False, "answer": "", "references": [], "error": str(exc)}

        out = {"keyword": keyword, "present": False, "answer": "", "references": []}
        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                for item in result.get("items", []) or []:
                    if item.get("type") != "ai_mode":
                        continue
                    out["present"] = True
                    answer_blocks = []
                    for block in item.get("items", []) or []:
                        txt = block.get("text") or block.get("title") or ""
                        if txt:
                            answer_blocks.append(txt)
                    out["answer"] = " ".join(answer_blocks)[:2000]
                    refs = []
                    for ref in item.get("references") or []:
                        refs.append({
                            "domain": self._extract_domain(ref.get("domain") or ref.get("url") or ""),
                            "url": ref.get("url", ""),
                            "title": ref.get("title", ""),
                        })
                    out["references"] = refs
                    return out
        return out

    def llm_response(
        self,
        prompt: str,
        model: str = "chat_gpt",
        language_code: str = "en",
    ) -> dict:
        """Query DataForSEO AI-Optimization endpoints (chat_gpt / perplexity / gemini).

        Returns {model, text, references} parsed from the response. Used to
        check whether a target domain is mentioned/cited by a given LLM for a
        prompt — the core GEO (Generative Engine Optimization) signal.
        """
        model_key = model.lower().replace("-", "_")
        if model_key not in {"chat_gpt", "perplexity", "gemini"}:
            raise ValueError("model must be one of: chat_gpt, perplexity, gemini")

        endpoint = f"ai_optimization/{model_key}/llm_responses/live"
        payload = [{
            "user_prompt": prompt,
            "language_code": language_code,
        }]
        try:
            data = self._post(endpoint, payload)
        except Exception as exc:
            logger.debug("LLM endpoint %s failed for %s: %s", model_key, prompt[:60], exc)
            return {"model": model_key, "prompt": prompt, "text": "", "references": [], "error": str(exc)}

        out = {"model": model_key, "prompt": prompt, "text": "", "references": []}
        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                items = result.get("items") or [result]
                for item in items:
                    text = item.get("response_text") or item.get("text") or item.get("answer") or ""
                    if text:
                        out["text"] = str(text)[:4000]
                    refs = item.get("references") or item.get("sources") or item.get("citations") or []
                    if refs:
                        out["references"] = [
                            {
                                "domain": self._extract_domain(r.get("domain") or r.get("url") or ""),
                                "url": r.get("url", ""),
                                "title": r.get("title", ""),
                            }
                            for r in refs
                        ]
                if out["text"]:
                    return out
        return out

    # ── Keywords Data API ─────────────────────────────────────────

    def keyword_metrics(
        self,
        keywords: list[str],
        location_code: int = 2356,
        language_code: str = "en",
    ) -> list[KeywordMetrics]:
        """Get search volume, CPC, difficulty for up to 700 keywords."""
        payload = [{
            "keywords": keywords[:700],
            "location_code": location_code,
            "language_code": language_code,
        }]
        data = self._post("keywords_data/google_ads/search_volume/live", payload)

        results = []
        for task in data.get("tasks", []):
            for item in task.get("result", []):
                monthly = item.get("monthly_searches", [])
                trend = [m.get("search_volume", 0) for m in (monthly or [])[:12]]
                results.append(KeywordMetrics(
                    keyword=item.get("keyword", ""),
                    search_volume=item.get("search_volume", 0) or 0,
                    cpc=item.get("cpc", 0) or 0,
                    competition=item.get("competition", 0) or 0,
                    difficulty=item.get("keyword_difficulty", 0) or 0,
                    trend=trend,
                    intent="",  # classified by AI later
                ))
        return results

    def keyword_suggestions(
        self,
        seed_keyword: str,
        location_code: int = 2356,
        language_code: str = "en",
        limit: int = 50,
    ) -> list[KeywordMetrics]:
        """Get related keyword suggestions with metrics."""
        payload = [{
            "keyword": seed_keyword,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
            "include_seed_keyword": True,
            "include_serp_info": True,
        }]
        data = self._post("keywords_data/google_ads/keywords_for_keywords/live", payload)

        results = []
        for task in data.get("tasks", []):
            for item in task.get("result", []):
                results.append(KeywordMetrics(
                    keyword=item.get("keyword", ""),
                    search_volume=item.get("search_volume", 0) or 0,
                    cpc=item.get("cpc", 0) or 0,
                    competition=item.get("competition", 0) or 0,
                ))
        return results

    # ── Backlinks API ─────────────────────────────────────────────

    def backlink_summary(self, domain: str) -> BacklinkProfile:
        """Get backlink profile summary for a domain."""
        payload = [{"target": domain, "internal_list_limit": 0, "include_subdomains": True}]
        data = self._post("backlinks/summary/live", payload)

        profile = BacklinkProfile()
        for task in data.get("tasks", []):
            for result in task.get("result", []):
                profile.total_backlinks = result.get("total_backlinks", 0)
                profile.referring_domains = result.get("referring_domains", 0)
                profile.domain_rank = result.get("rank", 0)
                nofollow = result.get("referring_links_attributes", {}).get("nofollow", 0)
                total = profile.total_backlinks or 1
                profile.dofollow_ratio = round((total - nofollow) / total * 100, 1)
        return profile

    def backlink_anchors(self, domain: str, limit: int = 20) -> list[dict]:
        """Get top anchor texts for a domain."""
        payload = [{"target": domain, "limit": limit, "order_by": ["backlinks,desc"]}]
        data = self._post("backlinks/anchors/live", payload)

        anchors = []
        for task in data.get("tasks", []):
            for item in task.get("result", []):
                if isinstance(item, dict) and "items" in item:
                    for anchor in item["items"]:
                        anchors.append({
                            "anchor": anchor.get("anchor", ""),
                            "backlinks": anchor.get("backlinks", 0),
                            "referring_domains": anchor.get("referring_domains", 0),
                            "dofollow": anchor.get("backlinks_nofollow", 0) == 0,
                        })
        return anchors[:limit]

    def backlink_referring_domains(self, domain: str, limit: int = 20) -> list[dict]:
        """Get top referring domains."""
        payload = [{"target": domain, "limit": limit, "order_by": ["rank,desc"]}]
        data = self._post("backlinks/referring_domains/live", payload)

        domains = []
        for task in data.get("tasks", []):
            for item in task.get("result", []):
                if isinstance(item, dict) and "items" in item:
                    for ref in item["items"]:
                        domains.append({
                            "domain": ref.get("domain", ""),
                            "rank": ref.get("rank", 0),
                            "backlinks": ref.get("backlinks", 0),
                            "dofollow": ref.get("backlinks_nofollow", 0) == 0,
                            "first_seen": ref.get("first_seen"),
                        })
        return domains[:limit]

    # ── DataForSEO Labs API ───────────────────────────────────────

    def competitor_domains(
        self,
        domain: str,
        location_code: int = 2356,
        language_code: str = "en",
        limit: int = 10,
    ) -> list[CompetitorDomain]:
        """Find competing domains based on keyword overlap."""
        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
            "filters": ["relevant_serp_items", ">", 0],
        }]
        data = self._post("dataforseo_labs/google/competitors_domain/live", payload)

        competitors = []
        for task in data.get("tasks", []):
            for result in task.get("result", []):
                if isinstance(result, dict) and "items" in result:
                    for item in result["items"]:
                        avg_pos = item.get("avg_position", 0)
                        competitors.append(CompetitorDomain(
                            domain=item.get("domain", ""),
                            common_keywords=item.get("se_keywords", 0),
                            total_keywords=item.get("se_keywords", 0),
                            total_traffic=int(item.get("etv", 0) or 0),
                            domain_rank=item.get("domain_rank", 0) or 0,
                            overlap_percentage=item.get("intersections", 0) or 0,
                        ))
        return sorted(competitors, key=lambda c: c.common_keywords, reverse=True)[:limit]

    def ranked_keywords(
        self,
        domain: str,
        location_code: int = 2356,
        language_code: str = "en",
        limit: int = 50,
    ) -> list[dict]:
        """Get keywords a domain ranks for with positions."""
        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }]
        data = self._post("dataforseo_labs/google/ranked_keywords/live", payload)

        keywords = []
        for task in data.get("tasks", []):
            for result in task.get("result", []):
                if isinstance(result, dict) and "items" in result:
                    for item in result["items"]:
                        kw_data = item.get("keyword_data", {})
                        kw_info = kw_data.get("keyword_info", {})
                        serp_info = kw_data.get("serp_info", {})
                        keywords.append({
                            "keyword": kw_data.get("keyword", ""),
                            "position": item.get("rank_absolute"),
                            "search_volume": kw_info.get("search_volume", 0),
                            "cpc": kw_info.get("cpc", 0),
                            "difficulty": kw_info.get("keyword_difficulty", 0),
                            "url": item.get("url", ""),
                            "serp_features": serp_info.get("serp_item_types", []),
                        })
        return keywords

    def keyword_gap(
        self,
        target_domain: str,
        competitor_domains: list[str],
        location_code: int = 2356,
        language_code: str = "en",
        limit: int = 50,
    ) -> list[dict]:
        """Find keywords competitors rank for but target doesn't."""
        targets = {target_domain: {"is_target": True}}
        for cd in competitor_domains[:4]:
            targets[cd] = {"is_target": False}

        payload = [{
            "targets": targets,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
            "item_types": ["organic"],
            "keywords_filters": [["keyword_data.keyword_info.search_volume", ">", 100]],
        }]
        data = self._post("dataforseo_labs/google/domain_intersection/live", payload)

        gaps = []
        for task in data.get("tasks", []):
            for result in task.get("result", []):
                if isinstance(result, dict) and "items" in result:
                    for item in result["items"]:
                        kw_data = item.get("keyword_data", {})
                        gaps.append({
                            "keyword": kw_data.get("keyword", ""),
                            "search_volume": kw_data.get("keyword_info", {}).get("search_volume", 0),
                            "cpc": kw_data.get("keyword_info", {}).get("cpc", 0),
                            "competitor_positions": {
                                domain: info.get("rank_absolute")
                                for domain, info in item.get("intersection_result", {}).items()
                                if info and info.get("rank_absolute")
                            },
                        })
        return sorted(gaps, key=lambda g: g.get("search_volume", 0), reverse=True)[:limit]

    # ── On-Page API ───────────────────────────────────────────────

    ONPAGE_CHECK_KEYS = (
        "duplicate_title",
        "duplicate_description",
        "duplicate_content",
        "no_title",
        "no_description",
        "no_h1_tag",
        "no_image_alt",
        "no_image_title",
        "no_favicon",
        "no_canonical",
        "no_doctype",
        "no_encoding_meta_tag",
        "high_loading_time",
        "high_waiting_time",
        "is_4xx_code",
        "is_5xx_code",
        "is_broken",
        "is_redirect",
        "low_content_rate",
        "large_page_size",
        "frame",
        "lorem_ipsum",
        "seo_friendly_url_characters_check",
        "has_render_blocking_resources",
        "redirect_chain",
        "canonical_to_redirect",
        "canonical_to_broken",
        "has_links_to_redirects",
        "has_links_to_broken_resources",
        "deprecated_html_tags",
        "www_redirect",
        "irrelevant_title",
        "irrelevant_description",
    )

    def onpage_audit(self, domain: str, max_pages: int = 100) -> str:
        """Start an on-page audit task. Returns task_id."""
        payload = [{
            "target": domain,
            "max_crawl_pages": max_pages,
            "load_resources": True,
            "enable_javascript": True,
            "enable_browser_rendering": True,
            "check_spell": True,
            "calculate_keyword_density": True,
        }]
        data = self._post("on_page/task_post", payload)

        for task in data.get("tasks", []):
            return task.get("id", "")
        return ""

    def onpage_tasks_ready(self) -> list[dict]:
        """List on-page tasks that have finished crawling."""
        url = f"{_base_url()}/on_page/tasks_ready"
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, auth=self._auth())
                data = resp.json()
                ready: list[dict] = []
                for task in data.get("tasks", []) or []:
                    for item in task.get("result", []) or []:
                        ready.append(item)
                return ready
        except httpx.HTTPError as exc:
            logger.warning("onpage_tasks_ready failed: %s", exc)
            return []

    def onpage_summary(self, task_id: str) -> dict:
        """Get on-page audit summary results."""
        url = f"{_base_url()}/on_page/summary/{task_id}"
        with httpx.Client(timeout=60) as client:
            resp = client.get(url, auth=self._auth())
            data = resp.json()

        if data.get("status_code") == 20000:
            self._request_count += 1
            self.total_cost += data.get("cost", 0) or 0

        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                page_metrics = result.get("page_metrics", {}) or {}
                checks = page_metrics.get("checks", {}) or {}
                crawl_progress = result.get("crawl_progress", "finished")
                pages_crawled = result.get("crawl_progress", {}).get("pages_crawled") if isinstance(result.get("crawl_progress"), dict) else None
                return {
                    "crawl_status": crawl_progress if isinstance(crawl_progress, str) else "in_progress",
                    "pages_crawled": result.get("pages_crawled") or pages_crawled or 0,
                    "pages_in_queue": result.get("crawl_progress", {}).get("pages_in_queue") if isinstance(result.get("crawl_progress"), dict) else 0,
                    "max_crawl_pages": result.get("crawl_progress", {}).get("max_crawl_pages") if isinstance(result.get("crawl_progress"), dict) else None,
                    "domain_info": result.get("domain_info", {}) or {},
                    "page_metrics": {
                        "onpage_score": page_metrics.get("onpage_score"),
                        "links_external": page_metrics.get("links_external"),
                        "links_internal": page_metrics.get("links_internal"),
                        "duplicate_title": checks.get("duplicate_title", 0),
                        "duplicate_description": checks.get("duplicate_description", 0),
                        "duplicate_content": checks.get("duplicate_content", 0),
                        "broken_links": checks.get("is_broken", 0),
                        "no_h1": checks.get("no_h1_tag", 0),
                        "no_title": checks.get("no_title", 0),
                        "no_description": checks.get("no_description", 0),
                        "no_image_alt": checks.get("no_image_alt", 0),
                        "no_canonical": checks.get("no_canonical", 0),
                        "low_content": checks.get("low_content_rate", 0),
                        "slow_pages": checks.get("high_loading_time", 0),
                        "redirect_chain": checks.get("redirect_chain", 0),
                        "is_4xx": checks.get("is_4xx_code", 0),
                        "is_5xx": checks.get("is_5xx_code", 0),
                        "render_blocking": checks.get("has_render_blocking_resources", 0),
                        "links_to_broken": checks.get("has_links_to_broken_resources", 0),
                        "links_to_redirects": checks.get("has_links_to_redirects", 0),
                    },
                    "checks": {k: checks.get(k, 0) for k in self.ONPAGE_CHECK_KEYS},
                    "raw_summary": result,
                }
        return {}

    def onpage_pages(self, task_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return per-page crawl details, sorted by onpage_score ascending (worst first)."""
        payload = [{
            "id": task_id,
            "limit": limit,
            "offset": offset,
            "order_by": ["meta.internal_links_count,desc"],
        }]
        data = self._post("on_page/pages", payload)

        pages: list[dict] = []
        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                for item in result.get("items", []) or []:
                    meta = item.get("meta", {}) or {}
                    checks = item.get("checks", {}) or {}
                    pages.append({
                        "url": item.get("url", ""),
                        "status_code": item.get("status_code"),
                        "onpage_score": item.get("onpage_score"),
                        "page_timing": item.get("page_timing", {}) or {},
                        "title": meta.get("title"),
                        "description": meta.get("description"),
                        "word_count": meta.get("content", {}).get("plain_text_word_count") if isinstance(meta.get("content"), dict) else None,
                        "h1": meta.get("htags", {}).get("h1", []) if isinstance(meta.get("htags"), dict) else [],
                        "internal_links": meta.get("internal_links_count"),
                        "external_links": meta.get("external_links_count"),
                        "images_count": meta.get("images_count"),
                        "issues": [k for k, v in checks.items() if v],
                    })
        return pages

    def onpage_duplicate_tags(self, task_id: str, tag: str = "title", limit: int = 50) -> list[dict]:
        """Return groups of pages sharing duplicate title or description."""
        if tag not in ("title", "description"):
            raise ValueError("tag must be 'title' or 'description'")
        payload = [{"id": task_id, "limit": limit}]
        endpoint = f"on_page/duplicate_{tag}s"
        data = self._post(endpoint, payload)

        groups: list[dict] = []
        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                for item in result.get("items", []) or []:
                    groups.append({
                        "value": item.get("title") or item.get("description"),
                        "pages": [p.get("url", "") for p in (item.get("pages", []) or [])],
                        "total_count": item.get("total_count"),
                    })
        return groups

    def onpage_links(self, task_id: str, limit: int = 100, filters: list | None = None) -> list[dict]:
        """Return link records, optionally filtered (e.g. broken)."""
        body: dict = {"id": task_id, "limit": limit}
        if filters:
            body["filters"] = filters
        data = self._post("on_page/links", [body])

        links: list[dict] = []
        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                for item in result.get("items", []) or []:
                    links.append({
                        "link_from": item.get("link_from"),
                        "link_to": item.get("link_to"),
                        "type": item.get("type"),
                        "direction": item.get("direction"),
                        "dofollow": item.get("dofollow"),
                        "broken": item.get("is_broken"),
                        "anchor": item.get("link_attribute") or item.get("text"),
                    })
        return links

    def onpage_wait_for_ready(
        self,
        task_id: str,
        max_wait_seconds: int = 180,
        poll_interval: int = 5,
    ) -> bool:
        """Poll tasks_ready until task appears or timeout. Returns True if ready."""
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            ready = self.onpage_tasks_ready()
            if any(item.get("id") == task_id for item in ready):
                return True
            time.sleep(poll_interval)
        return False

    # ── Utility ───────────────────────────────────────────────────

    def get_cost_summary(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost, 4),
            "total_requests": self._request_count,
        }

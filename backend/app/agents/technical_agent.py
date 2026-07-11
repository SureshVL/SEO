"""AI-Powered Technical SEO Audit Agent.

Integrates PageSpeed Insights API for real performance data
and Claude for intelligent analysis and prioritized recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.clients.claude_client import AIUsageAccumulator
from app.clients.dataforseo_client import DataForSEOClient
from app.schemas.research import ResearchResponse

logger = logging.getLogger("omnirank.technical")


@dataclass
class TechnicalAction:
    category: str
    action: str
    impact: str  # critical, high, medium, low
    details: str = ""
    auto_fixable: bool = False


@dataclass
class TechnicalAuditResult:
    url: str
    performance_score: float | None = None
    accessibility_score: float | None = None
    seo_score: float | None = None
    best_practices_score: float | None = None
    core_web_vitals: dict[str, Any] = field(default_factory=dict)
    actions: list[TechnicalAction] = field(default_factory=list)
    execution_queue: list[dict[str, str]] = field(default_factory=list)
    raw_lighthouse: dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteCrawlResult:
    domain: str
    task_id: str = ""
    status: str = "pending"  # pending|crawling|finished|failed
    pages_crawled: int = 0
    pages_in_queue: int = 0
    max_crawl_pages: int | None = None
    onpage_score: float | None = None
    issues_by_check: dict[str, int] = field(default_factory=dict)
    actions: list[TechnicalAction] = field(default_factory=list)
    sample_pages: list[dict[str, Any]] = field(default_factory=list)
    duplicate_titles: list[dict[str, Any]] = field(default_factory=list)
    duplicate_descriptions: list[dict[str, Any]] = field(default_factory=list)
    broken_links: list[dict[str, Any]] = field(default_factory=list)
    raw_summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class TechnicalAgent:
    """Real technical SEO auditing with PageSpeed Insights + DataForSEO On-Page crawl."""

    # Human-readable labels + impact weights for DataForSEO on-page checks.
    _CHECK_META: dict[str, tuple[str, str, str]] = {
        "is_5xx_code": ("crawl_errors", "critical", "5xx server errors returned during crawl"),
        "is_4xx_code": ("crawl_errors", "high", "4xx client errors returned during crawl"),
        "is_broken": ("broken_links", "critical", "Broken internal links detected"),
        "has_links_to_broken_resources": ("broken_links", "high", "Pages link to broken resources"),
        "duplicate_title": ("metadata", "high", "Pages share identical title tags"),
        "duplicate_description": ("metadata", "medium", "Pages share identical meta descriptions"),
        "duplicate_content": ("content", "high", "Pages with near-duplicate body content"),
        "no_title": ("metadata", "critical", "Pages missing a title tag"),
        "no_description": ("metadata", "high", "Pages missing a meta description"),
        "no_h1_tag": ("on_page", "critical", "Pages without an H1"),
        "no_image_alt": ("accessibility", "medium", "Images without alt attributes"),
        "no_canonical": ("indexation", "medium", "Pages without a canonical tag"),
        "redirect_chain": ("indexation", "medium", "Multi-hop redirect chains"),
        "canonical_to_redirect": ("indexation", "high", "Canonical points to a redirect"),
        "canonical_to_broken": ("indexation", "critical", "Canonical points to a broken URL"),
        "has_render_blocking_resources": ("performance", "medium", "Render-blocking scripts or styles"),
        "high_loading_time": ("performance", "high", "Pages with slow server response"),
        "large_page_size": ("performance", "medium", "Pages exceeding recommended weight"),
        "low_content_rate": ("content", "medium", "Pages with thin body content"),
        "has_links_to_redirects": ("indexation", "low", "Internal links pointing to redirects"),
        "www_redirect": ("indexation", "low", "Missing canonical www/non-www redirect"),
        "lorem_ipsum": ("content", "high", "Placeholder copy detected"),
        "frame": ("accessibility", "low", "Iframes detected on pages"),
        "deprecated_html_tags": ("code_quality", "low", "Deprecated HTML tags used"),
        "seo_friendly_url_characters_check": ("indexation", "low", "URLs with unfriendly characters"),
    }

    def __init__(
        self,
        claude_client: ClaudeClient | None = None,
        pagespeed_api_key: str = "",
        dataforseo_client: DataForSEOClient | None = None,
    ):
        self.claude = claude_client
        self.pagespeed_key = pagespeed_api_key
        self.dataforseo = dataforseo_client
        self.usage = AIUsageAccumulator()

    def full_audit(self, url: str, research: ResearchResponse | None = None) -> TechnicalAuditResult:
        """Run a comprehensive technical SEO audit."""
        result = TechnicalAuditResult(url=url)

        # 1. PageSpeed Insights (real data)
        psi_data = self._fetch_pagespeed(url)
        if psi_data:
            result = self._parse_pagespeed(result, psi_data)

        # 2. Heading structure analysis from research
        if research:
            heading_actions = self._analyze_headings(research)
            result.actions.extend(heading_actions)

        # 3. AI-powered analysis and recommendations
        if self.claude:
            ai_actions = self._ai_audit(result, research)
            result.actions.extend(ai_actions)
        else:
            result.actions.extend(self._deterministic_actions(result, research))

        # 4. Generate execution queue
        result.execution_queue = self.execute(result.actions)

        return result

    def audit(self, research: ResearchResponse) -> list[TechnicalAction]:
        """Legacy interface — returns actions from research data only."""
        result = self.full_audit(str(research.client_profile.url), research)
        return result.actions

    def execute(self, actions: list[TechnicalAction]) -> list[dict[str, str]]:
        """Generate execution queue payloads from actions."""
        return [
            {
                "category": a.category,
                "status": "queued",
                "action": a.action,
                "impact": a.impact,
                "auto_fixable": str(a.auto_fixable).lower(),
                "details": a.details,
            }
            for a in actions
        ]

    def _fetch_pagespeed(self, url: str) -> dict[str, Any] | None:
        """Fetch real PageSpeed Insights data."""
        try:
            params: dict[str, str] = {
                "url": url,
                "strategy": "mobile",
                "category": "performance",
                "category": "accessibility",
                "category": "seo",
                "category": "best-practices",
            }
            # PageSpeed API supports multiple categories
            api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            query_params = f"?url={url}&strategy=mobile"
            query_params += "&category=performance&category=accessibility&category=seo&category=best-practices"
            if self.pagespeed_key:
                query_params += f"&key={self.pagespeed_key}"

            with httpx.Client(timeout=60) as client:
                resp = client.get(f"{api_url}{query_params}")
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("PageSpeed API returned %d for %s", resp.status_code, url)
        except Exception as exc:
            logger.warning("PageSpeed API call failed for %s: %s", url, exc)
        return None

    def _parse_pagespeed(self, result: TechnicalAuditResult, data: dict) -> TechnicalAuditResult:
        """Parse PageSpeed Insights response into structured audit result."""
        categories = data.get("lighthouseResult", {}).get("categories", {})

        result.performance_score = self._cat_score(categories, "performance")
        result.accessibility_score = self._cat_score(categories, "accessibility")
        result.seo_score = self._cat_score(categories, "seo")
        result.best_practices_score = self._cat_score(categories, "best-practices")

        # Core Web Vitals
        audits = data.get("lighthouseResult", {}).get("audits", {})
        cwv_metrics = {
            "LCP": audits.get("largest-contentful-paint", {}).get("numericValue"),
            "FID": audits.get("max-potential-fid", {}).get("numericValue"),
            "CLS": audits.get("cumulative-layout-shift", {}).get("numericValue"),
            "FCP": audits.get("first-contentful-paint", {}).get("numericValue"),
            "TBT": audits.get("total-blocking-time", {}).get("numericValue"),
            "SI": audits.get("speed-index", {}).get("numericValue"),
        }
        result.core_web_vitals = {k: v for k, v in cwv_metrics.items() if v is not None}

        # Extract failed audits as actions
        for audit_id, audit_data in audits.items():
            score = audit_data.get("score")
            if score is not None and score < 0.5 and audit_data.get("title"):
                impact = "critical" if score == 0 else "high"
                result.actions.append(TechnicalAction(
                    category="performance",
                    action=audit_data["title"],
                    impact=impact,
                    details=audit_data.get("description", "")[:200],
                ))

        result.raw_lighthouse = {
            "scores": {
                "performance": result.performance_score,
                "accessibility": result.accessibility_score,
                "seo": result.seo_score,
                "best_practices": result.best_practices_score,
            },
            "cwv": result.core_web_vitals,
        }

        return result

    def _analyze_headings(self, research: ResearchResponse) -> list[TechnicalAction]:
        """Analyze heading structure from research data."""
        actions: list[TechnicalAction] = []
        client = research.client_profile

        if not client.h1:
            actions.append(TechnicalAction(
                category="on_page", action="Add an H1 tag — page is missing primary heading",
                impact="critical", auto_fixable=True,
            ))

        if len(client.h2) < 3:
            actions.append(TechnicalAction(
                category="on_page", action=f"Add more H2 sections (currently {len(client.h2)}, competitors avg 6-8)",
                impact="high", auto_fixable=True,
            ))

        gap = research.gap_analysis
        if gap.heading_gaps:
            actions.append(TechnicalAction(
                category="information_architecture",
                action="Add sections for uncovered topics: " + ", ".join(gap.heading_gaps[:5]),
                impact="high", auto_fixable=True,
                details="Include FAQ schema markup for question-based sections.",
            ))

        return actions

    def _ai_audit(self, result: TechnicalAuditResult, research: ResearchResponse | None) -> list[TechnicalAction]:
        """Use Claude to analyze technical audit data and generate smart recommendations."""
        assert self.claude is not None

        system = """You are a technical SEO expert. Analyze the audit data and provide
specific, actionable technical recommendations. Focus on:
1. Core Web Vitals improvements
2. Crawlability and indexation
3. Schema/structured data opportunities
4. Internal linking optimization
5. Mobile optimization
6. Security headers

Respond ONLY with JSON:
{
  "actions": [
    {"category":"<cat>","action":"<specific action>","impact":"critical|high|medium","details":"<implementation notes>","auto_fixable":true|false}
  ]
}"""

        context = f"""URL: {result.url}
Performance scores: {result.raw_lighthouse.get('scores', {})}
Core Web Vitals: {result.core_web_vitals}
Existing issues found: {len(result.actions)}"""

        if research:
            context += f"""
Content word count: {research.client_profile.word_count}
H2 count: {len(research.client_profile.h2)}
Entity coverage: {len(research.client_profile.top_entities)} entities found"""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": context}],
            system=system, max_tokens=1500, temperature=0.2,
        )
        self.usage.record(resp)

        ai_actions = []
        for a in parsed.get("actions", []):
            if isinstance(a, dict):
                ai_actions.append(TechnicalAction(
                    category=a.get("category", "general"),
                    action=a.get("action", ""),
                    impact=a.get("impact", "medium"),
                    details=a.get("details", ""),
                    auto_fixable=a.get("auto_fixable", False),
                ))
        return ai_actions

    def _deterministic_actions(self, result: TechnicalAuditResult, research: ResearchResponse | None) -> list[TechnicalAction]:
        """Fallback deterministic actions."""
        actions = [
            TechnicalAction(category="core_web_vitals", action="Compress and lazy-load below-fold images; target LCP < 2.5s.", impact="high"),
            TechnicalAction(category="internal_linking", action="Add contextual links from high-traffic pages to new sections.", impact="medium"),
            TechnicalAction(category="structured_data", action="Add Article, FAQ, and BreadcrumbList schema markup.", impact="high", auto_fixable=True),
        ]
        if result.performance_score and result.performance_score < 50:
            actions.append(TechnicalAction(
                category="performance", action="Performance score is critically low — prioritize CWV fixes.",
                impact="critical",
            ))
        return actions

    @staticmethod
    def _cat_score(categories: dict, key: str) -> float | None:
        cat = categories.get(key, {})
        score = cat.get("score")
        return round(score * 100, 1) if score is not None else None

    # ── Full site crawl (DataForSEO On-Page) ─────────────────────────

    def start_site_crawl(self, domain: str, max_pages: int = 100) -> SiteCrawlResult:
        """Kick off a DataForSEO on-page crawl. Returns a result with task_id set."""
        result = SiteCrawlResult(domain=domain, max_crawl_pages=max_pages)
        if not self.dataforseo or not self.dataforseo.enabled:
            result.status = "failed"
            result.error = "DataForSEO credentials not configured"
            return result
        try:
            task_id = self.dataforseo.onpage_audit(domain, max_pages=max_pages)
        except Exception as exc:
            logger.warning("onpage_audit kickoff failed for %s: %s", domain, exc)
            result.status = "failed"
            result.error = str(exc)
            return result

        if not task_id:
            result.status = "failed"
            result.error = "DataForSEO did not return a task id"
            return result

        result.task_id = task_id
        result.status = "crawling"
        return result

    def fetch_site_crawl(
        self,
        task_id: str,
        domain: str = "",
        include_samples: bool = True,
    ) -> SiteCrawlResult:
        """Fetch crawl status + parsed results for a task_id."""
        result = SiteCrawlResult(domain=domain, task_id=task_id)
        if not self.dataforseo or not self.dataforseo.enabled:
            result.status = "failed"
            result.error = "DataForSEO credentials not configured"
            return result

        try:
            summary = self.dataforseo.onpage_summary(task_id)
        except Exception as exc:
            logger.warning("onpage_summary failed for %s: %s", task_id, exc)
            result.status = "failed"
            result.error = str(exc)
            return result

        if not summary:
            result.status = "crawling"
            return result

        result.raw_summary = summary.get("raw_summary", {})
        crawl_status = (summary.get("crawl_status") or "").lower()
        pages_in_queue = summary.get("pages_in_queue") or 0
        result.pages_crawled = summary.get("pages_crawled", 0) or 0
        result.pages_in_queue = pages_in_queue
        result.max_crawl_pages = summary.get("max_crawl_pages")

        if crawl_status in ("finished", "done") or (pages_in_queue == 0 and result.pages_crawled):
            result.status = "finished"
        else:
            result.status = "crawling"

        page_metrics = summary.get("page_metrics", {}) or {}
        result.onpage_score = page_metrics.get("onpage_score")
        checks = summary.get("checks", {}) or {}
        result.issues_by_check = {k: int(v or 0) for k, v in checks.items() if v}

        result.actions = self._actions_from_checks(result.issues_by_check, result.pages_crawled)

        if include_samples and result.status == "finished":
            try:
                result.sample_pages = self.dataforseo.onpage_pages(task_id, limit=25) or []
            except Exception as exc:
                logger.debug("onpage_pages failed: %s", exc)
            try:
                result.duplicate_titles = self.dataforseo.onpage_duplicate_tags(task_id, tag="title", limit=20) or []
            except Exception as exc:
                logger.debug("duplicate_titles failed: %s", exc)
            try:
                result.duplicate_descriptions = self.dataforseo.onpage_duplicate_tags(task_id, tag="description", limit=20) or []
            except Exception as exc:
                logger.debug("duplicate_descriptions failed: %s", exc)
            try:
                result.broken_links = self.dataforseo.onpage_links(
                    task_id,
                    limit=50,
                    filters=[["is_broken", "=", True]],
                ) or []
            except Exception as exc:
                logger.debug("onpage_links broken filter failed: %s", exc)

        return result

    def run_site_crawl(
        self,
        domain: str,
        max_pages: int = 100,
        max_wait_seconds: int = 180,
    ) -> SiteCrawlResult:
        """Blocking convenience: start crawl, poll until ready, return results."""
        started = self.start_site_crawl(domain, max_pages=max_pages)
        if started.status != "crawling" or not started.task_id:
            return started

        assert self.dataforseo is not None
        ready = self.dataforseo.onpage_wait_for_ready(
            started.task_id, max_wait_seconds=max_wait_seconds
        )
        if not ready:
            # Return whatever partial summary we can
            partial = self.fetch_site_crawl(started.task_id, domain=domain, include_samples=False)
            if partial.status == "finished":
                return partial
            partial.status = "crawling"
            partial.error = partial.error or "Crawl still in progress; poll /audit/crawl/{task_id}"
            return partial

        return self.fetch_site_crawl(started.task_id, domain=domain, include_samples=True)

    def _actions_from_checks(
        self, issues_by_check: dict[str, int], pages_crawled: int
    ) -> list[TechnicalAction]:
        """Convert DataForSEO issue counts to prioritized TechnicalAction list."""
        actions: list[TechnicalAction] = []
        pages_crawled = max(pages_crawled, 1)
        for check, count in issues_by_check.items():
            if not count:
                continue
            meta = self._CHECK_META.get(check)
            if meta:
                category, impact, label = meta
            else:
                category, impact, label = "technical", "medium", check.replace("_", " ").title()

            pct = round(count / pages_crawled * 100, 1)
            actions.append(TechnicalAction(
                category=category,
                action=f"{label} — {count} page(s) affected ({pct}%)",
                impact=impact,
                details=f"DataForSEO on-page check '{check}' flagged {count} of {pages_crawled} crawled pages.",
                auto_fixable=check in {"no_h1_tag", "no_title", "no_description", "no_image_alt", "no_canonical"},
            ))

        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        actions.sort(key=lambda a: severity_rank.get(a.impact, 9))
        return actions

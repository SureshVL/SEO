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


class TechnicalAgent:
    """Real technical SEO auditing with PageSpeed Insights + Claude analysis."""

    def __init__(
        self,
        claude_client: ClaudeClient | None = None,
        pagespeed_api_key: str = "",
    ):
        self.claude = claude_client
        self.pagespeed_key = pagespeed_api_key
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

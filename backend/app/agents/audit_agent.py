"""Technical SEO audit agent - continuous monitoring and issue detection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.clients.llm import llm_client

logger = logging.getLogger("omnirank.audit")


@dataclass
class AuditIssue:
    """A technical SEO issue found during audit."""
    issue_type: str
    severity: str  # critical, warning, info
    affected_url: str
    affected_element: str
    description: str
    recommendation: str
    evidence: dict[str, Any]


@dataclass
class AuditResult:
    """Result of an audit run."""
    audit_type: str
    status: str
    total_pages_checked: int
    issues_found: int
    critical_count: int
    warning_count: int
    summary: str
    issues: list[AuditIssue]


class AuditAgent:
    """Analyzes technical SEO issues and recommends fixes."""

    def __init__(self):
        self.llm = llm_client

    async def analyze_crawl_errors(
        self,
        site_domain: str,
        crawl_data: list[dict[str, Any]],
    ) -> AuditResult:
        """Analyze crawl errors and accessibility issues."""
        try:
            errors_summary = "\n".join(
                f"- {item.get('url')}: {item.get('error_type')} ({item.get('status_code')})"
                for item in crawl_data[:30]
            )

            prompt = f"""Analyze these crawl errors for {site_domain}:

{errors_summary}

For each error type, identify:
1. Root cause (server error, redirect chain, DNS issue, etc.)
2. Impact on SEO (crawlability, indexing, user experience)
3. Severity (critical = blocks crawling, warning = degrades experience, info = minor)
4. Recommended fix with implementation priority

Also identify:
- Error patterns (e.g., 404s on category pages, 503s on checkout)
- Pages with most errors
- Urgency of fixes

Format as JSON:
{{
  "audit_type": "crawl_errors",
  "total_errors": 42,
  "error_patterns": [
    {{
      "pattern": "404 on product pages",
      "count": 15,
      "severity": "critical",
      "root_cause": "Product deletion without redirect"
    }}
  ],
  "top_issues": [
    {{
      "issue_type": "broken_product_links",
      "severity": "critical",
      "affected_urls": ["/products/old-sku-123"],
      "description": "Product pages deleted without redirects",
      "recommendation": "Set up 301 redirects to category pages or similar products",
      "priority": 1
    }}
  ],
  "summary": "Critical: 15 product page 404s due to deletions without redirects. Recommend urgent redirect implementation."
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2500,
            )

            analysis = self._parse_audit_result(response, "crawl_errors", crawl_data)
            return analysis

        except Exception as exc:
            logger.error("Crawl error analysis failed: %s", exc)
            raise

    async def analyze_broken_links(
        self,
        site_domain: str,
        link_data: list[dict[str, Any]],
    ) -> AuditResult:
        """Identify broken internal and external links."""
        try:
            broken_summary = "\n".join(
                f"- {item.get('source_url')} -> {item.get('target_url')}: {item.get('status_code')}"
                for item in link_data[:30]
            )

            prompt = f"""Analyze broken links found on {site_domain}:

{broken_summary}

Categorize by:
1. Internal vs external links
2. Severity (4xx vs 5xx vs timeout)
3. Impact (linked from homepage vs deep pages, anchor text relevance)
4. Root cause (domain expired, URL typo, moved without redirect, etc.)

For each category, provide:
- Count and URLs
- Root cause analysis
- Recommended fix
- Implementation priority (1-10)

Format as JSON:
{{
  "audit_type": "broken_links",
  "total_broken": 28,
  "internal_broken": 12,
  "external_broken": 16,
  "critical_issues": [
    {{
      "issue_type": "broken_internal_link",
      "severity": "critical",
      "affected_url": "/homepage",
      "target_url": "/products/featured",
      "description": "Homepage links to deleted product page",
      "recommendation": "Update link to working product or category page",
      "evidence": {{"status_code": 404, "anchor_text": "Featured Products"}}
    }}
  ],
  "summary": "12 internal broken links (homepage + category pages), 16 external affiliate/reference links down."
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2500,
            )

            analysis = self._parse_audit_result(response, "broken_links", link_data)
            return analysis

        except Exception as exc:
            logger.error("Broken links analysis failed: %s", exc)
            raise

    async def analyze_schema_validation(
        self,
        site_domain: str,
        schema_data: list[dict[str, Any]],
    ) -> AuditResult:
        """Validate schema markup and identify issues."""
        try:
            schema_summary = "\n".join(
                f"- {item.get('url')}: {item.get('schema_type')} - {item.get('error') or 'Valid'}"
                for item in schema_data[:30]
            )

            prompt = f"""Analyze schema markup validation for {site_domain}:

{schema_summary}

For each schema type and error:
1. Impact on rich snippets (carousel, review stars, FAQ, etc.)
2. Severity (missing field, invalid value, syntax error)
3. Affected pages
4. How to fix

Also identify:
- Most common schema errors
- Missing schema opportunities (e.g., Organization, FAQPage)
- Mobile vs desktop rendering issues

Format as JSON:
{{
  "audit_type": "schema_validation",
  "total_pages_checked": 150,
  "pages_with_schema": 120,
  "issues_found": 8,
  "issue_details": [
    {{
      "issue_type": "invalid_product_schema",
      "severity": "warning",
      "affected_url": "/products/item-123",
      "description": "Product schema missing required 'offers' field",
      "recommendation": "Add offers array with price, availability, and merchant information",
      "evidence": {{"schema_type": "Product", "missing_field": "offers"}}
    }}
  ],
  "opportunities": [
    "FAQSchema on /help pages (10 pages identified)",
    "BreadcrumbList on category/product hierarchy"
  ],
  "summary": "8 validation issues affecting product and article pages. 2 schema types missing rich snippet eligibility."
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2500,
            )

            analysis = self._parse_audit_result(response, "schema_validation", schema_data)
            return analysis

        except Exception as exc:
            logger.error("Schema validation analysis failed: %s", exc)
            raise

    async def analyze_performance(
        self,
        site_domain: str,
        performance_data: list[dict[str, Any]],
    ) -> AuditResult:
        """Analyze page load performance and Core Web Vitals."""
        try:
            perf_summary = "\n".join(
                f"- {item.get('url')}: LCP={item.get('lcp')}ms, FID={item.get('fid')}ms, CLS={item.get('cls')}, Load={item.get('load_time')}ms"
                for item in performance_data[:20]
            )

            prompt = f"""Analyze page performance metrics for {site_domain}:

{perf_summary}

Identify:
1. Core Web Vitals issues (LCP > 2.5s, FID > 100ms, CLS > 0.1)
2. Overall page load time problems (> 3s is poor)
3. Mobile vs desktop performance gaps
4. Common bottlenecks by page type
5. Impact on rankings and user experience

For each issue:
- Affected pages
- Root cause (images, JavaScript, server response, CSS)
- Recommended optimization (compression, caching, lazy loading, CDN, code splitting)
- Expected improvement

Format as JSON:
{{
  "audit_type": "performance",
  "pages_analyzed": 45,
  "critical_issues": 12,
  "lcp_failures": 8,
  "fid_failures": 3,
  "cls_failures": 1,
  "issues": [
    {{
      "issue_type": "slow_page_load",
      "severity": "critical",
      "affected_url": "/product/category",
      "description": "Page load time 5.2s (threshold: 3s)",
      "recommendation": "Optimize product images (use WebP, lazy load). Implement resource caching.",
      "evidence": {{"load_time": 5200, "images_size": 3500, "javascript_size": 800}}
    }}
  ],
  "summary": "12 pages with critical performance issues. LCP failures on product pages due to unoptimized images."
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2500,
            )

            analysis = self._parse_audit_result(response, "performance", performance_data)
            return analysis

        except Exception as exc:
            logger.error("Performance analysis failed: %s", exc)
            raise

    async def analyze_orphan_pages(
        self,
        site_domain: str,
        page_data: list[dict[str, Any]],
        link_graph: dict[str, list[str]],
    ) -> AuditResult:
        """Identify orphaned and poorly-linked pages."""
        try:
            orphan_summary = "\n".join(
                f"- {page.get('url')}: {page.get('links_to_it', 0)} inbound, {page.get('links_from', 0)} outbound"
                for page in page_data[:20]
            )

            prompt = f"""Identify orphaned and poorly-linked pages for {site_domain}:

{orphan_summary}

For pages with few or no inbound links:
1. Severity (completely orphaned = no internal links, poorly linked = 1 link from footer)
2. Content value (important content vs duplicate vs outdated)
3. Visibility impact
4. Recommended linking strategy

Format as JSON:
{{
  "audit_type": "orphan_pages",
  "total_orphaned": 5,
  "poorly_linked": 12,
  "critical_issues": [
    {{
      "issue_type": "orphan_page",
      "severity": "critical",
      "affected_url": "/guides/advanced-tutorial",
      "description": "Page has no inbound internal links. Only discoverable via search or direct URL.",
      "recommendation": "Add links from: /guides (parent category), /resources page, related guide pages",
      "evidence": {{"inbound_links": 0, "page_type": "guide"}}
    }}
  ],
  "summary": "5 completely orphaned pages (no internal links). 12 pages with only 1 inbound link (footer only)."
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2000,
            )

            analysis = self._parse_audit_result(response, "orphan_pages", page_data)
            return analysis

        except Exception as exc:
            logger.error("Orphan page analysis failed: %s", exc)
            raise

    def _parse_audit_result(
        self,
        response: str,
        audit_type: str,
        source_data: list[dict[str, Any]],
    ) -> AuditResult:
        """Parse audit result from Claude response."""
        try:
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return AuditResult(
                    audit_type=audit_type,
                    status="failed",
                    total_pages_checked=len(source_data),
                    issues_found=0,
                    critical_count=0,
                    warning_count=0,
                    summary="Failed to parse results",
                    issues=[],
                )

            data = json.loads(json_match.group())

            # Extract issues
            issues = []
            for item in data.get("critical_issues", [])[:50]:
                issue = AuditIssue(
                    issue_type=item.get("issue_type", "unknown"),
                    severity=item.get("severity", "warning"),
                    affected_url=item.get("affected_url", ""),
                    affected_element=item.get("target_url", item.get("affected_element", "")),
                    description=item.get("description", ""),
                    recommendation=item.get("recommendation", ""),
                    evidence=item.get("evidence", {}),
                )
                issues.append(issue)

            # Also include other issues if present
            for item in data.get("issues", [])[:50]:
                if not any(i.affected_url == item.get("affected_url") for i in issues):
                    issue = AuditIssue(
                        issue_type=item.get("issue_type", "unknown"),
                        severity=item.get("severity", "info"),
                        affected_url=item.get("affected_url", ""),
                        affected_element=item.get("target_url", item.get("affected_element", "")),
                        description=item.get("description", ""),
                        recommendation=item.get("recommendation", ""),
                        evidence=item.get("evidence", {}),
                    )
                    issues.append(issue)

            critical = sum(1 for i in issues if i.severity == "critical")
            warnings = sum(1 for i in issues if i.severity == "warning")

            return AuditResult(
                audit_type=audit_type,
                status="completed",
                total_pages_checked=data.get("total_pages_checked", data.get("pages_analyzed", len(source_data))),
                issues_found=data.get("issues_found", data.get("total_issues", len(issues))),
                critical_count=critical,
                warning_count=warnings,
                summary=data.get("summary", ""),
                issues=issues,
            )

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse audit result: %s", exc)
            return AuditResult(
                audit_type=audit_type,
                status="failed",
                total_pages_checked=len(source_data),
                issues_found=0,
                critical_count=0,
                warning_count=0,
                summary="Parsing error",
                issues=[],
            )

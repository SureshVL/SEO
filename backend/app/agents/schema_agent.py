"""Schema Markup (JSON-LD) detection and generator agent.

Parses HTML for JSON-LD blocks, classifies the schema types present,
identifies recommended-but-missing types for the site's business profile,
and generates ready-to-paste JSON-LD for the gaps.

No external parsing dependency — JSON-LD lives inside
`<script type="application/ld+json">...</script>` which is cheap to extract
with a regex + json.loads.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("omnirank.schema")


JSONLD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


# Business-type → recommended schema types. Drives gap analysis + generation.
RECOMMENDED_BY_BUSINESS: dict[str, list[str]] = {
    "local_business": ["LocalBusiness", "WebSite", "BreadcrumbList", "FAQPage"],
    "restaurant": ["Restaurant", "WebSite", "BreadcrumbList", "Menu", "FAQPage"],
    "ecommerce": ["Organization", "WebSite", "Product", "BreadcrumbList", "FAQPage"],
    "saas": ["Organization", "WebSite", "SoftwareApplication", "FAQPage", "BreadcrumbList"],
    "publisher": ["Organization", "WebSite", "Article", "BreadcrumbList"],
    "agency": ["Organization", "WebSite", "Service", "BreadcrumbList", "FAQPage"],
    "default": ["Organization", "WebSite", "BreadcrumbList", "FAQPage"],
}

# All types we know how to generate stubs for
GENERATABLE_TYPES = {
    "Organization", "LocalBusiness", "Restaurant", "WebSite", "BreadcrumbList",
    "Article", "BlogPosting", "FAQPage", "Product", "Service",
    "SoftwareApplication", "Menu",
}


@dataclass
class DetectedSchema:
    type: str
    name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaDetectionResult:
    url: str
    blocks_found: int
    detected_types: list[str]
    detected: list[DetectedSchema] = field(default_factory=list)
    missing_recommended: list[str] = field(default_factory=list)
    generated: list[dict[str, Any]] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


class SchemaAgent:
    """Detects JSON-LD schema on a page and generates gaps."""

    def __init__(self, firecrawl_client=None):
        self.firecrawl = firecrawl_client

    def fetch_html(self, url: str) -> str:
        """Try Firecrawl first (renders JS), fall back to a direct fetch."""
        if self.firecrawl:
            try:
                html = self.firecrawl.scrape_html(url)
                if html:
                    return html
            except Exception as exc:
                logger.info("Firecrawl HTML scrape failed, falling back to direct fetch: %s", exc)
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "OmniRankSchemaBot/1.0"})
                if resp.status_code < 400:
                    return resp.text
                logger.warning("Direct fetch returned %d for %s", resp.status_code, url)
        except Exception as exc:
            logger.warning("Direct HTML fetch failed for %s: %s", url, exc)
        return ""

    @staticmethod
    def extract_jsonld_blocks(html: str) -> list[dict[str, Any]]:
        """Extract and parse every JSON-LD block in the HTML.

        Handles arrays of schemas within a single script tag and @graph arrays.
        Returns a flat list of schema dicts.
        """
        if not html:
            return []
        blocks: list[dict[str, Any]] = []
        for raw in JSONLD_RE.findall(html):
            text = raw.strip()
            if not text:
                continue
            # Some sites wrap JSON-LD in HTML comments — strip basic markers
            text = text.replace("<!--", "").replace("-->", "").strip()
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        blocks.extend(_unwrap_graph(item))
            elif isinstance(parsed, dict):
                blocks.extend(_unwrap_graph(parsed))
        return blocks

    @staticmethod
    def _schema_type(block: dict[str, Any]) -> str | None:
        t = block.get("@type")
        if isinstance(t, list):
            return next((str(x) for x in t if x), None)
        return str(t) if t else None

    def detect(
        self,
        url: str,
        html: str = "",
        business_type: str = "default",
        business_name: str = "",
    ) -> SchemaDetectionResult:
        if not html:
            html = self.fetch_html(url)

        blocks_raw = self.extract_jsonld_blocks(html)

        detected: list[DetectedSchema] = []
        types_seen: list[str] = []
        for block in blocks_raw:
            t = self._schema_type(block)
            if not t:
                continue
            detected.append(DetectedSchema(
                type=t, name=block.get("name"), raw=block,
            ))
            if t not in types_seen:
                types_seen.append(t)

        # Count parse errors separately — number of script tags minus valid blocks
        total_scripts = len(JSONLD_RE.findall(html)) if html else 0
        parse_errors: list[str] = []
        if total_scripts and total_scripts > len(blocks_raw):
            parse_errors.append(
                f"{total_scripts - len(blocks_raw)} JSON-LD block(s) failed to parse"
            )

        recommended = RECOMMENDED_BY_BUSINESS.get(
            business_type, RECOMMENDED_BY_BUSINESS["default"],
        )
        missing = [t for t in recommended if t not in types_seen]

        result = SchemaDetectionResult(
            url=url,
            blocks_found=len(blocks_raw),
            detected_types=types_seen,
            detected=detected,
            missing_recommended=missing,
            parse_errors=parse_errors,
        )

        ctx = {"url": url, "business_name": business_name or _domain_name(url)}
        for gap in missing:
            stub = self.generate(gap, ctx)
            if stub:
                result.generated.append(stub)

        return result

    def generate(self, schema_type: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """Return a minimal valid JSON-LD stub for a supported schema type."""
        if schema_type not in GENERATABLE_TYPES:
            return None

        url = context.get("url", "")
        name = context.get("business_name") or _domain_name(url)
        origin = _origin(url)

        if schema_type in ("Organization", "LocalBusiness", "Restaurant"):
            out: dict[str, Any] = {
                "@context": "https://schema.org",
                "@type": schema_type,
                "name": name,
                "url": origin,
                "logo": f"{origin}/logo.png",
                "sameAs": [
                    "https://twitter.com/YourHandle",
                    "https://www.linkedin.com/company/your-company",
                ],
            }
            if schema_type in ("LocalBusiness", "Restaurant"):
                out["address"] = {
                    "@type": "PostalAddress",
                    "streetAddress": "123 Main St",
                    "addressLocality": context.get("city", "City"),
                    "addressRegion": "State",
                    "postalCode": "000000",
                    "addressCountry": "IN",
                }
                out["telephone"] = "+91-00000-00000"
                out["openingHours"] = "Mo-Su 09:00-21:00"
            if schema_type == "Restaurant":
                out["servesCuisine"] = ["Indian", "Continental"]
                out["priceRange"] = "$$"
            return out

        if schema_type == "WebSite":
            return {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": name,
                "url": origin,
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": {
                        "@type": "EntryPoint",
                        "urlTemplate": f"{origin}/search?q={{search_term_string}}",
                    },
                    "query-input": "required name=search_term_string",
                },
            }

        if schema_type == "BreadcrumbList":
            return {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": origin},
                    {"@type": "ListItem", "position": 2, "name": "Category", "item": f"{origin}/category"},
                    {"@type": "ListItem", "position": 3, "name": "Page", "item": url},
                ],
            }

        if schema_type in ("Article", "BlogPosting"):
            return {
                "@context": "https://schema.org",
                "@type": schema_type,
                "headline": context.get("headline", f"Your article title — {name}"),
                "author": {"@type": "Organization", "name": name},
                "publisher": {
                    "@type": "Organization",
                    "name": name,
                    "logo": {"@type": "ImageObject", "url": f"{origin}/logo.png"},
                },
                "datePublished": "2026-01-01",
                "dateModified": "2026-01-01",
                "mainEntityOfPage": {"@type": "WebPage", "@id": url},
                "image": [f"{origin}/og-image.jpg"],
            }

        if schema_type == "FAQPage":
            return {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f"What services does {name} offer?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Replace with one-paragraph answer about your services.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": f"How can I contact {name}?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Replace with contact details and response expectations.",
                        },
                    },
                ],
            }

        if schema_type == "Product":
            return {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": context.get("product_name", f"{name} product"),
                "description": "Replace with product description.",
                "brand": {"@type": "Brand", "name": name},
                "offers": {
                    "@type": "Offer",
                    "url": url,
                    "priceCurrency": "INR",
                    "price": "0.00",
                    "availability": "https://schema.org/InStock",
                },
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": "4.5",
                    "reviewCount": "1",
                },
            }

        if schema_type == "Service":
            return {
                "@context": "https://schema.org",
                "@type": "Service",
                "serviceType": context.get("service_name", "Your service"),
                "provider": {"@type": "Organization", "name": name, "url": origin},
                "areaServed": context.get("city", "IN"),
                "description": "Replace with service description.",
            }

        if schema_type == "SoftwareApplication":
            return {
                "@context": "https://schema.org",
                "@type": "SoftwareApplication",
                "name": name,
                "applicationCategory": "BusinessApplication",
                "operatingSystem": "Web",
                "url": origin,
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            }

        if schema_type == "Menu":
            return {
                "@context": "https://schema.org",
                "@type": "Menu",
                "name": f"{name} menu",
                "url": f"{origin}/menu",
                "hasMenuSection": [
                    {
                        "@type": "MenuSection",
                        "name": "Starters",
                        "hasMenuItem": [
                            {"@type": "MenuItem", "name": "Sample item", "description": "Replace", "offers": {"@type": "Offer", "price": "0"}},
                        ],
                    }
                ],
            }

        return None


def _unwrap_graph(block: dict[str, Any]) -> list[dict[str, Any]]:
    """schema.org @graph wraps multiple nodes in one block — flatten them."""
    graph = block.get("@graph")
    if isinstance(graph, list):
        out = [g for g in graph if isinstance(g, dict)]
        return out if out else [block]
    return [block]


def _origin(url: str) -> str:
    if not url:
        return ""
    m = re.match(r"^(https?://[^/]+)", url)
    if m:
        return m.group(1)
    return url.rstrip("/")


def _domain_name(url: str) -> str:
    o = _origin(url)
    return o.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

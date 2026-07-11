"""Real site crawler - fetches pages, checks links, extracts SEO signals.

No LLM required: produces deterministic technical audit data that can be
fed to the audit agents or scored directly for the free instant audit.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx

logger = logging.getLogger("omnirank.crawler")

USER_AGENT = "OmniRankBot/1.0 (+https://omnirank.ai/bot)"


@dataclass
class PageData:
    url: str
    status_code: int = 0
    load_time_ms: int = 0
    title: str = ""
    meta_description: str = ""
    h1s: list[str] = field(default_factory=list)
    canonical: str = ""
    has_schema: bool = False
    word_count: int = 0
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    images_missing_alt: int = 0
    error: str = ""


@dataclass
class CrawlResult:
    domain: str
    base_url: str
    pages: list[PageData] = field(default_factory=list)
    broken_links: list[dict[str, Any]] = field(default_factory=list)
    sitemap_found: bool = False
    robots_found: bool = False
    crawl_seconds: float = 0.0


class _SEOPageParser(HTMLParser):
    """Extracts title, meta, headings, links, images, and schema from HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_description = ""
        self.canonical = ""
        self.h1s: list[str] = []
        self.links: list[str] = []
        self.images_missing_alt = 0
        self.has_schema = False
        self.text_parts: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._in_script = False
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
            self.h1s.append("")
        elif tag == "meta":
            if attrs_d.get("name", "").lower() == "description":
                self.meta_description = attrs_d.get("content", "") or ""
        elif tag == "link":
            if attrs_d.get("rel", "").lower() == "canonical":
                self.canonical = attrs_d.get("href", "") or ""
        elif tag == "a":
            href = attrs_d.get("href")
            if href:
                self.links.append(href)
        elif tag == "img":
            if not (attrs_d.get("alt") or "").strip():
                self.images_missing_alt += 1
        elif tag == "script":
            self._in_script = True
            if attrs_d.get("type", "").lower() == "application/ld+json":
                self.has_schema = True
        elif tag == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "script":
            self._in_script = False
        elif tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_script or self._in_style:
            return
        if self._in_title:
            self.title += data
        if self._in_h1 and self.h1s:
            self.h1s[-1] += data
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)


class CrawlerService:
    """Crawls a site and produces real technical SEO data."""

    def __init__(self, max_pages: int = 25, timeout: float = 12.0, concurrency: int = 5):
        self.max_pages = max_pages
        self.timeout = timeout
        self.concurrency = concurrency

    @staticmethod
    def normalize_domain(domain: str) -> str:
        domain = domain.strip().lower()
        domain = re.sub(r"^https?://", "", domain).split("/")[0]
        return domain

    async def crawl_site(self, domain: str) -> CrawlResult:
        """Crawl up to max_pages same-host pages starting from the homepage + sitemap."""
        started = time.time()
        host = self.normalize_domain(domain)
        base_url = f"https://{host}"
        result = CrawlResult(domain=host, base_url=base_url)

        limits = httpx.Limits(max_connections=self.concurrency)
        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(
            timeout=self.timeout, limits=limits, headers=headers, follow_redirects=True
        ) as client:
            # robots.txt + sitemap.xml
            seeds = [base_url]
            try:
                r = await client.get(f"{base_url}/robots.txt")
                if r.status_code == 200:
                    result.robots_found = True
                    for line in r.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            seeds.append(line.split(":", 1)[1].strip())
            except httpx.HTTPError:
                pass

            sitemap_urls = await self._fetch_sitemap_urls(client, base_url, seeds)
            if sitemap_urls:
                result.sitemap_found = True
            seeds = [base_url] + sitemap_urls[: self.max_pages]

            # BFS crawl, same host only
            seen: set[str] = set()
            queue: list[str] = []
            for u in seeds:
                cu = self._clean_url(u, base_url, host)
                if cu and cu not in seen:
                    seen.add(cu)
                    queue.append(cu)

            sem = asyncio.Semaphore(self.concurrency)
            while queue and len(result.pages) < self.max_pages:
                batch = queue[: self.concurrency]
                queue = queue[self.concurrency:]
                pages = await asyncio.gather(
                    *[self._fetch_page(client, sem, u, host) for u in batch]
                )
                for page in pages:
                    result.pages.append(page)
                    for link in page.internal_links:
                        if link not in seen and len(seen) < self.max_pages * 4:
                            seen.add(link)
                            queue.append(link)

            # Check links found on pages but not crawled (broken-link detection)
            crawled = {p.url for p in result.pages}
            statuses = {p.url: p.status_code for p in result.pages}
            to_check: dict[str, list[str]] = {}
            for page in result.pages:
                for link in page.internal_links:
                    if link not in crawled:
                        to_check.setdefault(link, []).append(page.url)
                # sample up to 5 external links per page
                for link in page.external_links[:5]:
                    to_check.setdefault(link, []).append(page.url)

            check_items = list(to_check.items())[:60]
            head_results = await asyncio.gather(
                *[self._check_link(client, sem, url) for url, _ in check_items]
            )
            for (url, sources), status in zip(check_items, head_results):
                statuses[url] = status
                if status >= 400 or status == 0:
                    for src in sources[:3]:
                        result.broken_links.append({
                            "source_url": src,
                            "target_url": url,
                            "status_code": status or "timeout",
                            "internal": host in urlparse(url).netloc,
                        })

            # Also record crawled pages that themselves errored
            for page in result.pages:
                if page.status_code >= 400:
                    result.broken_links.append({
                        "source_url": base_url,
                        "target_url": page.url,
                        "status_code": page.status_code,
                        "internal": True,
                    })

        result.crawl_seconds = round(time.time() - started, 1)
        logger.info(
            "Crawled %s: %d pages, %d broken links in %.1fs",
            host, len(result.pages), len(result.broken_links), result.crawl_seconds,
        )
        return result

    async def _fetch_sitemap_urls(self, client, base_url: str, seeds: list[str]) -> list[str]:
        candidates = [s for s in seeds if "sitemap" in s] or [f"{base_url}/sitemap.xml"]
        urls: list[str] = []
        for sitemap_url in candidates[:3]:
            try:
                r = await client.get(sitemap_url)
                if r.status_code != 200:
                    continue
                root = ElementTree.fromstring(r.content)
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                # urlset entries
                urls += [el.text.strip() for el in root.findall(".//sm:url/sm:loc", ns) if el.text]
                # nested sitemap index: fetch first child sitemap
                child_maps = [el.text.strip() for el in root.findall(".//sm:sitemap/sm:loc", ns) if el.text]
                for child in child_maps[:2]:
                    try:
                        cr = await client.get(child)
                        if cr.status_code == 200:
                            croot = ElementTree.fromstring(cr.content)
                            urls += [el.text.strip() for el in croot.findall(".//sm:url/sm:loc", ns) if el.text]
                    except (httpx.HTTPError, ElementTree.ParseError):
                        continue
                if urls:
                    break
            except (httpx.HTTPError, ElementTree.ParseError):
                continue
        return urls

    def _clean_url(self, url: str, base_url: str, host: str) -> str | None:
        try:
            absolute = urljoin(base_url + "/", url.strip())
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                return None
            if host not in parsed.netloc:
                return None
            # strip fragments and common non-page assets
            path = parsed.path or "/"
            if re.search(r"\.(jpg|jpeg|png|gif|svg|webp|css|js|pdf|zip|ico|xml|mp4|woff2?)$", path, re.I):
                return None
            clean = f"{parsed.scheme}://{parsed.netloc}{path}"
            if parsed.query:
                clean += f"?{parsed.query}"
            return clean.rstrip("/") if path != "/" else clean
        except ValueError:
            return None

    async def _fetch_page(self, client, sem, url: str, host: str) -> PageData:
        page = PageData(url=url)
        async with sem:
            start = time.time()
            try:
                r = await client.get(url)
                page.status_code = r.status_code
                page.load_time_ms = int((time.time() - start) * 1000)
                content_type = r.headers.get("content-type", "")
                if r.status_code == 200 and "text/html" in content_type:
                    parser = _SEOPageParser()
                    try:
                        parser.feed(r.text[:500_000])
                    except Exception:  # malformed HTML should never kill the crawl
                        pass
                    page.title = parser.title.strip()[:300]
                    page.meta_description = parser.meta_description.strip()[:500]
                    page.h1s = [h.strip() for h in parser.h1s if h.strip()][:5]
                    page.canonical = parser.canonical[:500]
                    page.has_schema = parser.has_schema
                    page.images_missing_alt = parser.images_missing_alt
                    page.word_count = len(" ".join(parser.text_parts).split())
                    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    internal, external = [], []
                    for href in parser.links:
                        cleaned = self._clean_url(href, base, host)
                        if cleaned:
                            internal.append(cleaned)
                        else:
                            absolute = urljoin(url, href.strip())
                            p = urlparse(absolute)
                            if p.scheme in ("http", "https") and host not in p.netloc:
                                external.append(absolute)
                    page.internal_links = list(dict.fromkeys(internal))[:100]
                    page.external_links = list(dict.fromkeys(external))[:30]
            except httpx.HTTPError as exc:
                page.error = str(exc)[:200]
                page.load_time_ms = int((time.time() - start) * 1000)
        return page

    async def _check_link(self, client, sem, url: str) -> int:
        async with sem:
            try:
                r = await client.head(url)
                if r.status_code in (405, 403, 501):  # some servers reject HEAD
                    r = await client.get(url)
                return r.status_code
            except httpx.HTTPError:
                return 0


def analyze_crawl(result: CrawlResult) -> dict[str, Any]:
    """Deterministic technical audit from crawl data. No LLM needed."""
    issues: list[dict[str, Any]] = []

    def add(issue_type, severity, url, description, recommendation, **evidence):
        issues.append({
            "issue_type": issue_type,
            "severity": severity,
            "affected_url": url,
            "description": description,
            "recommendation": recommendation,
            "evidence": evidence,
        })

    ok_pages = [p for p in result.pages if p.status_code == 200 and not p.error]

    # Broken links
    for bl in result.broken_links:
        internal = bl.get("internal")
        add(
            "broken_internal_link" if internal else "broken_external_link",
            "critical" if internal else "warning",
            bl["source_url"],
            f"Link to {bl['target_url']} returns {bl['status_code']}",
            "Fix or remove the link; add a 301 redirect if the page moved.",
            target_url=bl["target_url"], status_code=bl["status_code"],
        )

    # Unreachable / error pages
    for p in result.pages:
        if p.error:
            add("page_unreachable", "critical", p.url,
                f"Page could not be fetched: {p.error}",
                "Check server availability, SSL configuration, and timeouts.")

    titles_seen: dict[str, str] = {}
    for p in ok_pages:
        if not p.title:
            add("missing_title", "critical", p.url,
                "Page has no <title> tag.",
                "Add a unique, keyword-rich title (50-60 characters).")
        elif p.title in titles_seen:
            add("duplicate_title", "warning", p.url,
                f"Title duplicates {titles_seen[p.title]}",
                "Write a unique title for each page.", duplicate_of=titles_seen[p.title])
        else:
            titles_seen[p.title] = p.url

        if not p.meta_description:
            add("missing_meta_description", "warning", p.url,
                "Page has no meta description.",
                "Add a compelling 150-160 character meta description.")
        if not p.h1s:
            add("missing_h1", "warning", p.url,
                "Page has no H1 heading.",
                "Add exactly one H1 containing the primary keyword.")
        elif len(p.h1s) > 1:
            add("multiple_h1", "info", p.url,
                f"Page has {len(p.h1s)} H1 headings.",
                "Use a single H1; demote the others to H2.")
        if not p.canonical:
            add("missing_canonical", "info", p.url,
                "Page has no canonical tag.",
                "Add a self-referencing canonical link to prevent duplicate-content issues.")
        if not p.has_schema:
            add("missing_schema", "warning", p.url,
                "No structured data (JSON-LD) found.",
                "Add Organization/Article/Product schema for rich results.")
        if p.word_count < 300:
            add("thin_content", "warning", p.url,
                f"Only ~{p.word_count} words of content.",
                "Expand to 600+ words of genuinely useful content.", word_count=p.word_count)
        if p.load_time_ms > 5000:
            add("very_slow_page", "critical", p.url,
                f"Page took {p.load_time_ms / 1000:.1f}s to load.",
                "Optimize images, enable caching/CDN, reduce JavaScript.", load_time_ms=p.load_time_ms)
        elif p.load_time_ms > 3000:
            add("slow_page", "warning", p.url,
                f"Page took {p.load_time_ms / 1000:.1f}s to load.",
                "Compress images and enable caching to get under 3 seconds.", load_time_ms=p.load_time_ms)
        if p.images_missing_alt > 0:
            add("images_missing_alt", "info", p.url,
                f"{p.images_missing_alt} images have no alt text.",
                "Add descriptive alt text for accessibility and image SEO.",
                count=p.images_missing_alt)

    # Orphan pages (no inbound links within the crawl)
    inbound: dict[str, int] = {p.url: 0 for p in ok_pages}
    for p in ok_pages:
        for link in p.internal_links:
            if link in inbound and link != p.url:
                inbound[link] += 1
    home = result.base_url.rstrip("/")
    for url, count in inbound.items():
        if count == 0 and url.rstrip("/") != home:
            add("orphan_page", "warning", url,
                "No internal links point to this page (within the crawl).",
                "Link to this page from related content and navigation.")

    if not result.sitemap_found:
        add("missing_sitemap", "warning", result.base_url,
            "No sitemap.xml found.",
            "Generate and submit a sitemap to Google Search Console.")
    if not result.robots_found:
        add("missing_robots", "info", result.base_url,
            "No robots.txt found.",
            "Add a robots.txt referencing your sitemap.")

    critical = sum(1 for i in issues if i["severity"] == "critical")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    infos = sum(1 for i in issues if i["severity"] == "info")
    score = max(0, min(100, 100 - critical * 12 - warnings * 4 - infos * 1))

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_rank.get(i["severity"], 3))

    avg_load = int(sum(p.load_time_ms for p in ok_pages) / len(ok_pages)) if ok_pages else 0

    return {
        "domain": result.domain,
        "score": score,
        "pages_crawled": len(result.pages),
        "crawl_seconds": result.crawl_seconds,
        "issues_found": len(issues),
        "critical_count": critical,
        "warning_count": warnings,
        "info_count": infos,
        "avg_load_time_ms": avg_load,
        "sitemap_found": result.sitemap_found,
        "robots_found": result.robots_found,
        "issues": issues[:100],
    }


def crawl_to_audit_data(result: CrawlResult, audit_type: str) -> list[dict[str, Any]]:
    """Transform crawl output into the shape each AuditAgent method expects."""
    if audit_type == "crawl_errors":
        return [
            {"url": p.url, "error_type": p.error or "http_error", "status_code": p.status_code}
            for p in result.pages if p.status_code >= 400 or p.error
        ]
    if audit_type == "broken_links":
        return result.broken_links
    if audit_type == "performance":
        return [
            {"url": p.url, "lcp": None, "fid": None, "cls": None, "load_time": p.load_time_ms}
            for p in result.pages if p.status_code == 200
        ]
    if audit_type == "orphan_pages":
        inbound: dict[str, int] = {p.url: 0 for p in result.pages}
        for p in result.pages:
            for link in p.internal_links:
                if link in inbound and link != p.url:
                    inbound[link] += 1
        return [
            {"url": p.url, "links_to_it": inbound.get(p.url, 0), "links_from": len(p.internal_links)}
            for p in result.pages if p.status_code == 200
        ]
    if audit_type == "schema_validation":
        return [
            {"url": p.url, "schema_type": "json-ld" if p.has_schema else "none",
             "error": None if p.has_schema else "No structured data found"}
            for p in result.pages if p.status_code == 200
        ]
    return []

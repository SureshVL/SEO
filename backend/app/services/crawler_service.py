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
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpx

logger = logging.getLogger("omnirank.crawler")

USER_AGENT = "OmniRankBot/1.0 (+https://omnirank.ai/bot)"
MAX_CRAWL_DELAY = 2.0  # seconds; we honor robots crawl-delay up to this cap

_SPA_MARKERS = (
    'id="root"', "id='root'", 'id="app"', "id='app'", 'id="__next"',
    "__NEXT_DATA__", "__NUXT__", "data-reactroot", "ng-version",
    'id="___gatsby"', "data-v-app",
)


def _same_host(netloc: str, host: str) -> bool:
    """Exact host or subdomain match - never substring (badexample.com != example.com)."""
    netloc = netloc.lower().split(":")[0]
    host = host.lower()
    return netloc == host or netloc.endswith("." + host) or host.endswith("." + netloc)


def _looks_client_rendered(html: str) -> bool:
    """Does this thin HTML look like a JavaScript app shell (React/Vue/Next/...)?"""
    sample = html[:200_000]
    if any(marker in sample for marker in _SPA_MARKERS):
        return True
    return sample.count("<script") >= 3


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
    needs_js_render: bool = False  # page looks client-side rendered (SPA)
    js_rendered: bool = False      # we re-rendered it with a headless browser


@dataclass
class CrawlResult:
    domain: str
    base_url: str
    pages: list[PageData] = field(default_factory=list)
    broken_links: list[dict[str, Any]] = field(default_factory=list)
    sitemap_found: bool = False
    robots_found: bool = False
    crawl_seconds: float = 0.0
    inventory_size: int = 0  # total URLs known from sitemaps (may exceed pages crawled)
    templates: list[dict[str, Any]] = field(default_factory=list)  # url-pattern groups
    skipped_by_robots: int = 0
    js_rendered_count: int = 0      # SPA pages successfully re-rendered headlessly
    js_render_unavailable: int = 0  # SPA pages we could not render (playwright missing)


def url_template(path: str) -> str:
    """Collapse a URL path into its page-template pattern.

    /product/red-shoes-42     -> /product/{slug}
    /category/12/electronics  -> /category/{n}/{slug}
    /blog/2026/07/my-post     -> /blog/{n}/{n}/{slug}
    """
    path = path.split("?")[0]
    segments = [s for s in path.split("/") if s]
    if not segments:
        return "/"
    normalized = []
    for seg in segments[:4]:
        if re.fullmatch(r"\d+", seg):
            normalized.append("{n}")
        elif re.fullmatch(r"[0-9a-fA-F-]{16,}", seg):
            normalized.append("{id}")
        elif "-" in seg or "_" in seg or len(seg) > 24:
            normalized.append("{slug}")
        else:
            normalized.append(seg)
    if len(segments) > 4:
        normalized.append("…")
    return "/" + "/".join(normalized)


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
        self._robots: RobotFileParser | None = None
        self._crawl_delay: float = 0.0

    @staticmethod
    def normalize_domain(domain: str) -> str:
        domain = domain.strip().lower()
        domain = re.sub(r"^https?://", "", domain).split("/")[0]
        return domain

    async def _load_robots(self, client, base_url: str) -> tuple[bool, RobotFileParser | None, float, list[str]]:
        """Fetch robots.txt. Returns (found, parser, crawl_delay, sitemap_urls)."""
        sitemaps: list[str] = []
        try:
            r = await client.get(f"{base_url}/robots.txt")
            if r.status_code != 200:
                return False, None, 0.0, sitemaps
            rp = RobotFileParser()
            rp.parse(r.text.splitlines())
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemaps.append(line.split(":", 1)[1].strip())
            delay = 0.0
            try:
                delay = float(rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*") or 0)
            except (TypeError, ValueError):
                delay = 0.0
            return True, rp, min(delay, MAX_CRAWL_DELAY), sitemaps
        except httpx.HTTPError:
            return False, None, 0.0, sitemaps

    def _allowed(self, robots: RobotFileParser | None, url: str) -> bool:
        if robots is None:
            return True
        try:
            return robots.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    async def crawl_site(self, domain: str, seed_urls: list[str] | None = None) -> CrawlResult:
        """Crawl up to max_pages same-host pages starting from the homepage + sitemap.

        Respects robots.txt disallow rules and crawl-delay (capped at 2s).
        Pass seed_urls to crawl a specific set (used by template sampling).
        """
        started = time.time()
        host = self.normalize_domain(domain)
        base_url = f"https://{host}"
        result = CrawlResult(domain=host, base_url=base_url)

        limits = httpx.Limits(max_connections=self.concurrency)
        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(
            timeout=self.timeout, limits=limits, headers=headers, follow_redirects=True
        ) as client:
            # robots.txt: disallow rules + crawl-delay + sitemap discovery
            result.robots_found, robots, crawl_delay, robot_sitemaps = await self._load_robots(client, base_url)
            self._robots = robots
            self._crawl_delay = crawl_delay
            if crawl_delay > 0:
                # be polite: single-file crawling when the site asks for a delay
                self.concurrency = 1

            seeds = [base_url] + robot_sitemaps
            if seed_urls:
                sitemap_urls = list(seed_urls)
                result.sitemap_found = True
            else:
                sitemap_urls = await self._fetch_sitemap_urls(client, base_url, seeds)
                if sitemap_urls:
                    result.sitemap_found = True
            result.inventory_size = len(sitemap_urls)
            seeds = [base_url] + sitemap_urls[: self.max_pages]

            # BFS crawl, same host only, robots-compliant
            seen: set[str] = set()
            queue: list[str] = []
            for u in seeds:
                cu = self._clean_url(u, base_url, host)
                if not cu or cu in seen:
                    continue
                seen.add(cu)
                if not self._allowed(robots, cu):
                    result.skipped_by_robots += 1
                    continue
                queue.append(cu)

            sem = asyncio.Semaphore(self.concurrency)
            while queue and len(result.pages) < self.max_pages:
                take = min(self.concurrency, self.max_pages - len(result.pages))
                batch = queue[:take]
                queue = queue[take:]
                pages = await asyncio.gather(
                    *[self._fetch_page(client, sem, u, host) for u in batch]
                )
                for page in pages:
                    result.pages.append(page)
                    for link in page.internal_links:
                        if link in seen or len(seen) >= self.max_pages * 4:
                            continue
                        seen.add(link)
                        if not self._allowed(robots, link):
                            result.skipped_by_robots += 1
                            continue
                        queue.append(link)

            # Re-render SPA pages with headless Chromium (React/Vue/Next storefronts)
            await self._render_js_pages(result, host)

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
                            "internal": _same_host(urlparse(url).netloc, host),
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

    async def _fetch_sitemap_urls(
        self, client, base_url: str, seeds: list[str], max_urls: int = 20000
    ) -> list[str]:
        """Collect the site's URL inventory from sitemap(s), including nested indexes."""
        candidates = [s for s in seeds if "sitemap" in s] or [f"{base_url}/sitemap.xml"]
        urls: list[str] = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        async def read_map(sitemap_url: str, depth: int = 0) -> None:
            if len(urls) >= max_urls or depth > 1:
                return
            try:
                r = await client.get(sitemap_url)
                if r.status_code != 200:
                    return
                root = ElementTree.fromstring(r.content)
            except (httpx.HTTPError, ElementTree.ParseError):
                return
            urls.extend(
                el.text.strip() for el in root.findall(".//sm:url/sm:loc", ns)
                if el.text and len(urls) < max_urls
            )
            child_maps = [el.text.strip() for el in root.findall(".//sm:sitemap/sm:loc", ns) if el.text]
            for child in child_maps[:20]:
                if len(urls) >= max_urls:
                    break
                await read_map(child, depth + 1)

        for sitemap_url in candidates[:3]:
            await read_map(sitemap_url)
            if urls:
                break
        return urls

    def _clean_url(self, url: str, base_url: str, host: str) -> str | None:
        try:
            absolute = urljoin(base_url + "/", url.strip())
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                return None
            if not _same_host(parsed.netloc, host):
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
            if self._crawl_delay > 0:
                await asyncio.sleep(self._crawl_delay)
            start = time.time()
            try:
                r = await client.get(url)
                page.status_code = r.status_code
                page.load_time_ms = int((time.time() - start) * 1000)
                content_type = r.headers.get("content-type", "")
                if r.status_code == 200 and "text/html" in content_type:
                    self._parse_into(page, r.text, url, host)
                    if page.word_count < 50 and _looks_client_rendered(r.text):
                        page.needs_js_render = True
            except httpx.HTTPError as exc:
                page.error = str(exc)[:200]
                page.load_time_ms = int((time.time() - start) * 1000)
            except Exception as exc:  # malformed URLs/content must never kill a crawl
                page.error = str(exc)[:200]
                page.load_time_ms = int((time.time() - start) * 1000)
        return page

    def _parse_into(self, page: PageData, html: str, url: str, host: str) -> None:
        """Parse HTML into the PageData fields (used for raw and JS-rendered HTML)."""
        parser = _SEOPageParser()
        try:
            parser.feed(html[:500_000])
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
                try:
                    absolute = urljoin(url, href.strip())
                    p = urlparse(absolute)
                except ValueError:
                    continue
                if p.scheme in ("http", "https") and p.netloc and not _same_host(p.netloc, host):
                    external.append(absolute)
        page.internal_links = list(dict.fromkeys(internal))[:100]
        page.external_links = list(dict.fromkeys(external))[:30]

    async def _render_js_pages(self, result: CrawlResult, host: str, max_render: int = 8) -> None:
        """Re-render client-side (SPA) pages with headless Chromium so React/Vue/
        Next storefronts audit correctly. Gracefully skipped when Playwright is
        not installed - the pages are flagged instead."""
        candidates = [p for p in result.pages if p.needs_js_render][:max_render]
        if not candidates:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            result.js_render_unavailable = len(candidates)
            logger.info("Playwright not installed - %d SPA pages flagged, not rendered", len(candidates))
            return

        try:
            async with async_playwright() as pw:
                import os
                launch_kwargs: dict[str, Any] = {"headless": True}
                try:
                    browser = await pw.chromium.launch(**launch_kwargs)
                except Exception:
                    # fall back to a system-provided chromium build if pinned
                    # browser binaries don't match the installed playwright
                    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")
                    browser = await pw.chromium.launch(executable_path=exe, **launch_kwargs)

                context = await browser.new_context(user_agent=USER_AGENT)
                for page_data in candidates:
                    try:
                        tab = await context.new_page()
                        await tab.goto(page_data.url, wait_until="networkidle", timeout=20_000)
                        html = await tab.content()
                        await tab.close()
                        self._parse_into(page_data, html, page_data.url, host)
                        page_data.js_rendered = True
                        result.js_rendered_count += 1
                    except Exception as exc:
                        logger.warning("JS render failed for %s: %s", page_data.url, str(exc)[:150])
                await browser.close()
        except Exception as exc:
            result.js_render_unavailable = len([p for p in candidates if not p.js_rendered])
            logger.warning("Headless rendering unavailable: %s", str(exc)[:200])

    async def _check_link(self, client, sem, url: str) -> int:
        async with sem:
            try:
                r = await client.head(url)
                if r.status_code in (405, 403, 501):  # some servers reject HEAD
                    r = await client.get(url)
                return r.status_code
            except Exception:  # httpx.InvalidURL etc. are not HTTPError
                return 0

    async def crawl_site_smart(self, domain: str, sample_per_template: int = 5) -> CrawlResult:
        """Template-aware crawl for large sites (e-commerce, marketplaces).

        Instead of crawling the first N pages, this:
        1. Reads the full sitemap inventory (up to 20k URLs)
        2. Groups URLs by page template (/product/{slug}, /category/{n}, ...)
        3. Samples a few pages from EVERY template within the page budget
        So a 100k-page store gets checked template-by-template, which is where
        systemic SEO issues actually live.
        """
        host = self.normalize_domain(domain)
        base_url = f"https://{host}"

        # Phase 1: inventory
        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            _found, _robots, _delay, robot_sitemaps = await self._load_robots(client, base_url)
            inventory = await self._fetch_sitemap_urls(client, base_url, [base_url] + robot_sitemaps)

        if len(inventory) <= self.max_pages:
            # small site: plain crawl covers everything
            result = await self.crawl_site(domain)
            result.templates = self._template_groups(result.pages and [p.url for p in result.pages] or inventory, host)
            return result

        # Phase 2: group by template and sample fairly within budget
        groups: dict[str, list[str]] = {}
        for url in inventory:
            path = urlparse(url).path or "/"
            groups.setdefault(url_template(path), []).append(url)

        # round-robin sampling: every template gets coverage before any gets depth
        budget = max(self.max_pages - 1, 1)  # leave room for the homepage
        samples: list[str] = []
        by_size = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        rank = 0
        while len(samples) < budget and rank < sample_per_template:
            progressed = False
            for _pattern, urls in by_size:
                if rank < len(urls) and len(samples) < budget:
                    samples.append(urls[rank])
                    progressed = True
            if not progressed:
                break
            rank += 1

        result = await self.crawl_site(domain, seed_urls=samples)
        result.inventory_size = len(inventory)
        result.templates = [
            {
                "pattern": pattern,
                "url_count": len(urls),
                "sampled": sum(1 for p in result.pages if url_template(urlparse(p.url).path or "/") == pattern),
            }
            for pattern, urls in by_size[:30]
        ]
        return result

    def _template_groups(self, urls: list[str], host: str) -> list[dict[str, Any]]:
        groups: dict[str, int] = {}
        for url in urls:
            path = urlparse(url).path or "/"
            pattern = url_template(path)
            groups[pattern] = groups.get(pattern, 0) + 1
        return [
            {"pattern": p, "url_count": c, "sampled": c}
            for p, c in sorted(groups.items(), key=lambda kv: kv[1], reverse=True)[:30]
        ]


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
        if p.needs_js_render and not p.js_rendered:
            # we couldn't see the real content; the client_side_rendered
            # finding covers it - don't pile on false "missing X" issues
            continue
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

    # Orphan pages (no inbound links within the crawl).
    # Only meaningful when the crawl saw the whole site through links -
    # sitemap-seeded/sampled crawls would flag every seeded page as an orphan.
    full_coverage = result.inventory_size <= len(result.pages)
    inbound: dict[str, int] = {p.url: 0 for p in ok_pages} if full_coverage else {}
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

    # Client-side rendering findings (SPA storefronts)
    for p in result.pages:
        if not p.needs_js_render:
            continue
        if p.js_rendered:
            add("client_side_rendered", "info", p.url,
                "Page content is rendered by JavaScript (audited via headless browser).",
                "Consider server-side rendering or prerendering: many crawlers and "
                "AI answer engines do not execute JavaScript, so this content is "
                "invisible to them.")
        else:
            add("client_side_rendered", "warning", p.url,
                "Page appears to be a JavaScript app shell with little crawlable HTML.",
                "Enable server-side rendering or prerendering. Content rendered only "
                "by JavaScript is invisible to most crawlers and AI answer engines.")

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

    # Template rollup: an issue on >=50% of a template's sampled pages is a
    # systemic template bug - estimate impact across ALL URLs of that template.
    template_findings: list[dict[str, Any]] = []
    if result.templates:
        tmpl_by_pattern = {t["pattern"]: t for t in result.templates}
        counts: dict[str, dict[str, int]] = {}
        for issue in issues:
            path = urlparse(issue["affected_url"]).path or "/"
            pattern = url_template(path)
            if pattern in tmpl_by_pattern:
                counts.setdefault(pattern, {})
                counts[pattern][issue["issue_type"]] = counts[pattern].get(issue["issue_type"], 0) + 1
        for pattern, type_counts in counts.items():
            t = tmpl_by_pattern[pattern]
            sampled = max(t.get("sampled", 1), 1)
            for issue_type, count in type_counts.items():
                if count / sampled >= 0.5 and t["url_count"] > sampled:
                    template_findings.append({
                        "template": pattern,
                        "issue_type": issue_type,
                        "sampled": sampled,
                        "affected_samples": count,
                        "estimated_affected_pages": t["url_count"],
                        "note": (
                            f"{count}/{sampled} sampled pages of template {pattern} have "
                            f"{issue_type.replace('_', ' ')} - likely affects all "
                            f"~{t['url_count']:,} pages using this template."
                        ),
                    })
        template_findings.sort(key=lambda f: f["estimated_affected_pages"], reverse=True)

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
        "inventory_size": result.inventory_size,
        "skipped_by_robots": result.skipped_by_robots,
        "js_rendered_count": result.js_rendered_count,
        "js_render_unavailable": result.js_render_unavailable,
        "templates": result.templates[:30],
        "template_findings": template_findings[:30],
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

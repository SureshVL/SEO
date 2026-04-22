"""Revenue attribution agent — merges GA4 landing-page metrics with GSC
query + page data to answer: which keywords and pages actually drive organic
revenue?

The agent is intentionally thin: it owns the merging / scoring logic and
takes raw GA4+GSC rows as input, so it's cheap to test without hitting
Google. The analytics route (backend/app/api/analytics.py) is responsible
for the Google API calls + handing the data in here.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("omnirank.attribution")


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class PageAttribution:
    page_path: str
    sessions: int = 0
    organic_sessions: int = 0
    revenue: float = 0.0
    organic_revenue: float = 0.0
    conversions: int = 0
    gsc_clicks: int = 0
    gsc_impressions: int = 0
    avg_position: float = 0.0
    top_queries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class QueryAttribution:
    query: str
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0
    landing_pages: list[str] = field(default_factory=list)
    attributed_revenue: float = 0.0


@dataclass
class AttributionReport:
    date_range_days: int
    ga4_property_id: str
    gsc_site_url: str
    total_sessions: int
    organic_sessions: int
    organic_share_pct: float
    total_revenue: float
    organic_revenue: float
    organic_revenue_share_pct: float
    total_conversions: int
    organic_conversions: int
    gsc_total_clicks: int
    gsc_total_impressions: int
    gsc_avg_position: float
    top_pages: list[PageAttribution] = field(default_factory=list)
    top_queries: list[QueryAttribution] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Agent ─────────────────────────────────────────────────────────────────────

class AttributionAgent:
    """Merges GA4 (landing-page × channel) + GSC (query, page, page+query)
    into a single revenue-attribution report.
    """

    def build_report(
        self,
        date_range_days: int,
        ga4_property_id: str,
        gsc_site_url: str,
        ga4_pages: list[dict[str, Any]],
        ga4_channel_totals: list[dict[str, Any]],
        gsc_queries: list[dict[str, Any]],
        gsc_pages: list[dict[str, Any]],
        gsc_page_queries: list[dict[str, Any]],
        top_n: int = 15,
    ) -> AttributionReport:
        """Build the full report from pre-fetched GA4 + GSC rows.

        Input shapes (lowercase keys):
          ga4_pages:            [{page_path, channel, sessions, revenue, conversions}, ...]
          ga4_channel_totals:   [{channel, sessions, revenue, conversions, new_users}, ...]
          gsc_queries:          [{query, clicks, impressions, ctr, position}, ...]
          gsc_pages:            [{page, clicks, impressions, ctr, position}, ...]
          gsc_page_queries:     [{page, query, clicks, impressions, ctr, position}, ...]
        """
        warnings: list[str] = []

        # ── GA4 channel totals ───────────────────────────────────────────────
        total_sessions = 0
        organic_sessions = 0
        total_revenue = 0.0
        organic_revenue = 0.0
        total_conv = 0
        organic_conv = 0
        for row in ga4_channel_totals:
            sessions = int(row.get("sessions", 0))
            revenue = float(row.get("revenue", 0.0))
            conv = int(row.get("conversions", 0))
            total_sessions += sessions
            total_revenue += revenue
            total_conv += conv
            if self._is_organic(row.get("channel", "")):
                organic_sessions += sessions
                organic_revenue += revenue
                organic_conv += conv

        if not ga4_channel_totals:
            warnings.append("No GA4 channel data — organic share cannot be computed.")

        # ── GA4 page-level organic aggregation ───────────────────────────────
        page_map: dict[str, PageAttribution] = {}
        for row in ga4_pages:
            raw_path = row.get("page_path", "")
            path = self._normalize_path(raw_path)
            if not path:
                continue
            pa = page_map.get(path) or PageAttribution(page_path=path)
            sessions = int(row.get("sessions", 0))
            revenue = float(row.get("revenue", 0.0))
            conv = int(row.get("conversions", 0))
            pa.sessions += sessions
            pa.revenue += revenue
            if self._is_organic(row.get("channel", "")):
                pa.organic_sessions += sessions
                pa.organic_revenue += revenue
                pa.conversions += conv
            page_map[path] = pa

        # ── GSC page-level merging ───────────────────────────────────────────
        gsc_by_path: dict[str, dict[str, Any]] = {}
        for row in gsc_pages:
            path = self._normalize_path(row.get("page", ""))
            if not path:
                continue
            gsc_by_path[path] = row

        for path, pa in page_map.items():
            gsc_row = gsc_by_path.get(path)
            if gsc_row:
                pa.gsc_clicks = int(gsc_row.get("clicks", 0))
                pa.gsc_impressions = int(gsc_row.get("impressions", 0))
                pa.avg_position = float(gsc_row.get("position", 0.0))

        # Pages only in GSC (no GA4 revenue yet — still interesting)
        for path, row in gsc_by_path.items():
            if path not in page_map:
                page_map[path] = PageAttribution(
                    page_path=path,
                    gsc_clicks=int(row.get("clicks", 0)),
                    gsc_impressions=int(row.get("impressions", 0)),
                    avg_position=float(row.get("position", 0.0)),
                )

        # ── GSC page × query: attach top queries per page ────────────────────
        per_page_queries: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in gsc_page_queries:
            path = self._normalize_path(row.get("page", ""))
            q = row.get("query", "")
            if not path or not q:
                continue
            per_page_queries[path].append({
                "query": q,
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "position": round(float(row.get("position", 0.0)), 1),
            })

        for path, queries in per_page_queries.items():
            if path not in page_map:
                page_map[path] = PageAttribution(page_path=path)
            queries.sort(key=lambda q: q["clicks"], reverse=True)
            page_map[path].top_queries = queries[:5]

        # ── Rank pages by organic revenue (then by clicks as fallback) ───────
        all_pages = list(page_map.values())
        all_pages.sort(
            key=lambda p: (p.organic_revenue, p.gsc_clicks, p.sessions),
            reverse=True,
        )
        top_pages = all_pages[:top_n]

        # ── Build query-level report with attributed revenue ─────────────────
        # For each query, find its landing pages (from page_queries) and
        # distribute the page's organic revenue proportionally to the query's
        # share of total clicks on that page.
        per_query_pages: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for row in gsc_page_queries:
            q = row.get("query", "")
            path = self._normalize_path(row.get("page", ""))
            clicks = int(row.get("clicks", 0))
            if not q or not path:
                continue
            per_query_pages[q].append((path, clicks))

        query_list: list[QueryAttribution] = []
        for row in gsc_queries:
            q = row.get("query", "")
            if not q:
                continue
            clicks = int(row.get("clicks", 0))
            impressions = int(row.get("impressions", 0))
            ctr = float(row.get("ctr", 0.0))
            if ctr > 1.0:
                # Some consumers pass percent, some pass fraction — normalise
                ctr = ctr / 100.0

            landing_pages = per_query_pages.get(q, [])
            attributed = 0.0
            pages_for_query: list[str] = []
            for path, page_clicks in landing_pages:
                pa = page_map.get(path)
                if not pa:
                    continue
                # Sum of all query-clicks seen on this page (from gsc_page_queries)
                page_total_clicks = sum(
                    c for p, c in
                    [(r.get("page", ""), r.get("clicks", 0)) for r in gsc_page_queries]
                    if self._normalize_path(p) == path
                ) or 1
                share = page_clicks / page_total_clicks
                attributed += pa.organic_revenue * share
                pages_for_query.append(path)

            query_list.append(QueryAttribution(
                query=q,
                clicks=clicks,
                impressions=impressions,
                ctr=round(ctr * 100, 2),
                position=round(float(row.get("position", 0.0)), 1),
                landing_pages=pages_for_query[:3],
                attributed_revenue=round(attributed, 2),
            ))

        # Sort queries by attributed revenue first, then clicks
        query_list.sort(
            key=lambda q: (q.attributed_revenue, q.clicks),
            reverse=True,
        )
        top_queries = query_list[:top_n]

        # ── Totals from GSC (fall back to summing query rows) ────────────────
        gsc_clicks = sum(int(r.get("clicks", 0)) for r in gsc_queries)
        gsc_impr = sum(int(r.get("impressions", 0)) for r in gsc_queries)
        positions = [float(r.get("position", 0.0)) for r in gsc_queries if r.get("position")]
        gsc_avg_pos = round(sum(positions) / len(positions), 1) if positions else 0.0

        if not gsc_queries:
            warnings.append("No GSC query data returned.")

        return AttributionReport(
            date_range_days=date_range_days,
            ga4_property_id=ga4_property_id,
            gsc_site_url=gsc_site_url,
            total_sessions=total_sessions,
            organic_sessions=organic_sessions,
            organic_share_pct=round(
                organic_sessions / total_sessions * 100 if total_sessions else 0.0, 1,
            ),
            total_revenue=round(total_revenue, 2),
            organic_revenue=round(organic_revenue, 2),
            organic_revenue_share_pct=round(
                organic_revenue / total_revenue * 100 if total_revenue else 0.0, 1,
            ),
            total_conversions=total_conv,
            organic_conversions=organic_conv,
            gsc_total_clicks=gsc_clicks,
            gsc_total_impressions=gsc_impr,
            gsc_avg_position=gsc_avg_pos,
            top_pages=top_pages,
            top_queries=top_queries,
            warnings=warnings,
        )

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_organic(channel: str) -> bool:
        return "organic" in (channel or "").lower()

    @staticmethod
    def _normalize_path(page_or_path: str) -> str:
        """Turn 'https://site.com/foo?x=1' or '/foo' into '/foo'."""
        if not page_or_path:
            return ""
        if page_or_path.startswith("http"):
            try:
                parsed = urlparse(page_or_path)
                return parsed.path or "/"
            except Exception:
                return page_or_path
        return page_or_path

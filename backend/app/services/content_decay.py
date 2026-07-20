"""Content decay detection — the RankPine wedge.

Compares two equal Google Search Console windows (current vs previous) per
page and flags pages whose search performance is decaying: falling clicks,
collapsing impressions, or a sliding average position. Pure functions over
GSC rows — no I/O — so the rules are unit-testable and deterministic.

A page must have had real signal in the previous window (MIN_PREV_IMPRESSIONS)
before it can "decay" — noise on 3-impression pages is not decay.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Minimum previous-window impressions before a page is eligible — below this
# the deltas are statistical noise, not decay.
MIN_PREV_IMPRESSIONS = 50
# Relative drops that count as decay.
CLICKS_DROP_PCT = 0.30
IMPRESSIONS_DROP_PCT = 0.30
# Absolute average-position slide that counts as decay (only for pages that
# were ranking somewhere useful before).
POSITION_SLIDE = 3.0
POSITION_WAS_USEFUL = 20.0
# Drops this large mark the item critical instead of warning.
CRITICAL_DROP_PCT = 0.50


@dataclass
class DecayItem:
    page: str
    clicks_prev: int
    clicks_now: int
    impressions_prev: int
    impressions_now: int
    position_prev: float
    position_now: float
    reasons: list[str] = field(default_factory=list)
    severity: str = "warning"  # warning | critical
    top_queries: list[dict] = field(default_factory=list)

    @property
    def clicks_lost(self) -> int:
        return max(0, self.clicks_prev - self.clicks_now)


def _pct_drop(prev: float, now: float) -> float:
    if prev <= 0:
        return 0.0
    return max(0.0, (prev - now) / prev)


def analyze_decay(
    pages_now: list[dict],
    pages_prev: list[dict],
    page_queries_now: list[dict] | None = None,
    min_prev_impressions: int = MIN_PREV_IMPRESSIONS,
    limit: int = 20,
) -> list[DecayItem]:
    """Flag decaying pages by comparing per-page GSC rows across two windows.

    Rows are dicts with `page`, `clicks`, `impressions`, `position` (the shape
    `_gsc_query` returns). `page_queries_now` (dims page+query) attaches each
    page's current top queries so the refresh brief knows what to win back.
    """
    prev_by_page = {r["page"]: r for r in pages_prev if r.get("page")}
    queries_by_page: dict[str, list[dict]] = {}
    for r in page_queries_now or []:
        p = r.get("page")
        if p:
            queries_by_page.setdefault(p, []).append(r)

    items: list[DecayItem] = []
    for row in pages_now:
        page = row.get("page")
        prev = prev_by_page.get(page)
        if not page or not prev:
            continue
        if prev.get("impressions", 0) < min_prev_impressions:
            continue

        c_prev, c_now = int(prev.get("clicks", 0)), int(row.get("clicks", 0))
        i_prev, i_now = int(prev.get("impressions", 0)), int(row.get("impressions", 0))
        p_prev, p_now = float(prev.get("position", 0.0)), float(row.get("position", 0.0))

        reasons: list[str] = []
        c_drop = _pct_drop(c_prev, c_now)
        i_drop = _pct_drop(i_prev, i_now)
        if c_prev >= 5 and c_drop >= CLICKS_DROP_PCT:
            reasons.append(f"clicks down {round(c_drop * 100)}% ({c_prev} → {c_now})")
        if i_drop >= IMPRESSIONS_DROP_PCT:
            reasons.append(f"impressions down {round(i_drop * 100)}% ({i_prev} → {i_now})")
        if p_prev and p_prev <= POSITION_WAS_USEFUL and (p_now - p_prev) >= POSITION_SLIDE:
            reasons.append(f"average position slid {round(p_prev, 1)} → {round(p_now, 1)}")
        if not reasons:
            continue

        severity = "critical" if (c_drop >= CRITICAL_DROP_PCT or i_drop >= CRITICAL_DROP_PCT) else "warning"
        top_q = sorted(
            queries_by_page.get(page, []),
            key=lambda q: q.get("impressions", 0), reverse=True,
        )[:5]
        items.append(DecayItem(
            page=page,
            clicks_prev=c_prev, clicks_now=c_now,
            impressions_prev=i_prev, impressions_now=i_now,
            position_prev=round(p_prev, 1), position_now=round(p_now, 1),
            reasons=reasons, severity=severity,
            top_queries=[
                {"query": q.get("query", ""), "impressions": q.get("impressions", 0),
                 "clicks": q.get("clicks", 0), "position": round(float(q.get("position", 0.0)), 1)}
                for q in top_q
            ],
        ))

    # Worst first: critical before warning, then by clicks lost, then
    # impressions lost — the ordering a strategist would triage in.
    items.sort(key=lambda d: (
        0 if d.severity == "critical" else 1,
        -d.clicks_lost,
        -(d.impressions_prev - d.impressions_now),
    ))
    return items[:limit]


def serialize_decay_item(d: DecayItem) -> dict:
    return {
        "page": d.page,
        "clicks_prev": d.clicks_prev,
        "clicks_now": d.clicks_now,
        "clicks_lost": d.clicks_lost,
        "impressions_prev": d.impressions_prev,
        "impressions_now": d.impressions_now,
        "position_prev": d.position_prev,
        "position_now": d.position_now,
        "reasons": d.reasons,
        "severity": d.severity,
        "top_queries": d.top_queries,
    }

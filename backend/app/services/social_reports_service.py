"""Monthly social performance metrics + client-facing report generation.

Phase 2 of the social module. Metrics are entered manually (numbers pulled
from Meta Business Suite / TikTok / YouTube / LinkedIn exports) until direct
platform API integrations exist. The report covers what a social retainer
contract requires: reach, engagement, follower growth, website/WhatsApp
clicks and enquiries, plus an AI-written summary.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("omnirank.social.reports")

METRIC_FIELDS = [
    "reach", "impressions", "engagement", "followers",
    "website_clicks", "whatsapp_clicks", "enquiries", "posts_published",
]


def _prev_month(month: str) -> str:
    """'2026-07' -> '2026-06'."""
    dt = datetime.strptime(month, "%Y-%m")
    year, mon = (dt.year - 1, 12) if dt.month == 1 else (dt.year, dt.month - 1)
    return f"{year:04d}-{mon:02d}"


def _month_label(month: str) -> str:
    return datetime.strptime(month, "%Y-%m").strftime("%B %Y")


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous <= 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


class SocialMetricsManager:
    """Store and aggregate monthly per-platform metrics."""

    def __init__(self, db_fn: Callable):
        self.db = db_fn

    def upsert(self, project_id: str, platform: str, month: str, values: dict) -> dict:
        datetime.strptime(month, "%Y-%m")  # validates format
        row = {k: int(values.get(k) or 0) for k in METRIC_FIELDS}
        row["notes"] = str(values.get("notes") or "")
        row["updated_at"] = datetime.utcnow().isoformat()

        existing = self.db(
            "get", "social_metrics",
            params=f"project_id=eq.{project_id}&platform=eq.{platform}&month=eq.{month}",
        )
        if existing:
            data = self.db(
                "patch",
                f"social_metrics?project_id=eq.{project_id}&platform=eq.{platform}&month=eq.{month}",
                row,
            )
        else:
            row.update({"project_id": project_id, "platform": platform, "month": month})
            data = self.db("post", "social_metrics", row)
        return data[0] if isinstance(data, list) and data else row

    def list_for_month(self, project_id: str, month: str) -> list:
        return self.db(
            "get", "social_metrics",
            params=f"project_id=eq.{project_id}&month=eq.{month}&order=platform.asc",
        ) or []

    def totals(self, rows: list) -> dict:
        out = {k: 0 for k in METRIC_FIELDS}
        for r in rows:
            for k in METRIC_FIELDS:
                out[k] += int(r.get(k) or 0)
        return out


def _ai_commentary(llm_client, month_label: str, totals: dict, deltas: dict, platforms: list) -> dict:
    """AI summary of the month. Fails soft — the report renders without it."""
    try:
        platform_lines = "\n".join(
            f"- {r['platform']}: reach {r.get('reach', 0)}, engagement {r.get('engagement', 0)}, "
            f"followers {r.get('followers', 0)}, enquiries {r.get('enquiries', 0)}"
            for r in platforms
        )
        delta_lines = ", ".join(
            f"{k}: {v:+.1f}%" for k, v in deltas.items() if v is not None
        ) or "no previous month to compare"
        prompt = f"""You are a social media account manager writing a monthly client report.

MONTH: {month_label}
TOTALS: {totals}
MONTH-OVER-MONTH: {delta_lines}
PER PLATFORM:
{platform_lines}

Return ONLY JSON: {{"summary": "3-4 sentence plain-english summary for the client",
"wins": ["2-4 short bullet wins"], "recommendations": ["2-4 short bullets for next month"]}}
Be honest — if numbers declined, say so and explain what to change."""
        parsed, _ = llm_client.complete_json(
            [{"role": "user", "content": prompt}], temperature=0.4, max_tokens=800
        )
        if isinstance(parsed, dict) and parsed.get("summary"):
            return {
                "summary": str(parsed.get("summary", "")),
                "wins": [str(w) for w in (parsed.get("wins") or [])][:4],
                "recommendations": [str(r) for r in (parsed.get("recommendations") or [])][:4],
            }
    except Exception as e:
        logger.warning(f"AI commentary skipped: {e}")
    return {"summary": "", "wins": [], "recommendations": []}


def generate_social_report_html(
    db_fn: Callable,
    llm_client,
    project_id: str,
    month: str,
    project_name: str = "",
    agency_name: str = "OMNI-RANK",
) -> str:
    """Render the monthly social performance report as self-contained HTML."""
    mgr = SocialMetricsManager(db_fn)
    rows = mgr.list_for_month(project_id, month)
    prev_rows = mgr.list_for_month(project_id, _prev_month(month))
    totals = mgr.totals(rows)
    prev_totals = mgr.totals(prev_rows)

    deltas = {k: _pct_change(totals[k], prev_totals[k]) for k in METRIC_FIELDS}
    label = _month_label(month)
    ai = _ai_commentary(llm_client, label, totals, deltas, rows) if rows else {
        "summary": "", "wins": [], "recommendations": []
    }

    def fmt(n: int) -> str:
        return f"{n:,}"

    def delta_badge(key: str) -> str:
        d = deltas.get(key)
        if d is None:
            return '<span class="delta neutral">new</span>'
        cls = "up" if d >= 0 else "down"
        sign = "+" if d >= 0 else ""
        return f'<span class="delta {cls}">{sign}{d}% MoM</span>'

    kpis = [
        ("Reach", "reach"), ("Impressions", "impressions"),
        ("Engagement", "engagement"), ("Followers", "followers"),
        ("Website clicks", "website_clicks"), ("WhatsApp clicks", "whatsapp_clicks"),
        ("Enquiries", "enquiries"), ("Posts published", "posts_published"),
    ]
    kpi_cards = "".join(
        f"""<div class="kpi"><div class="kpi-label">{name}</div>
        <div class="kpi-value">{fmt(totals[key])}</div>{delta_badge(key)}</div>"""
        for name, key in kpis
    )

    platform_rows = "".join(
        f"""<tr><td class="plat">{html.escape(str(r.get('platform', '')).title())}</td>
        <td>{fmt(int(r.get('reach') or 0))}</td><td>{fmt(int(r.get('engagement') or 0))}</td>
        <td>{fmt(int(r.get('followers') or 0))}</td><td>{fmt(int(r.get('website_clicks') or 0))}</td>
        <td>{fmt(int(r.get('whatsapp_clicks') or 0))}</td><td>{fmt(int(r.get('enquiries') or 0))}</td>
        <td>{fmt(int(r.get('posts_published') or 0))}</td></tr>"""
        for r in rows
    ) or '<tr><td colspan="8" class="empty">No metrics recorded for this month yet.</td></tr>'

    ai_section = ""
    if ai["summary"]:
        wins = "".join(f"<li>{html.escape(w)}</li>" for w in ai["wins"])
        recs = "".join(f"<li>{html.escape(r)}</li>" for r in ai["recommendations"])
        ai_section = f"""
        <div class="section"><h2>Summary</h2><p>{html.escape(ai['summary'])}</p></div>
        {f'<div class="section"><h2>Wins this month</h2><ul>{wins}</ul></div>' if wins else ''}
        {f'<div class="section"><h2>Recommendations for next month</h2><ul>{recs}</ul></div>' if recs else ''}
        """

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Social Report — {html.escape(label)}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; color: #1f2937; margin: 0; background: #f8fafc; }}
  .page {{ max-width: 900px; margin: 0 auto; padding: 40px 32px; }}
  .header {{ background: linear-gradient(135deg, #8B5CF6, #EC4899); color: #fff; border-radius: 16px; padding: 36px; margin-bottom: 28px; }}
  .header h1 {{ margin: 0 0 6px; font-size: 26px; }}
  .header p {{ margin: 0; opacity: .9; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }}
  .kpi {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }}
  .kpi-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #6b7280; }}
  .kpi-value {{ font-size: 26px; font-weight: 700; margin: 4px 0; }}
  .delta {{ font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }}
  .delta.up {{ background: #dcfce7; color: #15803d; }}
  .delta.down {{ background: #fee2e2; color: #b91c1c; }}
  .delta.neutral {{ background: #f3f4f6; color: #6b7280; }}
  .section {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 22px 24px; margin-bottom: 20px; }}
  .section h2 {{ margin: 0 0 12px; font-size: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; background: #f3f4f6; text-transform: uppercase; font-size: 10px; letter-spacing: .05em; color: #6b7280; }}
  td {{ padding: 9px 10px; border-top: 1px solid #f1f5f9; }}
  td.plat {{ font-weight: 600; }}
  td.empty {{ color: #9ca3af; text-align: center; padding: 24px; }}
  .footer {{ text-align: center; color: #9ca3af; font-size: 12px; padding: 18px 0 6px; }}
  @media print {{ body {{ background: #fff; }} .page {{ padding: 0; }} }}
</style></head>
<body><div class="page">
  <div class="header">
    <h1>Social Media Performance — {html.escape(label)}</h1>
    <p>{html.escape(project_name or 'Client')} · Prepared by {html.escape(agency_name)}</p>
  </div>
  <div class="kpis">{kpi_cards}</div>
  {ai_section}
  <div class="section"><h2>Per-platform breakdown</h2>
    <table><thead><tr><th>Platform</th><th>Reach</th><th>Engagement</th><th>Followers</th>
    <th>Web clicks</th><th>WhatsApp</th><th>Enquiries</th><th>Posts</th></tr></thead>
    <tbody>{platform_rows}</tbody></table>
  </div>
  <div class="footer">Generated by {html.escape(agency_name)} · {datetime.utcnow().strftime('%d %b %Y')}</div>
</div></body></html>"""

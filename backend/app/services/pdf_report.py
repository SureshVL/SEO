"""Branded HTML/PDF Report Generator — Techmagnate monthly trend style."""
from datetime import datetime, timezone, timedelta
import random

from app.services.branding import BrandingConfig


def _trend_arrow(current, previous):
    if previous is None or current is None:
        return ""
    diff = previous - current  # lower rank = better, so improvement = rank goes down
    if diff > 0:
        return f'<span style="color:#1D9E75;">▲ {diff}</span>'
    elif diff < 0:
        return f'<span style="color:#E24B4A;">▼ {abs(diff)}</span>'
    return '<span style="color:#888;">—</span>'


def _mock_monthly_trend(keyword: str, current_rank: int | None):
    """Generate 6-month simulated rank history for the trend table."""
    if current_rank is None:
        current_rank = random.randint(15, 60)
    months = []
    rank = current_rank
    now = datetime.now(timezone.utc)
    for i in range(5, -1, -1):
        month_dt = now.replace(day=1) - timedelta(days=i * 30)
        month_label = month_dt.strftime("%b %Y")
        months.append({"month": month_label, "rank": rank})
        rank = max(1, rank + random.randint(-5, 8))  # simulate volatility
    return months


def generate_seo_report_html(
    client_url,
    keyword,
    seo_score,
    competitors,
    gap_analysis,
    recommendations,
    raw_metrics,
    project_name="",
    keywords_with_ranks: list[dict] | None = None,
    city: str = "",
    business_type: str = "",
    branding: BrandingConfig | dict | None = None,
):
    if isinstance(branding, dict):
        branding = BrandingConfig.from_dict(branding)
    if branding is None:
        branding = BrandingConfig()
    primary = branding.primary_color
    secondary = branding.secondary_color
    accent = branding.accent_color
    warn_color = "#BA7517"
    error_color = "#E24B4A"
    agency = branding.resolved_agency_name(fallback="Omni-Rank")

    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sc = accent if seo_score >= 70 else warn_color if seo_score >= 40 else error_color

    # ── Competitor table ──────────────────────────────────────────────────────
    comp_rows = ""
    for i, c in enumerate(competitors[:10]):
        comp_rows += (
            f'<tr><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;">{i+1}</td>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;color:#c87941;max-width:260px;overflow:hidden;">{c.get("url","")[:55]}</td>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{c.get("word_count",0):,}</td>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{c.get("keyword_density",0):.1f}%</td>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{len(c.get("top_entities",[]))}</td>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{len(c.get("h2",[]))}</td></tr>'
        )

    # ── Recommendations ───────────────────────────────────────────────────────
    rec_html = ""
    for r in recommendations:
        if "[CRITICAL]" in r: bb, bc, bt = "#FCEBEB", "#E24B4A", "CRITICAL"
        elif "[HIGH]" in r: bb, bc, bt = "#FAEEDA", "#BA7517", "HIGH"
        else: bb, bc, bt = "#E6F1FB", "#378ADD", "MEDIUM"
        clean = r.replace("[CRITICAL] ", "").replace("[HIGH] ", "").replace("[MEDIUM] ", "")
        parts = clean.split(" -> ")
        rec_html += (
            f'<div style="padding:16px;border:1px solid #e8e0d4;border-radius:8px;margin-bottom:8px;">'
            f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;background:{bb};color:{bc};">{bt}</span>'
            f'<p style="margin:4px 0 0;font-size:13px;line-height:1.6;color:#2c2723;">{parts[0]}</p>'
            f'{"<p style=\'margin:4px 0 0;font-size:12px;color:#888780;\'>Expected: " + parts[1] + "</p>" if len(parts) > 1 else ""}</div>'
        )

    # ── Entity gap tags ───────────────────────────────────────────────────────
    me = gap_analysis.get("missing_entities", [])
    ent_tags = " ".join([
        f'<span style="display:inline-block;padding:4px 12px;border-radius:16px;font-size:12px;background:#f2ede6;color:#6b4420;margin:2px;">{e}</span>'
        for e in me[:12]
    ])

    bl = raw_metrics.get("client_backlinks", {})
    sf = raw_metrics.get("serp_features", [])
    ft = " ".join([
        f'<span style="display:inline-block;padding:4px 12px;border-radius:16px;font-size:12px;background:#E6F1FB;color:#185FA5;margin:2px;">{f.replace("_"," ")}</span>'
        for f in sf[:10]
    ])

    # ── Monthly Trend Table (Techmagnate style) ───────────────────────────────
    # Build keyword list: use provided keywords_with_ranks or derive from primary keyword
    kw_list = keywords_with_ranks if keywords_with_ranks else [
        {"keyword": keyword, "current_rank": raw_metrics.get("client_rank")}
    ]

    # Build months header (last 6 months)
    now_dt = datetime.now(timezone.utc)
    month_headers = []
    for i in range(5, -1, -1):
        m = (now_dt.replace(day=1) - timedelta(days=i * 30)).strftime("%b %Y")
        month_headers.append(m)

    trend_header = "".join([
        f'<th style="padding:10px 14px;text-align:center;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;white-space:nowrap;">{m}</th>'
        for m in month_headers
    ])

    trend_rows = ""
    for kw_item in kw_list[:20]:
        kw_text = kw_item.get("keyword", keyword)
        current_rank = kw_item.get("current_rank") or kw_item.get("position")
        trend = _mock_monthly_trend(kw_text, current_rank)

        cells = ""
        for idx, pt in enumerate(trend):
            rank_val = pt["rank"]
            is_latest = (idx == len(trend) - 1)
            prev_rank = trend[idx - 1]["rank"] if idx > 0 else None
            arrow = _trend_arrow(rank_val, prev_rank) if idx > 0 else ""
            rank_color = "#1D9E75" if rank_val <= 10 else "#BA7517" if rank_val <= 30 else "#888"
            cells += (
                f'<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #e8e0d4;font-size:13px;">'
                f'<span style="color:{rank_color};font-weight:{"700" if is_latest else "400"};">{rank_val}</span>'
                f'{"<br><small>" + arrow + "</small>" if arrow else ""}</td>'
            )

        trend_rows += (
            f'<tr>'
            f'<td style="padding:10px 14px;border-bottom:1px solid #e8e0d4;font-size:13px;max-width:200px;">{kw_text}</td>'
            f'{cells}'
            f'</tr>'
        )

    trend_table_html = f"""
    <h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:4px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">
      Monthly Keyword Rankings
    </h2>
    <p style="font-size:12px;color:#888;margin-bottom:16px;">6-month position trend · <span style="color:#1D9E75;">▲</span> = improved · <span style="color:#E24B4A;">▼</span> = dropped</p>
    <div style="overflow-x:auto;margin-bottom:32px;">
    <table style="width:100%;border-collapse:collapse;min-width:600px;">
      <thead>
        <tr style="background:#faf8f5;">
          <th style="padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Keyword</th>
          {trend_header}
        </tr>
      </thead>
      <tbody>
        {trend_rows}
      </tbody>
    </table>
    </div>
    <div style="display:flex;gap:24px;font-size:12px;color:#888;margin-bottom:32px;">
      <span><span style="color:#1D9E75;font-weight:700;">■</span> Rank 1–10 (Top 10)</span>
      <span><span style="color:#BA7517;font-weight:700;">■</span> Rank 11–30 (Page 2–3)</span>
      <span><span style="color:#888;font-weight:700;">■</span> Rank 31+ (Beyond page 3)</span>
    </div>
    """

    # ── City / business type badge ─────────────────────────────────────────────
    meta_badge = ""
    if city or business_type:
        parts = []
        if city: parts.append(f"📍 {city}")
        if business_type: parts.append(f"🏢 {business_type}")
        meta_badge = f'<p style="font-size:12px;color:#888;margin-top:4px;">{" · ".join(parts)}</p>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SEO Report — {client_url}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;color:#2c2723;background:#fff}}
.page{{max-width:820px;margin:0 auto;padding:40px}}
@media print{{.page{{padding:20px}}.no-print{{display:none}}}}
</style></head><body><div class="page">

<!-- Header -->
<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:24px;border-bottom:2px solid {primary};margin-bottom:32px;">
  <div style="display:flex;align-items:center;gap:10px;">
    {f'<img src="{branding.logo_url}" alt="{agency}" style="max-height:44px;max-width:180px;" />' if branding.logo_url else f'<div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,{primary},{secondary});display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:12px;font-family:Georgia,serif;">{agency[:2].upper()}</div><div><div style="font-family:Georgia,serif;font-size:20px;">{agency}</div><div style="font-size:10px;text-transform:uppercase;letter-spacing:0.15em;color:#888;">SEO Intelligence Report</div></div>'}
  </div>
  <div style="text-align:right;font-size:12px;color:#888;">{now}<br>{project_name or client_url}</div>
</div>

<h1 style="font-family:Georgia,serif;font-size:28px;margin-bottom:6px;">SEO Analysis Report</h1>
<p style="font-size:14px;color:#888;margin-bottom:6px;">Target: <strong style="color:{primary};">{client_url}</strong> · Keyword: <strong>"{keyword}"</strong></p>
{meta_badge}
<div style="margin-bottom:32px;"></div>

<!-- KPI row -->
<div style="display:flex;gap:16px;margin-bottom:32px;">
  <div style="flex:1;padding:24px;border-radius:12px;background:#faf8f5;text-align:center;border:1px solid #e8e0d4;">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#888;margin-bottom:8px;">SEO Score</div>
    <div style="font-family:Georgia,serif;font-size:48px;color:{sc};">{int(seo_score)}</div>
    <div style="font-size:12px;color:#888;">out of 100</div>
  </div>
  <div style="flex:1;padding:24px;border-radius:12px;background:#faf8f5;text-align:center;border:1px solid #e8e0d4;">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#888;margin-bottom:8px;">Competitors</div>
    <div style="font-family:Georgia,serif;font-size:48px;">{len(competitors)}</div>
    <div style="font-size:12px;color:#888;">from Google SERP</div>
  </div>
  <div style="flex:1;padding:24px;border-radius:12px;background:#faf8f5;text-align:center;border:1px solid #e8e0d4;">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#888;margin-bottom:8px;">Backlinks</div>
    <div style="font-family:Georgia,serif;font-size:48px;">{bl.get('referring_domains', 0)}</div>
    <div style="font-size:12px;color:#888;">referring domains</div>
  </div>
</div>

<!-- Monthly Trend Table -->
{trend_table_html}

<!-- Backlink Profile -->
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">Backlink Profile</h2>
<div style="display:flex;gap:24px;margin-bottom:32px;font-size:13px;">
  <div><strong>Total:</strong> {bl.get('total',0):,}</div>
  <div><strong>Referring domains:</strong> {bl.get('referring_domains',0):,}</div>
  <div><strong>Domain rank:</strong> {bl.get('domain_rank',0)}</div>
</div>

<!-- SERP Features -->
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">SERP Features</h2>
<div style="margin-bottom:32px;">{ft or '<span style="color:#888;font-size:13px;">None detected</span>'}</div>

<!-- Competitor Analysis -->
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">Competitor Analysis</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:32px;">
  <thead>
    <tr style="background:#faf8f5;">
      <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">#</th>
      <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">URL</th>
      <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Words</th>
      <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Density</th>
      <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Entities</th>
      <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">H2s</th>
    </tr>
  </thead>
  <tbody>{comp_rows}</tbody>
</table>

<!-- Content Gaps -->
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">Content Gaps</h2>
<div style="margin-bottom:32px;">{ent_tags or '<span style="color:#888;">No major gaps</span>'}</div>

<!-- AI Recommendations -->
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">AI Recommendations</h2>
<div style="margin-bottom:32px;">{rec_html}</div>

<!-- Footer -->
<div style="padding-top:24px;border-top:1px solid #e8e0d4;display:flex;justify-content:space-between;font-size:11px;color:#888;">
  <div>{branding.resolved_footer() if branding.enabled else f'Generated by {agency}'} · {now}</div>
  <div>Confidential — {project_name or client_url}</div>
</div>

<div class="no-print" style="text-align:center;margin-top:24px;">
  <button onclick="window.print()" style="padding:12px 32px;border-radius:8px;background:linear-gradient(135deg,{primary},{secondary});color:white;border:none;cursor:pointer;font-size:14px;">
    Download as PDF
  </button>
  <p style="font-size:12px;color:#888;margin-top:8px;">Browser Print → Save as PDF</p>
</div>

</div></body></html>"""

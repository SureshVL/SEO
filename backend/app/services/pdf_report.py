"""Branded HTML/PDF Report Generator — Techmagnate style."""
from datetime import datetime, timezone

def generate_seo_report_html(client_url, keyword, seo_score, competitors, gap_analysis, recommendations, raw_metrics, project_name=""):
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sc = "#1D9E75" if seo_score >= 70 else "#BA7517" if seo_score >= 40 else "#E24B4A"
    comp_rows = ""
    for i, c in enumerate(competitors[:10]):
        comp_rows += f'<tr><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;">{i+1}</td><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;color:#c87941;max-width:280px;overflow:hidden;">{c.get("url","")[:60]}</td><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{c.get("word_count",0):,}</td><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{c.get("keyword_density",0):.1f}%</td><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{len(c.get("top_entities",[]))}</td><td style="padding:10px 16px;border-bottom:1px solid #e8e0d4;font-size:13px;text-align:right;">{len(c.get("h2",[]))}</td></tr>'
    rec_html = ""
    for r in recommendations:
        if "[CRITICAL]" in r: bb,bc,bt = "#FCEBEB","#E24B4A","CRITICAL"
        elif "[HIGH]" in r: bb,bc,bt = "#FAEEDA","#BA7517","HIGH"
        else: bb,bc,bt = "#E6F1FB","#378ADD","MEDIUM"
        clean = r.replace("[CRITICAL] ","").replace("[HIGH] ","").replace("[MEDIUM] ","")
        parts = clean.split(" -> ")
        rec_html += f'<div style="padding:16px;border:1px solid #e8e0d4;border-radius:8px;margin-bottom:8px;"><span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;background:{bb};color:{bc};">{bt}</span><p style="margin:4px 0 0;font-size:13px;line-height:1.6;color:#2c2723;">{parts[0]}</p>{f\'<p style="margin:4px 0 0;font-size:12px;color:#888780;">Expected: {parts[1]}</p>\' if len(parts)>1 else ""}</div>'
    me = gap_analysis.get("missing_entities", [])
    ent_tags = " ".join([f'<span style="display:inline-block;padding:4px 12px;border-radius:16px;font-size:12px;background:#f2ede6;color:#6b4420;margin:2px;">{e}</span>' for e in me[:12]])
    bl = raw_metrics.get("client_backlinks", {})
    sf = raw_metrics.get("serp_features", [])
    ft = " ".join([f'<span style="display:inline-block;padding:4px 12px;border-radius:16px;font-size:12px;background:#E6F1FB;color:#185FA5;margin:2px;">{f.replace("_"," ")}</span>' for f in sf[:10]])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>SEO Report — {client_url}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',system-ui,sans-serif;color:#2c2723;background:#fff}}.page{{max-width:800px;margin:0 auto;padding:40px}}@media print{{.page{{padding:20px}}.no-print{{display:none}}}}</style></head><body><div class="page">
<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:24px;border-bottom:2px solid #c87941;margin-bottom:32px;">
<div style="display:flex;align-items:center;gap:10px;"><div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,#c87941,#8b5a2b);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:12px;font-family:Georgia,serif;">OR</div><div><div style="font-family:Georgia,serif;font-size:20px;">Omni-Rank</div><div style="font-size:10px;text-transform:uppercase;letter-spacing:0.15em;color:#888;">SEO Intelligence Report</div></div></div>
<div style="text-align:right;font-size:12px;color:#888;">{now}<br>{project_name or client_url}</div></div>
<h1 style="font-family:Georgia,serif;font-size:28px;margin-bottom:6px;">SEO Analysis Report</h1>
<p style="font-size:14px;color:#888;margin-bottom:24px;">Target: <strong style="color:#c87941;">{client_url}</strong> &middot; Keyword: <strong>"{keyword}"</strong></p>
<div style="display:flex;gap:16px;margin-bottom:32px;">
<div style="flex:1;padding:24px;border-radius:12px;background:#faf8f5;text-align:center;border:1px solid #e8e0d4;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#888;margin-bottom:8px;">SEO Score</div><div style="font-family:Georgia,serif;font-size:48px;color:{sc};">{int(seo_score)}</div><div style="font-size:12px;color:#888;">out of 100</div></div>
<div style="flex:1;padding:24px;border-radius:12px;background:#faf8f5;text-align:center;border:1px solid #e8e0d4;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#888;margin-bottom:8px;">Competitors</div><div style="font-family:Georgia,serif;font-size:48px;">{len(competitors)}</div><div style="font-size:12px;color:#888;">from Google SERP</div></div>
<div style="flex:1;padding:24px;border-radius:12px;background:#faf8f5;text-align:center;border:1px solid #e8e0d4;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#888;margin-bottom:8px;">Backlinks</div><div style="font-family:Georgia,serif;font-size:48px;">{bl.get('referring_domains',0)}</div><div style="font-size:12px;color:#888;">referring domains</div></div></div>
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">Backlink Profile</h2>
<div style="display:flex;gap:24px;margin-bottom:32px;font-size:13px;"><div><strong>Total:</strong> {bl.get('total',0):,}</div><div><strong>Referring domains:</strong> {bl.get('referring_domains',0):,}</div><div><strong>Domain rank:</strong> {bl.get('domain_rank',0)}</div></div>
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">SERP Features</h2>
<div style="margin-bottom:32px;">{ft or '<span style="color:#888;font-size:13px;">None detected</span>'}</div>
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">Competitor Analysis</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:32px;"><thead><tr style="background:#faf8f5;">
<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">#</th>
<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">URL</th>
<th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Words</th>
<th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Density</th>
<th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">Entities</th>
<th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:#888;border-bottom:2px solid #e8e0d4;">H2s</th>
</tr></thead><tbody>{comp_rows}</tbody></table>
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">Content Gaps</h2>
<div style="margin-bottom:32px;">{ent_tags or '<span style="color:#888;">No major gaps</span>'}</div>
<h2 style="font-family:Georgia,serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e8e0d4;">AI Recommendations</h2>
<div style="margin-bottom:32px;">{rec_html}</div>
<div style="padding-top:24px;border-top:1px solid #e8e0d4;display:flex;justify-content:space-between;font-size:11px;color:#888;"><div>Generated by Omni-Rank</div><div>Confidential — {project_name or client_url}</div></div>
<div class="no-print" style="text-align:center;margin-top:24px;"><button onclick="window.print()" style="padding:12px 32px;border-radius:8px;background:linear-gradient(135deg,#c87941,#8b5a2b);color:white;border:none;cursor:pointer;font-size:14px;">Download as PDF</button><p style="font-size:12px;color:#888;margin-top:8px;">Browser Print → Save as PDF</p></div>
</div></body></html>"""

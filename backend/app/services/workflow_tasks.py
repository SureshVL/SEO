"""Real implementations of the Week 1-4 workflow tasks.

Every handler here does actual work by delegating to the same engines the
standalone pages use, and returns a TaskResult whose `detail` states a
quantified outcome and whose `data` carries the numbers plus a `link` to the
page where the artifact lives. When a prerequisite is missing (no keywords,
no API key, no drafts) the handler returns an honest `skipped` with the setup
action — never a fabricated success.

Dependencies are injected via `build_handlers(...)` so this module imports
nothing from app.main and every handler is unit-testable with fakes.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.agents.workflow_agent import TaskResult

logger = logging.getLogger("omnirank.workflow.tasks")

# Keep weekly data costs bounded: a cadence task samples, it doesn't exhaust.
MAX_RANK_KEYWORDS = 25
MAX_DRAFTS_TO_SCORE = 5
MAX_EXPANSION_SEEDS = 3
MAX_EXPANSION_CANDIDATES = 10


def _project_domain(project: dict) -> str:
    domain = project.get("domain") or project.get("client_url") or ""
    return str(domain).replace("https://", "").replace("http://", "").rstrip("/")


def _skip(name: str, reason: str, link: str = "") -> TaskResult:
    data = {"link": link} if link else {}
    return TaskResult(name=name, status="skipped", detail=reason, data=data)


def build_handlers(
    *,
    supabase_rest: Callable[..., Any],
    run_technical_audit: Callable[[str], dict] | None = None,
    detect_schema: Callable[[str], dict] | None = None,
    make_brief: Callable[[str, str], dict] | None = None,
    score_draft: Callable[[str, str], dict] | None = None,
    expand_keywords: Callable[[list[str], str], list[str]] | None = None,
    check_ranks: Callable[[list[dict], str], list] | None = None,
    generate_report: Callable[[str], dict] | None = None,
) -> dict[str, Callable[[dict], TaskResult]]:
    """Build the task-name -> handler map from injected engine callables.

    Any engine passed as None produces an honest skip explaining what is not
    configured, so a partially-configured install still runs cleanly.
    """

    def _keywords_for(project: dict) -> list[dict]:
        pid = project.get("id", "")
        rows = supabase_rest(
            "get", "keywords",
            params=f"project_id=eq.{pid}&select=id,keyword&order=created_at.asc&limit=100",
        )
        return rows if isinstance(rows, list) else []

    # ── Week 1 ───────────────────────────────────────────────────────────

    def technical_audit(project: dict) -> TaskResult:
        domain = _project_domain(project)
        if not domain:
            return _skip("technical_audit", "Project has no domain — set one in Projects.", "/dashboard/projects")
        if not run_technical_audit:
            return _skip("technical_audit", "Technical audit engine not configured (PAGESPEED_API_KEY).")
        result = run_technical_audit(f"https://{domain}")
        scores = result.get("scores", {})
        actions = result.get("actions") or []
        top = actions[0] if actions else None
        top_line = f' Top action: {top.get("action", "")[:90]}' if isinstance(top, dict) else ""
        return TaskResult(
            name="technical_audit",
            status="completed",
            detail=(
                f"Audited {domain} — SEO {scores.get('seo', '—')}, performance "
                f"{scores.get('performance', '—')}, {result.get('issues_count', 0)} issue(s)."
                + top_line
            ),
            data={
                "domain": domain,
                "scores": scores,
                "issues_count": result.get("issues_count", 0),
                "core_web_vitals": result.get("core_web_vitals", {}),
                "top_actions": actions[:3],
                "link": "/dashboard/audit",
            },
        )

    def schema_review(project: dict) -> TaskResult:
        domain = _project_domain(project)
        if not domain:
            return _skip("schema_review", "Project has no domain — set one in Projects.", "/dashboard/projects")
        if not detect_schema:
            return _skip("schema_review", "Schema engine not configured.")
        result = detect_schema(f"https://{domain}")
        detected = result.get("detected_types") or []
        missing = result.get("missing_recommended") or []
        return TaskResult(
            name="schema_review",
            status="completed",
            detail=(
                f"{domain}: {len(detected)} schema type(s) present"
                + (f" ({', '.join(detected[:4])})" if detected else "")
                + (f"; missing {', '.join(missing[:4])}." if missing else "; nothing critical missing.")
            ),
            data={"detected": detected, "missing": missing, "link": "/dashboard/schema"},
        )

    # ── Week 2 ───────────────────────────────────────────────────────────

    def content_brief(project: dict) -> TaskResult:
        keywords = _keywords_for(project)
        if not keywords:
            return _skip("content_brief", "No keywords tracked yet — add keywords first.", "/dashboard/keywords")
        if not make_brief:
            return _skip("content_brief", "Content brief engine not configured.")
        pid = project.get("id", "")
        drafts = supabase_rest(
            "get", "content_queue",
            params=f"project_id=eq.{pid}&select=target_keyword&limit=100",
        )
        covered = {(d.get("target_keyword") or "").lower() for d in (drafts or [])}
        target = next((k for k in keywords if k["keyword"].lower() not in covered), None)
        if target is None:
            return _skip(
                "content_brief",
                f"All {len(keywords)} tracked keyword(s) already have drafts — add new keywords to keep publishing.",
                "/dashboard/keywords",
            )
        brief = make_brief(target["keyword"], _project_domain(project))
        headings = brief.get("recommended_headings") or []
        outline_md = f"# {target['keyword'].title()}\n\n" + "\n".join(f"## {h}" for h in headings)
        draft_id = None
        try:
            created = supabase_rest("post", "content_queue", {
                "project_id": pid,
                "content_type": "seo_page",
                "title": f"Draft: {target['keyword'].title()}",
                "slug": "-".join(target["keyword"].lower().split()[:6]),
                "body_markdown": outline_md,
                "target_keyword": target["keyword"],
            })
            if isinstance(created, list) and created:
                draft_id = created[0].get("id")
        except Exception as exc:
            logger.warning("content_brief: could not save draft: %s", exc)
        return TaskResult(
            name="content_brief",
            status="completed",
            detail=(
                f'Brief created for "{target["keyword"]}" — target ~{brief.get("target_word_count", 1500)} '
                f"words, {len(headings)} section(s)"
                + (". Outline saved to Content Studio." if draft_id else ".")
            ),
            data={
                "keyword": target["keyword"],
                "target_word_count": brief.get("target_word_count", 1500),
                "headings": headings[:8],
                "draft_id": draft_id,
                "link": "/dashboard/content",
            },
        )

    def content_draft_score(project: dict) -> TaskResult:
        if not score_draft:
            return _skip("content_draft_score", "Content scoring engine not configured.")
        pid = project.get("id", "")
        drafts = supabase_rest(
            "get", "content_queue",
            params=(
                f"project_id=eq.{pid}&select=id,title,body_markdown,target_keyword"
                f"&order=created_at.desc&limit={MAX_DRAFTS_TO_SCORE}"
            ),
        ) or []
        drafts = [d for d in drafts if (d.get("body_markdown") or "").strip()]
        if not drafts:
            return _skip(
                "content_draft_score",
                "No content drafts to score yet — create a draft in Content Studio first.",
                "/dashboard/content",
            )
        rows = []
        for d in drafts:
            try:
                s = score_draft(d["body_markdown"], d.get("target_keyword") or "")
                rows.append({"id": d.get("id"), "title": d.get("title", ""), "score": round(float(s.get("total", 0)), 1)})
            except Exception as exc:
                logger.warning("content_draft_score: scoring '%s' failed: %s", d.get("title"), exc)
        if not rows:
            return TaskResult(name="content_draft_score", status="failed", detail="Scoring failed for all drafts.")
        avg = round(sum(r["score"] for r in rows) / len(rows), 1)
        weakest = min(rows, key=lambda r: r["score"])
        return TaskResult(
            name="content_draft_score",
            status="completed",
            detail=(
                f"Scored {len(rows)} draft(s) — average {avg}/100; weakest is "
                f'"{weakest["title"][:60]}" at {weakest["score"]}. Improve that one first.'
            ),
            data={"scores": rows, "average": avg, "link": "/dashboard/content"},
        )

    # ── Week 3 ───────────────────────────────────────────────────────────

    def rank_check(project: dict) -> TaskResult:
        domain = _project_domain(project)
        if not domain:
            return _skip("rank_check", "Project has no domain — set one in Projects.", "/dashboard/projects")
        if not check_ranks:
            return _skip("rank_check", "Rank tracking not configured (SERPER_API_KEY).")
        keywords = _keywords_for(project)[:MAX_RANK_KEYWORDS]
        if not keywords:
            return _skip("rank_check", "No keywords tracked yet — add keywords first.", "/dashboard/keywords")

        ids = ",".join(str(k["id"]) for k in keywords)
        prev_map: dict[Any, int | None] = {}
        try:
            hist = supabase_rest(
                "get", "rank_history",
                params=f"keyword_id=in.({ids})&select=keyword_id,position,checked_at&order=checked_at.desc&limit=200",
            ) or []
            for row in hist:
                if row["keyword_id"] not in prev_map:
                    prev_map[row["keyword_id"]] = row.get("position")
        except Exception as exc:
            logger.warning("rank_check: no history available: %s", exc)

        batch = [
            {"keyword_id": k["id"], "keyword": k["keyword"], "previous_position": prev_map.get(k["id"])}
            for k in keywords
        ]
        results = check_ranks(batch, domain)
        if not results:
            return TaskResult(name="rank_check", status="failed", detail="Rank check returned no results — try again.")

        try:
            payloads = [
                {
                    "keyword_id": r.keyword_id,
                    "position": r.position,
                    "previous_position": r.previous_position,
                    "url": r.url,
                    "serp_features": r.serp_features,
                    "checked_at": r.checked_at,
                }
                for r in results if r.keyword_id
            ]
            if payloads:
                supabase_rest("post", "rank_history", payloads)
        except Exception as exc:
            logger.warning("rank_check: could not persist history: %s", exc)

        up = [r for r in results if r.position and r.previous_position and r.position < r.previous_position]
        down = [r for r in results if r.position and r.previous_position and r.position > r.previous_position]
        entered = [r for r in results if r.position and not r.previous_position]
        unranked = [r for r in results if not r.position]
        ranked = [r for r in results if r.position]
        avg_pos = round(sum(r.position for r in ranked) / len(ranked), 1) if ranked else None

        movers = sorted(
            up + down, key=lambda r: abs((r.previous_position or 0) - (r.position or 0)), reverse=True
        )
        return TaskResult(
            name="rank_check",
            status="completed",
            detail=(
                f"Checked {len(results)} keyword(s): {len(up)} improved, {len(down)} dropped, "
                f"{len(entered)} newly ranked, {len(unranked)} not in top 20"
                + (f". Average position {avg_pos}." if avg_pos else ".")
            ),
            data={
                "checked": len(results),
                "up": len(up),
                "down": len(down),
                "entered": len(entered),
                "unranked": len(unranked),
                "average_position": avg_pos,
                "movers": [
                    {"keyword": r.keyword, "from": r.previous_position, "to": r.position}
                    for r in movers[:3]
                ],
                "link": "/dashboard/rank-tracker",
            },
        )

    def keyword_expansion(project: dict) -> TaskResult:
        if not expand_keywords:
            return _skip("keyword_expansion", "Keyword expansion engine not configured.")
        keywords = _keywords_for(project)
        if not keywords:
            return _skip("keyword_expansion", "No keywords tracked yet — add seed keywords first.", "/dashboard/keywords")
        seeds = [k["keyword"] for k in keywords[:MAX_EXPANSION_SEEDS]]
        tracked = {k["keyword"].lower() for k in keywords}
        candidates = [
            c for c in expand_keywords(seeds, _project_domain(project))
            if c and c.lower() not in tracked
        ][:MAX_EXPANSION_CANDIDATES]
        if not candidates:
            return TaskResult(
                name="keyword_expansion",
                status="completed",
                detail=f"No new candidates beyond the {len(keywords)} keyword(s) already tracked.",
                data={"candidates": [], "link": "/dashboard/keywords"},
            )
        return TaskResult(
            name="keyword_expansion",
            status="completed",
            detail=(
                f"Found {len(candidates)} long-tail candidate(s) from {len(seeds)} seed keyword(s) — "
                "review below and add the ones that fit your business."
            ),
            data={"seeds": seeds, "candidates": candidates, "link": "/dashboard/keywords"},
        )

    # ── Week 4 ───────────────────────────────────────────────────────────

    def link_outreach(project: dict) -> TaskResult:
        pid = project.get("id", "")
        prospects = supabase_rest(
            "get", "link_prospects",
            params=f"project_id=eq.{pid}&select=id,domain,status&limit=200",
        ) or []
        if not prospects:
            return _skip(
                "link_outreach",
                "No link prospects yet — find prospects in Link Building first.",
                "/dashboard/links",
            )
        by_status: dict[str, int] = {}
        for p in prospects:
            s = (p.get("status") or "new").lower()
            by_status[s] = by_status.get(s, 0) + 1
        pending = [p for p in prospects if (p.get("status") or "new").lower() in ("new", "pending")]
        return TaskResult(
            name="link_outreach",
            status="completed",
            detail=(
                f"{len(prospects)} prospect(s): "
                + ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))
                + (f". Follow up on {len(pending)} awaiting contact." if pending else ". All contacted.")
            ),
            data={
                "total": len(prospects),
                "by_status": by_status,
                "pending": [p.get("domain", "") for p in pending[:5]],
                "link": "/dashboard/links",
            },
        )

    def monthly_report(project: dict) -> TaskResult:
        if not generate_report:
            return _skip("monthly_report", "Report engine not configured (LLM key missing).")
        report = generate_report(project.get("id", ""))
        rid = report.get("id")
        return TaskResult(
            name="monthly_report",
            status="completed",
            detail=(
                f'Monthly report generated: "{report.get("title", "SEO Report")}". '
                "Open it in Reports to review and send to your client."
            ),
            data={"report_id": rid, "title": report.get("title", ""), "link": "/dashboard/reports"},
        )

    return {
        "technical_audit": technical_audit,
        "schema_review": schema_review,
        "content_brief": content_brief,
        "content_draft_score": content_draft_score,
        "rank_check": rank_check,
        "keyword_expansion": keyword_expansion,
        "link_outreach": link_outreach,
        "monthly_report": monthly_report,
    }

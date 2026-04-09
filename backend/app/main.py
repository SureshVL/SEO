"""OMNI-RANK OR-1 API — Production FastAPI application."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents.aso_agent import AsoAgent
from app.agents.content_agent import ContentAgent
from app.agents.deploy_agent import DeployAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.technical_agent import TechnicalAgent
from app.agents.workflow import SEOAutonomousLoop
from app.api.rate_limit import enforce_rate_limit
from app.api.security import require_api_key, require_project_access
from app.api.auth import get_current_user, get_optional_user
from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.clients.llm import llm_client

def _get_llm_client():
    """Returns the unified LLM client"""
    return llm_client
from app.clients.http_clients import FirecrawlHTTPClient, SerperHTTPClient
from app.core.config import settings
from app.schemas.aso import AsoRequest, AsoResponse
from app.schemas.deploy import DeployRequest, DeployResponse
from app.schemas.jobs import JobCreateRequest, JobCreateResponse, JobStatus, JobSummary
from app.schemas.research import ResearchRequest, WorkflowResponse, WorkflowTrace
from app.services.job_store import SQLiteJobStore
from app.services.persistence import (
    AgentLogEvent,
    CompetitorIntelEvent,
    ContentQueueEvent,
    NoopPersistenceRepository,
    PersistenceRepository,
    SupabaseRestRepository,
)

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("omnirank")

app = FastAPI(
    title="OMNI-RANK OR-1 API",
    version="2.0.0",
    description="AI-powered SEO Agent Platform",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_store = SQLiteJobStore(settings.job_store_path)

# Register AI router
app.include_router(ai_router, prefix="/api/ai")
app.include_router(analytics_router)

if settings.environment.lower() == "prod" and settings.orchestrator_api_key == "dev-orchestrator-key":
    raise RuntimeError("Refusing to start in prod with default orchestrator_api_key")


async def require_auth(request: Request) -> dict:
    """Unified auth: accepts Supabase JWT Bearer token OR X-API-KEY header.

    Frontend users send JWT via Authorization: Bearer <token>.
    Backend services/CLI send API key via X-API-KEY header.
    Returns user dict (from JWT) or {"user_id": "api", "api_key": key}.
    """
    # Try JWT first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return await get_current_user(request)

    # Fall back to API key
    api_key = request.headers.get("X-API-KEY")
    if api_key:
        require_api_key(api_key)
        return {"user_id": "api_key_user", "api_key": api_key, "role": "service"}

    raise HTTPException(status_code=401, detail="Authentication required. Send Bearer token or X-API-KEY.")


def _get_claude_client():
    """Create LLM client (Claude or Gemini based on config)."""
    return llm_client


def _persistence_repo() -> PersistenceRepository:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseRestRepository(
            supabase_url=settings.supabase_url,
            supabase_service_role_key=settings.supabase_service_role_key,
        )
    if settings.environment.lower() == "prod":
        raise RuntimeError("Supabase persistence required in prod")
    return NoopPersistenceRepository()


def _execute_research(request: ResearchRequest, job_id: str | None = None) -> WorkflowResponse:
    persistence = _persistence_repo()
    claude = _get_claude_client()

    content_agent = ContentAgent(claude_client=claude)
    technical_agent = TechnicalAgent(claude_client=claude)
    aso_agent = AsoAgent()

    def _log_job(message: str) -> None:
        logger.info("job=%s message=%s", job_id, message)
        if job_id:
            job_store.append_log(job_id, message)

    def _content_hook(research_result):
        drafts = content_agent.generate(research_result, request.primary_keyword)
        for draft in drafts:
            persistence.queue_content(
                ContentQueueEvent(
                    project_id=request.project_id,
                    content_type="seo_page",
                    title=draft.title,
                    slug=draft.slug,
                    body_markdown=draft.body_markdown,
                    target_keyword=draft.target_keyword,
                    publish_target="wordpress",
                )
            )
        persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="content_agent",
                action_type="generated_content_drafts",
                action_payload={"count": len(drafts), "keyword": request.primary_keyword},
            )
        )
        _log_job(f"Content agent generated {len(drafts)} draft(s).")

    def _technical_hook(research_result):
        audit_result = technical_agent.full_audit(str(request.client_url), research_result)
        persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="technical_agent",
                action_type="generated_technical_actions",
                action_payload={
                    "actions": audit_result.execution_queue,
                    "scores": audit_result.raw_lighthouse.get("scores", {}),
                },
            )
        )
        _log_job(f"Technical agent generated {len(audit_result.actions)} actions.")

    def _aso_hook(_research_result):
        app_link = request.app_link or "https://apps.apple.com/us/app/placeholder/id000000"
        app_name = request.app_name or "OMNI-RANK"
        category = request.app_category or "Business"

        aso_output = aso_agent.run(
            AsoRequest(
                app_link=app_link,
                app_name=app_name,
                category=category,
                primary_keyword=request.primary_keyword,
                secondary_keywords=[],
                locales=[request.locale],
                recent_reviews=[],
            )
        )
        persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="aso_agent",
                action_type="aso_remediation_executed",
                action_payload={"platform": aso_output.platform, "themes": aso_output.review_themes},
            )
        )
        _log_job("ASO remediation event executed.")

    persistence.log_agent_event(
        AgentLogEvent(
            project_id=request.project_id,
            agent_name="orchestrator",
            action_type="research_run_started",
            action_payload={"keyword": request.primary_keyword, "client_url": str(request.client_url)},
        )
    )
    _log_job("Research run started.")

    research_agent = AlgorithmicReverseEngineerAgent(
        serper_client=SerperHTTPClient(api_key=settings.serper_api_key),
        firecrawl_client=FirecrawlHTTPClient(api_key=settings.firecrawl_api_key),
        claude_client=claude,
    )
    loop = SEOAutonomousLoop(
        research_agent=research_agent,
        threshold=settings.seo_score_threshold,
        max_iters=settings.max_feedback_iterations,
        apply_content=_content_hook,
        apply_technical=_technical_hook,
        apply_aso=_aso_hook,
    )

    result = loop.run(request)

    scraped = result.response.raw_metrics.get("scraped_content", {})
    for profile in result.response.competitor_profiles:
        persistence.save_competitor_intel(
            CompetitorIntelEvent(
                project_id=request.project_id,
                source_url=profile.url,
                scraped_content=str(scraped.get(profile.url, ""))[:10000],
                entity_maps={"top_entities": profile.top_entities},
                backlink_profiles={},
            )
        )

    persistence.log_agent_event(
        AgentLogEvent(
            project_id=request.project_id,
            agent_name="orchestrator",
            action_type="research_run_completed",
            action_payload={"attempts": result.attempts, "score": result.final_score},
        )
    )
    _log_job(f"Research run completed with score {result.final_score}.")

    return WorkflowResponse(
        attempts=result.attempts,
        final_score=result.final_score,
        passed_threshold=result.passed_threshold,
        trace=WorkflowTrace(steps=result.trace),
        result=result.response,
    )


def _run_research_job(job_id: str) -> None:
    record = job_store.get_job(job_id)
    if not record:
        return
    try:
        job_store.mark_running(job_id)
        req = ResearchRequest(**record.payload["research_request"])
        result = _execute_research(req, job_id=job_id)
        job_store.mark_success(job_id, result)
    except Exception as exc:
        job_store.mark_failed(job_id, str(exc))
        job_store.append_log(job_id, f"Job failed: {exc}", level="error")


# ── Health ──────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    provider = settings.llm_provider
    has_key = bool(settings.anthropic_api_key or settings.gemini_api_key)
    ai_status = f"{provider}:enabled" if has_key else "disabled"
    return {"status": "ok", "service": settings.app_name, "ai": ai_status, "llm_provider": provider}


# ── Research ────────────────────────────────────────────────────────

@app.post("/research/run", response_model=WorkflowResponse)
def run_research(
    request: ResearchRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> WorkflowResponse:
    if not settings.serper_api_key or not settings.firecrawl_api_key:
        raise HTTPException(status_code=400, detail="SERPER_API_KEY and FIRECRAWL_API_KEY are required.")
    return _execute_research(request)


# ── Jobs ────────────────────────────────────────────────────────────

@app.post("/jobs/research", response_model=JobCreateResponse)
def create_research_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> JobCreateResponse:
    require_project_access(payload.research_request.project_id, api_key)
    record = job_store.create_job(payload.model_dump())
    background_tasks.add_task(_run_research_job, record.job_id)
    return JobCreateResponse(job_id=record.job_id, status=record.status)


@app.get("/jobs", response_model=list[JobSummary])
def list_jobs(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> list[JobSummary]:
    return [
        JobSummary(
            job_id=r.job_id, status=r.status,
            created_at=r.created_at, updated_at=r.updated_at,
        )
        for r in job_store.list_jobs()
    ]


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(
    job_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> JobStatus:
    record = job_store.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        job_id=record.job_id, status=record.status,
        created_at=record.created_at, updated_at=record.updated_at,
        result=record.result, error=record.error, logs=record.logs or [],
    )


@app.get("/jobs/{job_id}/stream")
async def stream_job_logs(
    job_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    if not job_store.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_seq = 0
        while True:
            record = job_store.get_job(job_id)
            if not record:
                yield 'event: error\ndata: {"message":"job_not_found"}\n\n'
                break
            new_logs = job_store.logs_since(job_id, last_seq)
            for log in new_logs:
                last_seq = int(log.get("seq", last_seq))
                yield f"event: log\ndata: {json.dumps(log)}\n\n"
            if record.status in {"completed", "failed"}:
                terminal = {"status": record.status, "error": record.error}
                yield f"event: done\ndata: {json.dumps(terminal)}\n\n"
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── ASO ─────────────────────────────────────────────────────────────

@app.post("/aso/run", response_model=AsoResponse)
def run_aso(
    request: AsoRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> AsoResponse:
    return AsoAgent().run(request)


# ── Deploy ──────────────────────────────────────────────────────────

@app.post("/deploy/run", response_model=DeployResponse)
def run_deploy(
    request: DeployRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> DeployResponse:
    return DeployAgent().run(request)


# ── Keyword Strategy (NEW) ──────────────────────────────────────────

@app.post("/keywords/research")
def keyword_research(
    seed_keyword: str,
    domain: str,
    locale: str = "en-US",
    region: str = "IN",
    industry: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    claude = _get_claude_client()
    if not claude:
        raise HTTPException(status_code=400, detail="AI features require ANTHROPIC_API_KEY.")
    from app.agents.keyword_agent import KeywordStrategyAgent
    serper = SerperHTTPClient(api_key=settings.serper_api_key) if settings.serper_api_key else None
    agent = KeywordStrategyAgent(claude_client=claude, serper_client=serper)
    result = agent.research(seed_keyword, domain, locale, region, industry)
    return {
        "primary_keyword": result.primary_keyword,
        "opportunities": [
            {
                "keyword": o.keyword,
                "volume": o.search_volume_est,
                "difficulty": o.difficulty_est,
                "intent": o.intent,
                "content_type": o.content_type,
                "priority": o.priority_score,
                "cluster": o.cluster,
            }
            for o in result.opportunities
        ],
        "clusters": result.clusters,
        "content_plan": result.content_plan,
        "competitor_keywords": result.competitor_keywords,
    }


# ── Technical Audit (NEW) ──────────────────────────────────────────

@app.post("/audit/technical")
def technical_audit(
    url: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    claude = _get_claude_client()
    agent = TechnicalAgent(claude_client=claude, pagespeed_api_key=settings.pagespeed_api_key)
    result = agent.full_audit(url)
    return {
        "url": result.url,
        "scores": {
            "performance": result.performance_score,
            "accessibility": result.accessibility_score,
            "seo": result.seo_score,
            "best_practices": result.best_practices_score,
        },
        "core_web_vitals": result.core_web_vitals,
        "actions": result.execution_queue,
        "issues_count": len(result.actions),
    }


# ── Projects CRUD ──────────────────────────────────────────────────

from app.schemas.project import (
    ContentDraftCreate, ContentDraftResponse, KeywordCreate, KeywordResponse,
    ProjectCreate, ProjectResponse, ProjectUpdate, RankHistoryPoint,
)


def _supabase_rest(method: str, path: str, payload: dict | list | None = None, params: str = "") -> dict | list:
    """Helper to call Supabase REST API."""
    import requests as req
    base = settings.supabase_url.rstrip("/") + "/rest/v1"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{base}/{path}{'?' + params if params else ''}"
    resp = getattr(req, method)(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json() if resp.content else []
    return data


@app.post("/projects", response_model=ProjectResponse)
def create_project(
    body: ProjectCreate,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    domain = body.domain or str(body.client_url).replace("https://", "").replace("http://", "").split("/")[0]
    data = _supabase_rest("post", "projects", {
        "name": body.name,
        "client_url": str(body.client_url),
        "domain": domain,
        "target_niche": body.target_niche,
        "goal_keywords": body.goal_keywords,
        "settings": body.settings,
    })
    return data[0] if isinstance(data, list) else data


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    return _supabase_rest("get", "projects", params="order=created_at.desc&limit=50")


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    data = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")
    return data[0]


@app.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    _auth: None = Depends(require_api_key),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "client_url" in updates:
        updates["client_url"] = str(updates["client_url"])
    data = _supabase_rest("patch", f"projects?id=eq.{project_id}", updates)
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")
    return data[0]


@app.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    _supabase_rest("delete", f"projects?id=eq.{project_id}")
    return {"deleted": True}


# ── Keywords ───────────────────────────────────────────────────────

@app.post("/projects/{project_id}/keywords", response_model=KeywordResponse)
def add_keyword(
    project_id: str,
    body: KeywordCreate,
    _auth: None = Depends(require_api_key),
):
    data = _supabase_rest("post", "keywords", {
        "project_id": project_id,
        "keyword": body.keyword,
        "locale": body.locale,
        "target_region": body.target_region,
        "intent": body.intent,
        "is_primary": body.is_primary,
        "tags": body.tags,
    })
    row = data[0] if isinstance(data, list) else data
    return KeywordResponse(id=row["id"], **{k: row[k] for k in ("keyword", "locale", "target_region", "intent", "is_primary", "tags") if k in row})


@app.get("/projects/{project_id}/keywords", response_model=list[KeywordResponse])
def list_keywords(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    rows = _supabase_rest("get", "keywords", params=f"project_id=eq.{project_id}&order=created_at.desc")
    return [KeywordResponse(id=r["id"], **{k: r.get(k) for k in ("keyword", "locale", "target_region", "search_volume", "difficulty", "intent", "is_primary", "tags")}) for r in rows]


@app.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: str, _auth: None = Depends(require_api_key)):
    _supabase_rest("delete", f"keywords?id=eq.{keyword_id}")
    return {"deleted": True}


# ── Rank History ───────────────────────────────────────────────────

@app.get("/keywords/{keyword_id}/rank-history", response_model=list[RankHistoryPoint])
def get_rank_history(
    keyword_id: str,
    limit: int = 90,
    _auth: None = Depends(require_api_key),
):
    rows = _supabase_rest(
        "get", "rank_history",
        params=f"keyword_id=eq.{keyword_id}&order=checked_at.desc&limit={limit}",
    )
    return [RankHistoryPoint(
        position=r.get("position"),
        url=r.get("url"),
        serp_features=r.get("serp_features", []),
        checked_at=r["checked_at"],
    ) for r in rows]


@app.post("/projects/{project_id}/rank-check")
def trigger_rank_check(
    project_id: str,
    background_tasks: BackgroundTasks,
    _auth: None = Depends(require_api_key),
):
    """Manually trigger a rank check for all keywords in a project."""
    if not settings.serper_api_key:
        raise HTTPException(status_code=400, detail="SERPER_API_KEY required for rank tracking.")

    def _run():
        from app.services.rank_tracker import RankPersistence, RankTracker
        serper = SerperHTTPClient(api_key=settings.serper_api_key)
        tracker = RankTracker(serper_client=serper)
        persistence = RankPersistence(settings.supabase_url, settings.supabase_service_role_key)

        project = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
        if not project:
            return
        domain = project[0].get("domain", "")

        keywords = persistence.get_keywords_for_project(project_id)
        latest = persistence.get_latest_positions(project_id)
        prev_map = {r["keyword_id"]: r.get("position") for r in latest}

        kw_batch = [{"keyword_id": kw["id"], "keyword": kw["keyword"], "previous_position": prev_map.get(kw["id"])} for kw in keywords]
        results = tracker.check_batch(kw_batch, domain)
        persistence.save_rank_checks(results)

    background_tasks.add_task(_run)
    return {"status": "rank_check_queued", "project_id": project_id}


# ── Content Queue ──────────────────────────────────────────────────

@app.get("/projects/{project_id}/content", response_model=list[ContentDraftResponse])
def list_content(
    project_id: str,
    status: str = "",
    _auth: None = Depends(require_api_key),
):
    params = f"project_id=eq.{project_id}&order=created_at.desc&limit=50"
    if status:
        params += f"&queue_status=eq.{status}"
    rows = _supabase_rest("get", "content_queue", params=params)
    return rows


@app.post("/projects/{project_id}/content", response_model=ContentDraftResponse)
def create_content_draft(
    project_id: str,
    body: ContentDraftCreate,
    _auth: None = Depends(require_api_key),
):
    slug = "-".join(body.title.lower().split()[:6])
    data = _supabase_rest("post", "content_queue", {
        "project_id": project_id,
        "content_type": "seo_page",
        "title": body.title,
        "slug": slug,
        "body_markdown": body.body_markdown,
        "target_keyword": body.target_keyword,
        "publish_target": body.publish_target,
        "queue_status": "draft",
    })
    return data[0] if isinstance(data, list) else data


@app.patch("/content/{content_id}")
def update_content_draft(
    content_id: str,
    body: dict,
    _auth: None = Depends(require_api_key),
):
    allowed = {"title", "body_markdown", "queue_status", "target_keyword", "publish_target"}
    updates = {k: v for k, v in body.items() if k in allowed}
    data = _supabase_rest("patch", f"content_queue?id=eq.{content_id}", updates)
    return data[0] if isinstance(data, list) and data else {"updated": True}


@app.post("/content/{content_id}/ai-rewrite")
def ai_rewrite_content(
    content_id: str,
    instruction: str = "Improve SEO optimization and readability",
    _auth: None = Depends(require_api_key),
):
    """Use AI to rewrite a content draft section."""
    claude = _get_claude_client()
    if not claude:
        raise HTTPException(status_code=400, detail="AI features require ANTHROPIC_API_KEY.")

    content_rows = _supabase_rest("get", f"content_queue", params=f"id=eq.{content_id}")
    if not content_rows:
        raise HTTPException(status_code=404, detail="Content not found")

    content = content_rows[0]
    agent = ContentAgent(claude_client=claude)
    rewritten = agent.rewrite_section(
        content=content["body_markdown"],
        keyword=content.get("target_keyword", ""),
        instruction=instruction,
    )

    _supabase_rest("patch", f"content_queue?id=eq.{content_id}", {"body_markdown": rewritten})
    return {"rewritten": True, "word_count": len(rewritten.split())}


# ── Competitor Monitoring ──────────────────────────────────────────

@app.post("/projects/{project_id}/competitors/check")
def check_competitors(
    project_id: str,
    background_tasks: BackgroundTasks,
    _auth: None = Depends(require_api_key),
):
    """Trigger competitor monitoring scan for a project."""
    if not settings.firecrawl_api_key:
        raise HTTPException(status_code=400, detail="FIRECRAWL_API_KEY required.")

    def _run():
        from app.services.competitor_monitor import CompetitorMonitor
        firecrawl = FirecrawlHTTPClient(api_key=settings.firecrawl_api_key)
        claude = _get_claude_client()
        monitor = CompetitorMonitor(firecrawl_client=firecrawl, claude_client=claude)

        intel_rows = _supabase_rest("get", "competitor_intel", params=f"project_id=eq.{project_id}&order=captured_at.desc&limit=20")
        for row in intel_rows:
            url = row.get("source_url", "")
            if not url:
                continue
            try:
                snapshot, changes = monitor.check_competitor(url)
                if changes:
                    _persistence_repo().log_agent_event(AgentLogEvent(
                        project_id=project_id,
                        agent_name="competitor_monitor",
                        action_type="changes_detected",
                        action_payload={"url": url, "changes": [{"type": c.change_type, "severity": c.severity, "desc": c.description} for c in changes]},
                    ))
            except Exception as exc:
                logger.warning("Competitor check failed for %s: %s", url, exc)

    background_tasks.add_task(_run)
    return {"status": "competitor_check_queued"}


# ── Reports ────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/reports")
def list_reports(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    return _supabase_rest("get", "reports", params=f"project_id=eq.{project_id}&order=created_at.desc&limit=20")


@app.post("/projects/{project_id}/reports/generate")
def generate_report(
    project_id: str,
    report_type: str = "seo_audit",
    background_tasks: BackgroundTasks = None,
    _auth: None = Depends(require_api_key),
):
    """Generate an AI-powered SEO report for a project."""
    claude = _get_claude_client()
    if not claude:
        raise HTTPException(status_code=400, detail="AI features require ANTHROPIC_API_KEY.")

    # Gather all data
    project = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project = project[0]

    keywords = _supabase_rest("get", "keywords", params=f"project_id=eq.{project_id}&limit=50")
    audits = _supabase_rest("get", "site_audits", params=f"project_id=eq.{project_id}&order=created_at.desc&limit=1")
    content = _supabase_rest("get", "content_queue", params=f"project_id=eq.{project_id}&limit=10")

    system = """Generate a concise SEO report summary. Include:
1. Overall assessment (2-3 sentences)
2. Key metrics summary
3. Top 5 priority actions
4. Competitive position summary

Respond ONLY with JSON:
{"title":"...","summary":"...","key_metrics":{},"priority_actions":["..."],"competitive_summary":"..."}"""

    context = f"""Project: {project.get('name')} ({project.get('domain')})
Keywords tracked: {len(keywords)}
Recent audits: {len(audits)}
Content drafts: {len(content)}
Audit scores: {audits[0].get('results', {}) if audits else 'No audits yet'}"""

    parsed, resp = claude.complete_json(
        messages=[{"role": "user", "content": context}],
        system=system, max_tokens=1500,
    )

    report_data = _supabase_rest("post", "reports", {
        "project_id": project_id,
        "report_type": report_type,
        "title": parsed.get("title", f"SEO Report — {project.get('name')}"),
        "summary": parsed.get("summary", ""),
        "data": parsed,
    })

    return report_data[0] if isinstance(report_data, list) else report_data


# ── Billing ────────────────────────────────────────────────────────

@app.post("/billing/subscribe")
def create_subscription(
    plan: str,
    email: str,
    name: str = "",
    _auth: None = Depends(require_api_key),
):
    from app.services.billing import PLANS, RazorpayClient
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {', '.join(PLANS.keys())}")

    plan_info = PLANS[plan]
    if not plan_info.get("razorpay_plan_id"):
        raise HTTPException(status_code=400, detail="Razorpay plan ID not configured for this plan.")

    client = RazorpayClient()
    if not client.enabled:
        raise HTTPException(status_code=400, detail="Razorpay not configured.")

    result = client.create_subscription(
        plan_id=plan_info["razorpay_plan_id"],
        customer_email=email,
        customer_name=name,
    )
    return {
        "subscription_id": result.subscription_id,
        "checkout_url": result.short_url,
        "status": result.status,
    }


@app.post("/billing/cancel")
def cancel_subscription(
    subscription_id: str,
    _auth: None = Depends(require_api_key),
):
    from app.services.billing import RazorpayClient
    client = RazorpayClient()
    if not client.enabled:
        raise HTTPException(status_code=400, detail="Razorpay not configured.")
    result = client.cancel_subscription(subscription_id)
    return {"status": result.get("status", "cancelled")}


from fastapi import Request

@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay subscription webhooks."""
    from app.services.billing import RazorpayClient
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not RazorpayClient.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    data = json.loads(body)
    event = data.get("event", "")
    payload = data.get("payload", {})

    logger.info("Razorpay webhook: %s", event)

    if event == "subscription.activated":
        sub = payload.get("subscription", {}).get("entity", {})
        notes = sub.get("notes", {})
        # Update org plan status
        if notes.get("email"):
            _supabase_rest("patch", f"organizations?id=eq.{notes.get('org_id', '')}", {
                "plan_status": "active",
                "razorpay_subscription_id": sub.get("id"),
            })

    elif event == "subscription.charged":
        sub = payload.get("subscription", {}).get("entity", {})
        payment = payload.get("payment", {}).get("entity", {})
        # Log billing event
        _supabase_rest("post", "billing_events", {
            "org_id": sub.get("notes", {}).get("org_id", ""),
            "event_type": "payment_success",
            "amount_inr": payment.get("amount"),
            "razorpay_payment_id": payment.get("id"),
            "metadata": {"subscription_id": sub.get("id")},
        })

    elif event in ("subscription.cancelled", "subscription.paused"):
        sub = payload.get("subscription", {}).get("entity", {})
        status = "cancelled" if "cancel" in event else "past_due"
        org_id = sub.get("notes", {}).get("org_id", "")
        if org_id:
            _supabase_rest("patch", f"organizations?id=eq.{org_id}", {"plan_status": status})

    return {"received": True}


# ── PDF Report Download ────────────────────────────────────────────

@app.get("/projects/{project_id}/reports/{report_id}/html")
def get_report_html(
    project_id: str,
    report_id: str,
    white_label: bool = False,
    _auth: None = Depends(require_api_key),
):
    """Get report as HTML (can be printed to PDF via browser)."""
    from app.services.report_generator import ReportGenerator

    report_rows = _supabase_rest("get", "reports", params=f"id=eq.{report_id}")
    if not report_rows:
        raise HTTPException(status_code=404, detail="Report not found")

    project_rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")

    keywords = _supabase_rest("get", "keywords", params=f"project_id=eq.{project_id}&limit=50")

    claude = _get_claude_client()
    generator = ReportGenerator(claude_client=claude)
    html = generator.generate_seo_report(
        project=project_rows[0],
        keywords=keywords,
        white_label=white_label,
    )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)

@app.get("/jobs/{job_id}/report")
def get_job_report(job_id: str):
    from fastapi.responses import HTMLResponse
    from app.services.pdf_report import generate_seo_report_html
    job = job_store.get_job(job_id)
    if not job: raise HTTPException(404, "Job not found")
    if job.status != "completed" or not job.result: raise HTTPException(400, "Not completed")
    result = job.result
    comps = [c.model_dump() if hasattr(c, "model_dump") else c.__dict__ for c in result.result.competitor_profiles]
    gap = result.result.gap_analysis.model_dump() if hasattr(result.result.gap_analysis, "model_dump") else result.result.gap_analysis.__dict__
    html = generate_seo_report_html(client_url=result.result.client_profile.url, keyword=job.payload.get("primary_keyword",""), seo_score=result.final_score, competitors=comps, gap_analysis=gap, recommendations=result.result.recommendations, raw_metrics=result.result.raw_metrics, project_name=job.payload.get("project_id",""))
    return HTMLResponse(content=html)

@app.get("/api/llm/status")
def llm_status():
    return llm_client.get_status()

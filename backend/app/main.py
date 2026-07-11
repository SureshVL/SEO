"""OMNI-RANK OR-1 API — Production FastAPI application."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents.ai_visibility_agent import AIVisibilityAgent
from app.agents.aso_agent import AsoAgent
from app.agents.content_agent import ContentAgent
from app.agents.deploy_agent import DeployAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.schema_agent import SchemaAgent
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

# ── Project scoping ─────────────────────────────────────────────────
# Clients select a project via the X-Project-ID header (or ?project_id=).
# Endpoints that resolve "the project" use _get_scoped_projects(), which
# honors that selection and falls back to the first project.
import contextvars

_scoped_project_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "scoped_project_id", default=""
)


@app.middleware("http")
async def _project_scope_middleware(request: Request, call_next):
    pid = request.headers.get("X-Project-ID", "") or request.query_params.get("project_id", "")
    token = _scoped_project_id.set(pid.strip())
    try:
        return await call_next(request)
    finally:
        _scoped_project_id.reset(token)


def _get_scoped_projects():
    """Rows for the client-selected project, else the first project.

    A project id that is explicitly supplied but unknown is an error -
    silently falling back to another tenant's project would read/write
    the wrong data.
    """
    pid = _scoped_project_id.get()
    if pid:
        import re as _re
        if not _re.fullmatch(r"[0-9a-fA-F-]{32,36}", pid):
            raise HTTPException(status_code=400, detail="Invalid X-Project-ID")
        rows = _supabase_rest("get", "projects", params=f"id=eq.{pid}")
        if not rows:
            raise HTTPException(status_code=404, detail="Project not found")
        return rows
    return _supabase_rest("get", "projects", params="limit=1")

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
    city: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    claude = _get_claude_client()
    if not claude:
        raise HTTPException(status_code=400, detail="AI features require ANTHROPIC_API_KEY.")
    from app.agents.keyword_agent import KeywordStrategyAgent
    serper = SerperHTTPClient(api_key=settings.serper_api_key) if settings.serper_api_key else None
    agent = KeywordStrategyAgent(claude_client=claude, serper_client=serper)
    # Localise seed keyword when city is provided
    localised_seed = f"{seed_keyword} in {city.title()}" if city and city.lower() not in seed_keyword.lower() else seed_keyword
    result = agent.research(localised_seed, domain, locale, region, industry, city=city)
    return {
        "primary_keyword": result.primary_keyword,
        "opportunities": [
            {
                "keyword": o.keyword,
                "search_volume_est": o.search_volume_est,
                "difficulty_est": o.difficulty_est,
                "intent": o.intent,
                "content_type": o.content_type,
                "priority_score": o.priority_score,
                "cluster": o.cluster,
                "notes": o.notes,
            }
            for o in result.opportunities
        ],
        "clusters": result.clusters,
        "content_plan": result.content_plan,
        "competitor_keywords": result.competitor_keywords,
    }


# ── Technical Audit (NEW) ──────────────────────────────────────────

def _build_technical_agent() -> TechnicalAgent:
    claude = _get_claude_client()
    dfs = None
    if settings.dataforseo_login and settings.dataforseo_password:
        from app.clients.dataforseo_client import DataForSEOClient
        dfs = DataForSEOClient(
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
        )
    return TechnicalAgent(
        claude_client=claude,
        pagespeed_api_key=settings.pagespeed_api_key,
        dataforseo_client=dfs,
    )


def _serialize_crawl(result) -> dict:
    """Serialize SiteCrawlResult to JSON-safe dict for API responses."""
    return {
        "domain": result.domain,
        "task_id": result.task_id,
        "status": result.status,
        "error": result.error,
        "pages_crawled": result.pages_crawled,
        "pages_in_queue": result.pages_in_queue,
        "max_crawl_pages": result.max_crawl_pages,
        "onpage_score": result.onpage_score,
        "issues_by_check": result.issues_by_check,
        "actions": [
            {
                "category": a.category,
                "action": a.action,
                "impact": a.impact,
                "details": a.details,
                "auto_fixable": a.auto_fixable,
            }
            for a in result.actions
        ],
        "sample_pages": result.sample_pages,
        "duplicate_titles": result.duplicate_titles,
        "duplicate_descriptions": result.duplicate_descriptions,
        "broken_links": result.broken_links,
    }


@app.post("/audit/technical")
def technical_audit(
    url: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    agent = _build_technical_agent()
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


@app.post("/audit/crawl")
def start_crawl_audit(
    domain: str,
    max_pages: int = 100,
    wait: bool = False,
    max_wait_seconds: int = 120,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Start a full-site crawl using DataForSEO On-Page.

    - wait=False (default): returns task_id immediately; poll GET /audit/crawl/{task_id}.
    - wait=True: blocks until crawl finishes or max_wait_seconds elapses.
    """
    if not settings.dataforseo_login or not settings.dataforseo_password:
        raise HTTPException(
            status_code=400,
            detail="DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required for full-site crawl.",
        )
    if max_pages < 1 or max_pages > 1000:
        raise HTTPException(status_code=400, detail="max_pages must be between 1 and 1000.")

    agent = _build_technical_agent()
    clean_domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
    if wait:
        result = agent.run_site_crawl(
            clean_domain, max_pages=max_pages, max_wait_seconds=max_wait_seconds
        )
    else:
        result = agent.start_site_crawl(clean_domain, max_pages=max_pages)
    return _serialize_crawl(result)


@app.get("/audit/crawl/{task_id}")
def get_crawl_audit(
    task_id: str,
    domain: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Poll a running crawl task; returns results when status == 'finished'."""
    if not settings.dataforseo_login or not settings.dataforseo_password:
        raise HTTPException(
            status_code=400,
            detail="DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required.",
        )
    agent = _build_technical_agent()
    result = agent.fetch_site_crawl(task_id, domain=domain, include_samples=True)
    return _serialize_crawl(result)


# ── AI Visibility / GEO ────────────────────────────────────────────

from pydantic import BaseModel, Field


class GeoCheckRequest(BaseModel):
    keywords: list[str] = Field(..., min_length=1, max_length=50)
    domain: str
    engines: list[str] = Field(default_factory=lambda: ["chat_gpt", "perplexity", "gemini"])
    location_code: int = 2356
    language_code: str = "en"
    include_ai_mode: bool = False
    prompt_template: str = "What are the best {keyword}? List specific providers with their websites."


def _build_ai_visibility_agent() -> AIVisibilityAgent:
    from app.clients.dataforseo_client import DataForSEOClient
    if not settings.dataforseo_login or not settings.dataforseo_password:
        raise HTTPException(
            status_code=400,
            detail="DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required for AI visibility tracking.",
        )
    dfs = DataForSEOClient(
        login=settings.dataforseo_login,
        password=settings.dataforseo_password,
    )
    return AIVisibilityAgent(dataforseo_client=dfs)


def _serialize_ai_visibility(report) -> dict:
    return {
        "domain": report.domain,
        "total_keywords": report.total_keywords,
        "engines": report.engines,
        "overall_score": report.overall_score,
        "ai_overview_coverage": report.ai_overview_coverage,
        "ai_overview_citation_rate": report.ai_overview_citation_rate,
        "llm_mention_rate": report.llm_mention_rate,
        "keywords": [
            {
                "keyword": k.keyword,
                "visibility_score": k.visibility_score,
                "ai_overview_present": k.ai_overview_present,
                "ai_overview_cited": k.ai_overview_cited,
                "ai_overview_position": k.ai_overview_position,
                "ai_overview_snippet": k.ai_overview_snippet,
                "ai_overview_citations": k.ai_overview_citations,
                "ai_mode_present": k.ai_mode_present,
                "ai_mode_cited": k.ai_mode_cited,
                "ai_mode_snippet": k.ai_mode_snippet,
                "llm_results": k.llm_results,
            }
            for k in report.keywords
        ],
    }


@app.post("/geo/check")
def geo_check(
    body: GeoCheckRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Ad-hoc AI visibility check across Google AI Overview + LLM engines."""
    valid_engines = {"chat_gpt", "perplexity", "gemini"}
    engines = tuple(e for e in body.engines if e in valid_engines)
    if not engines:
        raise HTTPException(status_code=400, detail="At least one valid engine required.")

    agent = _build_ai_visibility_agent()
    report = agent.run(
        keywords=body.keywords,
        domain=body.domain,
        location_code=body.location_code,
        language_code=body.language_code,
        engines=engines,
        include_ai_mode=body.include_ai_mode,
        prompt_template=body.prompt_template,
    )
    return _serialize_ai_visibility(report)


@app.post("/projects/{project_id}/ai-visibility")
def project_ai_visibility(
    project_id: str,
    engines: str = "chat_gpt,perplexity,gemini",
    include_ai_mode: bool = False,
    max_keywords: int = 10,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Run AI visibility on a project's stored keywords + domain."""
    project_rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")
    project = project_rows[0]
    domain = project.get("domain") or ""
    if not domain:
        raise HTTPException(status_code=400, detail="Project has no domain configured.")

    kw_rows = _supabase_rest(
        "get", "keywords",
        params=f"project_id=eq.{project_id}&order=is_primary.desc&limit={max_keywords}",
    )
    keywords = [r["keyword"] for r in (kw_rows or []) if r.get("keyword")]
    if not keywords:
        raise HTTPException(status_code=400, detail="No keywords tracked for this project.")

    valid = {"chat_gpt", "perplexity", "gemini"}
    engine_tuple = tuple(e.strip() for e in engines.split(",") if e.strip() in valid)
    if not engine_tuple:
        raise HTTPException(status_code=400, detail="No valid engines specified.")

    agent = _build_ai_visibility_agent()
    report = agent.run(
        keywords=keywords,
        domain=domain,
        engines=engine_tuple,
        include_ai_mode=include_ai_mode,
    )
    return _serialize_ai_visibility(report)


# ── Schema markup detection & generation ──────────────────────────

class SchemaDetectRequest(BaseModel):
    url: str
    html: str | None = None  # optional pre-fetched HTML
    business_type: str = "default"
    business_name: str = ""


class SchemaGenerateRequest(BaseModel):
    schema_types: list[str] = Field(..., min_length=1, max_length=20)
    url: str = ""
    business_name: str = ""
    city: str = ""


class SchemaInjectBatchRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=1000)
    schema_types: list[str] = Field(..., min_length=1, max_length=10)
    business_type: str = "default"
    business_name: str = ""
    cms_auto_detect: bool = True
    cms_platform: str | None = None


class CMSCredentialRequest(BaseModel):
    cms_platform: str  # wordpress, shopify, webflow, custom
    endpoint_url: str = ""  # e.g., https://mysite.com for WordPress
    api_key: str = ""  # REST API username or key
    api_secret: str = ""  # REST API password or token


class BulkContentJobRequest(BaseModel):
    template: dict[str, str] = Field(..., description="Article template with {{variable}} placeholders")
    csv_data: list[dict[str, str]] = Field(..., description="Parsed CSV rows")
    enhance_with_ai: bool = True
    export_format: str = "json"  # json, csv, markdown
    schedule_publish: str = ""  # ISO date to publish


class ScheduleArticleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    meta_description: str = Field(..., max_length=160)
    scheduled_date: str  # ISO datetime
    cms_platform: str = "wordpress"
    auto_publish: bool = True
    auto_social_share: bool = False
    social_platforms: list[str] = Field(default_factory=list)
    featured_image_url: str = ""
    content_type: str = "article"


class AddCompetitorRequest(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    name: str = ""
    country_code: str = ""
    language_code: str = "en"


class AnalyzeCompetitorRequest(BaseModel):
    competitor_id: int
    keywords: list[dict[str, Any]] = Field(default_factory=list)
    backlinks: int = 0
    referring_domains: int = 0
    top_pages: list[dict[str, Any]] = Field(default_factory=list)
    technical_score: int | None = None
    content_pages: int = 0
    avg_content_length: int = 0


class GenerateStrategiesRequest(BaseModel):
    competitor_id: int
    your_keywords: list[str] = Field(..., min_items=1)
    your_rankings: dict[str, int] = Field(default_factory=dict)


class AddSitePageRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=500)
    title: str = Field(..., max_length=500)
    content: str = Field(..., min_length=10)
    topics: list[str] = Field(default_factory=list)


class FindOpportunitiesRequest(BaseModel):
    source_url: str


def _build_schema_agent() -> SchemaAgent:
    firecrawl = None
    if settings.firecrawl_api_key:
        firecrawl = FirecrawlHTTPClient(api_key=settings.firecrawl_api_key)
    return SchemaAgent(firecrawl_client=firecrawl)


def _serialize_schema_detection(result) -> dict:
    return {
        "url": result.url,
        "blocks_found": result.blocks_found,
        "detected_types": result.detected_types,
        "detected": [
            {"type": d.type, "name": d.name, "raw": d.raw} for d in result.detected
        ],
        "missing_recommended": result.missing_recommended,
        "generated": result.generated,
        "parse_errors": result.parse_errors,
    }


@app.post("/schema/detect")
def schema_detect(
    body: SchemaDetectRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Detect JSON-LD schema on a URL and return gap-analysis + stubs."""
    agent = _build_schema_agent()
    result = agent.detect(
        url=body.url,
        html=body.html or "",
        business_type=body.business_type,
        business_name=body.business_name,
    )
    return _serialize_schema_detection(result)


@app.post("/schema/generate")
def schema_generate(
    body: SchemaGenerateRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate JSON-LD stubs for a list of schema types."""
    agent = _build_schema_agent()
    context = {
        "url": body.url,
        "business_name": body.business_name,
        "city": body.city,
    }
    out = []
    unknown: list[str] = []
    for t in body.schema_types:
        stub = agent.generate(t, context)
        if stub:
            out.append({"type": t, "jsonld": stub})
        else:
            unknown.append(t)
    return {"generated": out, "unsupported": unknown}


@app.post("/schema/inject-batch")
def schema_inject_batch(
    body: SchemaInjectBatchRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Inject schema markup into multiple URLs with CMS auto-detection."""
    from app.services.schema_injection_service import SchemaInjectionService, SchemaInjectionRequest
    from uuid import UUID

    # Extract project_id from the URL path or auth context
    # For now, assume it's embedded in a custom header or auth
    # Fallback: use first project for testing
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    svc = SchemaInjectionService()
    req = SchemaInjectionRequest(
        project_id=UUID(project_id),
        urls=body.urls,
        schema_types=body.schema_types,
        business_type=body.business_type,
        business_name=body.business_name,
        cms_auto_detect=body.cms_auto_detect,
        cms_platform=body.cms_platform,
    )

    try:
        result = svc.inject_batch(req, _supabase_rest)
        return {
            "job_id": result.job_id,
            "status": result.status,
            "total_urls": result.total_urls,
            "processed_count": result.processed_count,
            "success_count": result.success_count,
            "failure_count": result.failure_count,
            "injections": result.injections,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Batch injection failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/schema/injection-jobs/{job_id}")
def get_injection_job_status(
    job_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get status of a schema injection job."""
    from app.services.schema_injection_service import SchemaInjectionService

    svc = SchemaInjectionService()
    return svc.get_job_status(job_id, _supabase_rest)


@app.post("/cms/credentials")
def save_cms_credentials(
    body: CMSCredentialRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Save CMS platform credentials (WordPress REST API, etc.)."""
    # Get first project for now (in production, use project_id from request)
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        # Check if credentials already exist
        existing = _supabase_rest("get", "cms_credentials", params=f"project_id=eq.{project_id}&cms_platform=eq.{body.cms_platform}")

        if existing and isinstance(existing, list) and len(existing) > 0:
            # Update
            result = _supabase_rest("patch", f"cms_credentials?project_id=eq.{project_id}&cms_platform=eq.{body.cms_platform}", {
                "endpoint_url": body.endpoint_url,
                "api_key": body.api_key,
                "api_secret": body.api_secret,
            })
        else:
            # Create
            result = _supabase_rest("post", "cms_credentials", {
                "project_id": project_id,
                "cms_platform": body.cms_platform,
                "endpoint_url": body.endpoint_url,
                "api_key": body.api_key,
                "api_secret": body.api_secret,
            })

        return {
            "status": "saved",
            "platform": body.cms_platform,
            "endpoint": body.endpoint_url,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to save CMS credentials: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/cms/credentials/{platform}")
def get_cms_credentials(
    platform: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get saved CMS credentials for a platform."""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        result = _supabase_rest("get", "cms_credentials", params=f"project_id=eq.{project_id}&cms_platform=eq.{platform}")
        if not result or (isinstance(result, list) and len(result) == 0):
            return {"platform": platform, "saved": False}

        cred = result[0] if isinstance(result, list) else result
        # Don't return secrets, just confirm they're saved
        return {
            "platform": platform,
            "saved": True,
            "endpoint_url": cred.get("endpoint_url", ""),
            "has_api_key": bool(cred.get("api_key")),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get CMS credentials: %s", exc)
        return {"platform": platform, "saved": False, "error": str(exc)}


@app.delete("/cms/credentials/{platform}")
def delete_cms_credentials(
    platform: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Delete saved CMS credentials for a platform."""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        _supabase_rest("delete", f"cms_credentials?project_id=eq.{project_id}&cms_platform=eq.{platform}", None)
        return {"status": "deleted", "platform": platform}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete CMS credentials: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Bulk content generation ──────────────────────────────────────

@app.post("/bulk/jobs")
def create_bulk_content_job(
    body: BulkContentJobRequest,
    background_tasks: BackgroundTasks,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Create and queue a bulk content generation job."""
    from app.services.bulk_content_service import BulkContentService, BulkContentJobRequest
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = BulkContentService()
        req = BulkContentJobRequest(
            project_id=UUID(project_id),
            template=body.template,
            csv_data=body.csv_data,
            enhance_with_ai=body.enhance_with_ai,
            export_format=body.export_format,
            schedule_publish=body.schedule_publish,
        )

        result = svc.create_job(req, _supabase_rest)

        # Queue async processing
        background_tasks.add_task(
            svc.process_job,
            result.job_id,
            body.template,
            body.csv_data,
            body.enhance_with_ai,
            body.export_format,
            _supabase_rest,
        )

        return {
            "job_id": result.job_id,
            "status": result.status,
            "total_articles": result.total_articles,
            "completed_articles": result.completed_articles,
            "failed_articles": result.failed_articles,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create bulk content job: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/bulk/jobs/{job_id}")
def get_bulk_job_status(
    job_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get status of a bulk content job."""
    from app.services.bulk_content_service import BulkContentService

    try:
        svc = BulkContentService()
        result = svc.get_job_status(job_id, _supabase_rest)
        return {
            "job_id": result.job_id,
            "status": result.status,
            "total_articles": result.total_articles,
            "completed_articles": result.completed_articles,
            "failed_articles": result.failed_articles,
            "export_url": result.export_url,
            "error_message": result.error_message,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get bulk job status: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/bulk/jobs/{job_id}/articles")
def get_bulk_job_articles(
    job_id: str,
    limit: int = 100,
    offset: int = 0,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get generated articles for a bulk content job."""
    from app.services.bulk_content_service import BulkContentService

    try:
        svc = BulkContentService()
        articles = svc.get_articles(job_id, limit=limit, offset=offset, db_fn=_supabase_rest)
        return {"articles": articles, "limit": limit, "offset": offset}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get bulk articles: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/bulk/jobs/{job_id}")
def cancel_bulk_job(
    job_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Cancel a bulk content job."""
    from app.services.bulk_content_service import BulkContentService

    try:
        svc = BulkContentService()
        success = svc.cancel_job(job_id, _supabase_rest)
        if success:
            return {"status": "cancelled", "job_id": job_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cancel bulk job: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Content calendar + publishing ────────────────────────────────────

@app.post("/calendar/schedule")
def schedule_article(
    body: ScheduleArticleRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Schedule an article for future publication."""
    from app.services.content_calendar_service import (
        ContentCalendarService,
        ScheduleArticleRequest as CalendarRequest,
    )
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = ContentCalendarService()
        req = CalendarRequest(
            project_id=UUID(project_id),
            title=body.title,
            slug=body.slug,
            body=body.body,
            meta_description=body.meta_description,
            scheduled_date=body.scheduled_date,
            cms_platform=body.cms_platform,
            auto_publish=body.auto_publish,
            auto_social_share=body.auto_social_share,
            social_platforms=body.social_platforms,
            featured_image_url=body.featured_image_url,
            content_type=body.content_type,
        )

        result = svc.schedule_article(req, _supabase_rest)
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to schedule article: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/calendar")
def get_calendar(
    start_date: str = "",
    end_date: str = "",
    status: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Fetch calendar events for a date range."""
    from app.services.content_calendar_service import ContentCalendarService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = ContentCalendarService()
        events = svc.get_calendar(
            UUID(project_id),
            start_date=start_date,
            end_date=end_date,
            status=status,
            db_fn=_supabase_rest,
        )
        return {"events": events, "count": len(events)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch calendar: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/calendar/{calendar_id}")
def reschedule_article(
    calendar_id: int,
    new_date: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Reschedule a scheduled article."""
    from app.services.content_calendar_service import ContentCalendarService

    try:
        svc = ContentCalendarService()
        success = svc.reschedule_article(calendar_id, new_date, _supabase_rest)
        if success:
            return {"status": "rescheduled", "calendar_id": calendar_id, "new_date": new_date}
        else:
            raise HTTPException(status_code=400, detail="Failed to reschedule")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to reschedule article: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/calendar/{calendar_id}")
def cancel_article(
    calendar_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Cancel a scheduled article."""
    from app.services.content_calendar_service import ContentCalendarService

    try:
        svc = ContentCalendarService()
        success = svc.cancel_article(calendar_id, _supabase_rest)
        if success:
            return {"status": "cancelled", "calendar_id": calendar_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cancel article: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/calendar/{calendar_id}/publish")
async def publish_article(
    calendar_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Publish a scheduled article immediately."""
    from app.services.content_calendar_service import ContentCalendarService

    try:
        svc = ContentCalendarService()
        success = await svc.publish_article(calendar_id, _supabase_rest)
        if success:
            return {"status": "published", "calendar_id": calendar_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to publish")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to publish article: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/calendar/{calendar_id}/logs")
def get_publishing_logs(
    calendar_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get publishing logs for an article."""
    from app.services.content_calendar_service import ContentCalendarService

    try:
        svc = ContentCalendarService()
        logs = svc.get_publishing_logs(calendar_id, db_fn=_supabase_rest)
        return {"logs": logs, "count": len(logs)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch publishing logs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Competitor analysis + outrank strategies ──────────────────────

@app.post("/competitors/add")
def add_competitor(
    body: AddCompetitorRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Add a competitor to track."""
    from app.services.competitor_service import CompetitorService, AddCompetitorRequest as CompReq
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = CompetitorService()
        req = CompReq(
            project_id=UUID(project_id),
            domain=body.domain,
            name=body.name,
            country_code=body.country_code,
            language_code=body.language_code,
        )

        result = svc.add_competitor(req, _supabase_rest)
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to add competitor: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/competitors")
def get_competitors(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get all competitors for a project."""
    from app.services.competitor_service import CompetitorService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = CompetitorService()
        competitors = svc.get_competitors(UUID(project_id), db_fn=_supabase_rest)
        return {"competitors": competitors, "count": len(competitors)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch competitors: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/competitors/{competitor_id}")
def remove_competitor(
    competitor_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Remove a competitor."""
    from app.services.competitor_service import CompetitorService

    try:
        svc = CompetitorService()
        success = svc.remove_competitor(competitor_id, _supabase_rest)
        if success:
            return {"status": "removed", "competitor_id": competitor_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to remove")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to remove competitor: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/competitors/{competitor_id}/analyze")
async def analyze_competitor(
    competitor_id: int,
    body: AnalyzeCompetitorRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Analyze a competitor with Claude."""
    from app.services.competitor_service import CompetitorService

    try:
        svc = CompetitorService()
        result = await svc.analyze_competitor(
            competitor_id,
            {
                "keywords": body.keywords,
                "backlinks": body.backlinks,
                "referring_domains": body.referring_domains,
                "top_pages": body.top_pages,
                "technical_score": body.technical_score,
                "content_pages": body.content_pages,
                "avg_content_length": body.avg_content_length,
            },
            _supabase_rest,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to analyze competitor: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/competitors/{competitor_id}/analysis")
def get_competitor_analysis(
    competitor_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get latest analysis for a competitor."""
    from app.services.competitor_service import CompetitorService

    try:
        svc = CompetitorService()
        analysis = svc.get_analysis(competitor_id, db_fn=_supabase_rest)
        if not analysis:
            raise HTTPException(status_code=404, detail="No analysis found")
        return analysis

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch analysis: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/competitors/{competitor_id}/strategies")
async def generate_strategies(
    competitor_id: int,
    body: GenerateStrategiesRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate outrank strategies for a competitor."""
    from app.services.competitor_service import CompetitorService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = CompetitorService()
        strategies = await svc.generate_strategies(
            competitor_id,
            your_domain=projects[0].get("domain", ""),
            your_keywords=body.your_keywords,
            your_rankings=body.your_rankings,
            db_fn=_supabase_rest,
        )
        return {"strategies": strategies, "count": len(strategies)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to generate strategies: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/competitors/strategies")
def get_strategies(
    competitor_id: int | None = None,
    status: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get outrank strategies."""
    from app.services.competitor_service import CompetitorService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = CompetitorService()
        strategies = svc.get_strategies(
            UUID(project_id),
            competitor_id=competitor_id,
            status=status,
            db_fn=_supabase_rest,
        )
        return {"strategies": strategies, "count": len(strategies)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch strategies: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/competitors/strategies/{strategy_id}")
def update_strategy(
    strategy_id: int,
    status: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Update strategy implementation status."""
    from app.services.competitor_service import CompetitorService

    try:
        svc = CompetitorService()
        success = svc.update_strategy_status(strategy_id, status, _supabase_rest)
        if success:
            return {"status": "updated", "strategy_id": strategy_id, "new_status": status}
        else:
            raise HTTPException(status_code=400, detail="Failed to update")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update strategy: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Internal linking + site structure ─────────────────────────────

@app.post("/linking/pages")
def add_site_page(
    body: AddSitePageRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Add a page to the site structure analysis."""
    from app.services.internal_linking_service import InternalLinkingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        result = svc.add_page(
            UUID(project_id),
            body.url,
            body.title,
            body.content,
            body.topics,
            _supabase_rest,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to add page: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/linking/analyze")
async def analyze_site(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Analyze overall site structure and linking patterns."""
    from app.services.internal_linking_service import InternalLinkingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        analysis = await svc.analyze_site_structure(UUID(project_id), _supabase_rest)
        return analysis

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to analyze site: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/linking/opportunities")
async def find_opportunities(
    body: FindOpportunitiesRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Find linking opportunities for a page."""
    from app.services.internal_linking_service import InternalLinkingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        opportunities = await svc.find_opportunities(
            UUID(project_id),
            body.source_url,
            _supabase_rest,
        )
        return {"opportunities": opportunities, "count": len(opportunities)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to find opportunities: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/linking/opportunities")
def get_opportunities(
    source_url: str = "",
    status: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get linking opportunities."""
    from app.services.internal_linking_service import InternalLinkingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        opportunities = svc.get_opportunities(
            UUID(project_id),
            source_url=source_url if source_url else None,
            status=status,
            db_fn=_supabase_rest,
        )
        return {"opportunities": opportunities, "count": len(opportunities)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch opportunities: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/linking/opportunities/{opportunity_id}")
def approve_opportunity(
    opportunity_id: int,
    status: str = "approved",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Approve or implement a linking opportunity."""
    from app.services.internal_linking_service import InternalLinkingService

    try:
        svc = InternalLinkingService()

        if status == "approved":
            success = svc.approve_opportunity(opportunity_id, _supabase_rest)
        elif status == "implemented":
            success = svc.implement_link(opportunity_id, _supabase_rest)
        else:
            success = svc.reject_opportunity(opportunity_id, db_fn=_supabase_rest)

        if success:
            return {"status": status, "opportunity_id": opportunity_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to update")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update opportunity: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/linking/orphans")
async def identify_orphans(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Identify orphan pages in the site."""
    from app.services.internal_linking_service import InternalLinkingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        orphans = await svc.identify_orphans(UUID(project_id), _supabase_rest)
        return orphans

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to identify orphans: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Keyword mapping + clustering ──────────────────────────────────

class ImportKeywordsRequest(BaseModel):
    keywords: list[dict[str, Any]] = Field(..., description="List of keywords to import")


class ClusterKeywordsRequest(BaseModel):
    pass


@app.post("/keywords/import")
def import_keywords(
    body: ImportKeywordsRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Import keywords into a project."""
    from app.services.keyword_mapping_service import KeywordMappingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        result = svc.import_keywords(
            UUID(project_id),
            body.keywords,
            _supabase_rest,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to import keywords: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/keywords/cluster")
async def cluster_keywords(
    body: ClusterKeywordsRequest = None,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Cluster keywords by semantic similarity and intent."""
    from app.services.keyword_mapping_service import KeywordMappingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        clusters = await svc.cluster_keywords(UUID(project_id), _supabase_rest)
        return {"clusters": clusters, "count": len(clusters)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cluster keywords: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/keywords/assign")
async def assign_keywords(
    body: ClusterKeywordsRequest = None,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Assign keyword clusters to best-matching URLs."""
    from app.services.keyword_mapping_service import KeywordMappingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        assignments = await svc.assign_keywords_to_urls(UUID(project_id), _supabase_rest)
        return {"assignments": assignments, "count": len(assignments)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to assign keywords: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/keywords/clusters")
def get_clusters(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get all keyword clusters for a project."""
    from app.services.keyword_mapping_service import KeywordMappingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        clusters = svc.get_clusters(UUID(project_id), _supabase_rest)
        return {"clusters": clusters, "count": len(clusters)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch clusters: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/keywords/mappings")
def get_mappings(
    url: str = "",
    status: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get keyword-URL mappings."""
    from app.services.keyword_mapping_service import KeywordMappingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        mappings = svc.get_mappings(
            UUID(project_id),
            url=url if url else None,
            status=status,
            db_fn=_supabase_rest,
        )
        return {"mappings": mappings, "count": len(mappings)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch mappings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/keywords/gaps")
def get_gaps(
    gap_type: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Read stored keyword gaps. (POST /keywords/gaps/identify runs the analysis.)"""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        params = f"project_id=eq.{project_id}&order=priority.desc"
        if gap_type:
            params += f"&gap_type=eq.{gap_type}"
        gaps = _supabase_rest("get", "keyword_gaps", params=params)
        gaps = gaps if isinstance(gaps, list) else [gaps] if gaps else []
        return {"gaps": gaps, "count": len(gaps)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch gaps: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/keywords/gaps/identify")
async def identify_gaps(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Run AI gap analysis and store the results."""
    from app.services.keyword_mapping_service import KeywordMappingService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        gaps = await svc.identify_gaps(UUID(project_id), _supabase_rest)
        return gaps

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to identify gaps: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Multilingual + localization ───────────────────────────────────

class AddLanguageRequest(BaseModel):
    language_code: str = Field(..., min_length=2, max_length=10)
    region_code: str | None = None
    display_name: str = ""
    is_default: bool = False


class LocalizeContentRequest(BaseModel):
    source_url: str = ""
    source_content: str = ""
    source_title: str = ""
    source_keywords: list[str] = []
    target_language_id: int
    target_region: str | None = None


class AnalyzeHreflangRequest(BaseModel):
    source_url: str = ""


class IdentifyRegionalRequest(BaseModel):
    language_id: int
    competitor_regions: list[str] = []


@app.post("/multilingual/languages")
def add_language(
    body: AddLanguageRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Add a new language/region to the project."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        result = svc.add_language(
            UUID(project_id),
            body.language_code,
            body.region_code,
            body.display_name or body.language_code,
            body.is_default,
            _supabase_rest,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to add language: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/multilingual/languages")
def get_languages(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get all configured languages for a project."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        languages = svc.get_languages(UUID(project_id), _supabase_rest)
        return {"languages": languages, "count": len(languages)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch languages: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/multilingual/localize")
async def localize_content(
    body: LocalizeContentRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Translate and localize content for a target language."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        result = await svc.localize_content(
            UUID(project_id),
            body.source_url,
            body.source_content,
            body.source_title,
            body.source_keywords,
            body.target_language_id,
            body.target_region,
            _supabase_rest,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to localize content: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/multilingual/hreflang")
async def generate_hreflang(
    body: AnalyzeHreflangRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate hreflang strategy for language versions."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        hreflang = await svc.generate_hreflang_strategy(
            UUID(project_id),
            body.source_url,
            _supabase_rest,
        )
        return {"hreflang_links": hreflang, "count": len(hreflang)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to generate hreflang: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/multilingual/hreflang")
def get_hreflang_config(
    source_url: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get hreflang configuration."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        config = svc.get_hreflang_config(
            UUID(project_id),
            source_url=source_url if source_url else None,
            db_fn=_supabase_rest,
        )
        return {"hreflang_config": config, "count": len(config)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch hreflang config: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/multilingual/regional-opportunities")
async def identify_regional_opportunities(
    body: IdentifyRegionalRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Identify regional content opportunities."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        opportunities = await svc.identify_regional_opportunities(
            UUID(project_id),
            body.language_id,
            body.competitor_regions,
            _supabase_rest,
        )
        return {"opportunities": opportunities, "count": len(opportunities)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to identify regional opportunities: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/multilingual/regional-targeting")
def get_regional_targeting(
    language_id: int | None = None,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get regional targeting configuration."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        targeting = svc.get_regional_targeting(
            UUID(project_id),
            language_id=language_id,
            db_fn=_supabase_rest,
        )
        return {"regional_targeting": targeting, "count": len(targeting)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch regional targeting: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/multilingual/content")
def get_localized_content(
    language_id: int | None = None,
    source_url: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get localized content."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        content = svc.get_localized_content(
            UUID(project_id),
            language_id=language_id,
            source_url=source_url if source_url else None,
            db_fn=_supabase_rest,
        )
        return {"localized_content": content, "count": len(content)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch localized content: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/multilingual/analyze")
async def analyze_multilingual_seo(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Analyze multilingual SEO setup and identify gaps."""
    from app.services.multilingual_service import MultilingualService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        analysis = await svc.analyze_multilingual_setup(UUID(project_id), _supabase_rest)
        return analysis

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to analyze multilingual setup: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Content briefs + scoring ──────────────────────────────────────

class ContentBriefRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    domain: str = ""
    location_code: int = 2356
    language_code: str = "en"
    scrape_top_n: int = Field(5, ge=1, le=10)


class ContentScoreRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    url: str = ""
    markdown: str = ""
    brief: dict | None = None  # optional pre-generated brief payload
    location_code: int = 2356
    language_code: str = "en"


def _build_content_agent() -> ContentAgent:
    """Build a ContentAgent wired up with whichever clients are configured."""
    from app.clients.dataforseo_client import DataForSEOClient
    claude = _get_claude_client()
    firecrawl = None
    if settings.firecrawl_api_key:
        firecrawl = FirecrawlHTTPClient(api_key=settings.firecrawl_api_key)
    dfs = None
    if settings.dataforseo_login and settings.dataforseo_password:
        dfs = DataForSEOClient(
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
        )
    return ContentAgent(
        claude_client=claude,
        dataforseo_client=dfs,
        firecrawl_client=firecrawl,
    )


def _serialize_brief(brief) -> dict:
    return {
        "keyword": brief.keyword,
        "target_word_count": brief.target_word_count,
        "serp_median_words": brief.serp_median_words,
        "competitors": [
            {
                "url": c.url, "title": c.title,
                "word_count": c.word_count, "headings": c.headings,
                "position": c.position,
            }
            for c in brief.competitors
        ],
        "recommended_headings": brief.recommended_headings,
        "must_cover_entities": brief.must_cover_entities,
        "questions_to_answer": brief.questions_to_answer,
        "meta_title_suggestion": brief.meta_title_suggestion,
        "meta_description_suggestion": brief.meta_description_suggestion,
        "internal_links": brief.internal_links,
        "ai_overview_present": brief.ai_overview_present,
        "ai_overview_snippet": brief.ai_overview_snippet,
        "ai_generated": brief.ai_generated,
    }


def _serialize_score(score) -> dict:
    return {
        "keyword": score.keyword,
        "total": score.total,
        "word_count": score.word_count,
        "serp_median_words": score.serp_median_words,
        "breakdown": {
            "length": score.length_score,
            "headings": score.heading_score,
            "entities": score.entity_score,
            "questions": score.question_score,
            "keyword_usage": score.keyword_usage_score,
        },
        "missing_headings": score.missing_headings,
        "missing_entities": score.missing_entities,
        "missing_questions": score.missing_questions,
        "recommendations": score.recommendations,
    }


@app.post("/content/brief")
def content_brief(
    body: ContentBriefRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate a SERP-driven content brief for a keyword."""
    agent = _build_content_agent()
    brief = agent.generate_brief(
        keyword=body.keyword,
        domain=body.domain,
        location_code=body.location_code,
        language_code=body.language_code,
        scrape_top_n=body.scrape_top_n,
    )
    return _serialize_brief(brief)


@app.post("/content/score")
def content_score(
    body: ContentScoreRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Score content against the SERP competitive landscape."""
    if not body.url and not body.markdown:
        raise HTTPException(
            status_code=400,
            detail="Provide either `url` or `markdown`.",
        )
    from app.agents.content_agent import ContentBrief, CompetitorSummary
    agent = _build_content_agent()

    brief_obj = None
    if body.brief:
        b = body.brief
        brief_obj = ContentBrief(
            keyword=b.get("keyword", body.keyword),
            target_word_count=int(b.get("target_word_count", 1500)),
            serp_median_words=int(b.get("serp_median_words", 1500)),
            competitors=[
                CompetitorSummary(
                    url=c.get("url", ""), title=c.get("title", ""),
                    word_count=int(c.get("word_count") or 0),
                    headings=list(c.get("headings", [])),
                    position=c.get("position"),
                )
                for c in b.get("competitors", [])
            ],
            recommended_headings=list(b.get("recommended_headings", [])),
            must_cover_entities=list(b.get("must_cover_entities", [])),
            questions_to_answer=list(b.get("questions_to_answer", [])),
            meta_title_suggestion=b.get("meta_title_suggestion", ""),
            meta_description_suggestion=b.get("meta_description_suggestion", ""),
            internal_links=list(b.get("internal_links", [])),
            ai_overview_present=bool(b.get("ai_overview_present", False)),
            ai_overview_snippet=b.get("ai_overview_snippet", ""),
            ai_generated=bool(b.get("ai_generated", False)),
        )

    score = agent.score_content(
        keyword=body.keyword,
        url=body.url,
        markdown=body.markdown,
        brief=brief_obj,
    )
    return _serialize_score(score)


# ── Link-building ──────────────────────────────────────────────────

class BacklinkProfileRequest(BaseModel):
    domain: str = Field(..., min_length=3, max_length=200)
    anchors_limit: int = Field(20, ge=1, le=100)
    referring_limit: int = Field(20, ge=1, le=100)


class OutreachDraftRequest(BaseModel):
    prospect: dict
    campaign: dict | None = None
    template: str = Field("intro", pattern="^(intro|broken_link|guest_post|resource_page)$")


class LinkProspectCreate(BaseModel):
    project_id: str
    domain: str = Field(..., min_length=1, max_length=200)
    url: str = ""
    contact_name: str = ""
    contact_email: str = ""
    domain_rating: float | None = None
    referring_domains: int | None = None
    status: str = Field("new", pattern="^(new|researching|contacted|replied|agreed|placed|declined)$")
    template: str = ""
    subject: str = ""
    notes: str = ""
    already_linking: bool = False


class LinkProspectUpdate(BaseModel):
    domain: str | None = None
    url: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    domain_rating: float | None = None
    referring_domains: int | None = None
    status: str | None = Field(None, pattern="^(new|researching|contacted|replied|agreed|placed|declined)$")
    template: str | None = None
    subject: str | None = None
    notes: str | None = None
    already_linking: bool | None = None
    outreach_sent_at: str | None = None
    response_at: str | None = None
    placed_at: str | None = None


def _build_link_agent():
    from app.agents.link_agent import LinkAgent
    from app.clients.dataforseo_client import DataForSEOClient
    dfs = None
    if settings.dataforseo_login and settings.dataforseo_password:
        dfs = DataForSEOClient(
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
        )
    return LinkAgent(dataforseo_client=dfs, claude_client=_get_claude_client())


def _serialize_backlink_report(r) -> dict:
    return {
        "domain": r.domain,
        "total_backlinks": r.total_backlinks,
        "referring_domains": r.referring_domains,
        "domain_rank": r.domain_rank,
        "dofollow_ratio": r.dofollow_ratio,
        "top_anchors": r.top_anchors,
        "top_referring": r.top_referring,
        "warnings": r.warnings,
    }


@app.post("/links/backlinks")
def link_backlinks(
    body: BacklinkProfileRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Fetch a domain's backlink profile via DataForSEO."""
    agent = _build_link_agent()
    report = agent.backlink_profile(
        domain=body.domain,
        anchors_limit=body.anchors_limit,
        referring_limit=body.referring_limit,
    )
    return _serialize_backlink_report(report)


@app.post("/links/outreach/draft")
def link_outreach_draft(
    body: OutreachDraftRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Draft an outreach email for a given prospect + campaign."""
    agent = _build_link_agent()
    email = agent.draft_outreach_email(
        prospect=body.prospect,
        campaign=body.campaign,
        template=body.template,
    )
    return {
        "subject": email.subject,
        "body": email.body,
        "template": email.template,
        "model_used": email.model_used,
        "cost_usd": email.cost_usd,
        "fallback": email.fallback,
    }


@app.get("/projects/{project_id}/link-prospects")
def list_link_prospects(
    project_id: str,
    status: str = "",
    _auth: None = Depends(require_api_key),
):
    params = f"project_id=eq.{project_id}&order=created_at.desc&limit=200"
    if status:
        params = f"project_id=eq.{project_id}&status=eq.{status}&order=created_at.desc&limit=200"
    return _supabase_rest("get", "link_prospects", params=params)


@app.post("/projects/{project_id}/link-prospects")
def create_link_prospect(
    project_id: str,
    body: LinkProspectCreate,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.agents.link_agent import LinkAgent
    score = LinkAgent.score_prospect({
        "domain_rating": body.domain_rating,
        "referring_domains": body.referring_domains,
        "contact_email": body.contact_email,
        "already_linking": body.already_linking,
    })
    payload = body.model_dump()
    payload["project_id"] = project_id
    payload["opportunity_score"] = score
    data = _supabase_rest("post", "link_prospects", payload)
    return data[0] if isinstance(data, list) else data


@app.patch("/link-prospects/{prospect_id}")
def update_link_prospect(
    prospect_id: str,
    body: LinkProspectUpdate,
    _auth: None = Depends(require_api_key),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    updates["updated_at"] = "now()"
    data = _supabase_rest("patch", f"link_prospects?id=eq.{prospect_id}", updates)
    if not data:
        raise HTTPException(status_code=404, detail="Link prospect not found")
    return data[0]


@app.delete("/link-prospects/{prospect_id}")
def delete_link_prospect(
    prospect_id: str,
    _auth: None = Depends(require_api_key),
):
    _supabase_rest("delete", f"link_prospects?id=eq.{prospect_id}")
    return {"deleted": True}


@app.post("/link-prospects/{prospect_id}/draft-email")
def draft_prospect_email(
    prospect_id: str,
    body: OutreachDraftRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate an email draft for a persisted prospect and save subject+template."""
    rows = _supabase_rest("get", "link_prospects", params=f"id=eq.{prospect_id}")
    if not rows:
        raise HTTPException(status_code=404, detail="Link prospect not found")
    prospect_row = rows[0]

    merged_prospect = {
        "domain": prospect_row.get("domain"),
        "url": prospect_row.get("url"),
        "contact_name": prospect_row.get("contact_name"),
        "contact_email": prospect_row.get("contact_email"),
        "domain_rating": prospect_row.get("domain_rating"),
        "notes": prospect_row.get("notes"),
        **(body.prospect or {}),
    }
    agent = _build_link_agent()
    email = agent.draft_outreach_email(
        prospect=merged_prospect,
        campaign=body.campaign,
        template=body.template,
    )
    _supabase_rest(
        "patch", f"link_prospects?id=eq.{prospect_id}",
        {"subject": email.subject, "template": email.template, "updated_at": "now()"},
    )
    return {
        "subject": email.subject,
        "body": email.body,
        "template": email.template,
        "model_used": email.model_used,
        "cost_usd": email.cost_usd,
        "fallback": email.fallback,
    }


# ── White-label branding ──────────────────────────────────────────

class BrandingUpdate(BaseModel):
    agency_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    text_color: str | None = None
    background_color: str | None = None
    cover_title: str | None = None
    cover_subtitle: str | None = None
    footer_text: str | None = None
    website: str | None = None
    email: str | None = None
    enabled: bool | None = None


@app.get("/projects/{project_id}/branding")
def get_project_branding(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    from app.services.branding import BrandingConfig
    rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}&select=settings")
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")
    branding_dict = (rows[0].get("settings") or {}).get("branding") or {}
    cfg = BrandingConfig.from_dict(branding_dict)
    return {
        "branding": cfg.to_dict(),
        "validation_warnings": cfg.validate(),
    }


@app.patch("/projects/{project_id}/branding")
def update_project_branding(
    project_id: str,
    body: BrandingUpdate,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.branding import BrandingConfig
    rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}&select=settings")
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")
    settings_obj = rows[0].get("settings") or {}
    existing = settings_obj.get("branding") or {}
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    merged = {**existing, **updates}
    cfg = BrandingConfig.from_dict(merged)
    warnings = cfg.validate()
    if warnings:
        raise HTTPException(status_code=400, detail={"validation_warnings": warnings})
    settings_obj["branding"] = cfg.to_dict()
    _supabase_rest(
        "patch", f"projects?id=eq.{project_id}",
        {"settings": settings_obj},
    )
    return {"branding": cfg.to_dict()}


@app.post("/projects/{project_id}/branding/preview")
def preview_branded_report(
    project_id: str,
    body: BrandingUpdate | None = None,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Render a small sample report HTML with the given branding for preview."""
    from app.services.branding import BrandingConfig
    from app.services.report_generator import ReportGenerator
    rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    project = rows[0] if rows else {"name": "Preview", "domain": "example.com"}

    if body:
        overrides = {k: v for k, v in body.model_dump().items() if v is not None}
        existing = (project.get("settings") or {}).get("branding") or {}
        branding = BrandingConfig.from_dict({**existing, **overrides, "enabled": True})
    else:
        branding = BrandingConfig.from_dict(
            (project.get("settings") or {}).get("branding") or {},
        )
        branding.enabled = True

    gen = ReportGenerator()
    sample_keywords = [
        {"keyword": "seo software", "latest_position": 4, "previous_position": 7, "intent": "commercial"},
        {"keyword": "rank tracker", "latest_position": 12, "previous_position": 15, "intent": "commercial"},
        {"keyword": "content brief tool", "latest_position": 28, "previous_position": 31, "intent": "informational"},
    ]
    report = gen.generate_seo_report(
        project=project,
        keywords=sample_keywords,
        rank_data=sample_keywords,
        audit_data={"scores": {"performance": 82, "seo": 90, "accessibility": 88, "best_practices": 85}},
        branding=branding,
        white_label=True,
    )
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=report["html"])


# ── Programmatic SEO ──────────────────────────────────────────────

class ProgrammaticTemplate(BaseModel):
    name: str | None = None
    slug_template: str = "/{{slug}}"
    title_template: str = "{{title}}"
    meta_description_template: str = ""
    h1_template: str | None = None
    body_template: str = ""


class ProgrammaticGenerateRequest(BaseModel):
    template: ProgrammaticTemplate
    rows: list[dict] | None = None
    csv: str | None = None
    dedupe_on: str = "slug"
    max_pages: int = Field(500, ge=1, le=5000)


def _serialize_programmatic_page(page) -> dict:
    return {
        "slug": page.slug,
        "title": page.title,
        "meta_description": page.meta_description,
        "h1": page.h1,
        "body_markdown": page.body_markdown,
        "variables": page.variables,
        "warnings": page.warnings,
    }


@app.post("/programmatic/generate")
def generate_programmatic_pages(
    body: ProgrammaticGenerateRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate bulk SEO pages from a template + CSV/JSON dataset."""
    from app.agents.programmatic_agent import ProgrammaticAgent

    agent = ProgrammaticAgent()
    rows = body.rows
    if not rows and body.csv:
        rows = agent.parse_csv(body.csv)
    rows = rows or []

    template_dict = body.template.model_dump()
    if not template_dict.get("h1_template"):
        template_dict["h1_template"] = template_dict["title_template"]

    result = agent.generate(
        template_dict,
        rows,
        dedupe_on=body.dedupe_on,
        max_pages=body.max_pages,
    )
    return {
        "template_name": result.template_name,
        "total_rows": result.total_rows,
        "generated": result.generated,
        "skipped": result.skipped,
        "variables_used": result.variables_used,
        "warnings": result.warnings,
        "pages": [_serialize_programmatic_page(p) for p in result.pages],
    }


# ── Monthly workflow (Week 1-4 cadence) ────────────────────────────

class WorkflowRunRequest(BaseModel):
    only: list[str] | None = None
    triggered_by: str = "manual"


def _serialize_task_result(task) -> dict:
    return {
        "name": task.name,
        "status": task.status,
        "detail": task.detail,
        "data": task.data,
    }


def _serialize_workflow_run(run) -> dict:
    return {
        "project_id": run.project_id,
        "week": run.week,
        "week_label": run.week_label,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "completed": run.completed,
        "skipped": run.skipped,
        "failed": run.failed,
        "tasks": [_serialize_task_result(t) for t in run.tasks],
    }


def _fetch_project(project_id: str) -> dict | None:
    rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    return rows[0] if rows else None


@app.get("/workflow/schedule/{project_id}")
def workflow_schedule(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    """Return this week's Week 1-4 task list for the project."""
    from app.agents.workflow_agent import WorkflowAgent

    project = _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return WorkflowAgent().schedule_for(project)


@app.post("/workflow/run/{project_id}")
def workflow_run(
    project_id: str,
    body: WorkflowRunRequest | None = None,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Execute this week's workflow tasks for the project."""
    from app.agents.workflow_agent import WorkflowAgent

    project = _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    agent = WorkflowAgent()
    run = agent.run(project, only=(body.only if body else None))

    # Persist to workflow_runs (best-effort — don't fail the request if
    # the table/column isn't there yet; surface a warning header instead).
    try:
        _supabase_rest(
            "post", "workflow_runs",
            {
                "project_id": project_id,
                "week": run.week,
                "week_label": run.week_label,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "completed": run.completed,
                "skipped": run.skipped,
                "failed": run.failed,
                "tasks": [_serialize_task_result(t) for t in run.tasks],
                "triggered_by": (body.triggered_by if body else "manual"),
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Could not persist workflow_run: %s", exc)

    return _serialize_workflow_run(run)


@app.get("/workflow/runs/{project_id}")
def workflow_runs(
    project_id: str,
    limit: int = 20,
    _auth: None = Depends(require_api_key),
):
    """Most-recent workflow runs for the project."""
    try:
        rows = _supabase_rest(
            "get", "workflow_runs",
            params=f"project_id=eq.{project_id}&order=started_at.desc&limit={max(1, min(limit, 100))}",
        ) or []
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("workflow_runs fetch failed: %s", exc)
        rows = []
    return {"runs": rows}


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

@app.get("/projects/{project_id}/competitors")
def list_competitors(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    """List stored competitor intel for a project."""
    rows = _supabase_rest(
        "get", "competitor_intel",
        params=f"project_id=eq.{project_id}&order=captured_at.desc&limit=30",
    )
    return rows if isinstance(rows, list) else []


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


# ── Technical Audits ────────────────────────────────────────────────

class CreateAuditScheduleRequest(BaseModel):
    audit_type: str = Field(..., description="crawl_errors, broken_links, schema_validation, performance, orphan_pages")
    frequency: str = Field("weekly", description="daily, weekly, monthly, on_demand")
    config: dict[str, Any] | None = None


class RunAuditRequest(BaseModel):
    audit_type: str = Field(...)
    audit_data: list[dict[str, Any]] = Field(default_factory=list)


class UpdateIssueRequest(BaseModel):
    status: str = Field(..., description="open, in_progress, resolved, ignored")


class ResolveIssueRequest(BaseModel):
    resolution_type: str = Field(..., description="auto_fix, manual_fix, ignored, false_positive")
    resolution_details: str = ""


@app.post("/audits/schedule")
def create_audit_schedule(
    body: CreateAuditScheduleRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Create an audit schedule."""
    from app.services.audit_service import AuditService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        result = svc.create_audit_schedule(
            UUID(project_id),
            body.audit_type,
            body.frequency,
            body.config,
            _supabase_rest,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create audit schedule: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/audits/schedules")
def get_audit_schedules(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get all audit schedules for a project."""
    from app.services.audit_service import AuditService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        schedules = svc.get_audit_schedules(UUID(project_id), _supabase_rest)
        return {"schedules": schedules, "count": len(schedules)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch audit schedules: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def _org_crawl_budget(project: dict) -> tuple[int, str]:
    """Plan-gated crawl budget for the project's org. Trials get the trial cap."""
    from app.services.billing import crawl_budget_for

    plan, status = None, None
    org_id = project.get("org_id")
    if org_id:
        try:
            orgs = _supabase_rest(
                "get", "organizations", params=f"id=eq.{org_id}&select=plan,plan_status"
            )
            orgs = orgs if isinstance(orgs, list) else [orgs] if orgs else []
            if orgs:
                plan, status = orgs[0].get("plan"), orgs[0].get("plan_status")
        except Exception:
            pass
    budget = crawl_budget_for(plan, status)
    label = plan if status == "active" else "trial"
    return budget, label or "trial"


@app.post("/audits/run")
async def run_audit(
    body: RunAuditRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Run an audit. When no audit_data is supplied, the project's domain is
    crawled live (template-aware for large sites) within the org's plan budget."""
    from app.services.audit_service import AuditService
    from app.services.crawler_service import CrawlerService, crawl_to_audit_data
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project = projects[0] if isinstance(projects, list) else projects
    project_id = project["id"]

    try:
        audit_data = body.audit_data
        crawl_info = None
        if not audit_data:
            domain = project.get("domain") or str(project.get("client_url", ""))
            if not domain:
                raise HTTPException(status_code=400, detail="Project has no domain to crawl")
            budget, plan_label = _org_crawl_budget(project)
            # interactive requests stay snappy; scheduled audits use the full budget
            crawler = CrawlerService(max_pages=min(budget, 200))
            crawl_result = await crawler.crawl_site_smart(domain)
            if not crawl_result.pages:
                raise HTTPException(status_code=400, detail=f"Could not crawl {domain}")
            audit_data = crawl_to_audit_data(crawl_result, body.audit_type)
            crawl_info = {
                "pages_crawled": len(crawl_result.pages),
                "inventory_size": crawl_result.inventory_size,
                "skipped_by_robots": crawl_result.skipped_by_robots,
                "js_rendered": crawl_result.js_rendered_count,
                "js_render_unavailable": crawl_result.js_render_unavailable,
                "templates": crawl_result.templates[:15],
                "crawl_budget": budget,
                "plan": plan_label,
                "upgrade_hint": (
                    f"Crawled {len(crawl_result.pages)} of {crawl_result.inventory_size:,} known pages "
                    f"(plan budget: {budget}). Upgrade for deeper crawls."
                ) if crawl_result.inventory_size > budget else None,
            }

        svc = AuditService()
        result = await svc.run_audit(
            UUID(project_id),
            body.audit_type,
            audit_data,
            _supabase_rest,
        )
        if crawl_info:
            result["crawl"] = crawl_info
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to run audit: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Free Instant Audit (public lead-gen funnel) ─────────────────────

_public_audits: dict[str, dict] = {}  # in-memory store: audit_id -> report/status
_public_audit_rate: dict[str, list[float]] = {}  # ip -> request timestamps


class PublicAuditRequest(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)


def _check_public_rate_limit(ip: str, max_per_hour: int = 5) -> None:
    import time as _time
    now = _time.time()
    window = [t for t in _public_audit_rate.get(ip, []) if now - t < 3600]
    if len(window) >= max_per_hour:
        raise HTTPException(status_code=429, detail="Too many audits from this IP. Try again later.")
    window.append(now)
    _public_audit_rate[ip] = window


async def _run_public_audit(audit_id: str, domain: str, email: str) -> None:
    from app.services.crawler_service import CrawlerService, analyze_crawl

    _public_audits[audit_id]["status"] = "crawling"
    try:
        crawler = CrawlerService(max_pages=20)
        crawl_result = await crawler.crawl_site(domain)
        if not crawl_result.pages:
            raise ValueError(f"Could not reach {domain}")
        report = analyze_crawl(crawl_result)
        _public_audits[audit_id].update({"status": "completed", "report": report})

        # Persist lead best-effort (table may not exist yet on fresh installs)
        try:
            _supabase_rest("post", "audit_leads", {
                "id": audit_id,
                "email": email,
                "domain": report["domain"],
                "status": "completed",
                "score": report["score"],
                "report": report,
            })
        except Exception as exc:
            logger.warning("Could not persist audit lead: %s", exc)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Public audit failed for %s: %s", domain, exc)
        _public_audits[audit_id].update({"status": "failed", "error": str(exc)[:300]})


@app.post("/public/audit")
async def start_public_audit(
    body: PublicAuditRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Start a free instant audit. Public - no API key required."""
    import uuid as _uuid

    ip = request.client.host if request.client else "unknown"
    _check_public_rate_limit(ip)

    if "@" not in body.email or "." not in body.email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please provide a valid email address")

    # bound the in-memory store (multi-worker/GC safety; DB holds the record)
    if len(_public_audits) > 500:
        for old_key in list(_public_audits.keys())[:100]:
            _public_audits.pop(old_key, None)
    if len(_public_audit_rate) > 10_000:
        _public_audit_rate.clear()

    audit_id = str(_uuid.uuid4())
    _public_audits[audit_id] = {
        "status": "queued",
        "domain": body.domain,
        "email": body.email,
        "report": None,
    }
    background_tasks.add_task(_run_public_audit, audit_id, body.domain, body.email)
    return {"audit_id": audit_id, "status": "queued"}


@app.get("/public/audit/{audit_id}")
def get_public_audit(audit_id: str):
    """Poll a free audit's status/report. Public - no API key required."""
    entry = _public_audits.get(audit_id)
    if not entry:
        # different worker or restarted process: fall back to the DB record
        try:
            rows = _supabase_rest("get", "audit_leads", params=f"id=eq.{audit_id}")
            rows = rows if isinstance(rows, list) else [rows] if rows else []
            if rows:
                return {
                    "status": rows[0].get("status", "completed"),
                    "domain": rows[0].get("domain"),
                    "report": rows[0].get("report"),
                    "error": None,
                }
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Audit not found")
    return {
        "status": entry["status"],
        "domain": entry.get("domain"),
        "report": entry.get("report"),
        "error": entry.get("error"),
    }


# ── Edge snippet injection (works on ANY website) ───────────────────

from fastapi.responses import Response as _Response


@app.get("/edge/v1/omnirank.js")
def serve_edge_snippet():
    """The loader script clients embed. Public, heavily cacheable."""
    from app.services.edge_service import EDGE_SNIPPET_JS

    return _Response(
        content=EDGE_SNIPPET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/edge/v1/config")
def edge_config(token: str, url: str = "/"):
    """Directives for a page. Called by the snippet on every pageview - public."""
    from app.services.edge_service import EdgeService

    if not token or len(token) > 80:
        raise HTTPException(status_code=400, detail="Invalid token")
    try:
        result = EdgeService().resolve_directives(token, url, _supabase_rest)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("edge config lookup failed: %s", exc)
        result = None
    if result is None:
        # Unknown/disabled site: return an empty directive set so the
        # snippet never errors on the client's page.
        return {"directives": []}
    return result


class CreateEdgeSiteRequest(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)


class CreateEdgeRuleRequest(BaseModel):
    site_id: str
    url_pattern: str = "*"
    match_type: str = "exact"  # exact, prefix, contains, all
    rule_type: str  # schema, title, meta_description, canonical, hreflang, meta
    payload: dict[str, Any]
    notes: str = ""


class UpdateEdgeRuleRequest(BaseModel):
    enabled: bool | None = None
    url_pattern: str | None = None
    match_type: str | None = None
    payload: dict[str, Any] | None = None
    priority: int | None = None
    notes: str | None = None


@app.post("/edge/sites")
def create_edge_site(
    body: CreateEdgeSiteRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        site = EdgeService().create_site(project_id, body.domain, _supabase_rest)
        return site
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create edge site: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/edge/sites")
def list_edge_sites(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    sites = EdgeService().get_sites(project_id, _supabase_rest)
    return {"sites": sites, "count": len(sites)}


@app.post("/edge/sites/{site_id}/verify")
async def verify_edge_site(
    site_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    sites = _supabase_rest("get", "edge_sites", params=f"id=eq.{site_id}&project_id=eq.{project_id}")
    sites = sites if isinstance(sites, list) else [sites] if sites else []
    if not sites:
        raise HTTPException(status_code=404, detail="Site not found")

    result = await EdgeService().verify_site(sites[0], _supabase_rest)
    return result


@app.post("/edge/rules")
def create_edge_rule(
    body: CreateEdgeRuleRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        rule = EdgeService().create_rule(
            project_id,
            body.site_id,
            body.url_pattern,
            body.match_type,
            body.rule_type,
            body.payload,
            notes=body.notes,
            db_fn=_supabase_rest,
        )
        return rule
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create edge rule: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/edge/rules")
def list_edge_rules(
    site_id: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    rules = EdgeService().get_rules(project_id, site_id=site_id or None, db_fn=_supabase_rest)
    return {"rules": rules, "count": len(rules)}


@app.patch("/edge/rules/{rule_id}")
def update_edge_rule(
    rule_id: int,
    body: UpdateEdgeRuleRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    ok = EdgeService().update_rule(rule_id, changes, _supabase_rest, project_id=project_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Nothing to update")
    return {"updated": True, "rule_id": rule_id}


@app.delete("/edge/rules/{rule_id}")
def delete_edge_rule(
    rule_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    EdgeService().delete_rule(rule_id, _supabase_rest, project_id=project_id)
    return {"deleted": True, "rule_id": rule_id}


# ── Git write-back (PRs with SEO fixes for headless/JAMstack sites) ─

class ConnectRepoRequest(BaseModel):
    repo_owner: str = Field(..., min_length=1, max_length=255)
    repo_name: str = Field(..., min_length=1, max_length=255)
    base_branch: str = ""
    access_token: str = Field(..., min_length=10)


class FixFile(BaseModel):
    path: str = Field(..., min_length=1, max_length=500)
    content: str


class OpenFixPRRequest(BaseModel):
    connection_id: str
    title: str = Field(..., min_length=3, max_length=300)
    description: str = ""
    fix_type: str = "other"  # content, schema, meta, redirects, hreflang, other
    files: list[FixFile]


@app.post("/git/connect")
def connect_git_repo(
    body: ConnectRepoRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Connect a GitHub repository for PR-based SEO fixes."""
    from app.services.git_writeback_service import GitWritebackService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        svc = GitWritebackService()
        conn = svc.connect_repo(
            project_id, body.repo_owner, body.repo_name,
            body.base_branch, body.access_token, _supabase_rest,
        )
        return conn
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to connect repo: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach GitHub")


@app.get("/git/connections")
def list_git_connections(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.git_writeback_service import GitWritebackService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    conns = GitWritebackService().get_connections(project_id, _supabase_rest)
    return {"connections": conns, "count": len(conns)}


@app.delete("/git/connections/{connection_id}")
def delete_git_connection(
    connection_id: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.git_writeback_service import GitWritebackService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    GitWritebackService().delete_connection(connection_id, _supabase_rest, project_id=project_id)
    return {"deleted": True}


@app.post("/git/pr")
def open_fix_pr(
    body: OpenFixPRRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Open a pull request on the connected repo with SEO fix files."""
    from app.services.git_writeback_service import GitWritebackService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        svc = GitWritebackService()
        result = svc.open_fix_pr(
            project_id,
            body.connection_id,
            body.title,
            body.description,
            body.fix_type,
            [f.model_dump() for f in body.files],
            _supabase_rest,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to open PR: %s", exc)
        raise HTTPException(status_code=502, detail="Could not open the pull request on GitHub")


@app.get("/git/prs")
def list_fix_prs(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.git_writeback_service import GitWritebackService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    prs = GitWritebackService().list_prs(project_id, _supabase_rest)
    return {"pull_requests": prs, "count": len(prs)}


# ── Product-feed intelligence (SKU-scale listing optimization) ──────

class ImportFeedRequest(BaseModel):
    name: str = ""
    source_url: str = ""
    csv_text: str = ""


@app.post("/feeds/import")
async def import_product_feed(
    body: ImportFeedRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Import a product feed (URL to Google Merchant XML/CSV, or pasted CSV)."""
    from app.services.feed_service import FeedService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        result = await FeedService().import_feed(
            project_id, body.name, body.source_url, body.csv_text, _supabase_rest,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Feed import failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not import the feed")


@app.get("/feeds")
def list_product_feeds(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.feed_service import FeedService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    feeds = FeedService().get_feeds(project_id, _supabase_rest)
    return {"feeds": feeds, "count": len(feeds)}


@app.get("/feeds/{feed_id}/products")
def list_feed_products(
    feed_id: int,
    only_issues: bool = False,
    limit: int = 100,
    offset: int = 0,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.feed_service import FeedService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    products = FeedService().get_products(
        feed_id, _supabase_rest,
        only_issues=only_issues, limit=min(limit, 500), offset=offset,
        project_id=project_id,
    )
    return {"products": products, "count": len(products)}


def _require_feed_in_project(feed_id: int) -> str:
    """404 unless the feed belongs to the scoped project. Returns project_id."""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]
    rows = _supabase_rest(
        "get", "product_feeds", params=f"id=eq.{feed_id}&project_id=eq.{project_id}&select=id"
    )
    rows = rows if isinstance(rows, list) else [rows] if rows else []
    if not rows:
        raise HTTPException(status_code=404, detail="Feed not found")
    return project_id


@app.post("/feeds/{feed_id}/optimize")
async def optimize_feed_products(
    feed_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """AI-optimize titles/descriptions for products with issues (plan-limited)."""
    from app.services.feed_service import FeedService, feed_sku_budget_for

    _require_feed_in_project(feed_id)
    projects = _get_scoped_projects()
    project = projects[0] if isinstance(projects, list) else projects

    # plan-gated SKU budget
    plan, status = None, None
    org_id = project.get("org_id")
    if org_id:
        try:
            orgs = _supabase_rest("get", "organizations", params=f"id=eq.{org_id}&select=plan,plan_status")
            orgs = orgs if isinstance(orgs, list) else [orgs] if orgs else []
            if orgs:
                plan, status = orgs[0].get("plan"), orgs[0].get("plan_status")
        except Exception:
            pass
    budget = feed_sku_budget_for(plan, status)

    try:
        result = await FeedService().optimize_products(feed_id, budget, _supabase_rest)
        result["plan"] = plan if status == "active" else "trial"
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Feed optimization failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/feeds/{feed_id}/export")
def export_supplemental_feed(
    feed_id: int,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Download the optimized supplemental feed CSV for Google Merchant Center."""
    from app.services.feed_service import FeedService

    _require_feed_in_project(feed_id)
    csv_content = FeedService().export_supplemental_feed(feed_id, _supabase_rest)
    return _Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="omnirank-supplemental-feed-{feed_id}.csv"'},
    )


@app.get("/audits/runs")
def get_audit_runs(
    audit_type: str = "",
    status: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get audit runs."""
    from app.services.audit_service import AuditService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        runs = svc.get_audit_runs(
            UUID(project_id),
            audit_type=audit_type if audit_type else None,
            status=status,
            db_fn=_supabase_rest,
        )
        return {"runs": runs, "count": len(runs)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch audit runs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/audits/issues")
def get_audit_issues(
    issue_type: str = "",
    severity: str = "",
    status: str = "open",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get audit issues."""
    from app.services.audit_service import AuditService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        issues = svc.get_audit_issues(
            UUID(project_id),
            issue_type=issue_type if issue_type else None,
            severity=severity,
            status=status,
            db_fn=_supabase_rest,
        )
        return {"issues": issues, "count": len(issues)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch audit issues: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/audits/issues/{issue_id}")
def update_issue(
    issue_id: int,
    body: UpdateIssueRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Update issue status."""
    from app.services.audit_service import AuditService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        svc = AuditService()
        success = svc.update_issue_status(issue_id, body.status, _supabase_rest, project_id=project_id)

        if success:
            return {"status": body.status, "issue_id": issue_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to update")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update issue: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/audits/issues/{issue_id}/resolve")
def resolve_issue(
    issue_id: int,
    body: ResolveIssueRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Resolve an issue."""
    from app.services.audit_service import AuditService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        svc = AuditService()
        success = svc.resolve_issue(
            issue_id,
            body.resolution_type,
            body.resolution_details,
            db_fn=_supabase_rest,
            project_id=project_id,
        )

        if success:
            return {"status": "resolved", "issue_id": issue_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to resolve")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to resolve issue: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/audits/summary")
def get_audit_summary(
    days: int = 30,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get audit summary for a project."""
    from app.services.audit_service import AuditService
    from uuid import UUID

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        summary = svc.get_audit_summary(UUID(project_id), days, _supabase_rest)
        return summary

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch audit summary: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


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

    projects = _get_scoped_projects()
    projects = projects if isinstance(projects, list) else [projects] if projects else []
    org_id = projects[0].get("org_id", "") if projects else ""

    result = client.create_subscription(
        plan_id=plan_info["razorpay_plan_id"],
        customer_email=email,
        customer_name=name,
        org_id=org_id,
        plan_name=plan,
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

    try:
        if event == "subscription.activated":
            sub = payload.get("subscription", {}).get("entity", {})
            notes = sub.get("notes", {}) or {}
            org_id = notes.get("org_id", "")
            if org_id:
                _supabase_rest("patch", f"organizations?id=eq.{org_id}", {
                    "plan_status": "active",
                    **({"plan": notes["plan"]} if notes.get("plan") else {}),
                    "razorpay_subscription_id": sub.get("id"),
                })
            else:
                logger.error("Razorpay activation without org_id in notes: %s", sub.get("id"))

        elif event == "subscription.charged":
            sub = payload.get("subscription", {}).get("entity", {})
            payment = payload.get("payment", {}).get("entity", {})
            org_id = (sub.get("notes", {}) or {}).get("org_id", "")
            if org_id:
                _supabase_rest("post", "billing_events", {
                    "org_id": org_id,
                    "event_type": "payment_success",
                    "amount_inr": payment.get("amount"),
                    "razorpay_payment_id": payment.get("id"),
                    "metadata": {"subscription_id": sub.get("id")},
                })

        elif event in ("subscription.cancelled", "subscription.paused"):
            sub = payload.get("subscription", {}).get("entity", {})
            status = "cancelled" if "cancel" in event else "past_due"
            org_id = (sub.get("notes", {}) or {}).get("org_id", "")
            if org_id:
                _supabase_rest("patch", f"organizations?id=eq.{org_id}", {"plan_status": status})
    except Exception as exc:
        # log but acknowledge - a 500 makes the provider retry forever and
        # eventually disable the webhook
        logger.error("Razorpay webhook handling failed (%s): %s", event, exc)

    return {"received": True}


@app.get("/billing/plans")
def list_plans():
    """Public plan catalog with INR + USD pricing for the pricing page."""
    from app.services.billing import PLANS, stripe_price_id_for
    from app.services.billing import RazorpayClient, StripeClient

    return {
        "plans": [
            {
                "id": key,
                "name": p["name"],
                "price_inr": p["price_inr"],
                "price_usd": p.get("price_usd"),
                "max_projects": p["max_projects"],
                "max_keywords": p["max_keywords"],
            }
            for key, p in PLANS.items()
        ],
        "rails": {
            "razorpay": RazorpayClient().enabled,
            "stripe": StripeClient().enabled,
        },
    }


@app.post("/billing/stripe/checkout")
def create_stripe_checkout(
    plan: str,
    email: str = "",
    org_id: str = "",
    _auth: None = Depends(require_api_key),
):
    """Create a Stripe Checkout session (international payments)."""
    from app.services.billing import PLANS, StripeClient

    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {', '.join(PLANS.keys())}")

    client = StripeClient()
    if not client.enabled:
        raise HTTPException(status_code=400, detail="Stripe not configured.")

    if not org_id:
        # resolve the org from the scoped project - payments must never be
        # attributed to an arbitrary org
        projects = _get_scoped_projects()
        projects = projects if isinstance(projects, list) else [projects] if projects else []
        org_id = projects[0].get("org_id", "") if projects else ""
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found for this project")

    try:
        result = client.create_checkout_session(plan, org_id, customer_email=email)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Stripe checkout failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not create Stripe checkout session")


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe subscription webhooks."""
    from app.services.billing import StripeClient

    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    if not StripeClient.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    data = json.loads(body)
    event_type = data.get("type", "")
    obj = data.get("data", {}).get("object", {})
    logger.info("Stripe webhook: %s", event_type)

    def _org_id_of(o: dict) -> str:
        return (o.get("metadata") or {}).get("org_id", "")

    if event_type == "checkout.session.completed":
        org_id = _org_id_of(obj)
        plan = (obj.get("metadata") or {}).get("plan", "")
        if org_id:
            _supabase_rest("patch", f"organizations?id=eq.{org_id}", {
                "plan_status": "active",
                **({"plan": plan} if plan else {}),
                "stripe_customer_id": obj.get("customer") or "",
                "stripe_subscription_id": obj.get("subscription") or "",
            })

    elif event_type == "invoice.paid":
        org_id = _org_id_of(obj) or (obj.get("subscription_details", {}).get("metadata", {}) or {}).get("org_id", "")
        try:
            _supabase_rest("post", "billing_events", {
                "org_id": org_id,
                "event_type": "payment_success",
                "amount_inr": None,
                "metadata": {
                    "provider": "stripe",
                    "amount": obj.get("amount_paid"),
                    "currency": obj.get("currency"),
                    "invoice_id": obj.get("id"),
                },
            })
        except Exception as exc:
            logger.warning("Could not log stripe billing event: %s", exc)

    elif event_type == "invoice.payment_failed":
        org_id = _org_id_of(obj) or (obj.get("subscription_details", {}).get("metadata", {}) or {}).get("org_id", "")
        if org_id:
            _supabase_rest("patch", f"organizations?id=eq.{org_id}", {"plan_status": "past_due"})

    elif event_type == "customer.subscription.deleted":
        org_id = _org_id_of(obj)
        if org_id:
            _supabase_rest("patch", f"organizations?id=eq.{org_id}", {"plan_status": "cancelled"})

    return {"received": True}


# ── Wins / ROI counter ──────────────────────────────────────────────

@app.get("/wins/summary")
def get_wins_summary(
    days: int = 30,
    project_id: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Value delivered to the client in the window - powers the dashboard ROI counter."""
    from app.services.wins_service import WinsService

    if not project_id:
        projects = _get_scoped_projects()
        projects = projects if isinstance(projects, list) else [projects] if projects else []
        if not projects:
            raise HTTPException(status_code=400, detail="No projects found")
        project_id = projects[0]["id"]

    svc = WinsService()
    wins = svc.compute_wins(project_id, days=max(1, min(days, 365)), db_fn=_supabase_rest)
    return wins


# ── Autopilot scheduler lifecycle ───────────────────────────────────

@app.on_event("startup")
async def _start_autopilot_scheduler():
    import asyncio as _asyncio

    if not (settings.supabase_url and settings.supabase_service_role_key):
        logger.info("Autopilot scheduler not started (Supabase not configured)")
        return
    from app.services.scheduler import AutopilotScheduler
    scheduler = AutopilotScheduler(_supabase_rest, interval_seconds=300)
    app.state.autopilot = scheduler
    app.state.autopilot_task = _asyncio.create_task(scheduler.run_forever())


@app.on_event("shutdown")
async def _stop_autopilot_scheduler():
    scheduler = getattr(app.state, "autopilot", None)
    task = getattr(app.state, "autopilot_task", None)
    if scheduler:
        scheduler.stop()
    if task:
        task.cancel()


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
    report_result = generator.generate_seo_report(
        project=project_rows[0],
        keywords=keywords,
        white_label=white_label,
    )
    html = report_result["html"] if isinstance(report_result, dict) else report_result

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)

@app.get("/jobs/{job_id}/report")
def get_job_report(job_id: str):
    from fastapi.responses import HTMLResponse
    from app.services.pdf_report import generate_seo_report_html
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "completed" or not job.result:
        raise HTTPException(400, "Job not completed yet")

    result = job.result
    research_req = job.payload.get("research_request", job.payload)
    client_url = str(result.result.client_profile.url)
    primary_kw = research_req.get("primary_keyword", "")
    city = research_req.get("city", "")
    business_type = research_req.get("business_type", "")

    comps = [
        c.model_dump() if hasattr(c, "model_dump") else c.__dict__
        for c in result.result.competitor_profiles
    ]
    gap = (
        result.result.gap_analysis.model_dump()
        if hasattr(result.result.gap_analysis, "model_dump")
        else result.result.gap_analysis.__dict__
    )

    # Build keywords_with_ranks from job context if project_id present
    project_id = research_req.get("project_id", "")
    keywords_with_ranks = []
    if project_id:
        try:
            kw_rows = _supabase_rest("get", "keywords", params=f"project_id=eq.{project_id}&limit=20")
            keywords_with_ranks = [
                {"keyword": r.get("keyword", ""), "current_rank": r.get("latest_position")}
                for r in (kw_rows if isinstance(kw_rows, list) else [])
            ]
        except Exception:
            pass

    if not keywords_with_ranks:
        keywords_with_ranks = [{"keyword": primary_kw, "current_rank": None}]

    # Pull project branding if we have a project_id
    branding = None
    if project_id:
        try:
            proj_rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}&select=settings")
            if proj_rows:
                branding = (proj_rows[0].get("settings") or {}).get("branding")
        except Exception:
            branding = None

    html = generate_seo_report_html(
        client_url=client_url,
        keyword=primary_kw,
        seo_score=result.final_score,
        competitors=comps,
        gap_analysis=gap,
        recommendations=result.result.recommendations,
        raw_metrics=result.result.raw_metrics,
        project_name=project_id,
        keywords_with_ranks=keywords_with_ranks,
        city=city.title() if city else "",
        business_type=business_type,
        branding=branding,
    )
    return HTMLResponse(content=html)

@app.get("/api/llm/status")
def llm_status():
    return llm_client.get_status()

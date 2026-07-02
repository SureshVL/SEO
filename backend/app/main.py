"""OMNI-RANK OR-1 API — Production FastAPI application."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
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
    projects = _supabase_rest("get", "projects", params="limit=1")
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
    projects = _supabase_rest("get", "projects", params="limit=1")
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
    projects = _supabase_rest("get", "projects", params="limit=1")
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
    projects = _supabase_rest("get", "projects", params="limit=1")
    if not projects:
        raise HTTPException(status_code=400, detail="No projects found")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        _supabase_rest("delete", f"cms_credentials?project_id=eq.{project_id}&cms_platform=eq.{platform}", None)
        return {"status": "deleted", "platform": platform}
    except Exception as exc:
        logger.error("Failed to delete CMS credentials: %s", exc)
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

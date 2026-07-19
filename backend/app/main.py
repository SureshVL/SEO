"""OMNI-RANK OR-1 API — Production FastAPI application."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

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
from app.api.security import require_api_key as _require_api_key_header, require_project_access
from app.api.auth import resolve_user_org
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

# Fail fast in prod when shipped with dev-default secrets — a default JWT
# secret lets anyone forge tokens, and a default orchestrator key opens
# every API-key-protected endpoint.
if settings.environment.lower() == "prod":
    if settings.jwt_secret == "change-this-to-a-strong-secret":
        raise RuntimeError("JWT_SECRET is still the dev default — set a strong secret before running in prod")
    if settings.orchestrator_api_key == "dev-orchestrator-key" and not settings.orchestrator_keys_json:
        raise RuntimeError("ORCHESTRATOR_API_KEY is still the dev default — set a strong key before running in prod")

app = FastAPI(
    title="OMNI-RANK OR-1 API",
    version="2.0.0",
    description="AI-powered SEO Agent Platform",
)

# CORS for frontend. A wildcard origin cannot be combined with credentials,
# and echoing every origin with credentials is a vulnerability - so we use the
# explicit allowlist from config (comma-separated CORS_ORIGINS). The dashboard
# authenticates with bearer tokens/headers rather than cookies, so credentials
# are not required for it.
_cors_origins = [o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()]
if _cors_origins == ["*"] or not _cors_origins:
    # dev default: allow any origin but WITHOUT credentials (safe combination)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.environment.lower() == "prod":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

job_store = SQLiteJobStore(settings.job_store_path)

# ── Project scoping ─────────────────────────────────────────────────
# Clients select a project via the X-Project-ID header (or ?project_id=).
# Endpoints that resolve "the project" use _get_scoped_projects(), which
# honors that selection and falls back to the first project.
import contextvars

_scoped_project_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "scoped_project_id", default=""
)
# The org the current request is confined to. Empty = service/API-key caller
# (the platform operator) with cross-org access. Set = a logged-in end user,
# who may only touch their own org's data.
_scoped_org_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "scoped_org_id", default=""
)
_scoped_user_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "scoped_user_id", default=""
)

# Register AI router
app.include_router(ai_router, prefix="/api/ai")

@app.middleware("http")
async def _project_scope_middleware(request: Request, call_next):
    pid = request.headers.get("X-Project-ID", "") or request.query_params.get("project_id", "")
    p_tok = _scoped_project_id.set(pid.strip())
    o_tok = _scoped_org_id.set("")
    u_tok = _scoped_user_id.set("")
    # If a valid user JWT is present, confine the request to that user's org.
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from app.api.auth import _verify_token
            # Token verification may hit the network (Supabase); never run it
            # synchronously on the event loop or it blocks every other request.
            claims = await asyncio.to_thread(_verify_token, auth_header[7:].strip())
            uid = claims.get("sub", "")
            if uid:
                _scoped_user_id.set(uid)
                org = await asyncio.to_thread(resolve_user_org, uid, _supabase_rest)
                _scoped_org_id.set(org or "__none__")  # sentinel: user with no org sees nothing
        except Exception:
            pass  # invalid token -> endpoint auth dependency will reject
    try:
        return await call_next(request)
    finally:
        _scoped_project_id.reset(p_tok)
        _scoped_org_id.reset(o_tok)
        _scoped_user_id.reset(u_tok)


async def require_api_key(request: Request) -> str:
    """Auth dependency accepting EITHER a verified Supabase user JWT OR the
    service API key. JWT callers are org-scoped; API-key callers are not."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from app.api.auth import get_current_user
        await get_current_user(request)  # raises 401 if the JWT is invalid
        return "jwt"
    return _require_api_key_header(request.headers.get("X-API-KEY"))


def _get_scoped_projects():
    """Rows for the client-selected project, else the caller's first project.

    - JWT users are confined to their org: a project must belong to their org
      or it 404s, and the fallback only returns their org's projects.
    - Service/API-key callers (the operator) are unconstrained.
    An explicitly supplied but unknown/foreign project id is an error - never
    silently fall back to another tenant's project.
    """
    pid = _scoped_project_id.get()
    org_id = _scoped_org_id.get()

    if org_id == "__none__":
        raise HTTPException(status_code=403, detail="User is not attached to an organization")

    org_filter = f"&org_id=eq.{org_id}" if org_id else ""

    if pid:
        import re as _re
        if not _re.fullmatch(r"[0-9a-fA-F-]{32,36}", pid):
            raise HTTPException(status_code=400, detail="Invalid X-Project-ID")
        rows = _supabase_rest("get", "projects", params=f"id=eq.{pid}{org_filter}")
        if not rows:
            raise HTTPException(status_code=404, detail="Project not found")
        return rows

    return _supabase_rest("get", "projects", params=f"limit=1{org_filter}")


def _org_filter() -> str:
    """PostgREST filter fragment confining a query to the JWT user's org.
    Empty for service/API-key callers (the operator). Raises if the user has
    no org."""
    org_id = _scoped_org_id.get()
    if org_id == "__none__":
        raise HTTPException(status_code=403, detail="User is not attached to an organization")
    return f"&org_id=eq.{org_id}" if org_id else ""


def _require_owned_project(project_id: str) -> None:
    """404 unless the project belongs to the caller's org (no-op for operator)."""
    import re as _re
    if not _re.fullmatch(r"[0-9a-fA-F-]{32,36}", project_id):
        raise HTTPException(status_code=400, detail="Invalid project id")
    rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}{_org_filter()}&select=id")
    rows = rows if isinstance(rows, list) else [rows] if rows else []
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")

# Register AI router
app.include_router(ai_router, prefix="/api/ai")
app.include_router(analytics_router)

# Fail closed: never run with the committed default key or without one.
# (Set ENVIRONMENT=dev + ALLOW_DEFAULT_KEY=1 only for local throwaway testing.)
import os as _os
if settings.orchestrator_api_key in ("", "dev-orchestrator-key") and not settings.orchestrator_keys_json:
    if not (settings.environment.lower() == "dev" and _os.environ.get("ALLOW_DEFAULT_KEY") == "1"):
        raise RuntimeError(
            "Refusing to start with the default/empty orchestrator_api_key. "
            "Set a strong ORCHESTRATOR_API_KEY (or ORCHESTRATOR_KEYS_JSON)."
        )


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
        _require_api_key_header(api_key)
        return {"user_id": "api_key_user", "api_key": api_key, "role": "service"}

    raise HTTPException(status_code=401, detail="Authentication required. Send Bearer token or X-API-KEY.")


def _get_claude_client():
    """Create LLM client (Claude or Gemini based on config)."""
    return llm_client


def _llm_json(llm, *, messages, system=None, **kw):
    """complete_json wrapper for request handlers: surfaces provider outages
    as a clear 503 (rate limit) or 502 instead of an unexplained 500."""
    try:
        return llm.complete_json(messages=messages, system=system, **kw)
    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        logger.error("LLM call failed: %s", err[:300])
        if any(t in err.lower() for t in ("429", "rate", "quota", "exhausted", "resource")):
            raise HTTPException(
                status_code=503,
                detail="The AI provider is rate-limited right now (free-tier quota). "
                       "Wait a minute and retry, or add another provider API key in the backend .env.",
            )
        raise HTTPException(
            status_code=502,
            detail="AI analysis failed — the provider returned an error. Please try again shortly.",
        )


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


# ── Budget Keywords (PPC keyword mix for a spend target) ───────────
from pydantic import BaseModel, Field  # noqa: E402 (also imported below)


class OptimisedKeywordsRequest(BaseModel):
    budget_inr: float = Field(..., gt=0, le=10_000_000)
    seed_keyword: str = Field(..., min_length=1, max_length=200)
    url: str = ""
    mode: str = "balanced"  # aggressive | balanced | conservative
    region: str = "IN"
    locale: str = "en-US"


# How each mode weights volume (reach) vs relevance vs cheap clicks.
_BUDGET_MODE_WEIGHTS = {
    "aggressive":   {"volume": 0.55, "relevance": 0.25, "cheap": 0.20},
    "balanced":     {"volume": 0.35, "relevance": 0.35, "cheap": 0.30},
    "conservative": {"volume": 0.20, "relevance": 0.35, "cheap": 0.45},
}


def _build_optimised_keywords(body: OptimisedKeywordsRequest) -> dict:
    """Turn a monthly budget + seed into the best keyword mix that spend can buy.
    Serper provides live SERP context; the LLM expands + estimates CPC/volume;
    Python does the deterministic budget allocation."""
    mode = body.mode.lower() if body.mode.lower() in _BUDGET_MODE_WEIGHTS else "balanced"
    weights = _BUDGET_MODE_WEIGHTS[mode]

    # Live SERP context (grounds the suggestions in the real market).
    serp_titles: list[str] = []
    if settings.serper_api_key:
        try:
            serper = SerperHTTPClient(api_key=settings.serper_api_key)
            rows = serper.search_top_results(body.seed_keyword, body.locale, body.region, limit=8)
            serp_titles = [r.get("title", "") for r in rows if r.get("title")][:8]
        except Exception as exc:
            logger.warning("Serper context unavailable for budget keywords: %s", exc)

    llm = _get_llm_client()
    system = (
        "You are a paid-search strategist. Given a seed keyword and market, generate "
        "25-35 realistic PPC keyword candidates a business could bid on. For each, "
        "estimate CPC in INR (rupees, be realistic for the region — Indian CPCs are "
        "typically 5-120), monthly search volume, competition and intent. "
        'Respond ONLY as JSON: {"candidates":[{"keyword":"...","cpc_inr":<number>,'
        '"monthly_searches":<int>,"competition":"low|medium|high",'
        '"intent":"transactional|commercial|informational","relevance":<0-100>}]}'
    )
    user = (
        f"Seed keyword: {body.seed_keyword}\nMarket: {body.region} ({body.locale})\n"
        f"{'Site: ' + body.url if body.url else ''}\n"
        f"{'Live SERP titles: ' + ' | '.join(serp_titles) if serp_titles else ''}\n"
        f"Monthly budget: INR {int(body.budget_inr)}. Bias toward keywords that fit this budget."
    )
    parsed, _ = _llm_json(
        llm, messages=[{"role": "user", "content": user}],
        system=system, max_tokens=4096, temperature=0.3,
    )
    cands = parsed.get("candidates", []) if isinstance(parsed, dict) else []

    # Normalise + score each candidate under the chosen mode.
    clean = []
    for c in cands:
        if not isinstance(c, dict) or not c.get("keyword"):
            continue
        cpc = max(0.5, float(c.get("cpc_inr", 20) or 20))
        vol = max(0, int(c.get("monthly_searches", 0) or 0))
        rel = max(0, min(100, float(c.get("relevance", 50) or 50)))
        clean.append({
            "keyword": str(c.get("keyword"))[:120],
            "cpc_inr": round(cpc, 2),
            "monthly_searches": vol,
            "competition": c.get("competition", "medium"),
            "intent": c.get("intent", "commercial"),
            "relevance": round(rel),
            "_cpc": cpc, "_vol": vol, "_rel": rel,
        })
    if not clean:
        raise HTTPException(status_code=502, detail="Could not generate keyword candidates. Try again.")

    max_vol = max((c["_vol"] for c in clean), default=1) or 1
    max_cheap = max((1.0 / c["_cpc"] for c in clean), default=1) or 1
    for c in clean:
        vol_n = c["_vol"] / max_vol
        rel_n = c["_rel"] / 100.0
        cheap_n = (1.0 / c["_cpc"]) / max_cheap
        c["priority"] = round(
            (weights["volume"] * vol_n + weights["relevance"] * rel_n + weights["cheap"] * cheap_n) * 100, 1
        )
    clean.sort(key=lambda c: c["priority"], reverse=True)

    # Allocate the budget across the top keywords, weighted by priority.
    selected = clean[:12]
    total_pri = sum(c["priority"] for c in selected) or 1
    total_clicks = 0
    mix = []
    for c in selected:
        alloc = round(body.budget_inr * c["priority"] / total_pri, 2)
        clicks = int(alloc / c["_cpc"])
        total_clicks += clicks
        mix.append({
            "keyword": c["keyword"], "cpc_inr": c["cpc_inr"],
            "monthly_searches": c["monthly_searches"], "competition": c["competition"],
            "intent": c["intent"], "relevance": c["relevance"], "priority": c["priority"],
            "allocated_budget_inr": alloc, "estimated_clicks": clicks,
        })

    for c in clean:
        for k in ("_cpc", "_vol", "_rel"):
            c.pop(k, None)

    return {
        "seed_keyword": body.seed_keyword, "mode": mode, "budget_inr": body.budget_inr,
        "region": body.region, "total_estimated_clicks": total_clicks,
        "keywords_selected": len(mix), "recommended_mix": mix,
        "all_candidates": clean,
        "notes": "CPC and volume are AI estimates for planning; validate against Google Ads before spending.",
    }


@app.post("/keywords/optimised")
def optimised_keywords(
    body: OptimisedKeywordsRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate the best keyword mix a monthly budget can buy (PPC planning)."""
    return _build_optimised_keywords(body)


# ── CRO audit (conversion-rate optimization for a landing page) ─────

class CroAuditRequest(BaseModel):
    url: str
    goal: str = ""  # e.g. "sign up", "book a demo", "purchase"


def _validate_cro_url(url: str) -> None:
    from app.core.ssrf import validate_public_url, SSRFError

    try:
        validate_public_url(url)
    except SSRFError:
        raise HTTPException(status_code=400, detail="URL must be a public http(s) address.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL.")


def _execute_cro_audit(url: str, goal: str | None) -> dict:
    """Fetch + parse the page and run the LLM audit (no caching)."""
    import re as _re
    from app.core.ssrf import guarded_client

    try:
        with guarded_client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (OmniRank-CRO)"})
            html = resp.text[:200_000]
    except Exception:
        raise HTTPException(status_code=502, detail="Could not fetch that page.")

    ctas = [_re.sub(r"<[^>]+>", "", c).strip()
            for c in _re.findall(r"<(?:button|a)[^>]*>(.*?)</(?:button|a)>", html, _re.I | _re.S)]
    ctas = [c for c in ctas if 2 <= len(c) <= 40][:20]
    title_m = _re.search(r"<title[^>]*>(.*?)</title>", html, _re.I | _re.S)
    title = (title_m.group(1).strip() if title_m else "")
    text = _re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=_re.I | _re.S)
    text = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", text)).strip()[:4000]

    llm = _get_llm_client()
    system = (
        "You are a senior CRO (conversion-rate optimization) consultant. Audit a landing "
        "page and respond ONLY as JSON: {\"score\":<0-100>,\"summary\":\"1-2 sentences\","
        "\"issues\":[{\"category\":\"CTA|Trust|Copy|Form|Mobile|Value Prop|Social Proof|Urgency\","
        "\"severity\":\"high|medium|low\",\"finding\":\"...\",\"fix\":\"...\"}],"
        "\"quick_wins\":[\"...\"]}. Give 6-10 concrete, specific issues."
    )
    user = (
        f"URL: {url}\nConversion goal: {goal or 'primary conversion'}\n"
        f"Page title: {title}\nCTAs detected: {', '.join(ctas) or 'none found'}\n"
        f"Page copy excerpt: {text}"
    )
    parsed, _ = _llm_json(
        llm, messages=[{"role": "user", "content": user}], system=system,
        max_tokens=3000, temperature=0.3,
    )
    parsed = parsed if isinstance(parsed, dict) else {}
    score = parsed.get("score")
    try:
        score = round(float(score)) if score is not None else None
    except Exception:
        score = None
    return {
        "url": url, "goal": goal, "score": score,
        "summary": parsed.get("summary", ""),
        "issues": parsed.get("issues", []),
        "quick_wins": parsed.get("quick_wins", []),
        "ctas_detected": ctas[:12],
    }


@app.post("/cro/audit")
def cro_audit(
    body: CroAuditRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Audit a landing page for conversion issues (synchronous).

    LLM caching / provider failover / stale-serving happen centrally in the
    LLM client, so identical re-audits return instantly. Prefer POST
    /jobs/cro for UI use — the analysis can take a minute on first run.
    """
    _validate_cro_url(body.url)
    return _execute_cro_audit(body.url, body.goal)


@app.post("/jobs/cro", response_model=JobCreateResponse)
def create_cro_job(
    body: CroAuditRequest,
    background_tasks: BackgroundTasks,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
) -> JobCreateResponse:
    """Queue a CRO audit as a background job (poll GET /jobs/{id})."""
    _validate_cro_url(body.url)
    record = job_store.create_job({"type": "cro_audit", "url": body.url, "goal": body.goal})
    background_tasks.add_task(_run_cro_job, record.job_id)
    return JobCreateResponse(job_id=record.job_id, status=record.status)


def _run_cro_job(job_id: str) -> None:
    record = job_store.get_job(job_id)
    if not record:
        return
    try:
        job_store.mark_running(job_id)
        job_store.append_log(job_id, "Fetching and parsing the page…")
        result = _execute_cro_audit(record.payload["url"], record.payload.get("goal"))
        job_store.append_log(job_id, "CRO analysis complete")
        job_store.mark_success(job_id, result)
    except HTTPException as exc:
        job_store.mark_failed(job_id, str(exc.detail))
        job_store.append_log(job_id, f"Job failed: {exc.detail}", level="error")
    except Exception as exc:
        job_store.mark_failed(job_id, str(exc))
        job_store.append_log(job_id, f"Job failed: {exc}", level="error")


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


@app.get("/projects/{project_id}/ai-visibility/history")
def get_aeo_history(
    project_id: str,
    days: int = 30,
    _auth: None = Depends(require_api_key),
):
    """Get AEO (AI Visibility) tracking history for a project."""
    project_rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get keyword visibility history (last N days)
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    history_rows = _supabase_rest(
        "get", "keyword_ai_visibility",
        params=f"project_id=eq.{project_id}&created_at=gte.{cutoff}&order=created_at.asc",
    ) or []

    # Aggregate by date
    daily_data = {}
    for row in history_rows:
        date = row.get("created_at", "").split("T")[0]
        if date not in daily_data:
            daily_data[date] = {"overall_score": 0, "count": 0, "ai_overview_coverage": 0, "llm_citations": 0}
        daily_data[date]["overall_score"] += row.get("visibility_score", 0)
        daily_data[date]["ai_overview_coverage"] += (1 if row.get("ai_overview_cited") else 0)
        daily_data[date]["llm_citations"] += (1 if row.get("llm_citation_count", 0) > 0 else 0)
        daily_data[date]["count"] += 1

    # Calculate averages
    trends = [
        {
            "date": date,
            "overall_score": round(data["overall_score"] / data["count"], 1),
            "ai_overview_coverage": round((data["ai_overview_coverage"] / data["count"]) * 100, 1),
            "llm_citation_rate": round((data["llm_citations"] / data["count"]) * 100, 1),
        }
        for date, data in sorted(daily_data.items())
    ]

    return {
        "project_id": project_id,
        "days": days,
        "trends": trends,
        "latest": trends[-1] if trends else None,
    }


@app.get("/projects/{project_id}/ai-visibility/summary")
def get_aeo_summary(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    """Get current AEO visibility summary (latest snapshot)."""
    project_rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}")
    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get latest snapshot
    latest = _supabase_rest(
        "get", "keyword_ai_visibility",
        params=f"project_id=eq.{project_id}&order=created_at.desc&limit=100",
    ) or []

    if not latest:
        return {
            "project_id": project_id,
            "ai_visibility_score": None,
            "ai_overview_coverage": None,
            "llm_citation_rate": None,
            "total_keywords": 0,
            "engines": {},
        }

    # Calculate aggregate metrics
    total = len(latest)
    visibility_scores = [row.get("visibility_score", 0) for row in latest if row.get("visibility_score")]
    ai_overview_cited = sum(1 for row in latest if row.get("ai_overview_cited"))
    llm_cited = sum(1 for row in latest if row.get("llm_citation_count", 0) > 0)

    # Per-engine breakdown
    engines = {}
    for row in latest:
        for engine in ["chat_gpt", "perplexity", "gemini"]:
            if engine not in engines:
                engines[engine] = {"cited": 0, "mentioned": 0}
            if row.get(f"{engine}_citation_position"):
                engines[engine]["cited"] += 1
            elif row.get(f"{engine}_mentioned"):
                engines[engine]["mentioned"] += 1

    return {
        "project_id": project_id,
        "ai_visibility_score": round(sum(visibility_scores) / len(visibility_scores), 1) if visibility_scores else 0,
        "ai_overview_coverage": round((ai_overview_cited / total) * 100, 1) if total else 0,
        "llm_citation_rate": round((llm_cited / total) * 100, 1) if total else 0,
        "total_keywords": total,
        "engines": {
            engine: {
                "citation_rate": round((data["cited"] / total) * 100, 1) if total else 0,
                "mention_rate": round((data["mentioned"] / total) * 100, 1) if total else 0,
            }
            for engine, data in engines.items()
        },
    }


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        # Check if credentials already exist
        from app.core.secrets_crypto import encrypt
        from app.core.pgrest import q
        plat = q(body.cms_platform)
        existing = _supabase_rest("get", "cms_credentials", params=f"project_id=eq.{project_id}&cms_platform=eq.{plat}")

        enc_key = encrypt(body.api_key)
        enc_secret = encrypt(body.api_secret)
        if existing and isinstance(existing, list) and len(existing) > 0:
            # Update
            result = _supabase_rest("patch", f"cms_credentials?project_id=eq.{project_id}&cms_platform=eq.{plat}", {
                "endpoint_url": body.endpoint_url,
                "api_key": enc_key,
                "api_secret": enc_secret,
            })
        else:
            # Create
            result = _supabase_rest("post", "cms_credentials", {
                "project_id": project_id,
                "cms_platform": body.cms_platform,
                "endpoint_url": body.endpoint_url,
                "api_key": enc_key,
                "api_secret": enc_secret,
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
        raise HTTPException(status_code=500, detail="Internal error")


@app.get("/cms/credentials/{platform}")
def get_cms_credentials(
    platform: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Get saved CMS credentials for a platform."""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        from app.core.pgrest import q as _q
        result = _supabase_rest("get", "cms_credentials", params=f"project_id=eq.{project_id}&cms_platform=eq.{_q(platform)}")
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
        return {"platform": platform, "saved": False, "error": "Internal error"}


@app.delete("/cms/credentials/{platform}")
def delete_cms_credentials(
    platform: str,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Delete saved CMS credentials for a platform."""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        from app.core.pgrest import q as _q
        _supabase_rest("delete", f"cms_credentials?project_id=eq.{project_id}&cms_platform=eq.{_q(platform)}", None)
        return {"status": "deleted", "platform": platform}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete CMS credentials: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = CompetitorService()
        competitors = svc.get_competitors(UUID(project_id), db_fn=_supabase_rest)
        return {"competitors": competitors, "count": len(competitors)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch competitors: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        analysis = await svc.analyze_site_structure(UUID(project_id), _supabase_rest)
        return analysis

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to analyze site: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = InternalLinkingService()
        orphans = await svc.identify_orphans(UUID(project_id), _supabase_rest)
        return orphans

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to identify orphans: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        clusters = await svc.cluster_keywords(UUID(project_id), _supabase_rest)
        return {"clusters": clusters, "count": len(clusters)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cluster keywords: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        assignments = await svc.assign_keywords_to_urls(UUID(project_id), _supabase_rest)
        return {"assignments": assignments, "count": len(assignments)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to assign keywords: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        clusters = svc.get_clusters(UUID(project_id), _supabase_rest)
        return {"clusters": clusters, "count": len(clusters)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch clusters: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


@app.get("/keywords/gaps")
def get_gaps(
    gap_type: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Read stored keyword gaps. (POST /keywords/gaps/identify runs the analysis.)"""
    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = KeywordMappingService()
        gaps = await svc.identify_gaps(UUID(project_id), _supabase_rest)
        return gaps

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to identify gaps: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        languages = svc.get_languages(UUID(project_id), _supabase_rest)
        return {"languages": languages, "count": len(languages)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch languages: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = MultilingualService()
        analysis = await svc.analyze_multilingual_setup(UUID(project_id), _supabase_rest)
        return analysis

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to analyze multilingual setup: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        from app.core.pgrest import q as _q
        params = f"project_id=eq.{project_id}&status=eq.{_q(status)}&order=created_at.desc&limit=200"
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


def _build_workflow_handlers() -> dict:
    """Wire the Week 1-4 workflow tasks to whichever real engines are
    configured. Engines that aren't configured stay None — their tasks then
    report an honest skip instead of fake success."""
    from app.services.workflow_tasks import build_handlers

    claude = _get_claude_client()

    run_technical = None
    if settings.pagespeed_api_key:
        def run_technical(url: str) -> dict:
            r = _build_technical_agent().full_audit(url)
            return {
                "scores": {
                    "performance": r.performance_score,
                    "accessibility": r.accessibility_score,
                    "seo": r.seo_score,
                    "best_practices": r.best_practices_score,
                },
                "core_web_vitals": r.core_web_vitals,
                "actions": r.execution_queue,
                "issues_count": len(r.actions),
            }

    def detect_schema_fn(url: str) -> dict:
        return _serialize_schema_detection(_build_schema_agent().detect(url=url))

    make_brief = None
    if claude:
        def make_brief(keyword: str, domain: str) -> dict:
            return _serialize_brief(
                _build_content_agent().generate_brief(keyword=keyword, domain=domain)
            )

    def score_draft_fn(markdown: str, keyword: str) -> dict:
        return _serialize_score(
            _build_content_agent().score_content(keyword=keyword, markdown=markdown)
        )

    check_ranks = None
    if settings.serper_api_key:
        def check_ranks(batch: list[dict], domain: str) -> list:
            from app.services.rank_tracker import RankTracker
            tracker = RankTracker(serper_client=SerperHTTPClient(api_key=settings.serper_api_key))
            return tracker.check_batch(batch, domain)

    expand_kw = None
    if claude:
        def expand_kw(seeds: list[str], domain: str) -> list[str]:
            parsed, _resp = _llm_json(claude, messages=[{"role": "user", "content": (
                "You are an SEO strategist. Seed keywords: " + "; ".join(seeds)
                + (f". Business site: {domain}." if domain else "")
                + " Propose up to 12 long-tail keyword variants with clear buyer intent"
                " (services, pricing, comparisons, 'for <niche>' modifiers, location"
                " qualifiers). Avoid generic informational head terms."
                ' Respond ONLY with JSON: {"keywords": ["..."]}'
            )}], max_tokens=400, temperature=0.3)
            return [str(k).strip() for k in parsed.get("keywords", []) if str(k).strip()]

    report_fn = None
    if claude:
        def report_fn(project_id: str) -> dict:
            return generate_report(project_id)

    def find_decay_fn(project: dict) -> dict | None:
        """None → GSC not connected (honest skip); dict → decay report."""
        import asyncio
        try:
            return asyncio.run(_content_decay_core(
                project.get("id", ""), _default_gsc_site(project), 28,
            ))
        except HTTPException as exc:
            if exc.status_code == 400:
                return None
            raise

    return build_handlers(
        supabase_rest=_supabase_rest,
        run_technical_audit=run_technical,
        detect_schema=detect_schema_fn,
        make_brief=make_brief,
        score_draft=score_draft_fn,
        expand_keywords=expand_kw,
        check_ranks=check_ranks,
        generate_report=report_fn,
        find_decay=find_decay_fn,
    )


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

    agent = WorkflowAgent(task_handlers=_build_workflow_handlers())
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
    """Helper to call Supabase REST API.

    Every DB-backed endpoint funnels through here, so failures are translated
    into diagnosable HTTP errors centrally instead of leaking raw 500s.
    """
    import requests as req
    base = settings.supabase_url.rstrip("/") + "/rest/v1"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{base}/{path}{'?' + params if params else ''}"
    try:
        resp = getattr(req, method)(url, headers=headers, json=payload, timeout=20)
    except req.RequestException as exc:
        logger.error("Supabase unreachable (%s %s): %s", method, path, exc)
        raise HTTPException(status_code=503, detail="Database is unreachable — please retry shortly.")
    if resp.status_code in (401, 403):
        logger.error("Supabase auth rejected (%s %s): check SUPABASE_SERVICE_ROLE_KEY", method, path)
        raise HTTPException(
            status_code=503,
            detail="Database credentials are invalid or missing (SUPABASE_SERVICE_ROLE_KEY). Contact support.",
        )
    if resp.status_code == 404:
        logger.error("Supabase table missing (%s %s): %s", method, path, resp.text[:200])
        raise HTTPException(
            status_code=503,
            detail=f"Database table '{path.split('?')[0]}' is missing — run pending migrations.",
        )
    if resp.status_code >= 400:
        logger.error("Supabase error %s (%s %s): %s", resp.status_code, method, path, resp.text[:300])
        raise HTTPException(status_code=502, detail="Database request failed — please retry.")
    data = resp.json() if resp.content else []
    return data


@app.post("/projects", response_model=ProjectResponse)
def create_project(
    body: ProjectCreate,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    domain = body.domain or str(body.client_url).replace("https://", "").replace("http://", "").split("/")[0]
    row = {
        "name": body.name,
        "client_url": str(body.client_url),
        "domain": domain,
        "target_niche": body.target_niche,
        "goal_keywords": body.goal_keywords,
        "settings": body.settings,
    }
    # Stamp the creator's org so org-scoped listing can see the project.
    # Without this, a JWT user creates a project they can never list.
    org_id = _scoped_org_id.get()
    if org_id == "__none__":
        raise HTTPException(
            status_code=403,
            detail="Your user is not attached to an organization yet — cannot create a project.",
        )
    if org_id:
        row["org_id"] = org_id
    data = _supabase_rest("post", "projects", row)
    return data[0] if isinstance(data, list) else data


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    return _supabase_rest(
        "get", "projects", params=f"order=created_at.desc&limit=50{_org_filter()}"
    )


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    _auth: None = Depends(require_api_key),
):
    data = _supabase_rest("get", "projects", params=f"id=eq.{project_id}{_org_filter()}")
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")
    return data[0]


@app.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    _auth: None = Depends(require_api_key),
):
    _require_owned_project(project_id)
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
    _require_owned_project(project_id)
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


# ── Content decay (GSC-driven refresh loop) ────────────────────────

async def _content_decay_core(project_id: str, site_url: str, days: int = 28) -> dict:
    """Compare two GSC windows and flag decaying pages. Raises HTTPException
    400 when GSC isn't connected for the project."""
    import httpx as _httpx
    from urllib.parse import quote as _quote
    from datetime import date, timedelta
    from app.api.analytics import get_valid_access_token, _gsc_query
    from app.services.cache import cache_json_get, cache_json_set, cache_key
    from app.services.content_decay import analyze_decay, serialize_decay_item

    token = await get_valid_access_token(project_id, "gsc")
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Google Search Console is not connected for this project — connect it in Settings → Revenue Attribution first.",
        )

    today = date.today()
    now_start, now_end = today - timedelta(days=days), today
    prev_start, prev_end = today - timedelta(days=2 * days), today - timedelta(days=days + 1)

    ck = cache_key("content-decay-v1", project_id, site_url, str(days), now_end.isoformat())
    cached = cache_json_get(ck)
    if cached:
        return cached

    site_q = _quote(site_url, safe="")  # url-prefix properties contain '/' and ':'
    async with _httpx.AsyncClient(timeout=30.0) as client:
        pages_now = await _gsc_query(client, token, site_q, now_start.isoformat(), now_end.isoformat(), ["page"], 250)
        pages_prev = await _gsc_query(client, token, site_q, prev_start.isoformat(), prev_end.isoformat(), ["page"], 250)
        pq_now = await _gsc_query(client, token, site_q, now_start.isoformat(), now_end.isoformat(), ["page", "query"], 500)

    items = analyze_decay(pages_now, pages_prev, pq_now)
    result = {
        "project_id": project_id,
        "site_url": site_url,
        "window_days": days,
        "current_window": [now_start.isoformat(), now_end.isoformat()],
        "previous_window": [prev_start.isoformat(), prev_end.isoformat()],
        "pages_analyzed": len(pages_now),
        "decayed_count": len(items),
        "decayed": [serialize_decay_item(d) for d in items],
    }
    cache_json_set(ck, result, ttl=6 * 3600)
    return result


def _default_gsc_site(project: dict) -> str:
    domain = (project.get("domain") or "").replace("https://", "").replace("http://", "").rstrip("/")
    return f"sc-domain:{domain}"


@app.get("/projects/{project_id}/content-decay")
async def content_decay_report(
    project_id: str,
    site_url: str = "",
    days: int = 28,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Pages losing clicks/impressions/position vs the previous period."""
    project = _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    days = max(7, min(days, 90))
    return await _content_decay_core(project_id, site_url or _default_gsc_site(project), days)


class DecayRefreshRequest(BaseModel):
    page: str = Field(..., min_length=4, max_length=1000)
    queries: list[str] = Field(default_factory=list, max_length=10)
    reasons: list[str] = Field(default_factory=list, max_length=6)


@app.post("/projects/{project_id}/content-decay/refresh")
def content_decay_refresh(
    project_id: str,
    body: DecayRefreshRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Draft a refresh plan for a decaying page and queue it in Content Studio."""
    claude = _get_claude_client()
    if not claude:
        raise HTTPException(status_code=400, detail="AI features require an LLM API key.")
    project = _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.agents.research_agent import _scrape_page, _extract_from_html
    html = _scrape_page(body.page)
    extracted = _extract_from_html(html) if html else {}
    existing_heads = (extracted.get("h2s") or [])[:10]

    queries_txt = "; ".join(body.queries[:8]) or "(no query data)"
    parsed, _resp = _llm_json(claude, messages=[{"role": "user", "content": (
        f"A page is losing Google search traffic and needs a content refresh.\n"
        f"Page: {body.page}\n"
        f"Decay signals: {'; '.join(body.reasons[:4]) or 'declining clicks/impressions'}\n"
        f"Queries it should win back: {queries_txt}\n"
        f"Current page sections: {existing_heads or 'unknown (page may be JS-rendered)'}\n"
        f"Current word count: {extracted.get('word_count', 'unknown')}\n\n"
        "Produce a concrete refresh plan: which sections to update, what to add, "
        "and what to prune. Be specific to the declining queries — the goal is "
        "recovering those rankings, not a rewrite for its own sake.\n"
        'Respond ONLY with JSON: {"title": "...", "sections": [{"heading": "...", '
        '"action": "update|add|remove", "instruction": "..."}], "meta_description": "...", '
        '"notes": "..."}'
    )}], max_tokens=1200, temperature=0.3)

    sections = parsed.get("sections") or []
    outline = [f"# Refresh plan: {body.page}", ""]
    if body.reasons:
        outline += ["**Why:** " + "; ".join(body.reasons), ""]
    if body.queries:
        outline += ["**Queries to win back:** " + ", ".join(body.queries[:8]), ""]
    for s in sections:
        outline.append(f"## [{str(s.get('action', 'update')).upper()}] {s.get('heading', '')}")
        outline.append(str(s.get("instruction", "")))
        outline.append("")
    if parsed.get("meta_description"):
        outline += ["## [UPDATE] Meta description", str(parsed["meta_description"]), ""]
    if parsed.get("notes"):
        outline += ["---", str(parsed["notes"])]

    draft_id = None
    try:
        created = _supabase_rest("post", "content_queue", {
            "project_id": project_id,
            "content_type": "refresh",
            "title": parsed.get("title") or f"Refresh: {body.page}",
            "slug": "refresh-" + "-".join(body.page.rstrip("/").split("/")[-1].split()[:6])[:60],
            "body_markdown": "\n".join(outline),
            "target_keyword": (body.queries[0] if body.queries else ""),
        })
        if isinstance(created, list) and created:
            draft_id = created[0].get("id")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("decay refresh draft not persisted: %s", exc)

    return {
        "page": body.page,
        "title": parsed.get("title") or f"Refresh: {body.page}",
        "sections": sections,
        "draft_id": draft_id,
    }


# ── Content Queue ──────────────────────────────────────────────────

@app.get("/projects/{project_id}/content", response_model=list[ContentDraftResponse])
def list_content(
    project_id: str,
    status: str = "",
    _auth: None = Depends(require_api_key),
):
    params = f"project_id=eq.{project_id}&order=created_at.desc&limit=50"
    if status:
        from app.core.pgrest import q as _q
        params += f"&queue_status=eq.{_q(status)}"
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        schedules = svc.get_audit_schedules(UUID(project_id), _supabase_rest)
        return {"schedules": schedules, "count": len(schedules)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch audit schedules: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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


_edge_config_rate: dict[str, tuple[int, float]] = {}  # ip -> (count, window_start)


def _edge_config_rate_ok(ip: str, per_minute: int = 600) -> bool:
    import time as _t
    now = _t.time()
    count, start = _edge_config_rate.get(ip, (0, now))
    if now - start > 60:
        count, start = 0, now
    count += 1
    if len(_edge_config_rate) > 50_000:
        _edge_config_rate.clear()
    _edge_config_rate[ip] = (count, start)
    return count <= per_minute


@app.get("/edge/v1/config")
def edge_config(token: str, request: Request, url: str = "/"):
    """Directives for a page. Called by the snippet on every pageview - public."""
    from app.services.edge_service import EdgeService

    ip = request.client.host if request.client else "unknown"
    if not _edge_config_rate_ok(ip):
        raise HTTPException(status_code=429, detail="Rate limited")

    import re as _re
    if not token or not _re.fullmatch(r"or_[A-Za-z0-9_-]{1,80}", token):
        raise HTTPException(status_code=400, detail="Invalid token")
    try:
        result = EdgeService().resolve_directives(token, url, _supabase_rest)
    except Exception as exc:
        # Includes HTTPException from _supabase_rest: this endpoint runs in
        # visitors' browsers on customer sites, so a backend/db problem must
        # degrade to "no directives", never surface as an error there.
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
    project_id = projects[0]["id"] if isinstance(projects, list) else projects["id"]

    try:
        site = EdgeService().create_site(project_id, body.domain, _supabase_rest)
        return site
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create edge site: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


@app.get("/edge/sites")
def list_edge_sites(
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=500, detail="Internal error")


@app.get("/edge/rules")
def list_edge_rules(
    site_id: str = "",
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    from app.services.edge_service import EdgeService

    projects = _get_scoped_projects()
    if not projects:
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")
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
        raise HTTPException(status_code=500, detail="Internal error")


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
        raise HTTPException(status_code=400, detail="No project yet. Create a project first (Projects -> New) so this tool has a site to analyze.")

    project_id = projects[0]["id"] if isinstance(projects, list) else projects.get("id")

    try:
        svc = AuditService()
        summary = svc.get_audit_summary(UUID(project_id), days, _supabase_rest)
        return summary

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch audit summary: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error")


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

    # Enforce the plan's monthly report quota (was previously unchecked, so usage
    # could exceed the limit, e.g. "7/5"). Fail closed with a clear upgrade path.
    try:
        from app.services.billing import PLANS
        from datetime import datetime, timezone
        plan = "starter"
        org_id = project.get("org_id")
        if org_id:
            orgs = _supabase_rest("get", "organizations", params=f"id=eq.{org_id}&select=plan")
            if orgs:
                plan = (orgs[0].get("plan") or "starter").lower()
        limit = PLANS.get(plan, PLANS["starter"]).get("max_reports_per_month", 5)
        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        used_rows = _supabase_rest(
            "get", "reports",
            params=f"project_id=eq.{project_id}&created_at=gte.{month_start}&select=id")
        used = len(used_rows) if isinstance(used_rows, list) else 0
        if used >= limit:
            raise HTTPException(
                status_code=402,
                detail=f"Monthly report limit reached ({used}/{limit} on the {plan} plan). Upgrade to generate more.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Report quota check skipped (non-fatal): %s", exc)

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

    parsed, resp = _llm_json(
        claude, messages=[{"role": "user", "content": context}],
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
    interval: str = "month",
    _auth: None = Depends(require_api_key),
):
    from app.services.billing import PLANS, RazorpayClient
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {', '.join(PLANS.keys())}")
    if plan == "free":
        # Free tier has no checkout - activate directly (idempotent).
        projects = _get_scoped_projects()
        projects = projects if isinstance(projects, list) else [projects] if projects else []
        org_id = projects[0].get("org_id", "") if projects else ""
        if org_id:
            _supabase_rest("patch", f"organizations?id=eq.{org_id}",
                           {"plan": "free", "plan_status": "active"})
        return {"subscription_id": "", "checkout_url": "", "status": "active", "plan": "free"}

    plan_info = PLANS[plan]
    plan_id_key = "razorpay_plan_id_annual" if interval == "year" else "razorpay_plan_id"
    razorpay_plan_id = plan_info.get(plan_id_key) or plan_info.get("razorpay_plan_id")
    if not razorpay_plan_id:
        raise HTTPException(status_code=400, detail="Razorpay plan ID not configured for this plan.")

    client = RazorpayClient()
    if not client.enabled:
        raise HTTPException(status_code=400, detail="Razorpay not configured.")

    projects = _get_scoped_projects()
    projects = projects if isinstance(projects, list) else [projects] if projects else []
    org_id = projects[0].get("org_id", "") if projects else ""

    # annual = 1 charge/yr for 5 yrs, monthly = 12 charges/yr for 1 yr (Razorpay total_count semantics)
    total_count = 5 if interval == "year" else 12
    result = client.create_subscription(
        plan_id=razorpay_plan_id,
        customer_email=email,
        customer_name=name,
        org_id=org_id,
        plan_name=plan,
        total_count=total_count,
    )
    return {
        "subscription_id": result.subscription_id,
        "checkout_url": result.short_url,
        "status": result.status,
        "interval": interval,
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

def _webhook_already_processed(provider: str, event_id: str) -> bool:
    """Record a provider event id; return True if it was already seen (replay).

    Uses the DB unique constraint as the source of truth (survives restarts and
    is shared across workers). Fails open on DB errors so a transient outage
    doesn't drop a legitimate webhook."""
    if not event_id:
        return False
    try:
        rows = _supabase_rest("post", "webhook_events",
                              {"provider": provider, "event_id": event_id})
        # insert succeeded -> first time we've seen it
        return not rows
    except Exception:
        # unique-violation (already processed) OR table missing/transient error.
        # Distinguish by checking existence; if the row exists it's a replay.
        try:
            existing = _supabase_rest(
                "get", "webhook_events",
                params=f"provider=eq.{provider}&event_id=eq.{event_id}&select=id",
            )
            return bool(existing)
        except Exception:
            return False  # fail open


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

    # replay protection: Razorpay sends a unique delivery id per event
    event_id = request.headers.get("X-Razorpay-Event-Id", "") or data.get("id", "")
    if _webhook_already_processed("razorpay", event_id):
        logger.info("Razorpay webhook replay ignored: %s", event_id)
        return {"received": True, "duplicate": True}

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
    from app.services.billing import (
        ANNUAL_DISCOUNT,
        PLANS,
        RazorpayClient,
        StripeClient,
        annual_price_inr,
    )

    return {
        "plans": [
            {
                "id": key,
                "name": p["name"],
                "price_inr": p["price_inr"],
                "price_usd": p.get("price_usd"),
                "price_inr_annual": annual_price_inr(key),
                "max_projects": p["max_projects"],
                "max_keywords": p["max_keywords"],
                "serp_checks_per_day": p.get("serp_checks_per_day", 0),
                "ai_agents": p.get("ai_agents", 0),
            }
            for key, p in PLANS.items()
        ],
        "annual_discount": ANNUAL_DISCOUNT,
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
    interval: str = "month",
    _auth: None = Depends(require_api_key),
):
    """Create a Stripe Checkout session (international payments)."""
    from app.services.billing import PLANS, StripeClient

    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {', '.join(PLANS.keys())}")
    if plan == "free":
        # Free tier has no checkout - activate directly (idempotent).
        if not org_id:
            projects = _get_scoped_projects()
            projects = projects if isinstance(projects, list) else [projects] if projects else []
            org_id = projects[0].get("org_id", "") if projects else ""
        if org_id:
            _supabase_rest("patch", f"organizations?id=eq.{org_id}",
                           {"plan": "free", "plan_status": "active"})
        return {"checkout_url": "", "session_id": "", "plan": "free"}

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
        result = client.create_checkout_session(plan, org_id, customer_email=email, interval=interval)
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

    if _webhook_already_processed("stripe", data.get("id", "")):
        logger.info("Stripe webhook replay ignored: %s", data.get("id"))
        return {"received": True, "duplicate": True}

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

    empty_summary = {
        "project_id": None, "period_days": max(1, min(days, 365)),
        "stats": {}, "total_actions": 0, "value_inr": 0, "value_usd": 0,
        "empty": True,
    }
    if not project_id:
        # This tile loads on every dashboard render; a fresh account with no
        # project (or a transient lookup failure) is a normal empty state, not an
        # error — return a zeroed summary rather than 400/500.
        try:
            projects = _get_scoped_projects()
        except Exception:
            return empty_summary
        projects = projects if isinstance(projects, list) else [projects] if projects else []
        if not projects:
            return empty_summary
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

# ── Email & Subscription Management ──────────────────────────

@app.post("/email/subscribe")
def subscribe_to_research_report(
    email: str,
    vertical: str = "general",
    _rate: None = Depends(enforce_rate_limit),
):
    """Subscribe to monthly research report and nurture sequence."""
    # Validate email
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    try:
        from app.services.email_service import SubscriptionManager, get_email_service

        # Subscribe in database
        manager = SubscriptionManager(_supabase_rest)
        if not manager.subscribe(email, vertical, "research_report"):
            raise HTTPException(status_code=400, detail="Failed to subscribe")

        # Send welcome email with first report
        email_service = get_email_service()
        unsubscribe_link = f"https://omni-rank.com/email/unsubscribe?email={email}"
        email_service.send_research_report(email, unsubscribe_link)

        return {
            "status": "success",
            "message": f"Successfully subscribed {email} to research reports",
            "email": email,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        raise HTTPException(status_code=500, detail="Subscription failed")


@app.get("/email/unsubscribe")
def unsubscribe_from_emails(email: str):
    """Unsubscribe from all emails."""
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    try:
        from app.services.email_service import SubscriptionManager

        manager = SubscriptionManager(_supabase_rest)
        manager.unsubscribe(email)

        return {
            "status": "success",
            "message": f"{email} has been unsubscribed",
        }
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        raise HTTPException(status_code=500, detail="Unsubscribe failed")


@app.post("/cron/send-research-reports")
def send_monthly_research_reports(_auth: None = Depends(require_api_key)):
    """Cron job endpoint: Send monthly research reports to all subscribers.
    Run this monthly via external scheduler (GitHub Actions, AWS EventBridge, etc).
    Requires the orchestrator API key — an open endpoint here would let anyone
    trigger mass email sends."""
    try:
        from app.services.email_service import SubscriptionManager, get_email_service

        manager = SubscriptionManager(_supabase_rest)
        email_service = get_email_service()

        # Get all active subscribers
        subscribers = manager.get_active_subscribers(limit=1000)

        sent_count = 0
        failed_count = 0

        for subscriber in subscribers:
            email = subscriber.get("email")
            try:
                unsubscribe_link = f"https://omni-rank.com/email/unsubscribe?email={email}"
                if email_service.send_research_report(email, unsubscribe_link):
                    sent_count += 1
                    manager.update_subscription_state(email, 0, datetime.utcnow().isoformat())
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send report to {email}: {e}")
                failed_count += 1

        return {
            "status": "success",
            "sent": sent_count,
            "failed": failed_count,
            "total": len(subscribers),
        }
    except Exception as e:
        logger.error(f"Report distribution error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send reports")


@app.post("/cron/send-nurture-sequence")
def send_nurture_emails(_auth: None = Depends(require_api_key)):
    """Cron job endpoint: Send nurture emails to subscribers.
    Run this weekly via external scheduler. Requires the orchestrator API key."""
    try:
        from app.services.email_service import SubscriptionManager, get_email_service
        from datetime import datetime, timedelta

        manager = SubscriptionManager(_supabase_rest)
        email_service = get_email_service()

        # Get subscribers ready for next nurture email
        subscribers = manager.get_active_subscribers(limit=500)

        sent_count = 0
        for subscriber in subscribers:
            email = subscriber.get("email")
            vertical = subscriber.get("vertical", "general")
            sequence = subscriber.get("nurture_sequence", 0)
            last_sent = subscriber.get("last_email_sent")

            # Only send 1 nurture email per week
            if last_sent:
                last_sent_date = datetime.fromisoformat(last_sent)
                if (datetime.utcnow() - last_sent_date).days < 7:
                    continue

            # Send next email in sequence (max 3 emails)
            if sequence < 3:
                next_sequence = sequence + 1
                try:
                    unsubscribe_link = f"https://omni-rank.com/email/unsubscribe?email={email}"
                    if email_service.send_nurture_sequence(
                        email, next_sequence, vertical, unsubscribe_link
                    ):
                        manager.update_subscription_state(
                            email, next_sequence, datetime.utcnow().isoformat()
                        )
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send nurture email to {email}: {e}")

        return {
            "status": "success",
            "sent": sent_count,
        }
    except Exception as e:
        logger.error(f"Nurture sequence error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send nurture emails")


# ── AI Search Research Reports ──────────────────────────────────

@app.get("/api/research/reports/{vertical}/{month}")
def get_research_report(vertical: str, month: str):
    """Get a research report for a vertical and month."""
    from app.services.research_reports_service import ResearchReportsService

    service = ResearchReportsService(llm_client)
    report = service.get_report(vertical, month, _supabase_rest)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "vertical": report.vertical,
        "month": report.month,
        "status": report.status,
        "key_findings": report.key_findings,
        "ai_engines": report.ai_engines,
        "citations_analyzed": report.citations_analyzed,
        "top_movers": report.top_movers,
        "recommendations": report.recommendations,
    }


@app.get("/api/research/benchmarks/{vertical}")
def get_benchmark_data(vertical: str):
    """Get AI search benchmarks for a vertical."""
    from app.services.research_reports_service import ResearchReportsService

    service = ResearchReportsService(llm_client)
    data = service.get_benchmark_data(vertical, _supabase_rest)
    return data


@app.get("/api/research/latest")
def get_latest_reports():
    """Get latest research reports by vertical."""
    from app.services.research_reports_service import ResearchReportsService

    service = ResearchReportsService(llm_client)
    reports = service.get_latest_reports_by_vertical(limit=3, db_fn=_supabase_rest)

    return {
        "verticals": list(reports.keys()),
        "reports": {
            vertical: [
                {
                    "id": r.id,
                    "vertical": r.vertical,
                    "month": r.month,
                    "status": r.status,
                    "created_at": r.created_at,
                    "key_findings": r.key_findings,
                }
                for r in reports_list
            ]
            for vertical, reports_list in reports.items()
        },
    }


# ── Social Media Studio (Phase 1: generate + calendar + approvals) ──

from pydantic import BaseModel as _BaseModel


class SocialGenerateRequest(_BaseModel):
    topic: str
    platforms: list[str] = ["instagram", "facebook", "linkedin"]
    tone: str = "friendly"
    business_context: str = ""
    content_goal: str = "engagement"


class SocialPostCreate(_BaseModel):
    platform: str
    topic: str = ""
    caption: str
    hashtags: list[str] = []
    content_goal: str = "engagement"
    media_notes: str = ""
    scheduled_date: str | None = None


class SocialPostUpdate(_BaseModel):
    caption: str | None = None
    hashtags: list[str] | None = None
    topic: str | None = None
    content_goal: str | None = None
    media_notes: str | None = None
    scheduled_date: str | None = None
    status: str | None = None
    platform: str | None = None


class SocialRevisionRequest(_BaseModel):
    note: str


@app.post("/social/generate")
def social_generate(
    body: SocialGenerateRequest,
    _auth: None = Depends(require_api_key),
    _rate: None = Depends(enforce_rate_limit),
):
    """Generate platform-native captions + hashtags for a topic."""
    from app.services.social_media_service import generate_social_posts

    if not body.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")
    try:
        return generate_social_posts(
            llm_client,
            topic=body.topic,
            platforms=body.platforms,
            tone=body.tone,
            business_context=body.business_context,
            content_goal=body.content_goal,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Social generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed")


@app.get("/projects/{project_id}/social-posts")
def list_social_posts(
    project_id: str,
    status: str | None = None,
    platform: str | None = None,
    _auth: None = Depends(require_api_key),
):
    from app.services.social_media_service import SocialPostManager

    return SocialPostManager(_supabase_rest).list_posts(project_id, status, platform)


@app.post("/projects/{project_id}/social-posts")
def create_social_post(
    project_id: str,
    body: SocialPostCreate,
    _auth: None = Depends(require_api_key),
):
    from app.services.social_media_service import SocialPostManager

    try:
        return SocialPostManager(_supabase_rest).create_post(project_id, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/social-posts/{post_id}")
def update_social_post(
    post_id: str,
    body: SocialPostUpdate,
    _auth: None = Depends(require_api_key),
):
    from app.services.social_media_service import SocialPostManager

    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        return SocialPostManager(_supabase_rest).update_post(post_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/social-posts/{post_id}/approve")
def approve_social_post(post_id: str, _auth: None = Depends(require_api_key)):
    from app.services.social_media_service import SocialPostManager

    return SocialPostManager(_supabase_rest).approve(post_id)


@app.post("/social-posts/{post_id}/request-revision")
def request_social_revision(
    post_id: str,
    body: SocialRevisionRequest,
    _auth: None = Depends(require_api_key),
):
    from app.services.social_media_service import SocialPostManager

    try:
        return SocialPostManager(_supabase_rest).request_revision(post_id, body.note)
    except LookupError:
        raise HTTPException(status_code=404, detail="Post not found")
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.delete("/social-posts/{post_id}")
def delete_social_post(post_id: str, _auth: None = Depends(require_api_key)):
    from app.services.social_media_service import SocialPostManager

    SocialPostManager(_supabase_rest).delete_post(post_id)
    return {"deleted": True}


class SocialMetricsUpsert(_BaseModel):
    platform: str
    month: str  # 'YYYY-MM'
    reach: int = 0
    impressions: int = 0
    engagement: int = 0
    followers: int = 0
    website_clicks: int = 0
    whatsapp_clicks: int = 0
    enquiries: int = 0
    posts_published: int = 0
    notes: str = ""


@app.put("/projects/{project_id}/social-metrics")
def upsert_social_metrics(
    project_id: str,
    body: SocialMetricsUpsert,
    _auth: None = Depends(require_api_key),
):
    """Record (or update) one platform's metrics for a month."""
    from app.services.social_media_service import SUPPORTED_PLATFORMS
    from app.services.social_reports_service import SocialMetricsManager

    platform = body.platform.lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform. Supported: {SUPPORTED_PLATFORMS}")
    try:
        return SocialMetricsManager(_supabase_rest).upsert(
            project_id, platform, body.month, body.model_dump()
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="month must be 'YYYY-MM'")


@app.get("/projects/{project_id}/social-metrics")
def list_social_metrics(
    project_id: str,
    month: str,
    _auth: None = Depends(require_api_key),
):
    from app.services.social_reports_service import SocialMetricsManager

    return SocialMetricsManager(_supabase_rest).list_for_month(project_id, month)


@app.get("/projects/{project_id}/social-report/{month}")
def social_monthly_report(
    project_id: str,
    month: str,
    _auth: None = Depends(require_api_key),
):
    """Branded monthly social performance report (HTML, print-to-PDF ready)."""
    from fastapi.responses import HTMLResponse
    from app.services.social_reports_service import generate_social_report_html

    project_name = ""
    try:
        rows = _supabase_rest("get", "projects", params=f"id=eq.{project_id}&select=name")
        if rows:
            project_name = rows[0].get("name") or ""
    except Exception:
        pass

    try:
        html_out = generate_social_report_html(
            _supabase_rest, llm_client, project_id, month, project_name=project_name
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="month must be 'YYYY-MM'")
    return HTMLResponse(content=html_out)


@app.get("/api/llm/status")
def llm_status():
    return llm_client.get_status()

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.aso_agent import AsoAgent
from app.agents.content_agent import ContentAgent
from app.agents.deploy_agent import DeployAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.technical_agent import TechnicalAgent
from app.agents.workflow import SEOAutonomousLoop
from app.api.rate_limit import enforce_rate_limit
from app.api.security import require_api_key
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

app = FastAPI(title="OMNI-RANK OR-1 API", version="1.0.0")
job_store = SQLiteJobStore(settings.job_store_path)


if settings.environment.lower() == "prod" and settings.orchestrator_api_key == "dev-orchestrator-key":
    raise RuntimeError("Refusing to start in prod with default orchestrator_api_key")


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
    content_agent = ContentAgent()
    technical_agent = TechnicalAgent()
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
        actions = technical_agent.audit(research_result)
        execution = technical_agent.execute(actions)
        persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="technical_agent",
                action_type="generated_technical_actions",
                action_payload={"actions": execution},
            )
        )
        _log_job(f"Technical agent generated {len(actions)} actions.")

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

        payload = {"platform": aso_output.platform, "themes": aso_output.review_themes}

        persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="aso_agent",
                action_type="aso_remediation_executed",
                action_payload=payload,
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
                scraped_content=str(scraped.get(profile.url, "")),
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
    except Exception as exc:  # noqa: BLE001
        job_store.mark_failed(job_id, str(exc))
        job_store.append_log(job_id, f"Job failed: {exc}", level="error")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/research/run", response_model=WorkflowResponse)
def run_research(request: ResearchRequest, _auth: None = Depends(require_api_key), _rate: None = Depends(enforce_rate_limit)) -> WorkflowResponse:
    if not settings.serper_api_key or not settings.firecrawl_api_key:
        raise HTTPException(
            status_code=400,
            detail="SERPER_API_KEY and FIRECRAWL_API_KEY are required to execute /research/run.",
        )
    return _execute_research(request)


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
def list_jobs(_auth: None = Depends(require_api_key), _rate: None = Depends(enforce_rate_limit)) -> list[JobSummary]:
    return [
        JobSummary(
            job_id=record.job_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record in job_store.list_jobs()
    ]


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, _auth: None = Depends(require_api_key), _rate: None = Depends(enforce_rate_limit)) -> JobStatus:
    record = job_store.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        job_id=record.job_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        result=record.result,
        error=record.error,
        logs=record.logs or [],
    )


@app.get("/jobs/{job_id}/stream")
async def stream_job_logs(job_id: str, _auth: None = Depends(require_api_key), _rate: None = Depends(enforce_rate_limit)):
    if not job_store.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_seq = 0
        while True:
            record = job_store.get_job(job_id)
            if not record:
                yield "event: error\ndata: {\"message\": \"job_not_found\"}\n\n"
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


@app.post("/aso/run", response_model=AsoResponse)
def run_aso(request: AsoRequest, _auth: None = Depends(require_api_key), _rate: None = Depends(enforce_rate_limit)) -> AsoResponse:
    agent = AsoAgent()
    return agent.run(request)


@app.post("/deploy/run", response_model=DeployResponse)
def run_deploy(request: DeployRequest, _auth: None = Depends(require_api_key), _rate: None = Depends(enforce_rate_limit)) -> DeployResponse:
    return DeployAgent().run(request)

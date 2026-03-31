from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agents.aso_agent import AsoAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.workflow import SEOAutonomousLoop
from app.clients.http_clients import FirecrawlHTTPClient, SerperHTTPClient
from app.core.config import settings
from app.schemas.aso import AsoRequest, AsoResponse
from app.schemas.research import ResearchRequest, WorkflowResponse, WorkflowTrace
from app.services.persistence import (
    AgentLogEvent,
    CompetitorIntelEvent,
    NoopPersistenceRepository,
    PersistenceRepository,
    SupabaseRestRepository,
)

app = FastAPI(title="OMNI-RANK OR-1 API", version="0.4.0")


def _persistence_repo() -> PersistenceRepository:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseRestRepository(
            supabase_url=settings.supabase_url,
            supabase_service_role_key=settings.supabase_service_role_key,
        )
    return NoopPersistenceRepository()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/research/run", response_model=WorkflowResponse)
def run_research(request: ResearchRequest) -> WorkflowResponse:
    if not settings.serper_api_key or not settings.firecrawl_api_key:
        raise HTTPException(
            status_code=400,
            detail="SERPER_API_KEY and FIRECRAWL_API_KEY are required to execute /research/run.",
        )

    persistence = _persistence_repo()

    persistence.log_agent_event(
        AgentLogEvent(
            project_id=request.project_id,
            agent_name="orchestrator",
            action_type="research_run_started",
            action_payload={"keyword": request.primary_keyword, "client_url": str(request.client_url)},
        )
    )

    research_agent = AlgorithmicReverseEngineerAgent(
        serper_client=SerperHTTPClient(api_key=settings.serper_api_key),
        firecrawl_client=FirecrawlHTTPClient(api_key=settings.firecrawl_api_key),
    )
    loop = SEOAutonomousLoop(
        research_agent=research_agent,
        threshold=settings.seo_score_threshold,
        max_iters=settings.max_feedback_iterations,
        apply_content=lambda _: persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="content_agent",
                action_type="queued_content_remediation",
                action_payload={"reason": "score_below_threshold"},
            )
        ),
        apply_technical=lambda _: persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="technical_agent",
                action_type="queued_technical_remediation",
                action_payload={"reason": "score_below_threshold"},
            )
        ),
        apply_aso=lambda _: persistence.log_agent_event(
            AgentLogEvent(
                project_id=request.project_id,
                agent_name="aso_agent",
                action_type="queued_aso_remediation",
                action_payload={"reason": "score_below_threshold"},
            )
        ),
    )

    result = loop.run(request)

    for profile in result.response.competitor_profiles:
        persistence.save_competitor_intel(
            CompetitorIntelEvent(
                project_id=request.project_id,
                source_url=profile.url,
                scraped_content="",
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

    return WorkflowResponse(
        attempts=result.attempts,
        final_score=result.final_score,
        passed_threshold=result.passed_threshold,
        trace=WorkflowTrace(steps=result.trace),
        result=result.response,
    )


@app.post("/aso/run", response_model=AsoResponse)
def run_aso(request: AsoRequest) -> AsoResponse:
    agent = AsoAgent()
    return agent.run(request)

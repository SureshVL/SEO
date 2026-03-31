from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agents.aso_agent import AsoAgent
from app.agents.content_agent import ContentAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.technical_agent import TechnicalAgent
from app.agents.workflow import SEOAutonomousLoop
from app.clients.http_clients import FirecrawlHTTPClient, SerperHTTPClient
from app.core.config import settings
from app.schemas.aso import AsoRequest, AsoResponse
from app.schemas.orchestrator import OrchestratorRequest, OrchestratorResponse
from app.schemas.research import ResearchRequest, WorkflowResponse

app = FastAPI(title="OMNI-RANK OR-1 API", version="0.4.0")


def _build_research_agent() -> AlgorithmicReverseEngineerAgent:
    if not settings.serper_api_key or not settings.firecrawl_api_key:
        raise HTTPException(
            status_code=400,
            detail="SERPER_API_KEY and FIRECRAWL_API_KEY are required.",
        )
    return AlgorithmicReverseEngineerAgent(
        serper_client=SerperHTTPClient(api_key=settings.serper_api_key),
        firecrawl_client=FirecrawlHTTPClient(api_key=settings.firecrawl_api_key),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/research/run", response_model=WorkflowResponse)
def run_research(request: ResearchRequest) -> WorkflowResponse:
    research_agent = _build_research_agent()
    loop = SEOAutonomousLoop(
        research_agent=research_agent,
        threshold=settings.seo_score_threshold,
        max_iters=settings.max_feedback_iterations,
    )

    result = loop.run(request)
    return WorkflowResponse(
        attempts=result.attempts,
        final_score=result.final_score,
        passed_threshold=result.passed_threshold,
        result=result.response,
    )


@app.post("/aso/run", response_model=AsoResponse)
def run_aso(request: AsoRequest) -> AsoResponse:
    agent = AsoAgent()
    return agent.run(request)


@app.post("/orchestrator/run", response_model=OrchestratorResponse)
def run_orchestrator(request: OrchestratorRequest) -> OrchestratorResponse:
    research_agent = _build_research_agent()
    orchestrator = OrchestratorAgent(
        research_agent=research_agent,
        aso_agent=AsoAgent(),
        content_agent=ContentAgent(),
        technical_agent=TechnicalAgent(),
        threshold=settings.seo_score_threshold,
        max_cycles=request.max_cycles,
    )
    return orchestrator.run(request)

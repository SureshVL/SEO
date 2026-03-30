from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.workflow import SEOAutonomousLoop
from app.clients.http_clients import FirecrawlHTTPClient, SerperHTTPClient
from app.core.config import settings
from app.schemas.research import ResearchRequest, WorkflowResponse

app = FastAPI(title="OMNI-RANK OR-1 API", version="0.2.0")


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

    research_agent = AlgorithmicReverseEngineerAgent(
        serper_client=SerperHTTPClient(api_key=settings.serper_api_key),
        firecrawl_client=FirecrawlHTTPClient(api_key=settings.firecrawl_api_key),
    )
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

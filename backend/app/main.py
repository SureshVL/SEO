from fastapi import FastAPI, HTTPException

from app.core.config import settings
from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research_service import ResearchService

app = FastAPI(title="OMNI-RANK OR-1 API", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/research/run", response_model=ResearchResponse)
def run_research(request: ResearchRequest) -> ResearchResponse:
    if not settings.serper_api_key or not settings.firecrawl_api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing SERPER_API_KEY or FIRECRAWL_API_KEY in backend environment.",
        )

    service = ResearchService(
        serper_api_key=settings.serper_api_key,
        firecrawl_api_key=settings.firecrawl_api_key,
    )
    return service.run(request)

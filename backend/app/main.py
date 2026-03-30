from fastapi import FastAPI

from app.schemas.research import ResearchRequest

app = FastAPI(title="OMNI-RANK OR-1 API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research/run")
def run_research(request: ResearchRequest) -> dict[str, str]:
    # Placeholder endpoint. Wire in dependency-injected clients and agent runtime.
    return {
        "message": (
            "Research agent endpoint scaffolded. "
            "Instantiate AlgorithmicReverseEngineerAgent in service layer."
        ),
        "target": str(request.client_url),
    }

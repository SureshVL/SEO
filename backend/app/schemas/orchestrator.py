from pydantic import BaseModel, Field, HttpUrl

from app.schemas.aso import AsoResponse
from app.schemas.research import ResearchResponse


class OrchestratorRequest(BaseModel):
    client_url: HttpUrl
    primary_keyword: str = Field(min_length=2)
    target_region: str = "US"
    locale: str = "en-US"
    app_link: HttpUrl | None = None
    app_name: str | None = None
    app_category: str | None = None
    secondary_keywords: list[str] = Field(default_factory=list)
    max_cycles: int = Field(default=3, ge=1, le=10)


class AgentLogEntry(BaseModel):
    step: str
    status: str
    detail: str


class ContentQueueItem(BaseModel):
    title: str
    slug: str
    body_markdown: str
    target_keyword: str


class TechnicalFix(BaseModel):
    issue: str
    recommendation: str
    priority: str


class OrchestratorResponse(BaseModel):
    cycles: int
    final_score: float
    threshold_met: bool
    research: ResearchResponse
    aso: AsoResponse | None = None
    technical_fixes: list[TechnicalFix] = Field(default_factory=list)
    content_queue: list[ContentQueueItem] = Field(default_factory=list)
    logs: list[AgentLogEntry] = Field(default_factory=list)

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ResearchRequest(BaseModel):
    client_url: HttpUrl
    primary_keyword: str = Field(min_length=2)
    locale: str = Field(default="en-US")
    target_region: str = Field(default="US")
    project_id: str = Field(default="")
    app_link: HttpUrl | None = None
    app_name: str | None = None
    app_category: str | None = None
    city: str | None = None          # Indian city code e.g. "hyderabad"
    business_type: str | None = None  # e.g. "restaurant", "saas"


class CompetitorPageProfile(BaseModel):
    url: str
    title: str
    h1: str | None = None
    h2: list[str] = Field(default_factory=list)
    top_entities: list[str] = Field(default_factory=list)
    top_questions: list[str] = Field(default_factory=list)
    word_count: int = 0
    keyword_density: float = 0.0


class GapAnalysis(BaseModel):
    missing_entities: list[str] = Field(default_factory=list)
    missing_questions: list[str] = Field(default_factory=list)
    heading_gaps: list[str] = Field(default_factory=list)
    density_gap: float = 0.0


class ResearchResponse(BaseModel):
    seo_score: float
    competitor_profiles: list[CompetitorPageProfile]
    client_profile: CompetitorPageProfile
    gap_analysis: GapAnalysis
    recommendations: list[str]
    # Plain-language "what this means and what to do first" written for the
    # site owner, generated from the findings (empty when unavailable).
    analyst_summary: str = ""
    raw_metrics: dict[str, Any] = Field(default_factory=dict)


class WorkflowTrace(BaseModel):
    steps: list[str] = Field(default_factory=list)


class WorkflowResponse(BaseModel):
    attempts: int
    final_score: float
    passed_threshold: bool
    trace: WorkflowTrace
    result: ResearchResponse

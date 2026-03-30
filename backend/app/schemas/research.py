from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ResearchRequest(BaseModel):
    client_url: HttpUrl
    primary_keyword: str = Field(min_length=2)
    locale: str = Field(default="en-US")
    target_region: str = Field(default="US")


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
    raw_metrics: dict[str, Any] = Field(default_factory=dict)

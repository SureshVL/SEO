from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.research import ResearchRequest, WorkflowResponse


class JobCreateRequest(BaseModel):
    research_request: ResearchRequest


class JobStatus(BaseModel):
    job_id: str
    status: str = Field(default="pending")
    created_at: datetime
    updated_at: datetime
    result: WorkflowResponse | None = None
    error: str | None = None
    logs: list[dict[str, Any]] = Field(default_factory=list)


class JobSummary(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class JobCreateResponse(BaseModel):
    job_id: str
    status: str

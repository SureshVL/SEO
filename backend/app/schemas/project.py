"""Project and keyword management schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_url: HttpUrl
    domain: str | None = None
    target_niche: str | None = None
    goal_keywords: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_url: HttpUrl | None = None
    domain: str | None = None
    target_niche: str | None = None
    status: str | None = None
    settings: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client_url: str
    domain: str | None = None
    target_niche: str | None = None
    status: str = "active"
    goal_keywords: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class KeywordCreate(BaseModel):
    keyword: str = Field(min_length=1)
    locale: str = "en-US"
    target_region: str = "IN"
    intent: str | None = None
    is_primary: bool = False
    tags: list[str] = Field(default_factory=list)


class KeywordResponse(BaseModel):
    id: str
    keyword: str
    locale: str
    target_region: str
    search_volume: int | None = None
    difficulty: float | None = None
    intent: str | None = None
    is_primary: bool = False
    tags: list[str] = Field(default_factory=list)
    latest_position: int | None = None
    previous_position: int | None = None


class RankHistoryPoint(BaseModel):
    position: int | None
    url: str | None
    serp_features: list[str] = Field(default_factory=list)
    checked_at: datetime


class ContentDraftCreate(BaseModel):
    title: str
    body_markdown: str
    target_keyword: str
    meta_description: str = ""
    publish_target: str = "wordpress"


class ContentDraftResponse(BaseModel):
    id: str
    title: str
    slug: str | None
    body_markdown: str
    target_keyword: str | None
    queue_status: str = "draft"
    publish_target: str | None
    created_at: datetime
    updated_at: datetime

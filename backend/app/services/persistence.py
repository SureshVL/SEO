from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import requests


@dataclass
class AgentLogEvent:
    project_id: str
    agent_name: str
    action_type: str
    action_payload: dict[str, Any]
    status: str = "ok"


@dataclass
class CompetitorIntelEvent:
    project_id: str
    source_url: str
    scraped_content: str
    entity_maps: dict[str, Any]
    backlink_profiles: dict[str, Any] | None = None


@dataclass
class ContentQueueEvent:
    project_id: str
    content_type: str
    title: str
    slug: str
    body_markdown: str
    target_keyword: str
    publish_target: str = "wordpress"


class PersistenceRepository(Protocol):
    def log_agent_event(self, event: AgentLogEvent) -> None:
        ...

    def save_competitor_intel(self, event: CompetitorIntelEvent) -> None:
        ...

    def queue_content(self, event: ContentQueueEvent) -> None:
        ...


class NoopPersistenceRepository:
    """Safe fallback repository for local/dev when Supabase credentials are unavailable."""

    def log_agent_event(self, event: AgentLogEvent) -> None:
        _ = event

    def save_competitor_intel(self, event: CompetitorIntelEvent) -> None:
        _ = event

    def queue_content(self, event: ContentQueueEvent) -> None:
        _ = event


class SupabaseRestRepository:
    def __init__(self, supabase_url: str, supabase_service_role_key: str, timeout: int = 20):
        self.base = supabase_url.rstrip("/") + "/rest/v1"
        self.timeout = timeout
        self.headers = {
            "apikey": supabase_service_role_key,
            "Authorization": f"Bearer {supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def log_agent_event(self, event: AgentLogEvent) -> None:
        payload = {
            "project_id": event.project_id,
            "agent_name": event.agent_name,
            "action_type": event.action_type,
            "action_payload": event.action_payload,
            "status": event.status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._insert("agent_logs", payload)

    def save_competitor_intel(self, event: CompetitorIntelEvent) -> None:
        payload = {
            "project_id": event.project_id,
            "source_url": event.source_url,
            "scraped_content": event.scraped_content,
            "entity_maps": event.entity_maps,
            "backlink_profiles": event.backlink_profiles or {},
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        self._insert("competitor_intel", payload)

    def queue_content(self, event: ContentQueueEvent) -> None:
        payload = {
            "project_id": event.project_id,
            "content_type": event.content_type,
            "title": event.title,
            "slug": event.slug,
            "body_markdown": event.body_markdown,
            "target_keyword": event.target_keyword,
            "publish_target": event.publish_target,
            "queue_status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._insert("content_queue", payload)

    def _insert(self, table: str, payload: dict[str, Any]) -> None:
        response = requests.post(
            f"{self.base}/{table}",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

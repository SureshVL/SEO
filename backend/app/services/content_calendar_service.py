"""Content calendar and automated publishing service."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from app.clients.cms_client import get_cms_client
from app.core.secrets_crypto import decrypt

logger = logging.getLogger("omnirank.calendar")


@dataclass
class ScheduleArticleRequest:
    project_id: UUID
    title: str
    slug: str
    body: str
    meta_description: str
    scheduled_date: str  # ISO datetime
    cms_platform: str = "wordpress"
    auto_publish: bool = True
    auto_social_share: bool = False
    social_platforms: list[str] | None = None
    featured_image_url: str = ""
    content_type: str = "article"


@dataclass
class CalendarEvent:
    id: int
    title: str
    slug: str
    scheduled_date: str
    status: str  # scheduled, draft, published, failed
    cms_platform: str
    cms_url: str = ""


class ContentCalendarService:
    """Manages editorial calendar and publishing automation."""

    def schedule_article(
        self,
        req: ScheduleArticleRequest,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Schedule an article for future publication."""
        try:
            # Fetch CMS credentials
            creds = self._fetch_cms_creds(str(req.project_id), req.cms_platform, db_fn)

            # Create calendar entry
            calendar_entry = {
                "project_id": str(req.project_id),
                "title": req.title,
                "slug": req.slug,
                "body": req.body,
                "meta_description": req.meta_description,
                "scheduled_date": req.scheduled_date,
                "status": "scheduled",
                "cms_platform": req.cms_platform,
                "auto_publish": req.auto_publish,
                "auto_social_share": req.auto_social_share,
                "social_platforms": req.social_platforms or [],
                "featured_image_url": req.featured_image_url,
                "content_type": req.content_type,
            }

            result = db_fn("post", "content_calendar", calendar_entry)
            calendar_id = result.get("id") if isinstance(result, dict) else result[0].get("id")

            logger.info("Scheduled article: %s for %s", req.title, req.scheduled_date)

            return {
                "calendar_id": calendar_id,
                "status": "scheduled",
                "scheduled_date": req.scheduled_date,
                "auto_publish": req.auto_publish,
            }

        except Exception as exc:
            logger.error("Failed to schedule article: %s", exc)
            raise

    def get_calendar(
        self,
        project_id: UUID,
        start_date: str = "",
        end_date: str = "",
        status: str = "",
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch calendar events for a date range."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}"
            if status:
                params += f"&status=eq.{status}"
            if start_date:
                params += f"&scheduled_date=gte.{start_date}"
            if end_date:
                params += f"&scheduled_date=lte.{end_date}"
            params += "&order=scheduled_date.asc"

            result = db_fn("get", "content_calendar", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch calendar: %s", exc)
            return []

    def reschedule_article(
        self,
        calendar_id: int,
        new_date: str,
        db_fn: Callable,
    ) -> bool:
        """Reschedule a scheduled article."""
        try:
            db_fn("patch", f"content_calendar?id=eq.{calendar_id}", {
                "scheduled_date": new_date,
                "status": "scheduled",
            })
            logger.info("Rescheduled article %d to %s", calendar_id, new_date)
            return True
        except Exception as exc:
            logger.error("Failed to reschedule article: %s", exc)
            return False

    def cancel_article(self, calendar_id: int, db_fn: Callable) -> bool:
        """Cancel a scheduled article."""
        try:
            db_fn("patch", f"content_calendar?id=eq.{calendar_id}", {
                "status": "cancelled",
            })
            logger.info("Cancelled article: %d", calendar_id)
            return True
        except Exception as exc:
            logger.error("Failed to cancel article: %s", exc)
            return False

    async def publish_article(
        self,
        calendar_id: int,
        db_fn: Callable,
    ) -> bool:
        """Publish a calendar article to CMS."""
        try:
            # Fetch calendar entry
            article = db_fn("get", "content_calendar", params=f"id=eq.{calendar_id}")
            if not article or (isinstance(article, list) and len(article) == 0):
                logger.error("Calendar entry not found: %d", calendar_id)
                return False

            article = article[0] if isinstance(article, list) else article

            # Log publishing attempt
            db_fn("post", "publishing_logs", {
                "project_id": article["project_id"],
                "calendar_id": calendar_id,
                "event_type": "started",
                "cms_platform": article["cms_platform"],
            })

            # Fetch CMS credentials
            creds = self._fetch_cms_creds(
                article["project_id"],
                article["cms_platform"],
                db_fn,
            )

            # Get CMS client and publish
            cms_client = get_cms_client(
                article["cms_platform"],
                creds.get("endpoint_url", ""),
                decrypt(creds.get("api_key", "")),
                decrypt(creds.get("api_secret", "")),
            )

            # Prepare content for CMS
            content_payload = {
                "title": article["title"],
                "slug": article["slug"],
                "content": article["body"],
                "excerpt": article["meta_description"],
                "featured_image": article.get("featured_image_url", ""),
            }

            # Publish via CMS
            result = cms_client.publish_post(content_payload)

            if result.get("success"):
                # Update calendar with published status
                db_fn("patch", f"content_calendar?id=eq.{calendar_id}", {
                    "status": "published",
                    "cms_post_id": result.get("post_id"),
                    "cms_url": result.get("post_url"),
                    "published_at": datetime.utcnow().isoformat(),
                })

                # Log success
                db_fn("post", "publishing_logs", {
                    "project_id": article["project_id"],
                    "calendar_id": calendar_id,
                    "event_type": "success",
                    "cms_platform": article["cms_platform"],
                    "http_status": 200,
                    "response_data": {"post_id": result.get("post_id"), "post_url": result.get("post_url")},
                })

                logger.info("Published article: %d to %s", calendar_id, article["cms_platform"])
                return True
            else:
                # Log failure
                db_fn("post", "publishing_logs", {
                    "project_id": article["project_id"],
                    "calendar_id": calendar_id,
                    "event_type": "failed",
                    "cms_platform": article["cms_platform"],
                    "error_message": result.get("message"),
                })

                # Update calendar with failed status
                db_fn("patch", f"content_calendar?id=eq.{calendar_id}", {
                    "status": "failed",
                })

                logger.error("Failed to publish article: %d", calendar_id)
                return False

        except Exception as exc:
            logger.error("Publishing error: %s", exc)
            return False

    def get_publishing_logs(
        self,
        calendar_id: int,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get publishing logs for an article."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "publishing_logs", params=f"calendar_id=eq.{calendar_id}&order=created_at.desc")
            return result if isinstance(result, list) else [result] if result else []
        except Exception as exc:
            logger.warning("Failed to fetch publishing logs: %s", exc)
            return []

    def _fetch_cms_creds(
        self,
        project_id: str,
        platform: str,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Fetch stored CMS credentials."""
        try:
            result = db_fn("get", "cms_credentials", params=f"project_id=eq.{project_id}&cms_platform=eq.{platform}")
            if result:
                cred = result[0] if isinstance(result, list) else result
                return {
                    "endpoint_url": cred.get("endpoint_url", ""),
                    "api_key": decrypt(cred.get("api_key", "")),
                    "api_secret": decrypt(cred.get("api_secret", "")),
                }
            return {}
        except Exception as exc:
            logger.warning("Failed to fetch CMS credentials: %s", exc)
            return {}

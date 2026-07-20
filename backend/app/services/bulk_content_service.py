"""Bulk content job management and async processing."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID, uuid4

from app.agents.bulk_content_agent import BulkContentAgent, ContentRow, ContentTemplate

logger = logging.getLogger("omnirank.bulk_content")


@dataclass
class BulkContentJobRequest:
    project_id: UUID
    template: dict[str, Any]
    csv_data: list[dict[str, str]]  # parsed CSV rows
    enhance_with_ai: bool = True
    export_format: str = "json"  # json, csv, markdown
    schedule_publish: str = ""  # ISO date to publish


@dataclass
class BulkContentJobResult:
    job_id: str
    status: str  # queued, running, completed, failed
    total_articles: int
    completed_articles: int
    failed_articles: int
    articles: list[dict[str, Any]] = None
    export_url: str = ""  # S3 or download link
    error_message: str = ""


class BulkContentService:
    """Orchestrates bulk article generation jobs."""

    def __init__(self):
        self.agent = BulkContentAgent()

    def create_job(
        self,
        req: BulkContentJobRequest,
        db_fn: Callable,
    ) -> BulkContentJobResult:
        """Create and queue a bulk content generation job."""
        job_id = f"bulk_{uuid4().hex[:12]}"

        try:
            # Parse template
            template = ContentTemplate(**req.template)

            # Create job record
            db_fn("post", "bulk_content_jobs", {
                "project_id": str(req.project_id),
                "job_id": job_id,
                "status": "queued",
                "total_articles": len(req.csv_data),
                "completed_articles": 0,
                "failed_articles": 0,
                "template_name": template.name,
                "enhance_with_ai": req.enhance_with_ai,
                "export_format": req.export_format,
                "schedule_publish": req.schedule_publish or None,
            })

            # Queue async processing
            # In production: use Celery, Bull, or similar
            # For now: return job_id for polling
            logger.info("Created bulk content job: %s with %d articles", job_id, len(req.csv_data))

            return BulkContentJobResult(
                job_id=job_id,
                status="queued",
                total_articles=len(req.csv_data),
                completed_articles=0,
                failed_articles=0,
            )

        except Exception as exc:
            logger.error("Failed to create bulk content job: %s", exc)
            raise

    def get_job_status(self, job_id: str, db_fn: Callable) -> BulkContentJobResult:
        """Get status of a bulk content job."""
        try:
            result = db_fn("get", "bulk_content_jobs", params=f"job_id=eq.{job_id}")
            if not result:
                return BulkContentJobResult(
                    job_id=job_id,
                    status="not_found",
                    total_articles=0,
                    completed_articles=0,
                    failed_articles=0,
                    error_message="Job not found",
                )

            job = result[0] if isinstance(result, list) else result
            return BulkContentJobResult(
                job_id=job_id,
                status=job.get("status", "unknown"),
                total_articles=job.get("total_articles", 0),
                completed_articles=job.get("completed_articles", 0),
                failed_articles=job.get("failed_articles", 0),
                export_url=job.get("export_url", ""),
            )
        except Exception as exc:
            logger.error("Failed to get job status: %s", exc)
            return BulkContentJobResult(
                job_id=job_id,
                status="error",
                total_articles=0,
                completed_articles=0,
                failed_articles=0,
                error_message=str(exc),
            )

    def get_articles(
        self, job_id: str, limit: int = 100, offset: int = 0, db_fn: Callable = None
    ) -> list[dict[str, Any]]:
        """Fetch generated articles for a job."""
        if not db_fn:
            return []
        try:
            params = f"job_id=eq.{job_id}&order=created_at.desc&limit={limit}&offset={offset}"
            result = db_fn("get", "bulk_content_articles", params=params)
            return result if isinstance(result, list) else []
        except Exception as exc:
            logger.warning("Failed to fetch articles: %s", exc)
            return []

    def cancel_job(self, job_id: str, db_fn: Callable) -> bool:
        """Cancel a queued or running job."""
        try:
            db_fn("patch", f"bulk_content_jobs?job_id=eq.{job_id}", {
                "status": "cancelled",
            })
            logger.info("Cancelled job: %s", job_id)
            return True
        except Exception as exc:
            logger.error("Failed to cancel job: %s", exc)
            return False

    def parse_csv(self, csv_content: str) -> list[dict[str, str]]:
        """Parse CSV into row dicts."""
        import csv
        from io import StringIO

        rows = []
        reader = csv.DictReader(StringIO(csv_content))
        for row in reader:
            rows.append(row)
        return rows

    async def process_job(
        self,
        job_id: str,
        template: dict[str, Any],
        csv_rows: list[dict[str, str]],
        enhance_with_ai: bool = True,
        export_format: str = "json",
        db_fn: Callable = None,
    ) -> bool:
        """Process a job (run async in background)."""
        if not db_fn:
            return False

        try:
            # Update status
            db_fn("patch", f"bulk_content_jobs?job_id=eq.{job_id}", {
                "status": "running",
            })

            # Parse template + rows
            tmpl = ContentTemplate(**template)
            content_rows = [ContentRow(data=row, variables=self.agent.extract_variables(str(template))) for row in csv_rows]

            # Generate articles
            articles = await self.agent.generate_batch(
                tmpl, content_rows, enhance_with_ai=enhance_with_ai
            )

            # Store articles
            successful = 0
            failed = 0
            for article in articles:
                if not article.errors:
                    db_fn("post", "bulk_content_articles", {
                        "job_id": job_id,
                        "slug": article.slug,
                        "title": article.title,
                        "meta_description": article.meta_description,
                        "h1": article.h1,
                        "body": article.body,
                        "word_count": article.word_count,
                        "reading_time_minutes": article.reading_time_minutes,
                        "variables_used": article.variables_used,
                        "ai_enhanced": article.ai_enhanced,
                    })
                    successful += 1
                else:
                    failed += 1

            # Export
            export_data = self.agent.export_articles(articles, format=export_format)

            # Update job
            db_fn("patch", f"bulk_content_jobs?job_id=eq.{job_id}", {
                "status": "completed",
                "completed_articles": successful,
                "failed_articles": failed,
                "export_data": export_data,
            })

            logger.info(
                "Completed job %s: %d successful, %d failed",
                job_id, successful, failed,
            )
            return True

        except Exception as exc:
            logger.error("Job processing failed: %s", exc)
            db_fn("patch", f"bulk_content_jobs?job_id=eq.{job_id}", {
                "status": "failed",
                "error_message": str(exc),
            })
            return False

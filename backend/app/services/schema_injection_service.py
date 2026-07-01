"""Schema batch injection service.

Handles batch schema injection across multiple URLs with CMS auto-detection,
job tracking, and error handling.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID, uuid4

from app.clients.cms_client import detect_cms, get_cms_client
from app.agents.schema_agent import SchemaAgent

logger = logging.getLogger("omnirank.schema_injection")


@dataclass
class SchemaInjectionRequest:
    project_id: UUID
    urls: list[str]  # pages to inject into
    schema_types: list[str]  # FAQ, Product, Organization, etc.
    business_type: str = "default"
    business_name: str = ""
    cms_auto_detect: bool = True
    cms_platform: str | None = None  # override auto-detect


@dataclass
class InjectionJobResult:
    job_id: str
    status: str
    total_urls: int
    processed_count: int
    success_count: int
    failure_count: int
    injections: list[dict[str, Any]]


class SchemaInjectionService:
    """Orchestrates batch schema injection."""

    def __init__(self, db_fn: Callable | None = None):
        self.db_fn = db_fn  # Injected Supabase REST function (defaults to _supabase_rest in main.py)
        self.schema_agent = SchemaAgent()

    def inject_batch(self, req: SchemaInjectionRequest, db_fn: Callable) -> InjectionJobResult:
        """
        Inject schema into multiple URLs with CMS auto-detection.
        Returns job ID and initial status.
        """
        job_id = f"inj_{uuid4().hex[:12]}"
        batch_id = uuid4()

        # Create job record
        db_fn("post", "schema_injection_jobs", {
            "project_id": str(req.project_id),
            "job_id": job_id,
            "status": "running",
            "total_urls": len(req.urls),
            "schema_types": req.schema_types,
            "cms_auto_detect": req.cms_auto_detect,
        })

        injections: list[dict[str, Any]] = []

        try:
            for url in req.urls:
                try:
                    # Detect CMS if needed
                    cms_platform = req.cms_platform
                    if not cms_platform and req.cms_auto_detect:
                        detection = detect_cms(url)
                        cms_platform = detection.platform
                        logger.info("Detected CMS: %s for %s", cms_platform, url)

                    # Generate schema for each type
                    for schema_type in req.schema_types:
                        schema_jsonld = self.schema_agent.generate(
                            schema_type,
                            {
                                "url": url,
                                "business_name": req.business_name,
                                "business_type": req.business_type,
                            },
                        )
                        if not schema_jsonld:
                            logger.warning("Could not generate schema type: %s", schema_type)
                            continue

                        # Inject via CMS client
                        cms_client = get_cms_client(cms_platform or "custom", url)
                        injection_result = cms_client.inject_schema(schema_jsonld, url)

                        # Record injection attempt
                        inj_row = {
                            "project_id": str(req.project_id),
                            "batch_id": str(batch_id),
                            "url": url,
                            "cms_platform": injection_result.cms_platform,
                            "schema_type": schema_type,
                            "status": "injected" if injection_result.success else "failed",
                            "error_message": None if injection_result.success else injection_result.message,
                            "request_body": schema_jsonld,
                            "response_body": injection_result.response_data,
                        }
                        db_fn("post", "schema_injections", inj_row)
                        injections.append(inj_row)

                        if injection_result.success:
                            logger.info(
                                "Injected %s to %s via %s",
                                schema_type, url, injection_result.cms_platform,
                            )

                except Exception as exc:
                    logger.error("Injection error for %s: %s", url, exc)
                    db_fn("post", "schema_injections", {
                        "project_id": str(req.project_id),
                        "batch_id": str(batch_id),
                        "url": url,
                        "cms_platform": "unknown",
                        "schema_type": "error",
                        "status": "failed",
                        "error_message": str(exc),
                    })

            # Update job status
            success_count = sum(1 for r in injections if r["status"] == "injected")
            db_fn("patch", f"schema_injection_jobs?job_id=eq.{job_id}", {
                "status": "completed",
                "processed_count": len(req.urls),
                "success_count": success_count,
                "failure_count": len(req.urls) - success_count,
            })

            return InjectionJobResult(
                job_id=job_id,
                status="completed",
                total_urls=len(req.urls),
                processed_count=len(req.urls),
                success_count=success_count,
                failure_count=len(req.urls) - success_count,
                injections=injections,
            )

        except Exception as exc:
            logger.error("Batch injection job %s failed: %s", job_id, exc)
            db_fn("patch", f"schema_injection_jobs?job_id=eq.{job_id}", {
                "status": "failed",
                "error_message": str(exc),
            })
            raise

    def get_job_status(self, job_id: str, db_fn: Callable) -> dict[str, Any]:
        """Get status of an injection job."""
        result = db_fn("get", "schema_injection_jobs", params=f"job_id=eq.{job_id}")
        if not result:
            return {"error": "Job not found"}
        return result[0] if isinstance(result, list) else result

    def get_injections(self, project_id: UUID, batch_id: UUID | None = None, db_fn: Callable | None = None) -> list[dict[str, Any]]:
        """Get injection records for a project (optionally filtered by batch)."""
        if not db_fn:
            return []
        params = f"project_id=eq.{project_id}"
        if batch_id:
            params += f"&batch_id=eq.{batch_id}"
        result = db_fn("get", "schema_injections", params=params)
        return result if isinstance(result, list) else []

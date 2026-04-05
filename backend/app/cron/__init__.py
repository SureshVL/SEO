"""Daily cron tasks for OMNI-RANK.

Run with: python -m app.cron.daily_ranks
Or via scheduler (crontab, Railway cron, etc.)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from app.clients.http_clients import SerperHTTPClient
from app.core.config import settings
from app.services.rank_tracker import RankPersistence, RankTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnirank.cron")


def run_daily_rank_checks():
    """Check positions for all tracked keywords across all projects."""

    if not settings.serper_api_key:
        logger.error("SERPER_API_KEY required for rank tracking")
        return

    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.error("Supabase credentials required for rank tracking")
        return

    serper = SerperHTTPClient(api_key=settings.serper_api_key)
    tracker = RankTracker(serper_client=serper)
    persistence = RankPersistence(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )

    logger.info("Starting daily rank check at %s", datetime.now(timezone.utc).isoformat())

    # Fetch all projects
    import requests
    base = settings.supabase_url.rstrip("/") + "/rest/v1"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }

    projects_resp = requests.get(
        f"{base}/projects?status=eq.active&select=id,client_url,domain",
        headers=headers,
        timeout=20,
    )
    if projects_resp.status_code != 200:
        logger.error("Failed to fetch projects: %s", projects_resp.status_code)
        return

    projects = projects_resp.json()
    logger.info("Found %d active projects", len(projects))

    total_checked = 0
    total_saved = 0

    for project in projects:
        project_id = project["id"]
        domain = project.get("domain") or project.get("client_url", "")
        if not domain:
            continue

        # Clean domain
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        keywords = persistence.get_keywords_for_project(project_id)
        if not keywords:
            continue

        logger.info("Project %s: checking %d keywords for %s", project_id[:8], len(keywords), domain)

        # Get previous positions
        latest = persistence.get_latest_positions(project_id)
        prev_map = {r["keyword_id"]: r.get("position") for r in latest}

        kw_batch = [
            {
                "keyword_id": kw["id"],
                "keyword": kw["keyword"],
                "previous_position": prev_map.get(kw["id"]),
            }
            for kw in keywords
        ]

        results = tracker.check_batch(
            keywords=kw_batch,
            domain=domain,
            locale=keywords[0].get("locale", "en-US"),
            region=keywords[0].get("target_region", "IN"),
        )

        total_checked += len(results)

        saved = persistence.save_rank_checks(results)
        total_saved += saved

        # Log significant rank changes
        for r in results:
            if r.position and r.previous_position:
                change = r.previous_position - r.position
                if abs(change) >= 5:
                    direction = "improved" if change > 0 else "dropped"
                    logger.info(
                        "Rank %s: '%s' %s %d positions (was %d, now %d)",
                        direction, r.keyword, direction, abs(change),
                        r.previous_position, r.position,
                    )

    logger.info(
        "Daily rank check complete: %d keywords checked, %d records saved",
        total_checked, total_saved,
    )


if __name__ == "__main__":
    run_daily_rank_checks()

"""Rank tracking service.

Checks keyword positions via Serper API and stores history.
Designed to run as a daily cron job via background task or external scheduler.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.clients.http_clients import SerperHTTPClient
from app.services.cache import cache_key, cache_json_get, cache_json_set

logger = logging.getLogger("omnirank.rank_tracker")


@dataclass
class RankCheckResult:
    keyword_id: str
    keyword: str
    position: int | None
    previous_position: int | None
    url: str | None
    serp_features: list[str]
    search_volume: int | None
    checked_at: str


class RankTracker:
    """Check keyword positions and detect SERP features."""

    def __init__(self, serper_client: SerperHTTPClient):
        self.serper = serper_client

    def check_keyword(
        self,
        keyword: str,
        domain: str,
        locale: str = "en-US",
        region: str = "IN",
        previous_position: int | None = None,
    ) -> RankCheckResult:
        """Check a single keyword position for a domain."""

        # Check cache first (same keyword+region within 6 hours)
        ck = cache_key("rank", keyword, region, locale)
        cached = cache_json_get(ck)

        if cached:
            serp_results = cached
        else:
            serp_results = self.serper.search_top_results(keyword, locale, region, limit=20)
            cache_json_set(ck, serp_results, ttl=21600)  # 6 hours

        position = None
        ranking_url = None
        domain_lower = domain.lower().replace("https://", "").replace("http://", "").rstrip("/")

        for i, result in enumerate(serp_results):
            link = result.get("link", "").lower()
            if domain_lower in link:
                position = i + 1
                ranking_url = result.get("link", "")
                break

        # Detect SERP features
        serp_features = self._detect_serp_features(serp_results, keyword)

        return RankCheckResult(
            keyword_id="",
            keyword=keyword,
            position=position,
            previous_position=previous_position,
            url=ranking_url,
            serp_features=serp_features,
            search_volume=None,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    def check_batch(
        self,
        keywords: list[dict[str, Any]],
        domain: str,
        locale: str = "en-US",
        region: str = "IN",
    ) -> list[RankCheckResult]:
        """Check multiple keywords. Each dict should have 'keyword', 'keyword_id', optional 'previous_position'."""
        results = []
        for kw_data in keywords:
            try:
                result = self.check_keyword(
                    keyword=kw_data["keyword"],
                    domain=domain,
                    locale=locale,
                    region=region,
                    previous_position=kw_data.get("previous_position"),
                )
                result.keyword_id = kw_data.get("keyword_id", "")
                results.append(result)
            except Exception as exc:
                logger.error("Failed to check keyword '%s': %s", kw_data.get("keyword"), exc)
        return results

    def _detect_serp_features(self, serp_results: list[dict], keyword: str) -> list[str]:
        """Detect which SERP features appear for this keyword."""
        features: list[str] = []

        # Check top result patterns
        if serp_results:
            first = serp_results[0]
            if first.get("snippet") and len(first.get("snippet", "")) > 200:
                features.append("featured_snippet")

        # Check for common patterns in results
        all_text = " ".join(r.get("title", "") + " " + r.get("snippet", "") for r in serp_results[:5]).lower()

        if "people also ask" in all_text or any("?" in r.get("title", "") for r in serp_results[:5]):
            features.append("people_also_ask")

        if any("video" in r.get("link", "").lower() or "youtube" in r.get("link", "").lower() for r in serp_results[:10]):
            features.append("video_results")

        if any("image" in r.get("title", "").lower() for r in serp_results[:5]):
            features.append("image_pack")

        if any("maps" in r.get("link", "").lower() or "local" in r.get("title", "").lower() for r in serp_results[:5]):
            features.append("local_pack")

        if any("shopping" in r.get("link", "").lower() for r in serp_results[:5]):
            features.append("shopping_results")

        if any("news" in r.get("link", "").lower() for r in serp_results[:5]):
            features.append("top_stories")

        return features


class RankPersistence:
    """Save rank check results to Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str, timeout: int = 20):
        self.base = supabase_url.rstrip("/") + "/rest/v1"
        self.timeout = timeout
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def save_rank_checks(self, results: list[RankCheckResult]) -> int:
        """Batch insert rank history records. Returns count saved."""
        import requests

        payloads = [
            {
                "keyword_id": r.keyword_id,
                "position": r.position,
                "previous_position": r.previous_position,
                "url": r.url,
                "serp_features": r.serp_features,
                "search_volume": r.search_volume,
                "checked_at": r.checked_at,
            }
            for r in results
            if r.keyword_id  # skip if no keyword_id
        ]

        if not payloads:
            return 0

        resp = requests.post(
            f"{self.base}/rank_history",
            headers=self.headers,
            json=payloads,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return len(payloads)

    def get_keywords_for_project(self, project_id: str) -> list[dict]:
        """Fetch all tracked keywords for a project."""
        import requests

        resp = requests.get(
            f"{self.base}/keywords?project_id=eq.{project_id}&select=id,keyword,locale,target_region",
            headers=self.headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_latest_positions(self, project_id: str) -> list[dict]:
        """Get most recent position for each keyword in a project."""
        import requests

        # Use a subquery via Supabase RPC or just fetch recent history
        resp = requests.get(
            f"{self.base}/rank_history"
            f"?keyword_id=in.(select id from keywords where project_id=eq.{project_id})"
            f"&order=checked_at.desc&limit=200",
            headers={**self.headers, "Prefer": "return=representation"},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            return []

        rows = resp.json()
        # Deduplicate — keep latest per keyword_id
        seen: dict[str, dict] = {}
        for row in rows:
            kid = row.get("keyword_id")
            if kid and kid not in seen:
                seen[kid] = row
        return list(seen.values())

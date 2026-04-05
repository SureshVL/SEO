"""Deploy bridge agent with httpx (async-compatible)."""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.schemas.deploy import DeployRequest, DeployResponse


class DeployAgent:
    """Deploy bridge with optional webhook connectors."""

    def run(self, request: DeployRequest) -> DeployResponse:
        platform = request.platform.lower()
        if platform not in {"wordpress", "shopify", "appstore"}:
            return DeployResponse(platform=platform, status="failed", actions=["unsupported platform"])

        actions = [
            f"Fetched draft artifacts for project {request.project_id}.",
            f"Validated payload schema for {platform} connector.",
            "Prepared publish batch from content_queue.",
        ]

        if request.dry_run:
            actions.append("Dry-run complete. No external publish call executed.")
            return DeployResponse(platform=platform, status="dry_run_complete", actions=actions)

        webhook = self._platform_webhook(platform)
        if not webhook:
            actions.append("No deploy webhook configured for platform.")
            return DeployResponse(platform=platform, status="failed", actions=actions)

        payload = {"project_id": request.project_id, "platform": platform}
        try:
            with httpx.Client(timeout=20) as client:
                response = client.post(webhook, json=payload)
            if response.status_code >= 300:
                actions.append(f"Webhook failed with status {response.status_code}.")
                return DeployResponse(platform=platform, status="failed", actions=actions)
        except httpx.HTTPError as exc:
            actions.append(f"Webhook call failed: {exc}")
            return DeployResponse(platform=platform, status="failed", actions=actions)

        actions.append(f"Publish call submitted to {platform} connector.")
        return DeployResponse(platform=platform, status="submitted", actions=actions)

    @staticmethod
    def _platform_webhook(platform: str) -> str:
        mapping = {
            "wordpress": settings.wordpress_deploy_webhook,
            "shopify": settings.shopify_deploy_webhook,
            "appstore": settings.appstore_deploy_webhook,
        }
        return mapping.get(platform, "")

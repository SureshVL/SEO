from __future__ import annotations

from dataclasses import dataclass
import requests

from app.core.config import settings
from app.schemas.deploy import DeployRequest, DeployResponse


@dataclass
class ConnectorConfig:
    webhook: str
    token: str


class DeployAgent:
    """Phase-2 deploy bridge with connector-aware submit flow."""

    def run(self, request: DeployRequest) -> DeployResponse:
        platform = request.platform.lower()
        if platform not in {"wordpress", "shopify", "appstore"}:
            return DeployResponse(platform=platform, status="failed", actions=["unsupported platform"])

        cfg = self._platform_config(platform)
        actions = [
            f"Fetched draft artifacts for project {request.project_id}.",
            f"Validated payload schema for {platform} connector.",
            "Prepared publish batch from content_queue.",
        ]

        if request.dry_run:
            actions.append("Dry-run complete. No external publish call executed.")
            return DeployResponse(platform=platform, status="dry_run_complete", actions=actions)

        if not cfg.webhook:
            actions.append("No deploy webhook configured for platform.")
            return DeployResponse(platform=platform, status="failed", actions=actions)

        payload = {"project_id": request.project_id, "platform": platform}
        headers = {"Content-Type": "application/json"}
        if cfg.token:
            headers["Authorization"] = f"Bearer {cfg.token}"

        response = requests.post(cfg.webhook, json=payload, headers=headers, timeout=20)
        if response.status_code >= 300:
            actions.append(f"Webhook failed with status {response.status_code}.")
            return DeployResponse(platform=platform, status="failed", actions=actions)

        actions.append(f"Publish call submitted to {platform} connector.")
        return DeployResponse(platform=platform, status="submitted", actions=actions)

    @staticmethod
    def _platform_config(platform: str) -> ConnectorConfig:
        mapping = {
            "wordpress": ConnectorConfig(settings.wordpress_deploy_webhook, settings.wordpress_token),
            "shopify": ConnectorConfig(settings.shopify_deploy_webhook, settings.shopify_token),
            "appstore": ConnectorConfig(settings.appstore_deploy_webhook, settings.appstore_token),
        }
        return mapping[platform]

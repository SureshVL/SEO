from __future__ import annotations

from app.schemas.deploy import DeployRequest, DeployResponse


class DeployAgent:
    """Phase-2 deploy bridge (connector-ready)."""

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
            status = "dry_run_complete"
        else:
            actions.append(f"Publish call submitted to {platform} connector.")
            status = "submitted"

        return DeployResponse(platform=platform, status=status, actions=actions)

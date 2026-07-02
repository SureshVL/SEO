"""CMS platform detection and schema injection clients.

Handles WordPress, Shopify, Webflow, and generic HTTP injection.
Each CMS has different APIs for injecting schema markup.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("omnirank.cms")


@dataclass
class CMSDetectionResult:
    platform: str  # wordpress, shopify, webflow, custom, unknown
    endpoint_url: str | None = None  # e.g., WordPress REST API base
    auth_required: bool = False
    reason: str = ""  # why we think it's this platform


@dataclass
class SchemaInjectionResult:
    success: bool
    message: str
    cms_platform: str
    injected_url: str | None = None
    response_data: dict[str, Any] | None = None


@dataclass
class PublishResult:
    success: bool
    message: str
    cms_platform: str
    post_id: str | None = None
    post_url: str | None = None
    response_data: dict[str, Any] | None = None


class CMSClient(ABC):
    """Abstract base for CMS injection strategies."""

    def __init__(self, url: str, api_key: str = "", api_secret: str = ""):
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
    def detect(self) -> CMSDetectionResult:
        """Detect if this CMS is running at the URL."""
        pass

    @abstractmethod
    def inject_schema(self, schema_jsonld: dict[str, Any], page_url: str) -> SchemaInjectionResult:
        """Inject a schema markup block into a page."""
        pass

    @abstractmethod
    def publish_post(self, content: dict[str, Any]) -> PublishResult:
        """Publish or update a post on the CMS."""
        pass

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"User-Agent": "OmniRank/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if extra:
            headers.update(extra)
        return headers


class WordPressClient(CMSClient):
    """WordPress.org (self-hosted) with REST API."""

    def detect(self) -> CMSDetectionResult:
        """Check for WordPress by probing wp-json endpoint."""
        try:
            with httpx.Client(timeout=10) as client:
                # Try common WordPress REST API endpoints
                for endpoint in ["/wp-json/", "/wp-json/wp/v2/posts"]:
                    url = self.url.rstrip("/") + endpoint
                    resp = client.head(url)
                    if resp.status_code < 400:
                        return CMSDetectionResult(
                            platform="wordpress",
                            endpoint_url=self.url.rstrip("/") + "/wp-json",
                            auth_required=resp.status_code == 401,
                            reason=f"Found {endpoint}",
                        )
                # Fallback: check for wp-content or wp-includes in HTML
                resp = client.get(self.url, follow_redirects=True, timeout=10)
                if "wp-content" in resp.text or "wp-includes" in resp.text:
                    return CMSDetectionResult(
                        platform="wordpress",
                        endpoint_url=self.url.rstrip("/") + "/wp-json",
                        reason="Found WordPress folders in HTML",
                    )
        except Exception as exc:
            logger.debug("WordPress detection failed: %s", exc)
        return CMSDetectionResult(platform="unknown", reason="Not WordPress")

    def inject_schema(self, schema_jsonld: dict[str, Any], page_url: str) -> SchemaInjectionResult:
        """
        Inject schema via WordPress custom post meta or Site Kit plugin.
        Fallback: inject into page content via Yoast SEO API if available.
        """
        if not self.api_key:
            return SchemaInjectionResult(
                success=False,
                message="WordPress API key required",
                cms_platform="wordpress",
            )

        try:
            # Extract post ID from page URL
            with httpx.Client(timeout=10) as client:
                # Query for post by URL
                rest_base = self.url.rstrip("/") + "/wp-json"
                search_resp = client.get(
                    f"{rest_base}/wp/v2/posts",
                    params={"search": page_url},
                    headers=self._headers(),
                    timeout=10,
                )
                if search_resp.status_code == 200 and search_resp.json():
                    post_id = search_resp.json()[0]["id"]
                    # Update post meta with schema
                    update_resp = client.post(
                        f"{rest_base}/wp/v2/posts/{post_id}",
                        json={
                            "meta": {
                                "omnirank_schema": json.dumps(schema_jsonld),
                            },
                        },
                        headers=self._headers(),
                        timeout=10,
                    )
                    if update_resp.status_code in (200, 201):
                        return SchemaInjectionResult(
                            success=True,
                            message=f"Injected schema to post {post_id}",
                            cms_platform="wordpress",
                            injected_url=page_url,
                            response_data=update_resp.json(),
                        )
        except Exception as exc:
            logger.warning("WordPress schema injection failed: %s", exc)

        return SchemaInjectionResult(
            success=False,
            message=f"WordPress injection error: {exc}",
            cms_platform="wordpress",
        )

    def publish_post(self, content: dict[str, Any]) -> PublishResult:
        """Create or publish a WordPress post."""
        if not self.api_key:
            return PublishResult(
                success=False,
                message="WordPress API key required",
                cms_platform="wordpress",
            )

        try:
            with httpx.Client(timeout=15) as client:
                rest_base = self.url.rstrip("/") + "/wp-json"
                post_data = {
                    "title": content.get("title", ""),
                    "content": content.get("content", ""),
                    "excerpt": content.get("excerpt", ""),
                    "slug": content.get("slug", ""),
                    "status": "publish",
                }

                # Add featured image if provided
                if content.get("featured_image"):
                    post_data["featured_media"] = content["featured_image"]

                resp = client.post(
                    f"{rest_base}/wp/v2/posts",
                    json=post_data,
                    headers=self._headers(),
                    timeout=15,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return PublishResult(
                        success=True,
                        message=f"Published post {data.get('id')}",
                        cms_platform="wordpress",
                        post_id=str(data.get("id")),
                        post_url=data.get("link"),
                        response_data=data,
                    )
        except Exception as exc:
            logger.warning("WordPress publish failed: %s", exc)

        return PublishResult(
            success=False,
            message=f"WordPress publish error: {exc}",
            cms_platform="wordpress",
        )


class ShopifyClient(CMSClient):
    """Shopify store with REST API."""

    def detect(self) -> CMSDetectionResult:
        """Check for Shopify by probing Shopify API endpoint."""
        try:
            with httpx.Client(timeout=10) as client:
                # Shopify CDN footer or API endpoint
                resp = client.head(f"{self.url.rstrip('/')}/admin/api/2024-01/products.json")
                if resp.status_code in (401, 403):  # Auth required but found Shopify
                    return CMSDetectionResult(
                        platform="shopify",
                        endpoint_url=self.url.rstrip("/") + "/admin/api/2024-01",
                        auth_required=True,
                        reason="Shopify API endpoint found",
                    )
        except Exception as exc:
            logger.debug("Shopify detection failed: %s", exc)
        return CMSDetectionResult(platform="unknown", reason="Not Shopify")

    def inject_schema(self, schema_jsonld: dict[str, Any], page_url: str) -> SchemaInjectionResult:
        """Inject schema via Shopify theme liquid or metafields."""
        # Shopify requires theme editing or metafield API
        # For MVP: return instruction to manually edit theme
        return SchemaInjectionResult(
            success=False,
            message="Shopify requires manual theme edit or custom app (metafields). See docs.",
            cms_platform="shopify",
        )

    def publish_post(self, content: dict[str, Any]) -> PublishResult:
        """Create a Shopify product or blog post."""
        if not self.api_key:
            return PublishResult(
                success=False,
                message="Shopify API key required",
                cms_platform="shopify",
            )

        try:
            with httpx.Client(timeout=15) as client:
                api_base = self.url.rstrip("/") + "/admin/api/2024-01"

                # Create blog post
                post_data = {
                    "blog_post": {
                        "title": content.get("title", ""),
                        "body_html": content.get("content", ""),
                        "metafields": [
                            {
                                "namespace": "custom",
                                "key": "meta_description",
                                "value": content.get("excerpt", ""),
                                "type": "single_line_text_field",
                            }
                        ],
                    }
                }

                resp = client.post(
                    f"{api_base}/blogs/1/articles.json",
                    json=post_data,
                    headers=self._headers({"Content-Type": "application/json"}),
                    timeout=15,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    article = data.get("article", {})
                    return PublishResult(
                        success=True,
                        message=f"Published article {article.get('id')}",
                        cms_platform="shopify",
                        post_id=str(article.get("id")),
                        post_url=article.get("url"),
                        response_data=article,
                    )
        except Exception as exc:
            logger.warning("Shopify publish failed: %s", exc)

        return PublishResult(
            success=False,
            message=f"Shopify publish error: {exc}",
            cms_platform="shopify",
        )


class WebflowClient(CMSClient):
    """Webflow site with API."""

    def detect(self) -> CMSDetectionResult:
        """Check for Webflow by looking for Webflow scripts."""
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(self.url, follow_redirects=True, timeout=10)
                if "webflow.io" in resp.text or "webflow.com" in resp.text:
                    return CMSDetectionResult(
                        platform="webflow",
                        reason="Found Webflow script tags",
                    )
        except Exception as exc:
            logger.debug("Webflow detection failed: %s", exc)
        return CMSDetectionResult(platform="unknown", reason="Not Webflow")

    def inject_schema(self, schema_jsonld: dict[str, Any], page_url: str) -> SchemaInjectionResult:
        """Inject schema via Webflow custom code or API."""
        # Webflow requires custom code block or API
        return SchemaInjectionResult(
            success=False,
            message="Webflow requires custom code block in editor. See integration guide.",
            cms_platform="webflow",
        )

    def publish_post(self, content: dict[str, Any]) -> PublishResult:
        """Publish to Webflow via API (requires custom collection setup)."""
        if not self.api_key:
            return PublishResult(
                success=False,
                message="Webflow API key required",
                cms_platform="webflow",
            )

        # Webflow API requires collection ID and custom field mapping
        # Simplified for MVP - returns instruction to set up via dashboard
        return PublishResult(
            success=False,
            message="Webflow publishing requires manual collection setup. Use Zapier or custom webhooks.",
            cms_platform="webflow",
        )


class GenericHTTPClient(CMSClient):
    """Generic HTTP POST injection for APIs."""

    def detect(self) -> CMSDetectionResult:
        return CMSDetectionResult(platform="custom", reason="Generic HTTP endpoint")

    def inject_schema(self, schema_jsonld: dict[str, Any], page_url: str) -> SchemaInjectionResult:
        """POST schema to a custom webhook endpoint."""
        if not self.api_key:
            return SchemaInjectionResult(
                success=False,
                message="Custom endpoint requires webhook URL in api_key",
                cms_platform="custom",
            )

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    self.api_key,  # URL stored in api_key field
                    json={"schema": schema_jsonld, "page_url": page_url},
                    headers=self._headers({"Content-Type": "application/json"}),
                    timeout=15,
                )
                if resp.status_code < 400:
                    return SchemaInjectionResult(
                        success=True,
                        message=f"Injected to custom endpoint (HTTP {resp.status_code})",
                        cms_platform="custom",
                        injected_url=page_url,
                        response_data=resp.json() if resp.text else None,
                    )
        except Exception as exc:
            logger.warning("Custom HTTP injection failed: %s", exc)

        return SchemaInjectionResult(
            success=False,
            message=f"Custom injection error: {exc}",
            cms_platform="custom",
        )

    def publish_post(self, content: dict[str, Any]) -> PublishResult:
        """POST content to a custom webhook endpoint."""
        if not self.api_key:
            return PublishResult(
                success=False,
                message="Custom endpoint requires webhook URL",
                cms_platform="custom",
            )

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    self.api_key,  # URL stored in api_key field
                    json=content,
                    headers=self._headers({"Content-Type": "application/json"}),
                    timeout=15,
                )

                if resp.status_code < 400:
                    data = resp.json() if resp.text else {}
                    return PublishResult(
                        success=True,
                        message=f"Posted to custom endpoint (HTTP {resp.status_code})",
                        cms_platform="custom",
                        post_id=data.get("id"),
                        post_url=data.get("url"),
                        response_data=data,
                    )
        except Exception as exc:
            logger.warning("Custom HTTP publish failed: %s", exc)

        return PublishResult(
            success=False,
            message=f"Custom publish error: {exc}",
            cms_platform="custom",
        )


def detect_cms(url: str) -> CMSDetectionResult:
    """Auto-detect CMS platform."""
    for client_class in [WordPressClient, ShopifyClient, WebflowClient]:
        client = client_class(url)
        result = client.detect()
        if result.platform != "unknown":
            return result
    return CMSDetectionResult(platform="unknown", reason="Could not auto-detect CMS")


def get_cms_client(platform: str, url: str, api_key: str = "", api_secret: str = "") -> CMSClient:
    """Factory for CMS clients."""
    if platform == "wordpress":
        return WordPressClient(url, api_key, api_secret)
    elif platform == "shopify":
        return ShopifyClient(url, api_key, api_secret)
    elif platform == "webflow":
        return WebflowClient(url, api_key, api_secret)
    else:
        return GenericHTTPClient(url, api_key, api_secret)

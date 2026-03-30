from __future__ import annotations

import httpx


class FirecrawlHTTPClient:
    def __init__(self, api_key: str, timeout: float = 30.0, base_url: str = "https://api.firecrawl.dev"):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    def scrape_markdown(self, url: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/v1/scrape", headers=headers, json=payload)
            response.raise_for_status()

        data = response.json().get("data", {})
        markdown = data.get("markdown", "")
        return markdown or ""

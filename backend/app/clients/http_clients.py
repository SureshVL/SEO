from __future__ import annotations

import requests


class SerperHTTPClient:
    def __init__(self, api_key: str, base_url: str = "https://google.serper.dev/search", timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3) -> list[dict]:
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": keyword, "gl": region.lower(), "hl": locale.split("-")[0]}
        response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("organic", [])[:limit]


class FirecrawlHTTPClient:
    def __init__(self, api_key: str, base_url: str = "https://api.firecrawl.dev/v1/scrape", timeout: int = 45):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def scrape_markdown(self, url: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"url": url, "formats": ["markdown"]}
        response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("markdown", "")

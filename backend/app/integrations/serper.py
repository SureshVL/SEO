from __future__ import annotations

import httpx


class SerperHTTPClient:
    def __init__(self, api_key: str, timeout: float = 20.0, base_url: str = "https://google.serper.dev"):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3) -> list[dict]:
        payload = {
            "q": keyword,
            "gl": region,
            "hl": locale.split("-")[0],
            "num": max(limit, 3),
        }
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/search", headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        organic = data.get("organic", [])
        results = [{"link": item.get("link", "")} for item in organic if item.get("link")]
        return results[:limit]

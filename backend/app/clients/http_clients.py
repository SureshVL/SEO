from __future__ import annotations

import time

import requests


class HTTPProviderError(RuntimeError):
    pass


class _BaseHTTPClient:
    def _post_with_retry(
        self,
        url: str,
        headers: dict,
        payload: dict,
        timeout: int,
        retries: int = 3,
        fallback_url: str = "",
    ) -> dict:
        wait = 0.8
        last_error: Exception | None = None
        endpoints = [url] + ([fallback_url] if fallback_url else [])

        for endpoint in endpoints:
            for _ in range(retries):
                try:
                    response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
                    response.raise_for_status()
                    return response.json()
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    time.sleep(wait)
                    wait *= 2
        raise HTTPProviderError(f"Provider call failed after retries/fallback: {last_error}")


class SerperHTTPClient(_BaseHTTPClient):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://google.serper.dev/search",
        fallback_url: str = "",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.fallback_url = fallback_url
        self.timeout = timeout

    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3) -> list[dict]:
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": keyword, "gl": region.lower(), "hl": locale.split("-")[0]}
        data = self._post_with_retry(self.base_url, headers, payload, self.timeout, fallback_url=self.fallback_url)
        return data.get("organic", [])[:limit]


class FirecrawlHTTPClient(_BaseHTTPClient):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.firecrawl.dev/v1/scrape",
        fallback_url: str = "",
        timeout: int = 45,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.fallback_url = fallback_url
        self.timeout = timeout

    def scrape_markdown(self, url: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"url": url, "formats": ["markdown"]}
        data = self._post_with_retry(self.base_url, headers, payload, self.timeout, fallback_url=self.fallback_url)
        return data.get("data", {}).get("markdown", "")

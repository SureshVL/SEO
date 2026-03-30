from __future__ import annotations

from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.integrations.firecrawl import FirecrawlHTTPClient
from app.integrations.serper import SerperHTTPClient
from app.schemas.research import ResearchRequest, ResearchResponse


class ResearchService:
    def __init__(self, serper_api_key: str, firecrawl_api_key: str):
        self.serper_client = SerperHTTPClient(api_key=serper_api_key)
        self.firecrawl_client = FirecrawlHTTPClient(api_key=firecrawl_api_key)

    def run(self, request: ResearchRequest) -> ResearchResponse:
        agent = AlgorithmicReverseEngineerAgent(
            serper_client=self.serper_client,
            firecrawl_client=self.firecrawl_client,
        )
        return agent.run(request)

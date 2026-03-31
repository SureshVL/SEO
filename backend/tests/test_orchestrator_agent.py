from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.schemas.orchestrator import OrchestratorRequest


class MockSerper:
    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3):
        return [
            {"link": "https://comp1.example.com"},
            {"link": "https://comp2.example.com"},
            {"link": "https://comp3.example.com"},
        ]


class MockFirecrawl:
    pages = {
        "https://comp1.example.com": "# Comp One\n## Intro\nWhat is SEO automation?\nOpenAI Research Labs",
        "https://comp2.example.com": "# Comp Two\n## Strategy\nHow to improve ASO quickly?\nGoogle Search Console",
        "https://comp3.example.com": "# Comp Three\n## Technical\nWhy entities matter for ranking?\nAnthropic Claude",
        "https://client.example.com": "# Client\n## Start\nBasic seo page",
    }

    def scrape_markdown(self, url: str) -> str:
        return self.pages[url]


def test_orchestrator_generates_logs_content_and_optional_aso():
    research_agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    orchestrator = OrchestratorAgent(research_agent=research_agent, threshold=95, max_cycles=2)

    response = orchestrator.run(
        OrchestratorRequest(
            client_url="https://client.example.com",
            primary_keyword="seo automation",
            locale="en-US",
            target_region="US",
            app_link="https://play.google.com/store/apps/details?id=com.omnirank",
            app_name="OMNI-RANK",
            app_category="Business",
            secondary_keywords=["app growth"],
            max_cycles=2,
        )
    )

    assert response.logs
    assert response.content_queue
    assert response.technical_fixes
    assert response.aso is not None
    assert response.aso.platform == "google-play"

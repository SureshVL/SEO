from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.schemas.research import ResearchRequest


class MockSerper:
    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3):
        return [
            {"link": "https://comp1.example.com"},
            {"link": "https://comp2.example.com"},
            {"link": "https://comp3.example.com"},
        ]


class MockFirecrawl:
    payloads = {
        "https://comp1.example.com": """
# Best AI SEO Guide
## What is AI SEO?
## Entity Optimization
Google Search Console helps improve SEO. OpenAI Research powers content analysis.
How do you rank in position zero?
""",
        "https://comp2.example.com": """
# AI SEO Strategy 2026
## Featured Snippets
## Backlink Outreach
Anthropic Claude and OpenAI models support writing workflows.
What tools improve Core Web Vitals?
""",
        "https://comp3.example.com": """
# Technical SEO + AI
## Schema Markup
## Internal Linking Strategy
Firecrawl API and Serper API assist with competitor intelligence.
Why does entity density matter?
""",
        "https://client.example.com": """
# My SEO Page
## Intro
This page discusses seo basics.
""",
    }

    def scrape_markdown(self, url: str) -> str:
        return self.payloads[url]


def test_research_agent_returns_gaps_and_recommendations():
    agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    request = ResearchRequest(
        client_url="https://client.example.com",
        primary_keyword="ai seo",
    )

    result = agent.run(request)

    assert result.seo_score < 95
    assert len(result.competitor_profiles) == 3
    assert result.gap_analysis.missing_entities
    assert result.recommendations

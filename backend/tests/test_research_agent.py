from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.workflow import SEOAutonomousLoop
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


class EmptySerper:
    def search_top_results(self, keyword: str, locale: str, region: str, limit: int = 3):
        return []


class TinyFirecrawl:
    def scrape_markdown(self, url: str) -> str:
        return "# Tiny\n## One\nAI SEO"


def test_research_agent_returns_gaps_and_recommendations():
    agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    request = ResearchRequest(client_url="https://client.example.com", primary_keyword="ai seo")

    result = agent.run(request)

    assert result.seo_score < 95
    assert len(result.competitor_profiles) == 3
    assert result.gap_analysis.missing_entities
    assert result.recommendations


def test_research_agent_raises_when_serp_empty():
    agent = AlgorithmicReverseEngineerAgent(EmptySerper(), TinyFirecrawl())
    request = ResearchRequest(client_url="https://client.example.com", primary_keyword="ai seo")

    try:
        agent.run(request)
        assert False, "Expected ValueError for empty SERP results"
    except ValueError as exc:
        assert "No SERP results" in str(exc)


def test_workflow_runs_until_max_iters():
    agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    loop = SEOAutonomousLoop(research_agent=agent, threshold=99.0, max_iters=2)
    request = ResearchRequest(client_url="https://client.example.com", primary_keyword="ai seo")

    result = loop.run(request)

    assert result.attempts == 2
    assert not result.passed_threshold
    assert result.final_score == result.response.seo_score

"""Tests for research agent and workflow — deterministic mode (no Claude)."""

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
        "https://comp1.example.com": """\
# Best AI SEO Guide
## What is AI SEO?
## Entity Optimization
Google Search Console helps improve SEO. OpenAI Research powers content analysis.
How do you rank in position zero?
""",
        "https://comp2.example.com": """\
# AI SEO Strategy 2026
## Featured Snippets
## Backlink Outreach
Anthropic Claude and OpenAI models support writing workflows.
What tools improve Core Web Vitals?
""",
        "https://comp3.example.com": """\
# Technical SEO + AI
## Schema Markup
## Internal Linking Strategy
Firecrawl API and Serper API assist with competitor intelligence.
Why does entity density matter?
""",
        "https://client.example.com": """\
# My SEO Page
## Intro
This page discusses seo basics.
""",
    }

    def scrape_markdown(self, url: str) -> str:
        return self.payloads.get(url, "# Empty\nNo content")


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


def test_research_agent_includes_ai_usage_in_metrics():
    agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    request = ResearchRequest(client_url="https://client.example.com", primary_keyword="ai seo")
    result = agent.run(request)

    assert "ai_usage" in result.raw_metrics
    # Without Claude client, tokens should be 0
    assert result.raw_metrics["ai_usage"]["total_cost_usd"] == 0.0


def test_workflow_runs_with_transition_trace():
    calls = {"content": 0, "technical": 0, "aso": 0}

    def _content(_):
        calls["content"] += 1

    def _technical(_):
        calls["technical"] += 1

    def _aso(_):
        calls["aso"] += 1

    agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    loop = SEOAutonomousLoop(
        research_agent=agent,
        threshold=99.0,
        max_iters=2,
        apply_content=_content,
        apply_technical=_technical,
        apply_aso=_aso,
    )
    request = ResearchRequest(client_url="https://client.example.com", primary_keyword="ai seo")

    result = loop.run(request)

    assert result.attempts == 2
    assert not result.passed_threshold
    assert calls == {"content": 1, "technical": 1, "aso": 1}
    assert "input_intake" in result.trace
    assert "content_remediation_applied" in result.trace
    assert result.trace[-1] == "max_iterations_reached"


def test_workflow_does_not_inflate_score():
    """Verify the old +1.5 score hack is gone."""
    scores = []

    def _capture_score(research_result):
        scores.append(research_result.seo_score)

    agent = AlgorithmicReverseEngineerAgent(MockSerper(), MockFirecrawl())
    loop = SEOAutonomousLoop(
        research_agent=agent,
        threshold=99.0,
        max_iters=3,
        apply_content=_capture_score,
    )
    request = ResearchRequest(client_url="https://client.example.com", primary_keyword="ai seo")
    result = loop.run(request)

    # All scores should be the same since the underlying data hasn't changed
    # (no fake +1.5 inflation)
    first = agent.run(request).seo_score
    assert result.final_score == first

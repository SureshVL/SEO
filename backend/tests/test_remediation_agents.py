"""Tests for content and technical agents in deterministic (no-Claude) mode."""

from app.agents.content_agent import ContentAgent
from app.agents.technical_agent import TechnicalAgent
from app.schemas.research import (
    CompetitorPageProfile,
    GapAnalysis,
    ResearchResponse,
)


def _sample_research() -> ResearchResponse:
    return ResearchResponse(
        seo_score=72.0,
        competitor_profiles=[
            CompetitorPageProfile(url="https://c1", title="C1", top_entities=["Google Search"]),
        ],
        client_profile=CompetitorPageProfile(url="https://client", title="Client", h2=["Intro"]),
        gap_analysis=GapAnalysis(
            missing_entities=["Google Search Console", "OpenAI Research"],
            missing_questions=["How do you rank for position zero?"],
            heading_gaps=["Featured Snippets"],
            density_gap=0.8,
        ),
        recommendations=["Add FAQ"],
        raw_metrics={"avg_competitor_word_count": 1500},
    )


def test_content_agent_fallback_generates_draft():
    """Content agent without Claude produces template draft."""
    agent = ContentAgent()
    drafts = agent.generate(_sample_research(), "ai seo")

    assert len(drafts) == 1
    assert drafts[0].slug == "ai-seo-guide"
    assert "Featured Snippet Summary" in drafts[0].body_markdown


def test_content_agent_meta_fallback():
    """Meta generation without Claude returns sensible defaults."""
    agent = ContentAgent()
    meta = agent.generate_meta("Some page content about SEO", "ai seo")
    assert "title" in meta
    assert "description" in meta


def test_technical_agent_deterministic_actions():
    """Technical agent without Claude returns deterministic baseline actions."""
    agent = TechnicalAgent()
    result = agent.full_audit("https://example.com", _sample_research())

    assert result.url == "https://example.com"
    assert len(result.actions) > 0
    # Should have heading gap action from research
    categories = [a.category for a in result.actions]
    assert "information_architecture" in categories


def test_technical_agent_execution_queue():
    """Execution queue produces proper payloads."""
    agent = TechnicalAgent()
    result = agent.full_audit("https://example.com", _sample_research())

    assert len(result.execution_queue) == len(result.actions)
    for item in result.execution_queue:
        assert "category" in item
        assert "status" in item
        assert item["status"] == "queued"


def test_technical_agent_heading_analysis():
    """Heading analysis detects missing H1 and sparse H2s."""
    research = _sample_research()
    # Override client profile to have no H1
    research.client_profile = CompetitorPageProfile(url="https://client", title="Client", h1=None, h2=[])

    agent = TechnicalAgent()
    result = agent.full_audit("https://example.com", research)

    actions_text = " ".join(a.action for a in result.actions)
    assert "H1" in actions_text or "H2" in actions_text

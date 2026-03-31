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
        client_profile=CompetitorPageProfile(url="https://client", title="Client"),
        gap_analysis=GapAnalysis(
            missing_entities=["Google Search Console", "OpenAI Research"],
            missing_questions=["How do you rank for position zero?"],
            heading_gaps=["Featured Snippets"],
            density_gap=0.8,
        ),
        recommendations=["Add FAQ"],
        raw_metrics={},
    )


def test_content_agent_generates_position_zero_draft():
    agent = ContentAgent()
    drafts = agent.generate(_sample_research(), "ai seo")

    assert len(drafts) == 1
    assert drafts[0].slug == "ai-seo-guide"
    assert "Featured Snippet Summary" in drafts[0].body_markdown


def test_technical_agent_generates_actions():
    agent = TechnicalAgent()
    actions = agent.audit(_sample_research())

    assert actions
    assert any(a.category == "core_web_vitals" for a in actions)
    assert any(a.category == "information_architecture" for a in actions)

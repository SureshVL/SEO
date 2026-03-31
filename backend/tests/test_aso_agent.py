from app.agents.aso_agent import AsoAgent
from app.schemas.aso import AsoRequest


def test_aso_agent_generates_localized_metadata_for_play_store():
    agent = AsoAgent()
    request = AsoRequest(
        app_link="https://play.google.com/store/apps/details?id=com.omnirank.app",
        app_name="OMNI-RANK",
        category="Business",
        primary_keyword="seo automation",
        secondary_keywords=["keyword tracking", "competitor analysis"],
        locales=["en-US", "es-ES"],
    )

    result = agent.run(request)

    assert result.platform == "google-play"
    assert len(result.metadata) == 2
    assert result.metadata[0].title_variants
    assert result.review_response_playbook
    assert any("short description" in note.lower() for note in result.optimization_notes)


def test_aso_agent_detects_app_store_platform():
    agent = AsoAgent()
    request = AsoRequest(
        app_link="https://apps.apple.com/us/app/omni-rank/id123456789",
        app_name="OMNI-RANK",
        category="Productivity",
        primary_keyword="aso optimization",
        secondary_keywords=["app growth"],
        locales=["en-US"],
    )

    result = agent.run(request)

    assert result.platform == "app-store"
    assert result.metadata[0].keyword_field

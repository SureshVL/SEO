from app.services.persistence import AgentLogEvent, CompetitorIntelEvent, NoopPersistenceRepository


def test_noop_repository_accepts_events():
    repo = NoopPersistenceRepository()

    repo.log_agent_event(
        AgentLogEvent(
            project_id="project-1",
            agent_name="research_agent",
            action_type="started",
            action_payload={"keyword": "ai seo"},
        )
    )

    repo.save_competitor_intel(
        CompetitorIntelEvent(
            project_id="project-1",
            source_url="https://example.com",
            scraped_content="body",
            entity_maps={"top_entities": ["Google Search"]},
        )
    )

    assert True

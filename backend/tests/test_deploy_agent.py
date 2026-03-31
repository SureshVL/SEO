from app.agents.deploy_agent import DeployAgent
from app.schemas.deploy import DeployRequest


def test_deploy_agent_dry_run():
    agent = DeployAgent()
    result = agent.run(DeployRequest(project_id="p1", platform="wordpress", dry_run=True))
    assert result.status == "dry_run_complete"
    assert result.actions


def test_deploy_agent_invalid_platform():
    agent = DeployAgent()
    result = agent.run(DeployRequest(project_id="p1", platform="unknown", dry_run=False))
    assert result.status == "failed"

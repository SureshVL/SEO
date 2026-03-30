from fastapi.testclient import TestClient

from app.main import app


def test_research_endpoint_requires_api_keys():
    client = TestClient(app)
    response = client.post(
        "/research/run",
        json={
            "client_url": "https://example.com",
            "primary_keyword": "ai seo",
            "locale": "en-US",
            "target_region": "US",
        },
    )

    assert response.status_code == 500
    assert "Missing SERPER_API_KEY" in response.json()["detail"]

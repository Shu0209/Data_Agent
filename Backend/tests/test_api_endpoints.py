from fastapi.testclient import TestClient
from data_agent.main import app

client = TestClient(app)


def test_home_endpoint_status_and_message():
    """GET / should return 200 OK and live status message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Live" in data["message"]


def test_query_endpoint_missing_body():
    """POST /query with missing request body should return 422 Unprocessable Entity."""
    response = client.post("/query", json={})
    assert response.status_code == 422


def test_query_endpoint_empty_input():
    """POST /query with empty user_input should return 422 validation error."""
    response = client.post("/query", json={"user_input": ""})
    assert response.status_code == 422


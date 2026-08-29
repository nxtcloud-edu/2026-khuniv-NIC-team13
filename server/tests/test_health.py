from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "SUCCESS"
    assert body["data"]["status"] == "ok"
    assert body["data"]["app"] == "AI Rookie Pertineo API"

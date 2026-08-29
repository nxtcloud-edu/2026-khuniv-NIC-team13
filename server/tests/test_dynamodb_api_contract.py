import boto3
from fastapi.testclient import TestClient
from moto import mock_aws

from app.api.v1 import routes
from app.main import app
from app.repositories.dynamodb import DynamoDBRepository, create_required_tables

client = TestClient(app)


def assert_success(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "SUCCESS"
    return body


def full_agreements() -> dict:
    return {
        "termsOfServiceAgreed": True,
        "privacyCollectionAgreed": True,
        "privacyPolicyAgreed": True,
        "thirdPartySharingAgreed": True,
    }


@mock_aws
def test_core_api_flow_works_with_dynamodb_repository(monkeypatch):
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
    create_required_tables(dynamodb)
    repo = DynamoDBRepository(dynamodb)
    monkeypatch.setattr(routes, "store", repo)

    email = "student@khu.ac.kr"

    assert_success(client.post("/api/auth/email/verification", json={"email": email}))
    verified = assert_success(
        client.post("/api/auth/email/verify", json={"email": email, "code": "123456"})
    )
    assert verified["data"] == {"email": email, "verified": True}

    credit_before = assert_success(client.get("/api/auth/email/credit", params={"email": email}))[
        "data"
    ]
    assert credit_before["verified"] is True
    assert credit_before["remainCount"] == 3

    started = client.post(
        "/api/sessions/start",
        json={"email": email, "agreements": full_agreements()},
    )
    assert_success(started)
    assert "PERTINEO_SESSION" in started.cookies

    extended = client.post("/api/sessions/extend", cookies=started.cookies)
    assert_success(extended)

    analysis = client.post(
        "/api/analysis",
        json={"userId": email, "questionList": ["Q1"], "answerList": ["A1"]},
    )
    assert analysis.status_code == 200
    assert analysis.headers["content-type"].startswith("text/event-stream")
    assert '"status": "FAILED"' in analysis.text

    credit_after = assert_success(client.get("/api/auth/email/credit", params={"email": email}))["data"]
    assert credit_after["remainCount"] == credit_before["remainCount"]

    created = assert_success(client.post("/api/notice", json={"title": "공지", "content": "내용"}))
    notice_id = created["data"]["id"]
    detail = assert_success(client.get(f"/api/notice/{notice_id}"))
    assert detail["data"]["content"] == "내용"

    patched = assert_success(client.patch(f"/api/notice/{notice_id}", json={"title": "수정"}))
    assert patched["data"]["title"] == "수정"

    deleted = assert_success(client.delete(f"/api/notice/{notice_id}"))
    assert deleted["data"]["id"] == notice_id
    assert client.get(f"/api/notice/{notice_id}").status_code == 404

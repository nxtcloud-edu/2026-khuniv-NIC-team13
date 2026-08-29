import pytest
from fastapi.testclient import TestClient

from app.api.v1 import routes
from app.core.config import Settings
from app.main import app
from app.services.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    store.reset()
    client.cookies.clear()
    yield
    client.cookies.clear()


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


def verify_email(email: str = "student@khu.ac.kr") -> None:
    assert_success(client.post("/api/auth/email/verification", json={"email": email}))
    verified = assert_success(client.post("/api/auth/email/verify", json={"email": email, "code": "123456"}))
    assert verified["data"]["verified"] is True


def login_admin() -> dict:
    login = client.post("/admin/login", json={"username": "admin", "password": "1234"})
    assert login.status_code == 200
    assert "loginStatus" in login.cookies
    return dict(login.cookies)


def test_admin_login_cookie_is_httponly_and_samesite_lax():
    login = client.post("/admin/login", json={"username": "admin", "password": "1234"})
    assert login.status_code == 200
    set_cookie = login.headers["set-cookie"]
    assert "loginStatus=success" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_health_and_request_headers():
    response = client.get("/health", headers={"X-Request-ID": "qa-request"})
    body = assert_success(response)
    assert body["data"]["status"] == "ok"
    assert response.headers["X-Request-ID"] == "qa-request"
    assert "X-Process-Time-Ms" in response.headers


def test_setup_apis_match_legacy_contract():
    minimum_counts = {"companies": 200, "positions": 100, "universities": 400, "majors": 100}
    for kind in ["companies", "positions", "universities", "majors"]:
        body = assert_success(client.get(f"/api/setup/{kind}"))
        assert isinstance(body["data"]["items"], list)
        assert len(body["data"]["items"]) >= minimum_counts[kind]
        assert len(body["data"]["items"]) == len(set(body["data"]["items"]))


def test_email_verify_requires_previously_sent_code():
    response = client.post(
        "/api/auth/email/verify",
        json={"email": "magic@khu.ac.kr", "code": "123456"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "EMAIL_VERIFICATION_FAILED"


def test_email_verify_accepts_numeric_code_from_legacy_client():
    email = "numeric-code@khu.ac.kr"
    assert_success(client.post("/api/auth/email/verification", json={"email": email}))

    verified = assert_success(
        client.post("/api/auth/email/verify", json={"email": email, "code": 123456})
    )

    assert verified["data"] == {"email": email, "verified": True}


def test_email_session_credit_flow():
    email = "student@khu.ac.kr"
    verify_email(email)
    credit = assert_success(client.get("/api/auth/email/credit", params={"email": email}))
    assert credit["data"]["email"] == email
    assert credit["data"]["verified"] is True

    start = client.post(
        "/api/sessions/start",
        json={"email": email, "agreements": full_agreements()},
    )
    body = assert_success(start)
    assert body["data"]["member"]["email"] == email
    assert "PERTINEO_SESSION" in start.cookies

    extend = client.post("/api/sessions/extend", cookies=start.cookies)
    body = assert_success(extend)
    assert body["data"]["status"] == "ACTIVE"


def test_session_cookie_name_uses_settings_for_start_and_extend(monkeypatch):
    custom_settings = Settings(session_cookie_name="CUSTOM_SESSION")
    monkeypatch.setattr(routes, "get_settings", lambda: custom_settings)

    email = "custom@khu.ac.kr"
    verify_email(email)
    start = client.post(
        "/api/sessions/start",
        json={"email": email, "agreements": full_agreements()},
    )
    assert_success(start)
    assert "CUSTOM_SESSION" in start.cookies
    assert "PERTINEO_SESSION" not in start.cookies

    extend = client.post("/api/sessions/extend", cookies=start.cookies)
    assert_success(extend)
    assert "CUSTOM_SESSION" in extend.cookies


def test_session_extend_rejects_expired_session(monkeypatch):
    custom_settings = Settings(session_expire_minutes=-1)
    monkeypatch.setattr(routes, "get_settings", lambda: custom_settings)

    email = "expired@khu.ac.kr"
    verify_email(email)
    start = client.post(
        "/api/sessions/start",
        json={"email": email, "agreements": full_agreements()},
    )
    assert_success(start)

    extend = client.post("/api/sessions/extend", cookies=start.cookies)
    assert extend.status_code == 400
    assert extend.json()["code"] == "INVALID_SESSION"


def test_session_start_requires_verified_email():
    response = client.post(
        "/api/sessions/start",
        json={"email": "new@khu.ac.kr", "agreements": full_agreements()},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "EMAIL_NOT_VERIFIED"


def test_session_rejects_missing_agreements_and_non_member(monkeypatch):
    restricted_settings = Settings(
        allow_all_emails=False,
        allowed_member_email_domains=["khu.ac.kr"],
    )
    monkeypatch.setattr(routes, "get_settings", lambda: restricted_settings)

    response = client.post(
        "/api/sessions/start",
        json={"email": "outsider@example.com", "agreements": full_agreements()},
    )
    assert response.status_code == 403

    verify_email("student@khu.ac.kr")
    response = client.post(
        "/api/sessions/start",
        json={
            "email": "student@khu.ac.kr",
            "agreements": {
                "termsOfServiceAgreed": True,
                "privacyCollectionAgreed": False,
                "privacyPolicyAgreed": True,
                "thirdPartySharingAgreed": True,
            },
        },
    )
    assert response.status_code == 400


def test_general_email_can_verify_and_start_session():
    email = "person@example.com"
    verify_email(email)

    start = client.post(
        "/api/sessions/start",
        json={"email": email, "agreements": full_agreements()},
    )

    body = assert_success(start)
    assert body["data"]["member"]["email"] == email
    assert "PERTINEO_SESSION" in start.cookies


def test_notice_crud_contract():
    created = assert_success(client.post("/api/notice", json={"title": "공지", "content": "내용"}))
    notice_id = created["data"]["id"]
    assert created["data"]["author"] == "admin"

    listed = assert_success(client.get("/api/notice", params={"page": 1, "size": 10}))
    assert listed["data"]["totalElements"] >= 1

    detail = assert_success(client.get(f"/api/notice/{notice_id}"))
    assert detail["data"]["content"] == "내용"

    patched = assert_success(client.patch(f"/api/notice/{notice_id}", json={"title": "수정"}))
    assert patched["data"]["title"] == "수정"

    deleted = assert_success(client.delete(f"/api/notice/{notice_id}"))
    assert deleted["data"]["id"] == notice_id
    assert client.get(f"/api/notice/{notice_id}").status_code == 404


def test_parse_and_analysis_stream_contract():
    email = "student@khu.ac.kr"
    verify_email(email)
    parsed = assert_success(client.post("/api/parse/convert", content="Q1?\nA1", headers={"content-type": "text/plain"}))
    assert parsed["data"]["question_list"] == ["Q1?"]
    assert parsed["data"]["answer_list"] == ["A1"]

    before = assert_success(client.get("/api/auth/email/credit", params={"email": email}))["data"]["remainCount"]
    response = client.post(
        "/api/analysis",
        json={"userId": email, "questionList": ["Q1"], "answerList": ["A1"]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "evaluate_error"' in response.text
    assert '"status": "FAILED"' in response.text
    after = assert_success(client.get("/api/auth/email/credit", params={"email": email}))["data"]["remainCount"]
    assert after == before


def test_analysis_requires_verified_email_and_credit():
    response = client.post(
        "/api/analysis",
        json={"userId": "any@khu.ac.kr", "questionList": ["Q1"], "answerList": ["A1"]},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "EMAIL_NOT_VERIFIED"

    email = "limited@khu.ac.kr"
    verify_email(email)
    store.email_credit[email]["remainCount"] = 0
    response = client.post(
        "/api/analysis",
        json={"userId": email, "questionList": ["Q1"], "answerList": ["A1"]},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CREDIT_REQUIRED"


def test_admin_routes_require_login_status_cookie():
    protected_routes = [
        ("post", "/admin/notices"),
        ("get", "/admin/notices/form"),
        ("get", "/admin/notices/detail/1"),
        ("get", "/admin/notices/edit/1"),
        ("get", "/admin/popup/form"),
        ("get", "/admin/logs/2026-07-09"),
    ]
    for method, path in protected_routes:
        response = getattr(client, method)(path)
        assert response.status_code == 403, path

    cookies = login_admin()
    assert client.post("/admin/notices", cookies=cookies).status_code == 200
    assert client.get("/admin/notices/form", cookies=cookies).status_code == 200
    assert client.get("/admin/notices/detail/1", cookies=cookies).status_code == 200
    assert client.get("/admin/notices/edit/1", cookies=cookies).status_code == 200
    assert client.get("/admin/popup/form", cookies=cookies).status_code == 200
    assert client.get("/admin/logs/2026-07-09", cookies=cookies).status_code == 200

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_groups_endpoints_by_domain_tags():
    schema = client.get("/openapi.json").json()
    declared_tags = {tag["name"] for tag in schema["tags"]}
    assert {"Health", "Setup", "Auth", "Session", "Parsing", "Analysis", "Notice", "Admin"}.issubset(declared_tags)

    assert schema["paths"]["/health"]["get"]["tags"] == ["Health"]
    assert schema["paths"]["/api/setup/{kind}"]["get"]["tags"] == ["Setup"]
    assert schema["paths"]["/api/auth/email/verification"]["post"]["tags"] == ["Auth"]
    assert schema["paths"]["/api/sessions/start"]["post"]["tags"] == ["Session"]
    assert schema["paths"]["/api/parse/convert"]["post"]["tags"] == ["Parsing"]
    assert schema["paths"]["/api/analysis"]["post"]["tags"] == ["Analysis"]
    assert schema["paths"]["/api/notice"]["get"]["tags"] == ["Notice"]
    assert schema["paths"]["/admin/login"]["post"]["tags"] == ["Admin"]

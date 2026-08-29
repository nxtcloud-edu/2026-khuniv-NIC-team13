"""Port of ``AgentApplicationTests.contextLoads`` — verifies the FastAPI app
(dependency graph + routers) can be constructed and started end-to-end."""
from fastapi.testclient import TestClient

from app.main import create_app


def test_context_loads():
    app = create_app()
    with TestClient(app) as client:
        # DynamoDB Local isn't running in the test environment; startup must
        # not raise even so (mirrors the Java initializer's graceful skip).
        assert client.app is app

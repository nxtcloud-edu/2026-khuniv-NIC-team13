from app.config.settings import Settings
from app.repository import dynamodb_client
from app.vector import s3vectors_client


def settings_with_static_credentials() -> Settings:
    return Settings(
        _env_file=None,
        SPRING_PROFILES_ACTIVE="prod",
        AWS_REGION="ap-northeast-2",
        AWS_ACCESS_KEY_ID="access-test",
        AWS_SECRET_ACCESS_KEY="secret-test",
        AWS_SESSION_TOKEN="session-test",
    )


def test_dynamodb_client_receives_credentials_loaded_from_dotenv(monkeypatch):
    captured = {}
    monkeypatch.setattr(dynamodb_client.boto3, "client", lambda service, **kwargs: captured.update(kwargs))

    dynamodb_client.create_dynamodb_client(settings_with_static_credentials())

    assert captured["aws_access_key_id"] == "access-test"
    assert captured["aws_secret_access_key"] == "secret-test"
    assert captured["aws_session_token"] == "session-test"


def test_s3vectors_client_receives_credentials_loaded_from_dotenv(monkeypatch):
    captured = {}
    monkeypatch.setattr(s3vectors_client.boto3, "client", lambda service, **kwargs: captured.update(kwargs))

    s3vectors_client.create_s3vectors_client(settings_with_static_credentials())

    assert captured == {
        "region_name": "ap-northeast-2",
        "aws_access_key_id": "access-test",
        "aws_secret_access_key": "secret-test",
        "aws_session_token": "session-test",
    }


def test_clients_keep_default_provider_chain_when_static_credentials_are_absent(monkeypatch):
    captured = {}
    monkeypatch.setattr(s3vectors_client.boto3, "client", lambda service, **kwargs: captured.update(kwargs))
    settings = Settings(
        _env_file=None,
        SPRING_PROFILES_ACTIVE="prod",
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        AWS_SESSION_TOKEN="",
    )

    s3vectors_client.create_s3vectors_client(settings)

    assert captured.get("region_name") == "ap-northeast-2"
    assert "aws_access_key_id" not in captured
    assert "aws_secret_access_key" not in captured
    assert "aws_session_token" not in captured

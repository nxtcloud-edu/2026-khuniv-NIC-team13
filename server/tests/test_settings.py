from app.core.config import Settings


def test_settings_exposes_cors_origins_for_cors_middleware():
    settings = Settings(backend_cors_origins="http://localhost:3000, http://localhost:5173")
    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_settings_exposes_admin_credentials_from_environment_contract():
    settings = Settings(admin_username="ops-admin", admin_password="safe-password")
    assert settings.admin_username == "ops-admin"
    assert settings.admin_password == "safe-password"


def test_settings_exposes_email_verification_table_name():
    settings = Settings(dynamodb_email_verifications_table="custom-verifications")
    assert settings.dynamodb_email_verifications_table == "custom-verifications"


def test_settings_exposes_counter_table_name():
    settings = Settings(dynamodb_counters_table="custom-counters")
    assert settings.dynamodb_counters_table == "custom-counters"


def test_settings_allows_general_email_and_ses_delivery_configuration():
    settings = Settings(
        allow_all_emails=True,
        email_delivery_backend="ses",
        email_from_address="noreply@example.com",
    )

    assert settings.ALLOW_ALL_EMAILS is True
    assert settings.email_delivery_backend == "ses"
    assert settings.email_from_address == "noreply@example.com"

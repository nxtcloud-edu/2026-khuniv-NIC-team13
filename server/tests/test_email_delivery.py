import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.email_delivery import EmailDeliveryError, SmtpEmailDelivery


def smtp_settings() -> Settings:
    return Settings(
        email_delivery_backend="smtp",
        email_from_address="pertineo5@gmail.com",
        smtp_username="pertineo5@gmail.com",
        smtp_app_password="test-app-password",
    )


@patch("app.services.email_delivery.smtplib.SMTP_SSL")
def test_smtp_delivery_sends_verification_email(smtp_ssl: MagicMock) -> None:
    smtp = smtp_ssl.return_value.__enter__.return_value

    SmtpEmailDelivery(smtp_settings()).send_verification_code("user@example.com", "123456")

    smtp_ssl.assert_called_once()
    smtp.login.assert_called_once_with("pertineo5@gmail.com", "test-app-password")
    message = smtp.send_message.call_args.args[0]
    assert message["From"] == "pertineo5@gmail.com"
    assert message["To"] == "user@example.com"
    assert "123456" in message.get_content()


@patch("app.services.email_delivery.smtplib.SMTP_SSL")
def test_smtp_delivery_wraps_transport_errors(smtp_ssl: MagicMock) -> None:
    smtp = smtp_ssl.return_value.__enter__.return_value
    smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad credentials")

    with pytest.raises(EmailDeliveryError):
        SmtpEmailDelivery(smtp_settings()).send_verification_code("user@example.com", "123456")

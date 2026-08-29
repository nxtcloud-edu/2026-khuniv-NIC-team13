import secrets
import smtplib
import ssl
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings


class EmailDelivery(Protocol):
    def create_code(self) -> str: ...

    def send_verification_code(self, email: str, code: str) -> None: ...


class EmailDeliveryError(Exception):
    pass


class DisabledEmailDelivery:
    """Deterministic local/test delivery that never sends an external email."""

    def create_code(self) -> str:
        return "123456"

    def send_verification_code(self, email: str, code: str) -> None:
        return None


# SES delivery is intentionally retained so production can switch back with
# EMAIL_DELIVERY_BACKEND=ses without changing application code.
class SesEmailDelivery:
    def __init__(self, settings: Settings) -> None:
        self.client = boto3.client("sesv2", region_name=settings.aws_region)
        self.sender = settings.email_from_address
        self.subject = settings.email_verification_subject

    def create_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def send_verification_code(self, email: str, code: str) -> None:
        try:
            self.client.send_email(
                FromEmailAddress=self.sender,
                Destination={"ToAddresses": [email]},
                Content={
                    "Simple": {
                        "Subject": {"Data": self.subject, "Charset": "UTF-8"},
                        "Body": {
                            "Text": {
                                "Data": (
                                    "Pertineo 이메일 인증번호는 "
                                    f"{code} 입니다. 인증번호는 5분 동안 유효합니다."
                                ),
                                "Charset": "UTF-8",
                            }
                        },
                    }
                },
            )
        except (BotoCoreError, ClientError) as exc:
            raise EmailDeliveryError("SES failed to send the verification email") from exc


class SmtpEmailDelivery:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_app_password.replace(" ", "")
        self.sender = settings.email_from_address
        self.subject = settings.email_verification_subject

    def create_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def send_verification_code(self, email: str, code: str) -> None:
        message = EmailMessage()
        message["Subject"] = self.subject
        message["From"] = self.sender
        message["To"] = email
        message.set_content(
            f"Pertineo 이메일 인증번호는 {code} 입니다. "
            "인증번호는 5분 동안 유효합니다."
        )

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                self.host,
                self.port,
                context=context,
                timeout=10,
            ) as smtp:
                smtp.login(self.username, self.password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError("SMTP failed to send the verification email") from exc


@lru_cache
def get_email_delivery() -> EmailDelivery:
    settings = get_settings()
    backend = settings.email_delivery_backend.lower()
    if backend == "disabled":
        return DisabledEmailDelivery()
    if backend == "ses":
        if not settings.email_from_address:
            raise ValueError("EMAIL_FROM_ADDRESS is required when EMAIL_DELIVERY_BACKEND=ses")
        return SesEmailDelivery(settings)
    if backend == "smtp":
        required = {
            "EMAIL_FROM_ADDRESS": settings.email_from_address,
            "SMTP_USERNAME": settings.smtp_username,
            "SMTP_APP_PASSWORD": settings.smtp_app_password,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Required SMTP settings are missing: {', '.join(missing)}")
        return SmtpEmailDelivery(settings)
    raise ValueError(f"Unsupported email delivery backend: {settings.email_delivery_backend}")

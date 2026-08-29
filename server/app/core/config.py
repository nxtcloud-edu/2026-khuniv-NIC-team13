from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Rookie Pertineo API"
    app_env: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api"
    backend_cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")
    log_level: str = "INFO"
    session_cookie_name: str = "PERTINEO_SESSION"
    session_expire_minutes: int = 30
    session_extend_minutes: int = 30
    allow_all_emails: bool = True
    allowed_member_email_domains: list[str] = Field(default_factory=lambda: ["khu.ac.kr"])
    member_email_whitelist: list[str] = Field(default_factory=list)

    email_delivery_backend: str = "disabled"
    email_from_address: str = ""
    email_verification_subject: str = "Pertineo 이메일 인증번호"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_app_password: str = ""

    repository_backend: str = "memory"
    aws_region: str = "ap-northeast-2"
    dynamodb_notices_table: str = "pertineo-notices"
    dynamodb_emails_table: str = "pertineo-emails"
    dynamodb_email_verifications_table: str = "pertineo-email-verifications"
    dynamodb_sessions_table: str = "pertineo-sessions"
    dynamodb_popups_table: str = "pertineo-popups"
    dynamodb_counters_table: str = "pertineo-counters"

    admin_username: str = "admin"
    admin_password: str = "1234"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def APP_NAME(self) -> str:
        return self.app_name

    @property
    def ENV(self) -> str:
        return self.app_env

    @property
    def SESSION_COOKIE_NAME(self) -> str:
        return self.session_cookie_name

    @property
    def SESSION_EXPIRE_MINUTES(self) -> int:
        return self.session_expire_minutes

    @property
    def SESSION_EXTEND_MINUTES(self) -> int:
        return self.session_extend_minutes

    @property
    def ALLOWED_MEMBER_EMAIL_DOMAINS(self) -> list[str]:
        return self.allowed_member_email_domains

    @property
    def ALLOW_ALL_EMAILS(self) -> bool:
        return self.allow_all_emails

    @property
    def MEMBER_EMAIL_WHITELIST(self) -> list[str]:
        return self.member_email_whitelist


@lru_cache
def get_settings() -> Settings:
    return Settings()

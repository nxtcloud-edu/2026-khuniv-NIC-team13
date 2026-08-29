"""Application configuration.

Mirrors the Spring Boot ``application*.yml`` + ``@ConfigurationProperties``
classes (``AppConfig``, ``DynamoDBProperties``, ``SmartParsingProperties``,
``S3VectorsConfig``, ``LocalCacheConfig``) from the Java service.

Profile selection follows the same convention as the Java app:
``SPRING_PROFILES_ACTIVE`` (default ``local``) chooses between
``local`` and ``prod`` defaults, all overridable via environment
variables / a ``.env`` file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.smart_parsing_properties import SmartParsingProperties


class DynamoDBTables:
    def __init__(self, resume_coordinates: str, document_context: str) -> None:
        self.resume_coordinates = resume_coordinates
        self.document_context = document_context


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # --- Active profile: local | prod ---
    spring_profiles_active: str = Field(default="local", validation_alias="SPRING_PROFILES_ACTIVE")

    # --- OpenAI (structured output, resume parsing, and embeddings) ---
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(
        default="gpt-5.6-luna", validation_alias="OPENAI_CHAT_MODEL"
    )
    openai_reasoning_effort: Literal[
        "none", "low", "medium", "high", "xhigh", "max"
    ] = Field(default="low", validation_alias="OPENAI_REASONING_EFFORT")

    # --- Tavily ---
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")

    # --- AWS / DynamoDB ---
    aws_region: str = Field(default="ap-northeast-2", validation_alias="AWS_REGION")
    # pydantic-settings reads the dotenv file but does not export its values to
    # os.environ. Pass optional static credentials to boto3 explicitly; leave
    # them empty in deployed environments that use the normal role/provider chain.
    aws_access_key_id: str = Field(default="", validation_alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", validation_alias="AWS_SECRET_ACCESS_KEY")
    aws_session_token: str = Field(default="", validation_alias="AWS_SESSION_TOKEN")
    # local profile default endpoint override (application-local.yml -> DYNAMODB_ENDPOINT)
    dynamodb_endpoint_local: str = Field(default="http://localhost:8000", validation_alias="DYNAMODB_ENDPOINT")
    # prod profile default endpoint override (application-prod.yml -> AWS_DYNAMODB_ENDPOINT)
    dynamodb_endpoint_prod: str = Field(default="", validation_alias="AWS_DYNAMODB_ENDPOINT")
    dynamodb_table_resume_coordinates: str = Field(
        default="pertino-resume-coordinates", validation_alias="AWS_DYNAMODB_TABLE_RESUME_COORDINATES"
    )
    dynamodb_table_document_context: str = Field(
        default="pertineo-document-context", validation_alias="AWS_DYNAMODB_TABLE_DOCUMENT_CONTEXT"
    )

    # --- S3 Vectors ---
    s3_vectors_bucket: str = Field(default="pertineo-data-vector", validation_alias="S3_VECTORS_BUCKET")
    s3_vectors_index: str = Field(default="pertineo-data-vector-index", validation_alias="S3_VECTORS_INDEX")

    # --- LangSmith tracing ---
    langsmith_api_key: str = Field(default="설정안됨", validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="pertineo-default", validation_alias="LANGSMITH_PROJECT")

    # --- Smart parsing ---
    smart_parsing_primary_model: str = Field(
        default="gpt-5-nano", validation_alias="SMART_PARSING_PRIMARY_MODEL"
    )
    smart_parsing_fallback_model: str = Field(
        default="gpt-5-mini", validation_alias="SMART_PARSING_FALLBACK_MODEL"
    )
    smart_parsing_fallback_enabled: bool = Field(default=True, validation_alias="SMART_PARSING_FALLBACK_ENABLED")
    smart_parsing_fallback_max_chars: int = Field(default=1000, validation_alias="SMART_PARSING_FALLBACK_MAX_CHARS")
    resume_file_parsing_model: str = Field(
        default="gpt-5-mini", validation_alias="RESUME_FILE_PARSING_MODEL"
    )

    # --- Local cache (web search results) ---
    web_search_cache_ttl_seconds: int = 30 * 60
    web_search_cache_max_size: int = 1000

    # --- Resource directory (mirrors src/main/resources classpath root) ---
    resources_dir: str = Field(
        default_factory=lambda: __import__("os").path.join(
            __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__file__))),
            "resources",
        )
    )

    @property
    def is_local_profile(self) -> bool:
        return self.spring_profiles_active == "local"

    @property
    def dynamodb_endpoint(self) -> str | None:
        endpoint = self.dynamodb_endpoint_local if self.is_local_profile else self.dynamodb_endpoint_prod
        return endpoint or None

    @property
    def dynamodb_tables(self) -> DynamoDBTables:
        return DynamoDBTables(self.dynamodb_table_resume_coordinates, self.dynamodb_table_document_context)

    @property
    def boto3_credentials(self) -> dict[str, str]:
        if not self.aws_access_key_id and not self.aws_secret_access_key:
            return {}
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise RuntimeError("AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 함께 설정해야 합니다.")
        credentials = {
            "aws_access_key_id": self.aws_access_key_id,
            "aws_secret_access_key": self.aws_secret_access_key,
        }
        if self.aws_session_token:
            credentials["aws_session_token"] = self.aws_session_token
        return credentials

    @property
    def smart_parsing(self) -> SmartParsingProperties:
        return SmartParsingProperties(
            primary_model=self.smart_parsing_primary_model,
            fallback_model=self.smart_parsing_fallback_model,
            fallback_enabled=self.smart_parsing_fallback_enabled,
            fallback_max_chars=self.smart_parsing_fallback_max_chars,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

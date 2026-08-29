from functools import lru_cache

import boto3

from app.core.config import get_settings
from app.repositories.dynamodb import DynamoDBRepository
from app.repositories.in_memory import InMemoryRepository
from app.repositories.protocols import AppRepository

_memory_repository = InMemoryRepository()


@lru_cache
def get_repository() -> AppRepository:
    settings = get_settings()
    backend = settings.repository_backend.lower()
    if backend == "memory":
        return _memory_repository
    if backend == "dynamodb":
        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        return DynamoDBRepository(
            dynamodb_resource=dynamodb,
            notices_table=settings.dynamodb_notices_table,
            emails_table=settings.dynamodb_emails_table,
            email_verifications_table=settings.dynamodb_email_verifications_table,
            sessions_table=settings.dynamodb_sessions_table,
            popups_table=settings.dynamodb_popups_table,
            counters_table=settings.dynamodb_counters_table,
        )
    raise ValueError(f"Unsupported repository backend: {settings.repository_backend}")

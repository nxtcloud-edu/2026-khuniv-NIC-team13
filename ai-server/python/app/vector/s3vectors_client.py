"""Port of ``pertineo.agent.config.S3VectorsConfig`` (S3 Vectors client factory)."""
from __future__ import annotations

import boto3

from app.config.settings import Settings


def create_s3vectors_client(settings: Settings):
    return boto3.client(
        "s3vectors",
        region_name=settings.aws_region,
        **settings.boto3_credentials,
    )

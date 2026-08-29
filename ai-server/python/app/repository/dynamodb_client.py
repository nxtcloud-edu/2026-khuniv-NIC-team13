"""Port of ``pertineo.agent.config.DynamoDbConfig`` (DynamoDB client factory)."""
from __future__ import annotations

import boto3
from botocore.config import Config

from app.config.settings import Settings

# boto3's default connect/read timeouts are 60s with retries, which turns
# "DynamoDB Local isn't running" into a multi-minute hang instead of the
# graceful, fast skip the local table initializer is documented to do.
# These bounds are generous for real DynamoDB traffic too (typical latency
# is tens of ms), so they're safe to apply universally, not just locally.
_CLIENT_CONFIG = Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 2, "mode": "standard"})


def create_dynamodb_client(settings: Settings):
    kwargs: dict = {"region_name": settings.aws_region, "config": _CLIENT_CONFIG}

    endpoint = settings.dynamodb_endpoint
    if endpoint:
        # DynamoDB Local (or another custom endpoint) — use dummy static creds,
        # matching the Java StaticCredentialsProvider("dummy", "dummy") branch.
        kwargs["endpoint_url"] = endpoint
        kwargs["aws_access_key_id"] = "dummy"
        kwargs["aws_secret_access_key"] = "dummy"
    else:
        # pydantic-settings loads .env without mutating os.environ, so values
        # explicitly present there must be forwarded to boto3. Empty settings
        # preserve the default provider chain (shared config / instance role).
        kwargs.update(settings.boto3_credentials)

    return boto3.client("dynamodb", **kwargs)

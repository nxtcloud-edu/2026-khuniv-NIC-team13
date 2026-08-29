"""Upload the saved Upstage JSONL to S3 Vectors without calling an embedding API."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import dotenv_values

PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from tools.reembed_upstage import (
    EMBED_2_DIMENSION,
    get_index_or_none,
    list_existing_keys,
    sha256_file,
    validate_index,
)

PROJECT_ROOT = PYTHON_ROOT.parent
DEFAULT_SOURCE = PROJECT_ROOT / "private_exports" / "embedding_data_20260812" / "upstage_vectors.jsonl"
DEFAULT_INDEX = "pertineo-data-vector-upstage-embed2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=PYTHON_ROOT / ".env")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--profile", help="Named AWS CLI profile; takes precedence over static dotenv keys.")
    parser.add_argument("--region")
    parser.add_argument("--bucket")
    parser.add_argument("--index")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--create-resources",
        action="store_true",
        help="Create a missing vector bucket/index. No resource is deleted or overwritten.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, str | None]:
    config = dict(dotenv_values(path)) if path.is_file() else {}
    for name in (
        "AWS_PROFILE",
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "S3_VECTORS_BUCKET",
        "UPSTAGE_S3_VECTORS_INDEX",
    ):
        if name in os.environ:
            config[name] = os.environ[name]
    return config


def require(value: str | None, name: str) -> str:
    if not value or not value.strip():
        raise RuntimeError(f"Required setting is missing: {name}")
    return value.strip()


def create_aws_session(
    config: dict[str, str | None], *, profile: str | None, region: str
) -> boto3.Session:
    selected_profile = profile or config.get("AWS_PROFILE")
    if selected_profile:
        return boto3.Session(profile_name=selected_profile, region_name=region)

    access_key = config.get("AWS_ACCESS_KEY_ID")
    secret_key = config.get("AWS_SECRET_ACCESS_KEY")
    if bool(access_key) != bool(secret_key):
        raise RuntimeError("AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 함께 설정해야 합니다.")
    if access_key and secret_key:
        session_args: dict[str, Any] = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }
        if config.get("AWS_SESSION_TOKEN"):
            session_args["aws_session_token"] = config["AWS_SESSION_TOKEN"]
        return boto3.Session(**session_args)
    return boto3.Session(region_name=region)


def load_vectors(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"Local Upstage vector file is missing: {path}")

    records: list[dict[str, Any]] = []
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_number}") from exc

            key = record.get("key") if isinstance(record, dict) else None
            data = record.get("data") if isinstance(record, dict) else None
            values = data.get("float32") if isinstance(data, dict) else None
            metadata = record.get("metadata") if isinstance(record, dict) else None
            if not isinstance(key, str) or not key:
                raise RuntimeError(f"Missing vector key at {path}:{line_number}")
            if key in keys:
                raise RuntimeError(f"Duplicate vector key at {path}:{line_number}: {key}")
            if (
                not isinstance(values, list)
                or len(values) != EMBED_2_DIMENSION
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    for value in values
                )
            ):
                raise RuntimeError(f"Invalid 1024-dimensional vector at {path}:{line_number}: {key}")
            if not isinstance(metadata, dict):
                raise RuntimeError(f"Invalid vector metadata at {path}:{line_number}: {key}")
            if metadata.get("embeddingProvider") != "upstage":
                raise RuntimeError(f"Non-Upstage vector at {path}:{line_number}: {key}")

            keys.add(key)
            records.append(record)
    if not records:
        raise RuntimeError(f"Local Upstage vector file is empty: {path}")
    return records


def batched(values: Sequence[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    if not 1 <= size <= 100:
        raise ValueError("batch-size must be between 1 and 100")
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def get_vector_bucket_or_none(client: Any, bucket: str) -> dict[str, Any] | None:
    try:
        return client.get_vector_bucket(vectorBucketName=bucket).get("vectorBucket")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code", "") in {
            "NotFoundException",
            "ResourceNotFoundException",
        }:
            return None
        raise


def wait_for_index(client: Any, bucket: str, index: str) -> dict[str, Any]:
    for _ in range(30):
        value = get_index_or_none(client, bucket, index)
        if value is not None:
            return value
        time.sleep(1)
    raise RuntimeError(f"Created S3 Vector index is not readable: {bucket}/{index}")


def ensure_resources(
    client: Any, bucket: str, index: str, *, allow_create: bool
) -> tuple[dict[str, Any], bool, bool]:
    bucket_created = False
    index_created = False
    if get_vector_bucket_or_none(client, bucket) is None:
        if not allow_create:
            raise RuntimeError(
                f"S3 Vector bucket does not exist: {bucket}. Re-run with --create-resources."
            )
        client.create_vector_bucket(vectorBucketName=bucket)
        bucket_created = True

    existing_index = get_index_or_none(client, bucket, index)
    if existing_index is None:
        if not allow_create:
            raise RuntimeError(
                f"S3 Vector index does not exist: {bucket}/{index}. "
                "Re-run with --create-resources."
            )
        client.create_index(
            vectorBucketName=bucket,
            indexName=index,
            dataType="float32",
            dimension=EMBED_2_DIMENSION,
            distanceMetric="cosine",
        )
        index_created = True
        existing_index = wait_for_index(client, bucket, index)

    validate_index(existing_index, EMBED_2_DIMENSION)
    return existing_index, bucket_created, index_created


def upload_pending_vectors(
    client: Any,
    bucket: str,
    index: str,
    records: Sequence[dict[str, Any]],
    existing_keys: set[str],
    batch_size: int,
) -> int:
    pending = [record for record in records if record["key"] not in existing_keys]
    uploaded = 0
    for batch_number, batch in enumerate(batched(pending, batch_size), 1):
        client.put_vectors(
            vectorBucketName=bucket,
            indexName=index,
            vectors=batch,
        )
        uploaded += len(batch)
        print(f"batch={batch_number} uploaded={uploaded}/{len(pending)}", flush=True)
    return uploaded


def write_report(path: Path, report: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    source = args.source.resolve()
    records = load_vectors(source)
    config = load_config(args.env_file)
    region = args.region or config.get("AWS_REGION") or "ap-northeast-2"
    bucket = args.bucket or config.get("S3_VECTORS_BUCKET")
    index = args.index or config.get("UPSTAGE_S3_VECTORS_INDEX") or DEFAULT_INDEX
    selected_profile = args.profile or config.get("AWS_PROFILE")

    summary: dict[str, Any] = {
        "source_file": str(source),
        "source_sha256": sha256_file(source),
        "source_vectors": len(records),
        "dimension": EMBED_2_DIMENSION,
        "region": region,
        "bucket": bucket,
        "index": index,
        "aws_profile": selected_profile,
        "batch_size": args.batch_size,
        "create_resources": args.create_resources,
        "embedding_api_accessed": False,
        "dynamodb_accessed": False,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        return {**summary, "aws_accessed": False, "success": True}

    bucket = require(bucket, "S3_VECTORS_BUCKET")
    session = create_aws_session(config, profile=args.profile, region=region)
    client = session.client(
        "s3vectors",
        config=Config(connect_timeout=10, read_timeout=60, retries={"max_attempts": 5, "mode": "standard"}),
    )
    _index, bucket_created, index_created = ensure_resources(
        client, bucket, index, allow_create=args.create_resources
    )
    existing_keys = list_existing_keys(client, bucket, index)
    uploaded = upload_pending_vectors(
        client, bucket, index, records, existing_keys, args.batch_size
    )
    final_keys = list_existing_keys(client, bucket, index)
    requested_keys = {record["key"] for record in records}
    missing_keys = sorted(requested_keys - final_keys)
    extra_keys = sorted(final_keys - requested_keys)
    report = {
        **summary,
        "aws_accessed": True,
        "dry_run": False,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "bucket_created": bucket_created,
        "index_created": index_created,
        "preexisting_vectors": len(existing_keys),
        "uploaded_vectors": uploaded,
        "final_matching_vectors": len(requested_keys & final_keys),
        "failures": {},
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "success": not missing_keys and not extra_keys,
    }
    write_report(source.with_suffix(".upload_report.json"), report)
    return report


def main() -> None:
    args = parse_args()
    if not 1 <= args.batch_size <= 100:
        raise SystemExit("--batch-size must be between 1 and 100")
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

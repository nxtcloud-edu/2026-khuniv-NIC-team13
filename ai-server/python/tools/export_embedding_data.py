"""Export the production vector index and its DynamoDB source records.

Credentials and resource names are loaded from the project's dotenv file.
The export is read-only and writes gzip-compressed JSON Lines plus a manifest.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.config import Config
from dotenv import dotenv_values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path("python/.env"))
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def require(config: dict[str, str | None], name: str) -> str:
    value = config.get(name)
    if not value:
        raise RuntimeError(f"Required setting is missing: {name}")
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, set):
        return sorted(json_safe(item) for item in value)
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value


def write_jsonl(path: Path, records: Iterator[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    uncompressed_bytes = 0
    with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as output:
        for record in records:
            line = json.dumps(json_safe(record), ensure_ascii=False, separators=(",", ":")) + "\n"
            output.write(line)
            count += 1
            uncompressed_bytes += len(line.encode("utf-8"))

    digest = hashlib.sha256()
    with path.open("rb") as exported:
        for chunk in iter(lambda: exported.read(1024 * 1024), b""):
            digest.update(chunk)

    return {
        "path": path.name,
        "records": count,
        "uncompressed_bytes": uncompressed_bytes,
        "compressed_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def scan_table(client: Any, table_name: str) -> Iterator[dict[str, Any]]:
    deserializer = TypeDeserializer()
    exclusive_start_key: dict[str, Any] | None = None
    while True:
        request: dict[str, Any] = {"TableName": table_name, "ConsistentRead": True}
        if exclusive_start_key:
            request["ExclusiveStartKey"] = exclusive_start_key
        response = client.scan(**request)
        for raw_item in response.get("Items", []):
            yield {key: deserializer.deserialize(value) for key, value in raw_item.items()}
        exclusive_start_key = response.get("LastEvaluatedKey")
        if not exclusive_start_key:
            return


def list_vectors(client: Any, bucket: str, index: str) -> Iterator[dict[str, Any]]:
    next_token: str | None = None
    while True:
        request: dict[str, Any] = {
            "vectorBucketName": bucket,
            "indexName": index,
            "maxResults": 1000,
            "returnData": True,
            "returnMetadata": True,
        }
        if next_token:
            request["nextToken"] = next_token
        response = client.list_vectors(**request)
        yield from response.get("vectors", [])
        next_token = response.get("nextToken")
        if not next_token:
            return


def main() -> None:
    args = parse_args()
    config = dict(dotenv_values(args.env_file))
    region = config.get("AWS_REGION") or "ap-northeast-2"
    document_table = require(config, "AWS_DYNAMODB_TABLE_DOCUMENT_CONTEXT")
    coordinates_table = require(config, "AWS_DYNAMODB_TABLE_RESUME_COORDINATES")
    vector_bucket = require(config, "S3_VECTORS_BUCKET")
    vector_index = require(config, "S3_VECTORS_INDEX")

    session_args: dict[str, Any] = {
        "aws_access_key_id": require(config, "AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": require(config, "AWS_SECRET_ACCESS_KEY"),
        "region_name": region,
    }
    if config.get("AWS_SESSION_TOKEN"):
        session_args["aws_session_token"] = config["AWS_SESSION_TOKEN"]

    client_config = Config(connect_timeout=10, read_timeout=60, retries={"max_attempts": 5, "mode": "standard"})
    session = boto3.Session(**session_args)
    dynamodb = session.client("dynamodb", config=client_config)
    s3vectors = session.client("s3vectors", config=client_config)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    index_details = s3vectors.get_index(
        vectorBucketName=vector_bucket,
        indexName=vector_index,
    )["index"]

    files = {
        "document_context": write_jsonl(
            output_dir / "document_context.jsonl.gz",
            scan_table(dynamodb, document_table),
        ),
        "resume_coordinates": write_jsonl(
            output_dir / "resume_coordinates.jsonl.gz",
            scan_table(dynamodb, coordinates_table),
        ),
        "vectors": write_jsonl(
            output_dir / "vectors.jsonl.gz",
            list_vectors(s3vectors, vector_bucket, vector_index),
        ),
    }

    manifest = {
        "exported_at_utc": datetime.now(UTC).isoformat(),
        "consistency_note": (
            "DynamoDB scans used ConsistentRead, but this is not an atomic cross-service snapshot. "
            "S3 Vectors may change while pagination is in progress."
        ),
        "serialization_note": "DynamoDB Decimal values are encoded as exact JSON strings.",
        "aws_region": region,
        "sources": {
            "document_context_table": document_table,
            "resume_coordinates_table": coordinates_table,
            "vector_bucket": vector_bucket,
            "vector_index": vector_index,
            "vector_dimension": index_details.get("dimension"),
            "vector_distance_metric": index_details.get("distanceMetric"),
            "vector_data_type": index_details.get("dataType"),
        },
        "files": files,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"output_dir": str(output_dir), "files": files}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

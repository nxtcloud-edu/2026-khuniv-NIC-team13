"""Re-embed exported resume contexts with Upstage Embed 2 locally or into S3 Vectors."""
from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

import boto3
import httpx
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import dotenv_values

PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from app.vector.upstage_embedding_client import (
    DEFAULT_PASSAGE_MODEL,
    DEFAULT_QUERY_MODEL,
    DEFAULT_UPSTAGE_BASE_URL,
    UpstageEmbeddingClient,
)

PROJECT_ROOT = PYTHON_ROOT.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "private_exports" / "embedding_data_20260812"
DEFAULT_TARGET_INDEX = "pertineo-data-vector-upstage-embed2"
EMBED_2_DIMENSION = 1024
EMBED_2_PRICE_PER_MILLION_TOKENS_USD = 0.02
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
SPLITTABLE_STATUS_CODES = {400, 413, 422}


@dataclass(frozen=True)
class SourceRecord:
    key: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EmbeddedRecord:
    source: SourceRecord
    vector: list[float]


@dataclass
class BatchResult:
    records: list[EmbeddedRecord]
    prompt_tokens: int = 0
    failures: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.failures is None:
            self.failures = {}


class MinimumInterval:
    def __init__(self, seconds: float) -> None:
        self._seconds = max(0.0, seconds)
        self._last_call = 0.0

    async def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._seconds:
            await asyncio.sleep(self._seconds - elapsed)
        self._last_call = time.monotonic()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / "python" / ".env")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--target-index")
    parser.add_argument(
        "--local-output",
        type=Path,
        help="Write Upstage vectors to this local JSONL file without creating or accessing AWS clients.",
    )
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--min-interval-seconds", type=float, default=7.0)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def require(config: dict[str, str | None], name: str) -> str:
    value = config.get(name)
    if not value:
        raise RuntimeError(f"Required setting is missing: {name}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl_gzip(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"Expected a JSON object at {path}:{line_number}")
            yield value


def load_source_records(source_dir: Path) -> tuple[list[SourceRecord], dict[str, Any]]:
    manifest_path = source_dir / "manifest.json"
    documents_path = source_dir / "document_context.jsonl.gz"
    vectors_path = source_dir / "vectors.jsonl.gz"
    for required_path in (manifest_path, documents_path, vectors_path):
        if not required_path.is_file():
            raise RuntimeError(f"Export file is missing: {required_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hash = manifest.get("files", {}).get("document_context", {}).get("sha256")
    if expected_hash and sha256_file(documents_path) != expected_hash:
        raise RuntimeError("document_context export hash does not match manifest")

    vector_metadata: dict[str, dict[str, Any]] = {}
    for item in read_jsonl_gzip(vectors_path):
        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise RuntimeError("Vector export contains a missing key")
        if key in vector_metadata:
            raise RuntimeError(f"Vector export contains a duplicate key: {key}")
        metadata = item.get("metadata")
        vector_metadata[key] = dict(metadata) if isinstance(metadata, dict) else {}

    records: list[SourceRecord] = []
    seen: set[str] = set()
    for item in read_jsonl_gzip(documents_path):
        key = item.get("id")
        text = item.get("context")
        if not isinstance(key, str) or not key or not isinstance(text, str) or not text.strip():
            raise RuntimeError("Document export contains an invalid id/context record")
        if key in seen:
            raise RuntimeError(f"Document export contains a duplicate id: {key}")
        if key not in vector_metadata:
            raise RuntimeError(f"Document has no matching source vector metadata: {key}")
        seen.add(key)
        records.append(SourceRecord(key, text, vector_metadata[key]))

    extra_vectors = set(vector_metadata) - seen
    if extra_vectors:
        raise RuntimeError(f"Vector export has {len(extra_vectors)} keys without documents")
    return records, manifest


def batched(values: Sequence[SourceRecord], size: int) -> Iterator[list[SourceRecord]]:
    if not 1 <= size <= 100:
        raise ValueError("batch-size must be between 1 and 100")
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def get_index_or_none(client: Any, bucket: str, index: str) -> dict[str, Any] | None:
    try:
        return client.get_index(vectorBucketName=bucket, indexName=index)["index"]
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"NotFoundException", "ResourceNotFoundException"}:
            return None
        raise


def validate_index(index: dict[str, Any], expected_dimension: int) -> None:
    actual = (index.get("dataType"), index.get("dimension"), index.get("distanceMetric"))
    expected = ("float32", expected_dimension, "cosine")
    if actual != expected:
        raise RuntimeError(f"Target index contract mismatch: expected={expected}, actual={actual}")


def ensure_target_index(client: Any, bucket: str, index: str, dimension: int) -> bool:
    existing = get_index_or_none(client, bucket, index)
    if existing is not None:
        validate_index(existing, dimension)
        return False
    client.create_index(
        vectorBucketName=bucket,
        indexName=index,
        dataType="float32",
        dimension=dimension,
        distanceMetric="cosine",
    )
    return True


def list_existing_keys(client: Any, bucket: str, index: str) -> set[str]:
    keys: set[str] = set()
    next_token: str | None = None
    while True:
        request: dict[str, Any] = {
            "vectorBucketName": bucket,
            "indexName": index,
            "maxResults": 1000,
            "returnData": False,
            "returnMetadata": False,
        }
        if next_token:
            request["nextToken"] = next_token
        response = client.list_vectors(**request)
        for vector in response.get("vectors", []):
            keys.add(vector["key"])
        next_token = response.get("nextToken")
        if not next_token:
            return keys


def vector_payload(record: EmbeddedRecord, model: str) -> dict[str, Any]:
    metadata = dict(record.source.metadata)
    metadata.update(
        {
            "id": record.source.key,
            "embeddingProvider": "upstage",
            "embeddingModel": model,
        }
    )
    return {
        "key": record.source.key,
        "data": {"float32": record.vector},
        "metadata": metadata,
    }


def retry_after_seconds(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                pass
    return min(60.0, float(2**attempt))


async def embed_with_retry(
    client: UpstageEmbeddingClient,
    texts: list[str],
    limiter: MinimumInterval,
    max_retries: int,
):
    for attempt in range(max_retries + 1):
        await limiter.wait()
        try:
            return await client.embed_passages(texts)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRYABLE_STATUS_CODES or attempt >= max_retries:
                raise
            await asyncio.sleep(retry_after_seconds(exc.response, attempt))
        except httpx.TransportError:
            if attempt >= max_retries:
                raise
            await asyncio.sleep(retry_after_seconds(None, attempt))
    raise AssertionError("unreachable")


async def embed_resiliently(
    client: UpstageEmbeddingClient,
    records: list[SourceRecord],
    limiter: MinimumInterval,
    max_retries: int,
) -> BatchResult:
    try:
        result = await embed_with_retry(client, [record.text for record in records], limiter, max_retries)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in SPLITTABLE_STATUS_CODES and len(records) > 1:
            middle = len(records) // 2
            left = await embed_resiliently(client, records[:middle], limiter, max_retries)
            right = await embed_resiliently(client, records[middle:], limiter, max_retries)
            return BatchResult(
                left.records + right.records,
                left.prompt_tokens + right.prompt_tokens,
                {**(left.failures or {}), **(right.failures or {})},
            )
        if status in SPLITTABLE_STATUS_CODES and len(records) == 1:
            return BatchResult([], failures={records[0].key: f"HTTP {status}: input rejected"})
        raise

    embedded = [
        EmbeddedRecord(source, vector)
        for source, vector in zip(records, result.embeddings, strict=True)
    ]
    for record in embedded:
        if len(record.vector) != EMBED_2_DIMENSION:
            raise RuntimeError(
                f"Unexpected Upstage vector dimension for {record.source.key}: {len(record.vector)}"
            )
    return BatchResult(embedded, prompt_tokens=result.prompt_tokens)


def create_aws_session(config: dict[str, str | None]) -> boto3.Session:
    session_args: dict[str, Any] = {
        "aws_access_key_id": require(config, "AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": require(config, "AWS_SECRET_ACCESS_KEY"),
        "region_name": config.get("AWS_REGION") or "ap-northeast-2",
    }
    if config.get("AWS_SESSION_TOKEN"):
        session_args["aws_session_token"] = config["AWS_SESSION_TOKEN"]
    return boto3.Session(**session_args)


def write_report(path: Path, report: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_local_vector_keys(path: Path, expected_keys: set[str]) -> set[str]:
    if not path.exists():
        return set()

    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid local vector JSONL at {path}:{line_number}") from exc
            key = item.get("key") if isinstance(item, dict) else None
            values = item.get("data", {}).get("float32") if isinstance(item, dict) else None
            if not isinstance(key, str) or key not in expected_keys:
                raise RuntimeError(f"Unexpected local vector key at {path}:{line_number}: {key}")
            if key in keys:
                raise RuntimeError(f"Duplicate local vector key at {path}:{line_number}: {key}")
            if (
                not isinstance(values, list)
                or len(values) != EMBED_2_DIMENSION
                or not all(isinstance(value, (int, float)) for value in values)
            ):
                raise RuntimeError(
                    f"Invalid local vector dimension or value at {path}:{line_number}: {key}"
                )
            keys.add(key)
    return keys


def append_local_vectors(path: Path, records: Sequence[EmbeddedRecord], model: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as destination:
        for record in records:
            destination.write(
                json.dumps(vector_payload(record, model), ensure_ascii=False, separators=(",", ":"))
                + "\n"
            )
        destination.flush()


async def run_local(
    args: argparse.Namespace,
    config: dict[str, str | None],
    records: list[SourceRecord],
    manifest: dict[str, Any],
    started: float,
) -> dict[str, Any]:
    output_path = args.local_output.resolve()
    expected_keys = {record.key for record in records}
    existing_keys = load_local_vector_keys(output_path, expected_keys)
    pending = [record for record in records if record.key not in existing_keys]
    model = config.get("UPSTAGE_EMBEDDING_PASSAGE_MODEL") or DEFAULT_PASSAGE_MODEL
    dimension = int(config.get("UPSTAGE_EMBEDDING_DIMENSION") or EMBED_2_DIMENSION)
    if dimension != EMBED_2_DIMENSION:
        raise RuntimeError(f"Solar Embedding 2 requires dimension {EMBED_2_DIMENSION}, got {dimension}")

    summary: dict[str, Any] = {
        "source_records": len(records),
        "source_document_sha256": manifest.get("files", {})
        .get("document_context", {})
        .get("sha256"),
        "source_chars": sum(len(record.text) for record in records),
        "source_max_chars": max(len(record.text) for record in records),
        "storage": "local_jsonl",
        "output_file": str(output_path),
        "aws_accessed": False,
        "query_model": config.get("UPSTAGE_EMBEDDING_QUERY_MODEL") or DEFAULT_QUERY_MODEL,
        "passage_model": model,
        "dimension": dimension,
        "batch_size": args.batch_size,
        "estimated_batches": (len(pending) + args.batch_size - 1) // args.batch_size,
        "upstage_api_key_configured": bool(config.get("UPSTAGE_API_KEY")),
        "dry_run": args.dry_run,
        "preexisting_vectors": len(existing_keys),
    }
    if args.dry_run:
        return summary

    api_key = require(config, "UPSTAGE_API_KEY")
    failures: dict[str, str] = {}
    prompt_tokens = 0
    written = 0
    limiter = MinimumInterval(args.min_interval_seconds)

    async with httpx.AsyncClient(timeout=90.0) as http_client:
        embedder = UpstageEmbeddingClient(
            api_key,
            base_url=config.get("UPSTAGE_BASE_URL") or DEFAULT_UPSTAGE_BASE_URL,
            query_model=config.get("UPSTAGE_EMBEDDING_QUERY_MODEL") or DEFAULT_QUERY_MODEL,
            passage_model=model,
            http_client=http_client,
        )
        for batch_number, batch in enumerate(batched(pending, args.batch_size), 1):
            result = await embed_resiliently(embedder, batch, limiter, args.max_retries)
            prompt_tokens += result.prompt_tokens
            failures.update(result.failures or {})
            if result.records:
                append_local_vectors(output_path, result.records, model)
                written += len(result.records)
            print(
                f"batch={batch_number} written={written}/{len(pending)} "
                f"failed={len(failures)} prompt_tokens={prompt_tokens}",
                flush=True,
            )

    final_keys = load_local_vector_keys(output_path, expected_keys)
    missing_keys = sorted(expected_keys - final_keys)
    report = {
        **summary,
        "dry_run": False,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "written_vectors": written,
        "final_matching_vectors": len(expected_keys & final_keys),
        "prompt_tokens": prompt_tokens,
        "cost_usd_at_list_price": round(
            prompt_tokens / 1_000_000 * EMBED_2_PRICE_PER_MILLION_TOKENS_USD, 8
        ),
        "output_bytes": output_path.stat().st_size if output_path.exists() else 0,
        "output_sha256": sha256_file(output_path) if output_path.exists() else None,
        "failures": failures,
        "missing_keys": missing_keys,
        "success": not failures and not missing_keys,
    }
    write_report(output_path.with_suffix(".report.json"), report)
    return report


async def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    source_dir = args.source_dir.resolve()
    records, manifest = load_source_records(source_dir)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("limit must be positive")
        records = records[: args.limit]

    config = dict(dotenv_values(args.env_file))
    if args.local_output is not None:
        return await run_local(args, config, records, manifest, started)

    target_index = args.target_index or config.get("UPSTAGE_S3_VECTORS_INDEX") or DEFAULT_TARGET_INDEX
    active_index = config.get("S3_VECTORS_INDEX")
    source_hash = manifest.get("files", {}).get("document_context", {}).get("sha256")

    summary: dict[str, Any] = {
        "source_records": len(records),
        "source_document_sha256": source_hash,
        "source_chars": sum(len(record.text) for record in records),
        "source_max_chars": max(len(record.text) for record in records),
        "target_bucket": config.get("S3_VECTORS_BUCKET"),
        "target_index": target_index,
        "active_index": active_index,
        "query_model": config.get("UPSTAGE_EMBEDDING_QUERY_MODEL") or DEFAULT_QUERY_MODEL,
        "passage_model": config.get("UPSTAGE_EMBEDDING_PASSAGE_MODEL") or DEFAULT_PASSAGE_MODEL,
        "dimension": int(config.get("UPSTAGE_EMBEDDING_DIMENSION") or EMBED_2_DIMENSION),
        "batch_size": args.batch_size,
        "estimated_batches": (len(records) + args.batch_size - 1) // args.batch_size,
        "upstage_api_key_configured": bool(config.get("UPSTAGE_API_KEY")),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        return summary

    if target_index == active_index:
        raise RuntimeError(
            "Target index is the currently active S3_VECTORS_INDEX. Use a new parallel index during migration."
        )
    api_key = require(config, "UPSTAGE_API_KEY")
    bucket = require(config, "S3_VECTORS_BUCKET")
    dimension = int(config.get("UPSTAGE_EMBEDDING_DIMENSION") or EMBED_2_DIMENSION)
    if dimension != EMBED_2_DIMENSION:
        raise RuntimeError(f"Solar Embedding 2 requires dimension {EMBED_2_DIMENSION}, got {dimension}")

    aws_config = Config(connect_timeout=10, read_timeout=60, retries={"max_attempts": 5, "mode": "standard"})
    s3vectors = create_aws_session(config).client("s3vectors", config=aws_config)
    existing_index = get_index_or_none(s3vectors, bucket, target_index)
    if existing_index is not None:
        validate_index(existing_index, dimension)
        existing_keys = list_existing_keys(s3vectors, bucket, target_index)
    else:
        existing_keys = set()

    pending = [record for record in records if record.key not in existing_keys]
    failures: dict[str, str] = {}
    prompt_tokens = 0
    uploaded = 0
    index_created = False
    limiter = MinimumInterval(args.min_interval_seconds)
    model = config.get("UPSTAGE_EMBEDDING_PASSAGE_MODEL") or DEFAULT_PASSAGE_MODEL

    async with httpx.AsyncClient(timeout=90.0) as http_client:
        embedder = UpstageEmbeddingClient(
            api_key,
            base_url=config.get("UPSTAGE_BASE_URL") or DEFAULT_UPSTAGE_BASE_URL,
            query_model=config.get("UPSTAGE_EMBEDDING_QUERY_MODEL") or DEFAULT_QUERY_MODEL,
            passage_model=model,
            http_client=http_client,
        )
        for batch_number, batch in enumerate(batched(pending, args.batch_size), 1):
            result = await embed_resiliently(embedder, batch, limiter, args.max_retries)
            prompt_tokens += result.prompt_tokens
            failures.update(result.failures or {})
            if result.records:
                if existing_index is None:
                    index_created = ensure_target_index(s3vectors, bucket, target_index, dimension)
                    existing_index = get_index_or_none(s3vectors, bucket, target_index)
                    if existing_index is None:
                        raise RuntimeError("Created S3 Vector index cannot be read")
                s3vectors.put_vectors(
                    vectorBucketName=bucket,
                    indexName=target_index,
                    vectors=[vector_payload(record, model) for record in result.records],
                )
                uploaded += len(result.records)
            print(
                f"batch={batch_number} uploaded={uploaded}/{len(pending)} "
                f"failed={len(failures)} prompt_tokens={prompt_tokens}",
                flush=True,
            )

    final_keys = list_existing_keys(s3vectors, bucket, target_index) if existing_index is not None else set()
    requested_keys = {record.key for record in records}
    missing_keys = sorted(requested_keys - final_keys)
    extra_keys = sorted(final_keys - requested_keys) if args.limit is None else []
    report = {
        **summary,
        "dry_run": False,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "preexisting_vectors": len(existing_keys),
        "uploaded_vectors": uploaded,
        "final_matching_vectors": len(requested_keys & final_keys),
        "prompt_tokens": prompt_tokens,
        "cost_usd_at_list_price": round(
            prompt_tokens / 1_000_000 * EMBED_2_PRICE_PER_MILLION_TOKENS_USD, 8
        ),
        "index_created": index_created,
        "failures": failures,
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "success": not failures and not missing_keys and not extra_keys,
    }
    write_report(source_dir / "upstage_reembedding_report.json", report)
    return report


def main() -> None:
    args = parse_args()
    if not 1 <= args.batch_size <= 100:
        raise SystemExit("--batch-size must be between 1 and 100")
    result = asyncio.run(run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.dry_run and not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

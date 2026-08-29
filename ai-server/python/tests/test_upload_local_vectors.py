import json
from pathlib import Path

import pytest

from tools.upload_local_vectors import load_vectors, upload_pending_vectors


def vector(key: str, dimension: int = 1024) -> dict:
    return {
        "key": key,
        "data": {"float32": [0.1] * dimension},
        "metadata": {
            "id": key,
            "embeddingProvider": "upstage",
            "embeddingModel": "solar-embedding-2-passage",
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


class FakeS3Vectors:
    def __init__(self):
        self.requests = []

    def put_vectors(self, **kwargs):
        self.requests.append(kwargs)


def test_loads_only_valid_upstage_vectors(tmp_path: Path):
    path = tmp_path / "upstage_vectors.jsonl"
    write_jsonl(path, [vector("one"), vector("two")])

    records = load_vectors(path)

    assert [record["key"] for record in records] == ["one", "two"]


def test_rejects_wrong_vector_dimension(tmp_path: Path):
    path = tmp_path / "upstage_vectors.jsonl"
    write_jsonl(path, [vector("one", dimension=1536)])

    with pytest.raises(RuntimeError, match="1024-dimensional"):
        load_vectors(path)


def test_uploads_only_keys_missing_from_the_target_index():
    client = FakeS3Vectors()

    uploaded = upload_pending_vectors(
        client,
        "bucket",
        "index",
        [vector("one"), vector("two"), vector("three")],
        {"one"},
        batch_size=1,
    )

    assert uploaded == 2
    assert [[item["key"] for item in request["vectors"]] for request in client.requests] == [
        ["two"],
        ["three"],
    ]
    assert all(request["vectorBucketName"] == "bucket" for request in client.requests)
    assert all(request["indexName"] == "index" for request in client.requests)

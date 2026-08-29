from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from tools.reembed_upstage import (
    EmbeddedRecord,
    SourceRecord,
    append_local_vectors,
    batched,
    ensure_target_index,
    load_local_vector_keys,
    validate_index,
    vector_payload,
)


class FakeS3Vectors:
    def __init__(self, index=None):
        self.index = index
        self.created = None

    def get_index(self, **kwargs):
        if self.index is None:
            raise ClientError(
                {"Error": {"Code": "NotFoundException", "Message": "missing"}},
                "GetIndex",
            )
        return {"index": self.index}

    def create_index(self, **kwargs):
        self.created = kwargs
        self.index = {
            "dataType": kwargs["dataType"],
            "dimension": kwargs["dimension"],
            "distanceMetric": kwargs["distanceMetric"],
        }


def test_creates_a_separate_1024_dimension_cosine_index():
    client = FakeS3Vectors()

    created = ensure_target_index(client, "bucket", "upstage-index", 1024)

    assert created is True
    assert client.created == {
        "vectorBucketName": "bucket",
        "indexName": "upstage-index",
        "dataType": "float32",
        "dimension": 1024,
        "distanceMetric": "cosine",
    }


def test_reuses_only_an_index_with_the_exact_contract():
    client = FakeS3Vectors({"dataType": "float32", "dimension": 1024, "distanceMetric": "cosine"})

    assert ensure_target_index(client, "bucket", "upstage-index", 1024) is False

    with pytest.raises(RuntimeError, match="contract mismatch"):
        validate_index({"dataType": "float32", "dimension": 1536, "distanceMetric": "cosine"}, 1024)


def test_preserves_source_metadata_and_marks_embedding_model():
    source = SourceRecord("resume-1", "본문", {"id": "resume-1", "fileName": "resume.txt"})

    payload = vector_payload(EmbeddedRecord(source, [0.1, 0.2]), "solar-embedding-2-passage")

    assert payload == {
        "key": "resume-1",
        "data": {"float32": [0.1, 0.2]},
        "metadata": {
            "id": "resume-1",
            "fileName": "resume.txt",
            "embeddingProvider": "upstage",
            "embeddingModel": "solar-embedding-2-passage",
        },
    }


def test_batch_limit_matches_upstage_contract():
    records = [SourceRecord(str(index), "본문", {}) for index in range(201)]

    assert [len(batch) for batch in batched(records, 100)] == [100, 100, 1]
    with pytest.raises(ValueError, match="between 1 and 100"):
        list(batched(records, 101))


def test_writes_resumable_local_jsonl_with_s3_compatible_payload(tmp_path: Path):
    output = tmp_path / "upstage_vectors.jsonl"
    source = SourceRecord("resume-1", "본문", {"fileName": "resume.txt"})
    vector = [0.25] * 1024

    append_local_vectors(
        output,
        [EmbeddedRecord(source, vector)],
        "solar-embedding-2-passage",
    )

    assert load_local_vector_keys(output, {"resume-1"}) == {"resume-1"}
    assert '"key":"resume-1"' in output.read_text(encoding="utf-8")
    assert '"embeddingProvider":"upstage"' in output.read_text(encoding="utf-8")


def test_rejects_wrong_dimension_in_existing_local_jsonl(tmp_path: Path):
    output = tmp_path / "upstage_vectors.jsonl"
    source = SourceRecord("resume-1", "본문", {})
    append_local_vectors(
        output,
        [EmbeddedRecord(source, [0.25])],
        "solar-embedding-2-passage",
    )

    with pytest.raises(RuntimeError, match="dimension"):
        load_local_vector_keys(output, {"resume-1"})

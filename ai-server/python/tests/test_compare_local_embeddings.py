import json
from pathlib import Path

import pytest

from tools.compare_local_embeddings import (
    create_query_text,
    evaluate_results,
    load_corpus,
    normalize_text,
)


def test_query_format_matches_runtime_contract():
    assert create_query_text("회사", "개발", ["질문"], ["답변"]) == (
        "기업: 회사\n직무: 개발\n\n질문 1: 질문\n답변 1: 답변"
    )


def test_normalize_text_removes_spacing_and_punctuation():
    assert normalize_text("R&D (연구 개발)") == "rd연구개발"


def test_load_corpus_requires_expected_dimension(tmp_path: Path):
    path = tmp_path / "vectors.jsonl"
    path.write_text(
        json.dumps({"key": "one", "data": {"float32": [1.0, 2.0]}}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="dimension"):
        load_corpus(path, 3)


def test_evaluate_results_calculates_rank_metrics():
    pairs = [("회사", "개발", 2)]
    results = [["first", "second", "third"]]
    documents = {
        "first": normalize_text("타사 영업"),
        "second": normalize_text("회사 개발 합격 자소서"),
        "third": normalize_text("회사 마케팅"),
    }

    summary, details = evaluate_results(pairs, results, documents)

    assert summary["company_hits"] == 2
    assert summary["both_hits"] == 1
    assert summary["both_mrr"] == 0.5
    assert details[0]["corpus_pair_relevant"] == 1

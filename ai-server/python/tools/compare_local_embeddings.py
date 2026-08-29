"""Compare local OpenAI and Upstage vector corpora without accessing AWS."""
from __future__ import annotations

import argparse
import asyncio
import gzip
import heapq
import json
import math
import statistics
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import httpx
from dotenv import dotenv_values

PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from app.vector.upstage_embedding_client import DEFAULT_QUERY_MODEL, DEFAULT_UPSTAGE_BASE_URL

PROJECT_ROOT = PYTHON_ROOT.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "private_exports" / "embedding_data_20260812"
OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"
OPENAI_MODEL = "text-embedding-3-small"
PLACEHOLDER_VALUES = {"미입력", "없음", "n/a", "na", "unknown", "null", "-"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=PYTHON_ROOT / ".env")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument(
        "--sample-request",
        type=Path,
        default=PYTHON_ROOT / "scripts" / "sample_analyze_request.json",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--query-count", type=int, default=20)
    parser.add_argument("--latency-runs", type=int, default=3)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def require(config: dict[str, str | None], name: str) -> str:
    value = config.get(name)
    if not value:
        raise RuntimeError(f"Required setting is missing: {name}")
    return value


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "rt", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(item, dict):
                raise RuntimeError(f"Expected JSON object at {path}:{line_number}")
            yield item


def normalize_text(value: str) -> str:
    return "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", value)
        if character.isalnum()
    )


def is_placeholder(value: str) -> bool:
    return value.strip().casefold() in PLACEHOLDER_VALUES


def normalize_vector(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm == 0:
        raise RuntimeError("Zero-length embedding vector")
    return [float(value) / norm for value in values]


def load_corpus(path: Path, expected_dimension: int) -> dict[str, list[float]]:
    corpus: dict[str, list[float]] = {}
    for item in read_jsonl(path):
        key = item.get("key")
        values = item.get("data", {}).get("float32")
        if not isinstance(key, str) or not isinstance(values, list):
            raise RuntimeError(f"Invalid vector payload in {path}")
        if key in corpus:
            raise RuntimeError(f"Duplicate vector key in {path}: {key}")
        if len(values) != expected_dimension:
            raise RuntimeError(
                f"Unexpected vector dimension in {path}: key={key}, dimension={len(values)}"
            )
        corpus[key] = normalize_vector(values)
    return corpus


def load_documents(path: Path) -> dict[str, str]:
    documents: dict[str, str] = {}
    for item in read_jsonl(path):
        key = item.get("id")
        context = item.get("context")
        if not isinstance(key, str) or not isinstance(context, str):
            raise RuntimeError(f"Invalid document payload in {path}")
        documents[key] = normalize_text(context)
    return documents


def load_test_pairs(path: Path, count: int) -> list[tuple[str, str, int]]:
    frequencies: Counter[tuple[str, str]] = Counter()
    for item in read_jsonl(path):
        company = item.get("company")
        position = item.get("position")
        if isinstance(company, str) and company.strip() and isinstance(position, str) and position.strip():
            frequencies[(company.strip(), position.strip())] += 1
    return [(company, position, frequency) for (company, position), frequency in frequencies.most_common(count)]


def create_query_text(
    company: str | None,
    position: str | None,
    questions: Sequence[str],
    answers: Sequence[str],
) -> str:
    lines = [f"기업: {company}", f"직무: {position}", ""]
    for index, question in enumerate(questions):
        lines.append(f"질문 {index + 1}: {question}")
        if index < len(answers):
            lines.append(f"답변 {index + 1}: {answers[index]}")
            lines.append("")
    return "\n".join(lines).strip()


def parse_embeddings(payload: dict[str, Any], expected_count: int, expected_dimension: int) -> list[list[float]]:
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != expected_count:
        raise RuntimeError("Embedding API returned an unexpected record count")
    ordered: list[list[float] | None] = [None] * expected_count
    for item in data:
        index = item.get("index") if isinstance(item, dict) else None
        values = item.get("embedding") if isinstance(item, dict) else None
        if (
            not isinstance(index, int)
            or not 0 <= index < expected_count
            or ordered[index] is not None
            or not isinstance(values, list)
            or len(values) != expected_dimension
        ):
            raise RuntimeError("Embedding API returned an invalid vector payload")
        ordered[index] = [float(value) for value in values]
    if any(values is None for values in ordered):
        raise RuntimeError("Embedding API response has missing indexes")
    return [values for values in ordered if values is not None]


async def embed_queries(
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    model: str,
    texts: list[str],
    expected_dimension: int,
) -> tuple[list[list[float]], float, int]:
    started = time.perf_counter()
    response = await client.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"input": texts, "model": model},
    )
    latency = time.perf_counter() - started
    response.raise_for_status()
    payload = response.json()
    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens", usage.get("total_tokens", 0)) or 0)
    return parse_embeddings(payload, len(texts), expected_dimension), latency, prompt_tokens


def search_top_k(
    corpus: dict[str, list[float]], queries: Sequence[Sequence[float]], top_k: int
) -> tuple[list[list[str]], float]:
    normalized_queries = [normalize_vector(query) for query in queries]
    started = time.perf_counter()
    results: list[list[str]] = []
    for query in normalized_queries:
        best = heapq.nlargest(
            top_k,
            corpus.items(),
            key=lambda item: sum(left * right for left, right in zip(query, item[1], strict=True)),
        )
        results.append([key for key, _vector in best])
    return results, time.perf_counter() - started


def reciprocal_rank(relevances: Sequence[bool]) -> float:
    for rank, relevant in enumerate(relevances, 1):
        if relevant:
            return 1.0 / rank
    return 0.0


def ndcg(relevances: Sequence[bool], total_relevant: int) -> float | None:
    if total_relevant == 0:
        return None
    dcg = sum((1.0 / math.log2(rank + 1)) for rank, relevant in enumerate(relevances, 1) if relevant)
    ideal_count = min(len(relevances), total_relevant)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal


def mean(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def evaluate_results(
    pairs: Sequence[tuple[str, str, int]],
    results: Sequence[Sequence[str]],
    documents: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    details: list[dict[str, Any]] = []
    company_hits = position_hits = both_hits = 0
    for (company, position, frequency), keys in zip(pairs, results, strict=True):
        company_term = normalize_text(company)
        position_term = normalize_text(position)
        corpus_relevant = sum(
            company_term in document and position_term in document for document in documents.values()
        )
        company_relevance = [company_term in documents[key] for key in keys]
        position_relevance = [position_term in documents[key] for key in keys]
        both_relevance = [company and position for company, position in zip(company_relevance, position_relevance)]
        company_count = sum(company_relevance)
        position_count = sum(position_relevance)
        both_count = sum(both_relevance)
        company_hits += company_count
        position_hits += position_count
        both_hits += both_count
        details.append(
            {
                "company": company,
                "position": position,
                "source_frequency": frequency,
                "placeholder": is_placeholder(company) or is_placeholder(position),
                "corpus_pair_relevant": corpus_relevant,
                "retrieved_keys": list(keys),
                "company_hits": company_count,
                "position_hits": position_count,
                "both_hits": both_count,
                "company_rr": reciprocal_rank(company_relevance),
                "both_rr": reciprocal_rank(both_relevance),
                "both_ndcg": ndcg(both_relevance, corpus_relevant),
            }
        )

    slots = sum(len(keys) for keys in results)
    return (
        {
            "queries": len(pairs),
            "result_slots": slots,
            "company_hits": company_hits,
            "company_precision_proxy": company_hits / slots if slots else 0.0,
            "position_hits": position_hits,
            "position_precision_proxy": position_hits / slots if slots else 0.0,
            "both_hits": both_hits,
            "both_precision_proxy": both_hits / slots if slots else 0.0,
            "company_hit_rate": mean(1.0 if item["company_hits"] else 0.0 for item in details),
            "both_hit_rate": mean(1.0 if item["both_hits"] else 0.0 for item in details),
            "company_mrr": mean(item["company_rr"] for item in details),
            "both_mrr": mean(item["both_rr"] for item in details),
            "both_ndcg": mean(item["both_ndcg"] for item in details),
            "queries_with_pair_labels": sum(item["corpus_pair_relevant"] > 0 for item in details),
        },
        details,
    )


def filter_evaluation(
    details: Sequence[dict[str, Any]], include_placeholders: bool
) -> dict[str, Any]:
    filtered = [item for item in details if include_placeholders or not item["placeholder"]]
    slots = len(filtered) * 3
    return {
        "queries": len(filtered),
        "result_slots": slots,
        "company_hits": sum(item["company_hits"] for item in filtered),
        "company_precision_proxy": sum(item["company_hits"] for item in filtered) / slots if slots else 0.0,
        "position_hits": sum(item["position_hits"] for item in filtered),
        "position_precision_proxy": sum(item["position_hits"] for item in filtered) / slots if slots else 0.0,
        "both_hits": sum(item["both_hits"] for item in filtered),
        "both_precision_proxy": sum(item["both_hits"] for item in filtered) / slots if slots else 0.0,
        "company_hit_rate": mean(1.0 if item["company_hits"] else 0.0 for item in filtered),
        "both_hit_rate": mean(1.0 if item["both_hits"] else 0.0 for item in filtered),
        "company_mrr": mean(item["company_rr"] for item in filtered),
        "both_mrr": mean(item["both_rr"] for item in filtered),
        "both_ndcg": mean(item["both_ndcg"] for item in filtered),
        "queries_with_pair_labels": sum(item["corpus_pair_relevant"] > 0 for item in filtered),
    }


def paired_outcomes(openai: Sequence[dict[str, Any]], upstage: Sequence[dict[str, Any]], field: str) -> dict[str, int]:
    outcomes = {"upstage_wins": 0, "ties": 0, "openai_wins": 0}
    for left, right in zip(openai, upstage, strict=True):
        if right[field] > left[field]:
            outcomes["upstage_wins"] += 1
        elif right[field] < left[field]:
            outcomes["openai_wins"] += 1
        else:
            outcomes["ties"] += 1
    return outcomes


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.top_k != 3:
        raise ValueError("This report currently fixes top-k at 3 for comparable metrics")
    if args.query_count < 1 or args.latency_runs < 1:
        raise ValueError("query-count and latency-runs must be positive")

    source_dir = args.source_dir.resolve()
    documents = load_documents(source_dir / "document_context.jsonl.gz")
    openai_corpus = load_corpus(source_dir / "vectors.jsonl.gz", 1536)
    upstage_corpus = load_corpus(source_dir / "upstage_vectors.jsonl", 1024)
    if set(documents) != set(openai_corpus) or set(documents) != set(upstage_corpus):
        raise RuntimeError("Document, OpenAI, and Upstage key sets do not match")

    pairs = load_test_pairs(source_dir / "resume_coordinates.jsonl.gz", args.query_count)
    sample = json.loads(args.sample_request.read_text(encoding="utf-8"))
    canonical = (
        str(sample.get("company") or ""),
        str(sample.get("jobPosition") or ""),
        1,
    )
    pair_texts = [create_query_text(company, position, [], []) for company, position, _ in pairs]
    canonical_text = create_query_text(
        canonical[0],
        canonical[1],
        sample.get("questionList") or [],
        sample.get("answerList") or [],
    )
    texts = [canonical_text, *pair_texts]

    config = dict(dotenv_values(args.env_file))
    openai_key = require(config, "OPENAI_API_KEY")
    upstage_key = require(config, "UPSTAGE_API_KEY")
    upstage_url = f"{(config.get('UPSTAGE_BASE_URL') or DEFAULT_UPSTAGE_BASE_URL).rstrip('/')}/embeddings"
    upstage_model = config.get("UPSTAGE_EMBEDDING_QUERY_MODEL") or DEFAULT_QUERY_MODEL

    provider_vectors: dict[str, list[list[float]]] = {}
    provider_latency: dict[str, list[float]] = {"openai": [], "upstage": []}
    provider_tokens: dict[str, list[int]] = {"openai": [], "upstage": []}
    async with httpx.AsyncClient(timeout=90.0) as client:
        for run_number in range(args.latency_runs):
            order = ("openai", "upstage") if run_number % 2 == 0 else ("upstage", "openai")
            for provider in order:
                if provider == "openai":
                    vectors, latency, tokens = await embed_queries(
                        client,
                        OPENAI_EMBEDDING_URL,
                        openai_key,
                        OPENAI_MODEL,
                        texts,
                        1536,
                    )
                else:
                    vectors, latency, tokens = await embed_queries(
                        client,
                        upstage_url,
                        upstage_key,
                        upstage_model,
                        texts,
                        1024,
                    )
                provider_vectors.setdefault(provider, vectors)
                provider_latency[provider].append(latency)
                provider_tokens[provider].append(tokens)
                print(
                    f"embedding_run={run_number + 1}/{args.latency_runs} "
                    f"provider={provider} latency_seconds={latency:.3f} tokens={tokens}",
                    flush=True,
                )

    openai_results, openai_search_latency = search_top_k(
        openai_corpus, provider_vectors["openai"], args.top_k
    )
    upstage_results, upstage_search_latency = search_top_k(
        upstage_corpus, provider_vectors["upstage"], args.top_k
    )

    openai_canonical, openai_details = evaluate_results([canonical], [openai_results[0]], documents)
    upstage_canonical, upstage_details = evaluate_results([canonical], [upstage_results[0]], documents)
    openai_legacy, openai_pair_details = evaluate_results(pairs, openai_results[1:], documents)
    upstage_legacy, upstage_pair_details = evaluate_results(pairs, upstage_results[1:], documents)
    clean_openai = filter_evaluation(openai_pair_details, include_placeholders=False)
    clean_upstage = filter_evaluation(upstage_pair_details, include_placeholders=False)

    overlap_slots = sum(
        len(set(openai_keys) & set(upstage_keys))
        for openai_keys, upstage_keys in zip(openai_results[1:], upstage_results[1:], strict=True)
    )
    report = {
        "method": {
            "storage": "local_exact_cosine_search",
            "aws_accessed": False,
            "openai_model": OPENAI_MODEL,
            "openai_dimension": 1536,
            "upstage_model": upstage_model,
            "upstage_dimension": 1024,
            "corpus_records": len(documents),
            "canonical_query": str(args.sample_request.resolve()),
            "aggregate_queries": f"{args.query_count} most frequent non-empty company/position pairs",
            "top_k": args.top_k,
            "latency_runs": args.latency_runs,
            "quality_note": (
                "Company/position occurrence in source text is a retrieval proxy, not a human relevance label."
            ),
        },
        "latency": {
            provider: {
                "embedding_api_seconds": [round(value, 6) for value in provider_latency[provider]],
                "embedding_api_mean_seconds": round(statistics.mean(provider_latency[provider]), 6),
                "embedding_api_median_seconds": round(statistics.median(provider_latency[provider]), 6),
                "prompt_tokens_per_run": provider_tokens[provider],
                "local_search_seconds": round(
                    openai_search_latency if provider == "openai" else upstage_search_latency, 6
                ),
            }
            for provider in ("openai", "upstage")
        },
        "canonical_query": {
            "openai": {**openai_canonical, "details": openai_details[0]},
            "upstage": {**upstage_canonical, "details": upstage_details[0]},
            "top3_overlap": len(set(openai_results[0]) & set(upstage_results[0])),
        },
        "legacy_top_20": {
            "openai": openai_legacy,
            "upstage": upstage_legacy,
            "top3_overlap_slots": overlap_slots,
            "top3_overlap_rate": overlap_slots / (len(pairs) * args.top_k),
            "paired_company_hits": paired_outcomes(
                openai_pair_details, upstage_pair_details, "company_hits"
            ),
            "paired_both_hits": paired_outcomes(openai_pair_details, upstage_pair_details, "both_hits"),
        },
        "clean_without_placeholders": {
            "openai": clean_openai,
            "upstage": clean_upstage,
        },
        "queries": [
            {
                "company": company,
                "position": position,
                "source_frequency": frequency,
                "placeholder": is_placeholder(company) or is_placeholder(position),
                "openai": openai_detail,
                "upstage": upstage_detail,
                "top3_overlap": len(
                    set(openai_detail["retrieved_keys"]) & set(upstage_detail["retrieved_keys"])
                ),
            }
            for (company, position, frequency), openai_detail, upstage_detail in zip(
                pairs, openai_pair_details, upstage_pair_details, strict=True
            )
        ],
    }
    return report


def main() -> None:
    args = parse_args()
    report = asyncio.run(run(args))
    output = args.output or args.source_dir / "embedding_comparison_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"output": str(output.resolve()), **report["method"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

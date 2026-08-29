#!/usr/bin/env python3
"""Benchmark Reviser repeatedly from a saved full-workflow result."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import sys
import time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mappers.analyze_request_mapper import to_agent_state
from app.schemas.analyze_request import AnalyzeRequestDto
from app.service.openai_chat_client import create_openai_client
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.evaluate_models import ResumeEvaluation
from app.workflow.nodes.reviser_models import SingleRevisedAnswer
from app.workflow.nodes.reviser_node import (
    ReviserNode,
    _MAX_NEAR_COPY_SIMILARITY,
    _MAX_TARGETED_ATTEMPTS,
    _SINGLE_OPTIONS,
)


class RecordingSink(WorkflowEventSink):
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def send(self, event: Any) -> None:
        self.events.append(event)


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def event_count(events: list[Any], event_type: str) -> int:
    return sum(event.type == event_type for event in events)


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * ratio
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def load_state(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    request = AnalyzeRequestDto.model_validate(payload["request"])
    state = to_agent_state(request)
    state.evaluation_result = ResumeEvaluation.model_validate(payload["evaluate_result"])
    return state


async def run_once(path: Path, run_number: int) -> dict[str, Any]:
    state = load_state(path)
    original_answers = list(state.answer_list or [])
    sink = RecordingSink()
    client = create_openai_client()
    node = ReviserNode(client=client)
    started = time.perf_counter()
    error: str | None = None
    try:
        await node.execute(sink, state)
    except Exception as exc:  # noqa: BLE001 - benchmark must retain each failure
        error = f"{type(exc).__name__}: {exc}"
    finally:
        elapsed = time.perf_counter() - started
        await client.close()

    revised = state.revised_result
    result: dict[str, Any] = {
        "run": run_number,
        "success": error is None and revised is not None,
        "error": error,
        "elapsed_seconds": round(elapsed, 3),
        "max_output_tokens_per_call": _SINGLE_OPTIONS.max_tokens,
        "max_attempts_per_question": _MAX_TARGETED_ATTEMPTS,
        "targeted_repairs": event_count(sink.events, "revise_targeted_repair"),
        "safe_fallbacks": event_count(sink.events, "revise_safe_fallback"),
        "explanation_fallbacks": event_count(sink.events, "revise_explanation_fallback"),
        "numeric_qualifier_restores": event_count(
            sink.events, "revise_numeric_qualifier_restore"
        ),
    }
    result["candidate_calls"] = len(original_answers) + result["targeted_repairs"]
    result["seconds_per_candidate_call"] = round(
        elapsed / result["candidate_calls"], 3
    )
    if revised is None:
        return result

    candidates = [
        SingleRevisedAnswer(
            best_reply=revised.best_reply[index],
            reply_reason=revised.reply_reason[index],
            expectation=revised.expectation[index],
        )
        for index in range(len(revised.best_reply))
    ]
    result.update(
        {
            "answer_count": len(revised.best_reply),
            "answer_lengths": [len(value) for value in revised.best_reply],
            "answer_fingerprints": [fingerprint(value) for value in revised.best_reply],
            "preserved_original_indices": [
                index + 1
                for index, value in enumerate(revised.best_reply)
                if index < len(original_answers) and value.strip() == original_answers[index].strip()
            ],
            "answer_similarities": [
                round(
                    SequenceMatcher(
                        None,
                        " ".join(original_answers[index].split()),
                        " ".join(value.split()),
                    ).ratio(),
                    4,
                )
                for index, value in enumerate(revised.best_reply)
            ],
            "validation_problems": [
                node._single_problems(candidate, state, index)
                for index, candidate in enumerate(candidates)
            ],
            "best_reply": revised.best_reply,
            "reply_reason": revised.reply_reason,
            "expectation": revised.expectation,
        }
    )
    return result


def summarize(results: list[dict[str, Any]], source: Path) -> dict[str, Any]:
    successes = [result for result in results if result["success"]]
    elapsed_values = [result["elapsed_seconds"] for result in results]
    candidate_calls = [result["candidate_calls"] for result in results]
    return {
        "source": str(source.resolve()),
        "runs": len(results),
        "successes": len(successes),
        "failures": len(results) - len(successes),
        "max_output_tokens_per_call": _SINGLE_OPTIONS.max_tokens,
        "max_attempts_per_question": _MAX_TARGETED_ATTEMPTS,
        "elapsed_seconds": {
            "per_run": elapsed_values,
            "mean": round(statistics.mean(elapsed_values), 3),
            "median": round(statistics.median(elapsed_values), 3),
            "p95": round(percentile(elapsed_values, 0.95), 3),
            "min": min(elapsed_values),
            "max": max(elapsed_values),
        },
        "candidate_calls": {
            "per_run": candidate_calls,
            "total": sum(candidate_calls),
            "mean": round(statistics.mean(candidate_calls), 3),
            "max": max(candidate_calls),
            "seconds_per_call_mean": round(
                statistics.mean(
                    result["seconds_per_candidate_call"] for result in results
                ),
                3,
            ),
        },
        "event_totals": {
            name: sum(result[name] for result in results)
            for name in (
                "targeted_repairs",
                "safe_fallbacks",
                "explanation_fallbacks",
                "numeric_qualifier_restores",
            )
        },
        "runs_with_safe_fallback": [
            result["run"] for result in results if result["safe_fallbacks"]
        ],
        "runs_with_validation_problems": [
            result["run"]
            for result in successes
            if any(result.get("validation_problems") or [])
        ],
        "preserved_original_counts": dict(
            Counter(
                index
                for result in successes
                for index in result.get("preserved_original_indices", [])
            )
        ),
        "meaningfully_revised_answers": sum(
            similarity <= _MAX_NEAR_COPY_SIMILARITY
            for result in successes
            for similarity in result.get("answer_similarities", [])
        ),
        "total_answers": sum(
            len(result.get("answer_similarities", [])) for result in successes
        ),
        "answer_fingerprint_counts": {
            str(index + 1): dict(
                Counter(result["answer_fingerprints"][index] for result in successes)
            )
            for index in range(3)
        }
        if successes
        else {},
    }


async def main(source: Path, runs: int, output: Path) -> None:
    results: list[dict[str, Any]] = []
    for run_number in range(1, runs + 1):
        result = await run_once(source, run_number)
        results.append(result)
        concise = {
            key: value
            for key, value in result.items()
            if key not in {"best_reply", "reply_reason", "expectation"}
        }
        print("RUN_RESULT " + json.dumps(concise, ensure_ascii=False), flush=True)

    report = {"summary": summarize(results, source), "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("BENCHMARK_SUMMARY " + json.dumps(report["summary"], ensure_ascii=False))
    print(f"Saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("scripts/upstage_full_pipeline_result.json"),
    )
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be positive")
    asyncio.run(main(args.source, args.runs, args.output))

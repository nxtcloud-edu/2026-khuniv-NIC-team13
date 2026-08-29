#!/usr/bin/env python3
"""Benchmark the real workflow with an AnalyzeRequest JSON file."""
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
from itertools import combinations
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.container import Container
from app.mappers.analyze_request_mapper import to_agent_state
from app.schemas.analyze_request import AnalyzeRequestDto
from app.workflow.engine import StateGraphEngine
from app.workflow.event import WorkflowEventSink
from app.workflow.state import AgentState


FALLBACK_EVENT_TYPES = {
    "schemer_recheck",
    "workflow_retrying",
    "evaluate_strategy_fallback",
    "revise_targeted_repair",
    "revise_safe_fallback",
    "pass_score_none",
}


class RecordingSink(WorkflowEventSink):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def send(self, event: Any) -> None:
        self.events.append(
            {
                "time": time.perf_counter(),
                "type": event.type,
                "status": event.status.value,
                "data": event.data,
            }
        )


class TimedNode:
    def __init__(
        self,
        name: str,
        delegate: Any,
        attempts: dict[str, list[dict[str, Any]]],
    ) -> None:
        self._name = name
        self._delegate = delegate
        self._attempts = attempts

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        started = time.perf_counter()
        attempt: dict[str, Any] = {"success": False}
        try:
            result = await self._delegate.execute(events, state)
            attempt["success"] = True
            return result
        except Exception as exc:
            attempt["error_type"] = type(exc).__name__
            attempt["error_message"] = str(exc)[:500]
            raise
        finally:
            attempt["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            self._attempts.setdefault(self._name, []).append(attempt)

    def decide_next_node(self, state: AgentState) -> str:
        return self._delegate.decide_next_node(state)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def pairwise_similarity(values: list[str]) -> dict[str, float | int]:
    if len(values) < 2:
        return {"pairs": 0, "mean": 1.0, "min": 1.0, "max": 1.0}
    ratios = [
        SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()
        for left, right in combinations(values, 2)
    ]
    return {
        "pairs": len(ratios),
        "mean": round(statistics.mean(ratios), 4),
        "min": round(min(ratios), 4),
        "max": round(max(ratios), 4),
    }


def score_stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": round(statistics.mean(values), 3),
        "stddev": round(statistics.pstdev(values), 3),
        "min": min(values),
        "max": max(values),
        "range": round(max(values) - min(values), 3),
    }


def categorical(values: list[Any]) -> dict[str, Any]:
    counts = Counter(values)
    mode, count = counts.most_common(1)[0]
    return {
        "mode": mode,
        "agreement": round(count / len(values), 4),
        "counts": dict(counts),
    }


def event_count(events: list[dict[str, Any]], event_type: str) -> int:
    return sum(event["type"] == event_type for event in events)


def build_engine(container: Container, attempts: dict[str, list[dict[str, Any]]]) -> StateGraphEngine:
    return StateGraphEngine(
        TimedNode("SCHEMER", container.schemer_node, attempts),
        TimedNode("WEBSEARCH", container.web_search_node, attempts),
        TimedNode("EVALUATE", container.evaluate_node, attempts),
        TimedNode("REVISE", container.reviser_node, attempts),
        TimedNode("DATA", container.data_node, attempts),
        container.tracer,
    )


async def run_once(
    container: Container,
    request: AnalyzeRequestDto,
    run_number: int,
) -> dict[str, Any]:
    state = to_agent_state(request)
    sink = RecordingSink()
    attempts: dict[str, list[dict[str, Any]]] = {}
    engine = build_engine(container, attempts)

    started = time.perf_counter()
    await engine.run_workflow(sink, state)
    elapsed = time.perf_counter() - started

    completed = event_count(sink.events, "workflow_completed") > 0
    workflow_errors = [
        str(event["data"])
        for event in sink.events
        if event["type"] == "workflow_error"
    ]
    failed_attempts = [
        {"node": node, "attempt": index + 1, **attempt}
        for node, node_attempts in attempts.items()
        for index, attempt in enumerate(node_attempts)
        if not attempt["success"]
    ]
    result: dict[str, Any] = {
        "run": run_number,
        "success": completed,
        "elapsed_seconds": round(elapsed, 3),
        "node_seconds": {
            node: round(sum(attempt["elapsed_seconds"] for attempt in node_attempts), 3)
            for node, node_attempts in attempts.items()
        },
        "node_attempts": {node: len(node_attempts) for node, node_attempts in attempts.items()},
        "failed_attempts": failed_attempts,
        "failure_node": failed_attempts[-1]["node"] if not completed and failed_attempts else None,
        "workflow_errors": workflow_errors,
        "fallbacks": [
            {"type": event["type"], "data": str(event["data"])[:500]}
            for event in sink.events
            if event["type"] in FALLBACK_EVENT_TYPES
        ],
        "fallback_counts": {
            event_type: event_count(sink.events, event_type)
            for event_type in sorted(FALLBACK_EVENT_TYPES)
            if event_count(sink.events, event_type)
        },
        "web_search_cache_hit": event_count(sink.events, "web_search_cache_hit") > 0,
        "event_count": len(sink.events),
    }

    if state.evaluation_result is not None:
        evaluation = state.evaluation_result
        result["scores"] = {
            "x": evaluation.x.score,
            "y": evaluation.y.score,
            "z": evaluation.z.score,
        }
        result["level"] = evaluation.level
        result["overall_fingerprint"] = fingerprint(evaluation.overall)
        result["overall"] = evaluation.overall
    else:
        result["scores"] = None
        result["level"] = None

    if state.revised_result is not None:
        result["revised_fingerprints"] = [
            fingerprint(value) for value in state.revised_result.best_reply
        ]
        result["revised_answers"] = state.revised_result.best_reply
    else:
        result["revised_fingerprints"] = None

    return result


def summarize(results: list[dict[str, Any]], request_path: Path) -> dict[str, Any]:
    successes = [result for result in results if result["success"]]
    failures = [result for result in results if not result["success"]]
    summary: dict[str, Any] = {
        "request_path": str(request_path),
        "request_sha256": sha256_file(request_path),
        "runs": len(results),
        "successes": len(successes),
        "failures": len(failures),
        "failure_runs": [result["run"] for result in failures],
        "failure_nodes": dict(
            Counter(result["failure_node"] or "unknown" for result in failures)
        ),
        "elapsed_seconds": {
            "per_run": [result["elapsed_seconds"] for result in results],
            "mean": round(statistics.mean(result["elapsed_seconds"] for result in results), 3),
            "median": round(statistics.median(result["elapsed_seconds"] for result in results), 3),
            "min": min(result["elapsed_seconds"] for result in results),
            "max": max(result["elapsed_seconds"] for result in results),
            "total": round(sum(result["elapsed_seconds"] for result in results), 3),
        },
        "fallback_counts": dict(
            Counter(
                fallback["type"]
                for result in results
                for fallback in result["fallbacks"]
            )
        ),
        "runs_with_fallback": [result["run"] for result in results if result["fallbacks"]],
        "cache_hit_runs": [result["run"] for result in results if result["web_search_cache_hit"]],
    }
    all_nodes = ["SCHEMER", "WEBSEARCH", "DATA", "EVALUATE", "REVISE"]
    summary["node_seconds"] = {
        node: {
            "per_run": [result["node_seconds"].get(node) for result in results],
            "mean": round(
                statistics.mean(
                    result["node_seconds"].get(node, 0.0) for result in results
                ),
                3,
            ),
        }
        for node in all_nodes
    }

    scored = [result for result in results if result["scores"] is not None]
    if scored:
        summary["scores"] = {
            axis: score_stats([result["scores"][axis] for result in scored])
            for axis in ["x", "y", "z"]
        }
        summary["score_rows"] = [
            {"run": result["run"], **result["scores"]} for result in scored
        ]
        summary["level_consistency"] = categorical(
            [result["level"] for result in scored]
        )
        summary["overall_similarity"] = pairwise_similarity(
            [result["overall"] for result in scored]
        )
        summary["overall_exact"] = categorical(
            [result["overall_fingerprint"] for result in scored]
        )

    revised = [result for result in results if result["revised_fingerprints"] is not None]
    if revised:
        answer_count = len(revised[0]["revised_answers"])
        summary["revised_similarity"] = {
            str(index + 1): pairwise_similarity(
                [result["revised_answers"][index] for result in revised]
            )
            for index in range(answer_count)
        }
        summary["revised_exact"] = {
            str(index + 1): categorical(
                [result["revised_fingerprints"][index] for result in revised]
            )
            for index in range(answer_count)
        }
    return summary


async def main(request_path: Path, runs: int) -> None:
    raw_request = json.loads(request_path.read_text(encoding="utf-8"))
    request = AnalyzeRequestDto.model_validate(raw_request)
    container = Container()
    results: list[dict[str, Any]] = []

    print(
        "BENCHMARK_INPUT "
        + json.dumps(
            {
                "request_path": str(request_path),
                "request_sha256": sha256_file(request_path),
                "question_count": len(request.question_list),
                "answer_count": len(request.answer_list),
                "question_chars": sum(map(len, request.question_list)),
                "answer_chars": sum(map(len, request.answer_list)),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    for run_number in range(1, runs + 1):
        result = await run_once(container, request, run_number)
        results.append(result)
        concise = {
            key: value
            for key, value in result.items()
            if key not in {"overall", "revised_answers"}
        }
        print("RUN_RESULT " + json.dumps(concise, ensure_ascii=False), flush=True)

    print(
        "BENCHMARK_SUMMARY "
        + json.dumps(summarize(results, request_path), ensure_ascii=False),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--request",
        type=Path,
        default=Path("scripts/sample_analyze_request.json"),
    )
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be positive")
    asyncio.run(main(args.request, args.runs))

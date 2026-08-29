#!/usr/bin/env python3
"""Run the active OpenAI workflow repeatedly with fully synthetic, fixed context.

The filename is retained so historical commands and reports remain reproducible.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import statistics
import sys
import time
from collections import Counter
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cache.web_search_cache import LocalWebSearchCache
from app.repository.models import PreviousAnalysisResult
from app.service.openai_chat_client import create_openai_client
from app.vector.vector_context_service import VectorEvaluationContext
from app.workflow.engine import StateGraphEngine
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.data_node import DataNode
from app.workflow.nodes.evaluate_node import EvaluateNode
from app.workflow.nodes.reviser_models import SingleRevisedAnswer
from app.workflow.nodes.reviser_node import ReviserNode, _SINGLE_OPTIONS
from app.workflow.nodes.schemer.client import OpenAiSchemerClient
from app.workflow.nodes.schemer_node import SchemerNode
from app.workflow.nodes.websearch_node import WebSearchNode
from app.workflow.state import AgentState

logger = logging.getLogger(__name__)


class RecordingSink(WorkflowEventSink):
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def send(self, event: Any) -> None:
        self.events.append(event)


class FixedResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "answer": (
                "테스트전자는 사용자 중심 개발과 협업을 중시하는 가상의 검증용 회사입니다."
            ),
            "results": [
                {
                    "url": "https://example.invalid/synthetic",
                    "content": (
                        "소프트웨어 개발자는 요구사항 분석과 기록 기반 문제 해결, "
                        "협업 역량이 필요합니다."
                    ),
                }
            ],
        }


class FixedHttpClient:
    async def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> FixedResponse:
        return FixedResponse()


class FixedRepository:
    async def get_score_by_company_and_track(
        self, company: str, track: str
    ) -> PreviousAnalysisResult:
        return PreviousAnalysisResult(
            company="테스트전자",
            position="소프트웨어 개발",
            track="engineering",
            x=4.0,
            y=3.9,
            z=4.1,
            overall=4.0,
        )

    async def get_score_by_track(self, track: str) -> None:
        return None


class FixedVectorContextService:
    async def build_evaluation_context(self, request: Any) -> VectorEvaluationContext:
        return VectorEvaluationContext(
            selected_keys=["synthetic-reference"],
            documents=[
                "합성 합격자 문서는 질문에 대한 결론, 본인의 행동, 배운 점을 명확히 연결합니다."
            ],
            status="synthetic",
        )


class NoOpTracer:
    async def start_trace(self, *args: Any) -> str:
        return "synthetic-root"

    async def start_span(self, *args: Any) -> str:
        return "synthetic-span"

    async def end_trace(self, *args: Any) -> None:
        return None

    async def error_trace(self, *args: Any) -> None:
        return None


class TimedNode:
    def __init__(self, name: str, delegate: Any, durations: dict[str, list[float]]) -> None:
        self._name = name
        self._delegate = delegate
        self._durations = durations

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        started = time.perf_counter()
        try:
            return await self._delegate.execute(events, state)
        finally:
            self._durations.setdefault(self._name, []).append(time.perf_counter() - started)

    def decide_next_node(self, state: AgentState) -> str:
        return self._delegate.decide_next_node(state)


def synthetic_state(run_number: int) -> AgentState:
    return AgentState(
        user_id=f"synthetic-benchmark-{run_number}",
        question_list=[
            "테스트전자에 지원한 이유와 입사 후 기여 방안을 설명해 주세요.",
            "개발 과정에서 문제를 발견하고 해결한 경험을 설명해 주세요.",
        ],
        answer_list=[
            "학습용 프로젝트에서 사용자 의견을 정리하고 기능 우선순위를 조정한 경험이 "
            "있습니다. 팀원들과 매주 요구사항을 검토하며 꼭 필요한 기능부터 구현했고, "
            "사용자가 이해하기 쉬운 흐름을 만드는 일이 제품의 신뢰와 연결된다는 점을 "
            "배웠습니다. 이 경험을 바탕으로 테스트전자에서도 사용자의 목소리를 개발 "
            "과정에 반영하고 싶습니다.",
            "동아리 예약 서비스를 만들 때 요청이 몰리면 화면 응답이 늦어지는 문제를 "
            "발견했습니다. 로그를 살펴 반복되는 조회가 원인임을 확인했고, 조회 결과를 "
            "재사용하도록 로직을 정리했습니다. 그 결과 기존에 관찰되던 850밀리초 수준의 "
            "응답 지연이 줄어드는 것을 확인했습니다. 이 과정에서 추측보다 측정과 기록을 "
            "먼저 확인하는 습관을 배웠습니다.",
        ],
        education="가상대학교 재학",
        major="소프트웨어 전공",
        company="테스트전자",
        job_position="소프트웨어 개발",
        job_field="개발",
        division="가상제품팀",
    )


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[가-힣A-Za-z0-9]+", value.lower()))


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


def categorical_consistency(values: list[Any]) -> dict[str, Any]:
    counts = Counter(values)
    mode, count = counts.most_common(1)[0]
    return {
        "mode": mode,
        "agreement": round(count / len(values), 4),
        "counts": dict(counts),
    }


def score_consistency(values: list[float]) -> dict[str, float]:
    return {
        "mean": round(statistics.mean(values), 3),
        "stddev": round(statistics.pstdev(values), 3),
        "min": min(values),
        "max": max(values),
        "range": round(max(values) - min(values), 3),
    }


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def event_data(events: list[Any], event_type: str) -> list[Any]:
    return [event.data for event in events if event.type == event_type]


async def run_once(run_number: int) -> dict[str, Any]:
    client = create_openai_client()
    durations: dict[str, list[float]] = {}
    state = synthetic_state(run_number)
    sink = RecordingSink()
    reviser = ReviserNode(client=client)
    nodes = {
        "schemer": SchemerNode(OpenAiSchemerClient(client=client)),
        "websearch": WebSearchNode(
            LocalWebSearchCache(), client=client, http_client=FixedHttpClient()
        ),
        "data": DataNode(FixedRepository()),
        "evaluate": EvaluateNode(FixedVectorContextService(), client=client),
        "revise": reviser,
    }
    engine = StateGraphEngine(
        TimedNode("schemer", nodes["schemer"], durations),
        TimedNode("websearch", nodes["websearch"], durations),
        TimedNode("evaluate", nodes["evaluate"], durations),
        TimedNode("revise", nodes["revise"], durations),
        TimedNode("data", nodes["data"], durations),
        NoOpTracer(),
    )
    started = time.perf_counter()
    try:
        await engine.run_workflow(sink, state)
    finally:
        elapsed = time.perf_counter() - started
        await client.close()

    completed = any(event.type == "workflow_completed" for event in sink.events)
    errors = event_data(sink.events, "workflow_error")
    recoveries = [
        {"type": event.type, "data": str(event.data)}
        for event in sink.events
        if event.type
        in {
            "schemer_recheck",
            "workflow_retrying",
            "evaluate_strategy_fallback",
            "revise_targeted_repair",
            "revise_numeric_qualifier_restore",
            "revise_explanation_fallback",
            "revise_safe_fallback",
        }
    ]
    plans = event_data(sink.events, "web_search_plan_generated")
    queries: list[str] = []
    if plans:
        queries = [plan.query for plan in plans[-1]]

    result: dict[str, Any] = {
        "run": run_number,
        "success": completed,
        "elapsed_seconds": round(elapsed, 3),
        "stage_seconds": {
            name: round(sum(attempts), 3) for name, attempts in durations.items()
        },
        "stage_attempts": {name: len(attempts) for name, attempts in durations.items()},
        "errors": [str(error) for error in errors],
        "recoveries": recoveries,
        "track": state.track,
        "queries": queries,
    }
    if not completed or state.evaluation_result is None or state.revised_result is None:
        return result

    evaluation = state.evaluation_result
    revised = state.revised_result
    validation_problems = [
        reviser._single_problems(
            SingleRevisedAnswer(
                best_reply=revised.best_reply[index],
                reply_reason=revised.reply_reason[index],
                expectation=revised.expectation[index],
            ),
            state,
            index,
        )
        for index in range(len(revised.best_reply))
    ]
    result.update(
        {
            "scores": {"x": evaluation.x.score, "y": evaluation.y.score, "z": evaluation.z.score},
            "compare_scores": {
                "x": evaluation.x.compare_score,
                "y": evaluation.y.compare_score,
                "z": evaluation.z.compare_score,
            },
            "level": evaluation.level,
            "strategy_count": len(evaluation.improve_strategy),
            "overall": evaluation.overall,
            "overall_fingerprint": fingerprint(evaluation.overall),
            "revised_answers": revised.best_reply,
            "revised_fingerprints": [fingerprint(value) for value in revised.best_reply],
            "revised_lengths": [len(value) for value in revised.best_reply],
            "revision_validation_problems": validation_problems,
            "cross_question_leak": {
                "question_1_contains_log": "로그" in revised.best_reply[0],
                "question_2_contains_user_feedback": "사용자 의견" in revised.best_reply[1],
            },
        }
    )
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [result for result in results if result["success"]]
    failures = [result for result in results if not result["success"]]
    summary: dict[str, Any] = {
        "runs": len(results),
        "successes": len(successes),
        "failures": len(failures),
        "failure_runs": [result["run"] for result in failures],
        "elapsed_seconds": {
            "per_run": [result["elapsed_seconds"] for result in results],
            "mean": round(statistics.mean(result["elapsed_seconds"] for result in results), 3),
            "median": round(statistics.median(result["elapsed_seconds"] for result in results), 3),
            "min": min(result["elapsed_seconds"] for result in results),
            "max": max(result["elapsed_seconds"] for result in results),
            "total": round(sum(result["elapsed_seconds"] for result in results), 3),
        },
        "recovery_event_counts": dict(
            Counter(
                recovery["type"]
                for result in results
                for recovery in result["recoveries"]
            )
        ),
        "reviser_max_output_tokens_per_call": _SINGLE_OPTIONS.max_tokens,
    }
    if not successes:
        return summary

    summary["stage_seconds_mean"] = {
        stage: round(
            statistics.mean(
                result["stage_seconds"].get(stage, 0.0) for result in successes
            ),
            3,
        )
        for stage in ["schemer", "websearch", "data", "evaluate", "revise"]
    }
    summary["track_consistency"] = categorical_consistency(
        [result["track"] for result in successes]
    )
    summary["level_consistency"] = categorical_consistency(
        [result["level"] for result in successes]
    )
    summary["query_count_consistency"] = categorical_consistency(
        [len(result["queries"]) for result in successes]
    )
    summary["strategy_count_consistency"] = categorical_consistency(
        [result["strategy_count"] for result in successes]
    )
    summary["scores"] = {
        axis: score_consistency([result["scores"][axis] for result in successes])
        for axis in ["x", "y", "z"]
    }
    summary["compare_score_consistency"] = {
        axis: categorical_consistency(
            [result["compare_scores"][axis] for result in successes]
        )
        for axis in ["x", "y", "z"]
    }
    summary["overall_text_similarity"] = pairwise_similarity(
        [result["overall"] for result in successes]
    )
    summary["revised_answer_similarity"] = {
        str(index + 1): pairwise_similarity(
            [result["revised_answers"][index] for result in successes]
        )
        for index in range(2)
    }
    summary["exact_output_consistency"] = {
        "overall": categorical_consistency(
            [result["overall_fingerprint"] for result in successes]
        ),
        "revised_answer_1": categorical_consistency(
            [result["revised_fingerprints"][0] for result in successes]
        ),
        "revised_answer_2": categorical_consistency(
            [result["revised_fingerprints"][1] for result in successes]
        ),
    }
    summary["quality_failures"] = {
        "revision_validation_problem_runs": [
            result["run"]
            for result in successes
            if any(result["revision_validation_problems"])
        ],
        "cross_question_leak_runs": [
            result["run"]
            for result in successes
            if any(result["cross_question_leak"].values())
        ],
    }
    return summary


async def main(runs: int, output: Path | None) -> None:
    results: list[dict[str, Any]] = []
    for run_number in range(1, runs + 1):
        result = await run_once(run_number)
        results.append(result)
        concise = {key: value for key, value in result.items() if key not in {"overall", "revised_answers"}}
        print("RUN_RESULT " + json.dumps(concise, ensure_ascii=False), flush=True)
    summary = summarize(results)
    print("BENCHMARK_SUMMARY " + json.dumps(summary, ensure_ascii=False), flush=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"Saved: {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be positive")
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main(args.runs, args.output))

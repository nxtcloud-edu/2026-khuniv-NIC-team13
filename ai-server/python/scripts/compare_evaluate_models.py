#!/usr/bin/env python3
"""Compare EVALUATE stages between GPT-5.4 and the configured K-EXAONE.

This is an offline evaluation harness: it uses the canonical sample request and
fixed reference context so prompt/model changes are not mixed with live search,
vector, or database variability.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import dotenv_values
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config.resources import read_text
from app.config.settings import get_settings
from app.mappers.analyze_request_mapper import to_agent_state
from app.schemas.analyze_request import AnalyzeRequestDto
from app.util.template import render
from app.workflow.nodes.evaluate_models import (
    AxisEvaluationReport,
    FitEvaluationReport,
    ImprovementStrategyReport,
    ImprovementSummaryReport,
)
from app.workflow.track import Track


T = TypeVar("T", bound=BaseModel)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?요다])\s+|\n+")
_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9+.#_-]*")
_RISKY_CLAIM_PATTERNS = {
    "unsupported_absence": re.compile(
        r"[^.!?\n]*(?:경험|역할|리더십|근무|기여|지식|전문성|사례)"
        r"[^.!?\n]*(?:없(?:습니다|음|고|어|는|다)|부재)[^.!?\n]*"
    ),
    "auxiliary_role": re.compile(r"[^.!?\n]*보조(?:적)? 역할[^.!?\n]*"),
    "not_core_role": re.compile(r"[^.!?\n]*핵심 역할(?:이)? (?:아님|아니)[^.!?\n]*"),
    "malformed_tenure": re.compile(r"[^.!?\n]*백\s*\d+\s*년[^.!?\n]*"),
    "unsupported_patent_or_paper": re.compile(r"[^.!?\n]*(?:특허|논문)[^.!?\n]*"),
}


def _legacy_provider_setting(name: str, default: str = "") -> str:
    """Read offline comparison credentials without restoring them to app Settings."""
    environment_value = os.environ.get(name)
    if environment_value:
        return environment_value
    dotenv_value = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get(name)
    return str(dotenv_value or default)


@dataclass
class CallStats:
    provider: str
    stage: str
    success: bool
    elapsed_seconds: float
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    output_chars: int | None = None
    leaf_strings: int | None = None
    list_items: int | None = None
    max_leaf_chars: int | None = None
    exact_duplicate_leaf_ratio: float | None = None
    exact_duplicate_sentence_ratio: float | None = None
    error_type: str | None = None
    error_message: str | None = None


def _leaf_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaf_strings(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaf_strings(item)]
    return []


def _leaf_items(value: Any, path: str = "$") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        return [
            leaf
            for key, item in value.items()
            for leaf in _leaf_items(item, f"{path}.{key}")
        ]
    if isinstance(value, list):
        return [
            leaf
            for index, item in enumerate(value)
            for leaf in _leaf_items(item, f"{path}[{index}]")
        ]
    return []


def _is_expected_output_letter(character: str) -> bool:
    codepoint = ord(character)
    return (
        "A" <= character <= "Z"
        or "a" <= character <= "z"
        or 0x1100 <= codepoint <= 0x11FF
        or 0x3130 <= codepoint <= 0x318F
        or 0xAC00 <= codepoint <= 0xD7A3
    )


def _corrupt_character_findings(outputs: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path, value in _leaf_items(outputs):
        suspicious: list[str] = []
        for character in value:
            category = unicodedata.category(character)
            unexpected_letter = category.startswith("L") and not _is_expected_output_letter(
                character
            )
            unexpected_whitespace = character.isspace() and character not in {" ", "\n", "\t"}
            if character == "\ufffd" or unexpected_letter or unexpected_whitespace:
                suspicious.append(character)
        for character in dict.fromkeys(suspicious):
            findings.append(
                {
                    "path": path,
                    "character": character,
                    "codepoint": f"U+{ord(character):04X}",
                    "name": unicodedata.name(character, "UNKNOWN"),
                    "text": value[:300],
                }
            )
    return findings


def _risky_claim_findings(outputs: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path, value in _leaf_items(outputs):
        for name, pattern in _RISKY_CLAIM_PATTERNS.items():
            for match in pattern.finditer(value):
                text = match.group(0).strip()
                if name == "unsupported_absence" and "확인되지" in text:
                    continue
                findings.append({"type": name, "path": path, "text": text[:300]})
    return findings


def _quality_diagnostics(
    outputs: dict[str, Any], source_text: str
) -> dict[str, Any]:
    source_tokens = {token.lower() for token in _LATIN_TOKEN.findall(source_text)}
    generated_tokens = {
        token.lower()
        for _path, value in _leaf_items(outputs)
        for token in _LATIN_TOKEN.findall(value)
    }
    axes = outputs.get("axes", {})
    scores = {
        axis: axes.get(axis, {}).get("score")
        for axis in ("x", "y", "z")
        if axes.get(axis, {}).get("score") is not None
    }
    corruption = _corrupt_character_findings(outputs)
    risky_claims = _risky_claim_findings(outputs)
    return {
        "scores": scores,
        "text_chars": sum(len(value) for _path, value in _leaf_items(outputs)),
        "corrupt_characters": corruption,
        "corrupt_character_count": len(corruption),
        "unknown_latin_tokens": sorted(generated_tokens - source_tokens),
        "risky_claims": risky_claims,
        "risky_claim_count": len(risky_claims),
    }


def _list_item_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_list_item_count(item) for item in value.values())
    if isinstance(value, list):
        return len(value) + sum(_list_item_count(item) for item in value)
    return 0


def _duplicate_ratio(values: list[str]) -> float:
    normalized = [" ".join(value.split()).lower() for value in values if value.strip()]
    if not normalized:
        return 0.0
    return round(1.0 - len(set(normalized)) / len(normalized), 4)


def _output_metrics(parsed: BaseModel) -> dict[str, Any]:
    payload = parsed.model_dump(mode="json")
    leaves = _leaf_strings(payload)
    sentences = [
        sentence.strip()
        for leaf in leaves
        for sentence in _SENTENCE_SPLIT.split(leaf)
        if sentence.strip()
    ]
    return {
        "output_chars": len(json.dumps(payload, ensure_ascii=False)),
        "leaf_strings": len(leaves),
        "list_items": _list_item_count(payload),
        "max_leaf_chars": max(map(len, leaves), default=0),
        "exact_duplicate_leaf_ratio": _duplicate_ratio(leaves),
        "exact_duplicate_sentence_ratio": _duplicate_ratio(sentences),
    }


def _usage_from_completion(completion: Any) -> dict[str, Any]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    return {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


async def _call_structured(
    *,
    client: AsyncOpenAI,
    provider: str,
    model: str,
    stage: str,
    system: str,
    user: str,
    response_model: type[T],
) -> tuple[T | None, CallStats]:
    started = time.perf_counter()
    try:
        common: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": response_model,
        }
        if provider == "exaone":
            common.update(
                temperature=0.0,
                max_tokens=4096,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "parse_reasoning": True,
                    "include_reasoning": False,
                },
            )
        else:
            common.update(max_completion_tokens=4096)

        completion = await client.chat.completions.parse(**common)
        choice = completion.choices[0]
        parsed = choice.message.parsed
        if parsed is None:
            raise RuntimeError("structured output parsing returned null")
        stats = CallStats(
            provider=provider,
            stage=stage,
            success=True,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            finish_reason=choice.finish_reason,
            **_usage_from_completion(completion),
            **_output_metrics(parsed),
        )
        return parsed, stats
    except Exception as exc:  # noqa: BLE001 - benchmark must record provider errors
        completion = getattr(exc, "completion", None)
        choice = completion.choices[0] if completion and completion.choices else None
        stats = CallStats(
            provider=provider,
            stage=stage,
            success=False,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            finish_reason=getattr(choice, "finish_reason", None),
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
            **_usage_from_completion(completion),
        )
        return None, stats


def _stage_input(
    state: Any,
    applicant_specs: dict[str, Any],
    prior_results: dict[str, Any],
    *,
    include_reference_context: bool = True,
    include_applicant_source: bool = True,
) -> str:
    payload: dict[str, Any] = {
        "company": state.company,
        "job_position": state.job_position,
        **prior_results,
    }
    if include_applicant_source:
        payload.update(
            applicant_info=applicant_specs,
            questions=state.question_list,
            answers=state.answer_list,
        )
    if include_reference_context:
        payload.update(
            pass_score="합격자 데이터 없음",
            web_context="수집된 기업 정보 없음",
        )
    return json.dumps(payload, ensure_ascii=False)


async def _run_provider(
    *,
    provider: str,
    client: AsyncOpenAI,
    model: str,
    state: Any,
) -> dict[str, Any]:
    applicant_specs = {
        "학력": state.education,
        "학점": state.gpa,
        "전공": state.major,
        "경력_수상": state.background_career_award,
        "어학": state.linguistic_ability,
        "자격증": state.certificates,
    }
    track = Track.parse(state.track)
    eval_prompts = read_text("3D_Eval_Prompt_v2.txt")
    eval_prompts += "\n\n" + read_text("track", f"{track.value}.txt")
    axes_system = render(
        read_text("prompts", "evaluate", "system.txt"),
        eval_prompts=eval_prompts,
        position=state.job_position,
        company=state.company,
        pass_score="합격자 데이터 없음",
        web_search="수집된 기업 정보 없음",
        vector_context="유사 자기소개서 데이터 없음",
    )
    axes_user = render(
        read_text("prompts", "evaluate", "user.txt"),
        applicant_info=json.dumps(applicant_specs, ensure_ascii=False),
        questions=json.dumps(state.question_list, ensure_ascii=False),
        answers=json.dumps(state.answer_list, ensure_ascii=False),
    )
    source_text = "\n".join(
        [
            axes_system,
            axes_user,
            read_text("prompts", "evaluate", "fit.txt"),
            read_text("prompts", "evaluate", "improvement.txt"),
            read_text("prompts", "evaluate", "strategy.txt"),
        ]
    )

    outputs: dict[str, Any] = {}
    stats: list[CallStats] = []

    def result() -> dict[str, Any]:
        return {
            "provider": provider,
            "model": model,
            "stats": [asdict(item) for item in stats],
            "outputs": outputs,
            "diagnostics": _quality_diagnostics(outputs, source_text),
        }

    axes, call_stats = await _call_structured(
        client=client,
        provider=provider,
        model=model,
        stage="axes",
        system=axes_system,
        user=axes_user,
        response_model=AxisEvaluationReport,
    )
    stats.append(call_stats)
    if axes is None:
        return result()
    outputs["axes"] = axes.model_dump(mode="json")

    fit, call_stats = await _call_structured(
        client=client,
        provider=provider,
        model=model,
        stage="fit",
        system=read_text("prompts", "evaluate", "fit.txt"),
        user=_stage_input(state, applicant_specs, {"axes": outputs["axes"]}),
        response_model=FitEvaluationReport,
    )
    stats.append(call_stats)
    if fit is None:
        return result()
    outputs["fit"] = fit.model_dump(mode="json")

    improvement, call_stats = await _call_structured(
        client=client,
        provider=provider,
        model=model,
        stage="improvement",
        system=read_text("prompts", "evaluate", "improvement.txt"),
        user=_stage_input(
            state,
            applicant_specs,
            {"axes": outputs["axes"], "fit_evaluation": outputs["fit"]},
            include_reference_context=False,
        ),
        response_model=ImprovementSummaryReport,
    )
    stats.append(call_stats)
    if improvement is None:
        return result()
    outputs["improvement"] = improvement.model_dump(mode="json")

    strategy, call_stats = await _call_structured(
        client=client,
        provider=provider,
        model=model,
        stage="strategy",
        system=read_text("prompts", "evaluate", "strategy.txt"),
        user=_stage_input(
            state,
            applicant_specs,
            {"improvement_summary": outputs["improvement"]},
            include_reference_context=False,
            include_applicant_source=False,
        ),
        response_model=ImprovementStrategyReport,
    )
    stats.append(call_stats)
    if strategy is not None:
        outputs["strategy"] = strategy.model_dump(mode="json")

    return result()


def _aggregate(results: list[dict[str, Any]], runs: int) -> dict[str, Any]:
    aggregates: dict[str, Any] = {}
    for provider in sorted({result["provider"] for result in results}):
        provider_results = [
            result for result in results if result["provider"] == provider
        ]
        stage_failures: Counter[str] = Counter()
        score_values: dict[str, list[float]] = {axis: [] for axis in ("x", "y", "z")}
        partial_output_text_chars: list[int] = []
        full_success_text_chars: list[int] = []
        billed_completion_tokens: list[int] = []
        elapsed_seconds: list[float] = []
        all_stage_successes = 0
        corruption_runs = 0
        risky_claim_runs = 0
        unknown_latin_tokens: Counter[str] = Counter()
        for result in provider_results:
            stats = result["stats"]
            failures = [stat["stage"] for stat in stats if not stat["success"]]
            stage_failures.update(failures)
            full_success = len(stats) == 4 and not failures
            if full_success:
                all_stage_successes += 1
            diagnostics = result.get("diagnostics", {})
            for axis, score in diagnostics.get("scores", {}).items():
                score_values[axis].append(float(score))
            output_text_chars = int(diagnostics.get("text_chars", 0))
            partial_output_text_chars.append(output_text_chars)
            if full_success:
                full_success_text_chars.append(output_text_chars)
            billed_completion_tokens.append(
                sum(
                    int(stat["completion_tokens"] or 0)
                    for stat in stats
                )
            )
            elapsed_seconds.append(sum(float(stat["elapsed_seconds"]) for stat in stats))
            corruption_runs += bool(diagnostics.get("corrupt_character_count"))
            risky_claim_runs += bool(diagnostics.get("risky_claim_count"))
            unknown_latin_tokens.update(diagnostics.get("unknown_latin_tokens", []))

        score_summary: dict[str, Any] = {}
        for axis, values in score_values.items():
            score_summary[axis] = {
                "values": values,
                "counts": dict(Counter(map(str, values))),
                "mean": round(statistics.mean(values), 3) if values else None,
                "population_stddev": round(statistics.pstdev(values), 3)
                if values
                else None,
                "min": min(values, default=None),
                "max": max(values, default=None),
                "range": round(max(values) - min(values), 3) if values else None,
            }
        aggregates[provider] = {
            "requested_runs": runs,
            "completed_runs": len(provider_results),
            "all_stage_successes": all_stage_successes,
            "all_stage_failures": len(provider_results) - all_stage_successes,
            "stage_failures": dict(stage_failures),
            "scores": score_summary,
            "full_success_text_chars": {
                "mean": round(statistics.mean(full_success_text_chars), 1)
                if full_success_text_chars
                else None,
                "min": min(full_success_text_chars, default=None),
                "max": max(full_success_text_chars, default=None),
            },
            "partial_output_text_chars": {
                "mean": round(statistics.mean(partial_output_text_chars), 1)
                if partial_output_text_chars
                else None,
                "min": min(partial_output_text_chars, default=None),
                "max": max(partial_output_text_chars, default=None),
            },
            "billed_completion_tokens": {
                "mean": round(statistics.mean(billed_completion_tokens), 1)
                if billed_completion_tokens
                else None,
                "min": min(billed_completion_tokens, default=None),
                "max": max(billed_completion_tokens, default=None),
            },
            "elapsed_seconds": {
                "mean": round(statistics.mean(elapsed_seconds), 3)
                if elapsed_seconds
                else None,
                "min": round(min(elapsed_seconds), 3) if elapsed_seconds else None,
                "max": round(max(elapsed_seconds), 3) if elapsed_seconds else None,
            },
            "runs_with_corrupt_characters": corruption_runs,
            "runs_with_risky_claims": risky_claim_runs,
            "unknown_latin_tokens": dict(unknown_latin_tokens),
        }
    return aggregates


async def main(
    request_path: Path,
    output_path: Path,
    label: str,
    providers: list[str],
    runs: int,
) -> None:
    settings = get_settings()
    request = AnalyzeRequestDto.model_validate_json(request_path.read_text(encoding="utf-8"))
    state = to_agent_state(request)
    state.track = request.job_field or "engineering"

    clients: dict[str, tuple[AsyncOpenAI, str]] = {}
    if "gpt-5.4" in providers:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the gpt-5.4 provider")
        clients["gpt-5.4"] = (
            AsyncOpenAI(api_key=settings.openai_api_key, max_retries=1, timeout=300.0),
            "gpt-5.4-2026-03-05",
        )
    if "exaone" in providers:
        friendli_api_key = _legacy_provider_setting("FRIENDLI_API_KEY")
        friendli_base_url = _legacy_provider_setting(
            "FRIENDLI_BASE_URL", "https://api.friendli.ai/serverless/v1"
        )
        exaone_chat_model = _legacy_provider_setting(
            "EXAONE_CHAT_MODEL", "LGAI-EXAONE/K-EXAONE-236B-A23B"
        )
        if not friendli_api_key:
            raise RuntimeError("FRIENDLI_API_KEY is required for the exaone provider")
        clients["exaone"] = (
            AsyncOpenAI(
                api_key=friendli_api_key,
                base_url=friendli_base_url,
                max_retries=1,
                timeout=300.0,
            ),
            exaone_chat_model,
        )
    results: list[dict[str, Any]] = []
    for run_number in range(1, runs + 1):
        run_results = await asyncio.gather(
            *(
                _run_provider(
                    provider=provider,
                    client=client,
                    model=model,
                    state=state,
                )
                for provider, (client, model) in clients.items()
            )
        )
        for result in run_results:
            result["run"] = run_number
            results.append(result)
        print(f"completed run {run_number}/{runs}", file=sys.stderr, flush=True)
    aggregates = _aggregate(results, runs)
    report = {
        "label": label,
        "request": str(request_path),
        "fixed_context": True,
        "runs": runs,
        "results": results,
        "aggregates": aggregates,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "label": label,
                "output": str(output_path),
                "aggregates": aggregates,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--request",
        type=Path,
        default=Path("scripts/sample_analyze_request.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=["gpt-5.4", "exaone"],
        default=["gpt-5.4", "exaone"],
    )
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    asyncio.run(main(args.request, args.output, args.label, args.providers, args.runs))

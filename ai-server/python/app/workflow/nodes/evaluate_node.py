"""Port of ``pertineo.agent.workflow.nodes.EvaluateNode``."""
from __future__ import annotations

import json
import logging
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional

from openai import AsyncOpenAI, LengthFinishReasonError
from pydantic import ValidationError

from app.config.resources import read_text
from app.repository.models import PreviousAnalysisResult
from app.service.openai_chat_client import OPENAI_FAST, create_openai_client, parse_structured
from app.util.template import render
from app.util.json_utils import jsonable
from app.vector.vector_context_service import VectorContextRequest, VectorContextService
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.base import AgentNode
from app.workflow.nodes.evaluate_models import (
    AxisEvaluationReport,
    FitEvaluationReport,
    ImprovementEvaluationReport,
    ImprovementStrategyReport,
    ImprovementSummaryReport,
    ResumeEvaluation,
)
from app.workflow.state import AgentState
from app.workflow.track import Track

logger = logging.getLogger(__name__)


_MAX_RETRIEVED_CONTEXT_CHARS = 6000
_EVALUATION_STAGE_OPTIONS = replace(OPENAI_FAST, max_tokens=4096)


def _score_comparison_text(applicant_score: float, pass_score: float) -> str:
    applicant = Decimal(str(applicant_score)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    baseline = Decimal(str(pass_score)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    difference = applicant - baseline
    if difference == 0:
        return f"지원자 {applicant:.2f}점으로 합격자 평균 {baseline:.2f}점과 동일합니다."
    direction = "높습니다" if difference > 0 else "낮습니다"
    return (
        f"지원자 {applicant:.2f}점으로 합격자 평균 {baseline:.2f}점보다 "
        f"{abs(difference):.2f}점 {direction}."
    )


def with_deterministic_compare_scores(
    axes: AxisEvaluationReport,
    pass_score: Optional[PreviousAnalysisResult],
) -> AxisEvaluationReport:
    updated = {}
    for axis_name in ("x", "y", "z"):
        axis = getattr(axes, axis_name)
        baseline = getattr(pass_score, axis_name, None) if pass_score is not None else None
        compare_score = (
            _score_comparison_text(axis.score, baseline)
            if baseline is not None
            else "비교 대상 없음"
        )
        updated[axis_name] = axis.model_copy(update={"compare_score": compare_score})
    return AxisEvaluationReport(**updated)


def system_prompt_parameters(
    eval_prompts: str,
    position: Optional[str],
    company: Optional[str],
    db_context: Any,
    web_context: str,
    vector_context: str,
) -> Dict[str, Any]:
    return {
        "eval_prompts": eval_prompts,
        "position": position,
        "company": company,
        "pass_score": db_context,
        "web_search": web_context,
        "vector_context": vector_context,
    }


class EvaluateNode(AgentNode):
    def __init__(
        self,
        vector_context_service: VectorContextService,
        client: Optional[AsyncOpenAI] = None,
    ) -> None:
        self._client = client or create_openai_client()
        self._vector_context_service = vector_context_service

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        await events.running("evaluate_start", "자기소개서 평가를 시작합니다.")

        questions_str = json.dumps(state.question_list, ensure_ascii=False)
        answers_str = json.dumps(state.answer_list, ensure_ascii=False)
        web_context = self._bounded_context(
            state.context_web if state.context_web is not None else "수집된 기업 정보 없음"
        )
        db_context: Any = (
            jsonable(state.context_db) if state.context_db is not None else "합격자 데이터 없음"
        )
        db_context_prompt = (
            json.dumps(db_context, ensure_ascii=False)
            if not isinstance(db_context, str)
            else db_context
        )

        vector_result = await self._vector_context_service.build_evaluation_context(
            VectorContextRequest(
                company=state.company,
                job_position=state.job_position,
                questions=state.question_list,
                answers=state.answer_list,
            )
        )
        await events.running(
            "evaluate_vector_context",
            {
                "status": vector_result.status,
                "selected_key_count": len(vector_result.selected_keys),
                "document_count": len(vector_result.documents),
            },
        )
        vector_context = vector_result.to_prompt_text()
        vector_context = self._bounded_context(vector_context)

        applicant_specs = self._format_specs(state)
        track = Track.parse(state.track)

        axes_prompt_text = read_text("prompts", "evaluate", "system.txt")
        fit_prompt_text = read_text("prompts", "evaluate", "fit.txt")
        improvement_prompt_text = read_text("prompts", "evaluate", "improvement.txt")
        strategy_prompt_text = read_text("prompts", "evaluate", "strategy.txt")
        user_prompt_text = read_text("prompts", "evaluate", "user.txt")
        eval_prompts = read_text("3D_Eval_Prompt_v2.txt")
        eval_prompts += "\n\n" + read_text("track", f"{track.value}.txt")

        await events.running("evaluate_generation", "평가 보고서를 생성중입니다...")

        params = system_prompt_parameters(
            eval_prompts,
            state.job_position,
            state.company,
            db_context_prompt,
            web_context,
            vector_context,
        )
        axes_system_prompt = render(axes_prompt_text, **params)
        user_prompt = render(
            user_prompt_text,
            applicant_info=applicant_specs,
            questions=questions_str,
            answers=answers_str,
        )

        axes = await parse_structured(
            self._client,
            axes_system_prompt,
            user_prompt,
            AxisEvaluationReport,
            options=_EVALUATION_STAGE_OPTIONS,
        )
        axes = with_deterministic_compare_scores(axes, state.context_db)
        await events.running("evaluate_axes_completed", "3축 점수와 근거 생성을 완료했습니다.")

        fit_input = self._stage_input(
            state,
            applicant_specs,
            db_context,
            web_context,
            {"axes": axes.model_dump(mode="json")},
        )
        fit = await parse_structured(
            self._client,
            fit_prompt_text,
            fit_input,
            FitEvaluationReport,
            options=_EVALUATION_STAGE_OPTIONS,
        )
        await events.running("evaluate_fit_completed", "적합성과 종합평가 생성을 완료했습니다.")

        improvement_input = self._stage_input(
            state,
            applicant_specs,
            db_context,
            web_context,
            {
                "axes": axes.model_dump(mode="json"),
                "fit_evaluation": fit.model_dump(mode="json"),
            },
            include_reference_context=False,
        )
        improvement_summary = await parse_structured(
            self._client,
            improvement_prompt_text,
            improvement_input,
            ImprovementSummaryReport,
            options=_EVALUATION_STAGE_OPTIONS,
        )
        await events.running(
            "evaluate_improvement_summary_completed",
            "강점·약점과 개선 방향 생성을 완료했습니다.",
        )

        strategy_input = self._stage_input(
            state,
            applicant_specs,
            db_context,
            web_context,
            {"improvement_summary": improvement_summary.model_dump(mode="json")},
            include_reference_context=False,
            include_applicant_source=False,
        )
        try:
            strategy = await parse_structured(
                self._client,
                strategy_prompt_text,
                strategy_input,
                ImprovementStrategyReport,
                options=_EVALUATION_STAGE_OPTIONS,
            )
        except (ValidationError, LengthFinishReasonError, RuntimeError) as exc:
            logger.warning(
                "Improvement strategy generation failed validation; using safe structural fallback: %s",
                type(exc).__name__,
            )
            strategy = self._safe_improvement_strategy()
            await events.running(
                "evaluate_strategy_fallback",
                "개선 전략 생성 결과를 검증하지 못해 안전한 구조 편집 전략을 사용합니다.",
            )
        improvement = ImprovementEvaluationReport.combine(improvement_summary, strategy)
        report = ResumeEvaluation.combine(axes, fit, improvement)

        state.evaluation_result = report

        await events.running("evaluate_result", report)
        await events.running("evaluate_end", "자기소개서 평가를 완료했습니다.")

        return state

    def decide_next_node(self, state: AgentState) -> str:
        return "REVISE"

    def _format_specs(self, state: AgentState) -> str:
        specs = {
            "학력": state.education,
            "학점": state.gpa,
            "전공": state.major,
            "경력_수상": state.background_career_award,
            "어학": state.linguistic_ability,
            "자격증": state.certificates,
        }
        try:
            return json.dumps(specs, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to format applicant specs: %s", exc)
            return str(specs)

    def _bounded_context(self, context: str) -> str:
        if len(context) <= _MAX_RETRIEVED_CONTEXT_CHARS:
            return context
        return context[:_MAX_RETRIEVED_CONTEXT_CHARS] + "\n[이후 내용 생략]"

    def _stage_input(
        self,
        state: AgentState,
        applicant_specs: str,
        db_context: Any,
        web_context: str,
        prior_results: Dict[str, Any],
        include_reference_context: bool = True,
        include_applicant_source: bool = True,
    ) -> str:
        payload = {
            "company": state.company,
            "job_position": state.job_position,
            **prior_results,
        }
        if include_applicant_source:
            payload["applicant_info"] = json.loads(applicant_specs)
            payload["questions"] = state.question_list
            payload["answers"] = state.answer_list
        if include_reference_context:
            payload["pass_score"] = db_context
            payload["web_context"] = self._bounded_context(web_context)[:3000]
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _safe_improvement_strategy() -> ImprovementStrategyReport:
        return ImprovementStrategyReport(
            improve_strategy=[
                {
                    "strategy_name": "핵심 결론 우선 배치",
                    "action_items": [
                        "각 문항이 요구하는 핵심 답을 첫 문장에 배치합니다.",
                        "뒤 문장에서는 원문에 있는 행동과 의미를 순서대로 연결합니다.",
                    ],
                },
                {
                    "strategy_name": "원문 근거 연결 강화",
                    "action_items": [
                        "주장마다 원문에서 확인되는 행동을 근거로 연결합니다.",
                        "새로운 사실을 추가하지 않고 중복 표현과 불필요한 수식을 줄입니다.",
                    ],
                },
            ]
        )

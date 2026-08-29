"""Port of ``pertineo.agent.workflow.nodes.ReviserNode``."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import replace
from difflib import SequenceMatcher
from math import ceil
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config.resources import read_text
from app.service.openai_chat_client import (
    OPENAI_FAST,
    OPENAI_REASONING,
    create_openai_client,
    parse_structured,
)
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.base import AgentNode
from app.workflow.nodes.reviser_models import RevisedAnswerInfo, SingleRevisedAnswer
from app.workflow.state import AgentState

logger = logging.getLogger(__name__)

_PLACEHOLDER_PATTERN = re.compile(r"^(?:[.\s…]|placeholder|예시|없음)+$", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"\d[\d,.]*(?:%|ms|밀리초|초|건|명|년|개월)?", re.IGNORECASE)
_LATIN_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+.#_-]*")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[!?])\s+|(?<!\d)(?<=\.)\s+")
_CLAIM_ESCALATION_TERMS = (
    "구축",
    "구현",
    "운영",
    "도입",
    "배포",
    "최적화",
    "장애",
    "복구",
    "유실",
    "알고리즘",
    "모델",
    "인프라",
    "가용성",
    "무결성",
    "정확도",
    "반응 속도",
    "병목",
    "프로토콜",
    "수율",
)
_DEFAULT_MIN_REPLY_CHARS = 40
_MIN_EXPLANATION_CHARS = 20
_MAX_PREVIOUS_CANDIDATE_CHARS = 3000
_MAX_TARGETED_ATTEMPTS = 5
_MIN_NEAR_COPY_SOURCE_CHARS = 100
_MAX_NEAR_COPY_SIMILARITY = 0.92
_MAX_EDITING_OPERATIONS_PER_STRATEGY = 3
_FIRST_PASS_OPTIONS = replace(OPENAI_FAST, max_tokens=4096)
_SINGLE_OPTIONS = replace(
    OPENAI_REASONING,
    reasoning_effort="low",
    max_tokens=4096,
)
_GENERIC_EXPLANATION_VALUES = {
    "보존한 핵심 근거와 개선한 구성 방식을 설명합니다.",
    "평가자에게 전달되는 역량과 설득 효과를 설명합니다.",
}
_INTERNAL_EXPLANATION_MARKERS = (
    "allowed_",
    "required_",
    "target_pair",
    "original_answer",
    "best_reply",
    "reply_reason",
    "expectation",
    "검증 규칙",
    "내부 처리",
)
_NUMERIC_PREFIX_QUALIFIERS = ("초당", "최대", "최소", "이후", "약", "첫")
_AUTO_RESTORE_NUMERIC_PREFIX_QUALIFIERS = ("초당", "최대", "최소", "약")
_NUMERIC_SUFFIX_QUALIFIERS = ("이상", "이하", "이내", "내외", "수준", "정도", "까지", "간")
_COMPANY_ATTRIBUTE_TERMS = (
    "평가 방식",
    "기업 문화",
    "조직 문화",
    "기술 중심 문화",
    "혁신 지향성",
    "핵심 가치",
    "인재상",
)
_SAFE_REPLY_REASON = (
    "원문의 핵심 경험과 수치·기술을 보존하면서 질문에 대한 결론, 행동, 결과가 "
    "자연스럽게 이어지도록 구성을 다듬었습니다."
)
_SAFE_EXPECTATION = (
    "지원자의 실제 경험과 문제 해결 과정이 명확하게 전달되어 직무 적합성과 "
    "답변의 설득력을 높일 수 있습니다."
)
_EDITING_OPERATION_RULES = (
    (
        ("결론", "핵심 답", "우선 배치", "두괄식"),
        "원문에서 확인되는 핵심 결론을 첫 문장에 분명하게 배치합니다.",
    ),
    (
        ("인과", "근거", "이유", "논리"),
        "원문에 있는 선택·행동·결과 사이의 인과관계를 연결어로 분명히 합니다.",
    ),
    (
        ("구조", "흐름", "순서", "전개"),
        "원문 문장을 질문에 대한 결론과 근거가 자연스럽게 이어지도록 재배열합니다.",
    ),
    (
        ("수치", "성과", "KPI", "결과"),
        "원문에 이미 있는 수치와 결과를 관련 행동 바로 뒤에 배치해 구체성을 높입니다.",
    ),
    (
        ("직무", "기여", "적합"),
        "원문에 이미 있는 경험과 목표가 지원 직무에 어떻게 연결되는지 선명하게 표현합니다.",
    ),
    (
        ("도메인", "산업", "공정"),
        "원문에 이미 언급된 산업·도메인 관심과 경험의 연결을 분명히 합니다.",
    ),
    (
        ("협업", "조직", "리더십"),
        "원문에 협업 행동이 있을 때만 지원자의 역할과 상호작용을 분명히 합니다.",
    ),
    (
        ("기술", "선택"),
        "원문에 선택 이유가 있을 때만 사용 기술과 판단 근거를 자연스럽게 연결합니다.",
    ),
    (
        ("중복", "간결", "문장", "표현"),
        "중복 표현을 줄이고 문장 경계를 다시 구성해 읽기 흐름을 개선합니다.",
    ),
)
_DEFAULT_EDITING_OPERATION = (
    "원문의 핵심 결론과 이를 뒷받침하는 근거의 순서가 선명해지도록 문장 구조를 재구성합니다."
)


def _is_invalid_text(value: Optional[str], minimum_chars: int) -> bool:
    if value is None:
        return True
    normalized = value.strip()
    return len(normalized) < minimum_chars or _PLACEHOLDER_PATTERN.fullmatch(normalized) is not None


class ReviserNode(AgentNode):
    def __init__(self, client: Optional[AsyncOpenAI] = None) -> None:
        self._client = client or create_openai_client()

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        await events.running("revise_start", "자기소개서 수정안 생성을 시작합니다.")
        system_prompt_text = read_text("prompts", "revise", "system.txt")
        await events.running("revise_generation", "수정된 답변을 생성중입니다...")

        context = self._build_revision_context(state)
        expected_size = len(state.question_list or [])
        if expected_size == 0 or len(state.answer_list or []) != expected_size:
            raise RuntimeError("질문과 원문 답변의 수가 일치하지 않거나 비어 있습니다.")

        targeted_results: Dict[int, SingleRevisedAnswer] = {}
        for index in range(expected_size):
            await events.running(
                "revise_item_generation",
                {"question_index": index + 1},
            )
            previous_candidate: Optional[SingleRevisedAnswer] = None
            for attempt in range(_MAX_TARGETED_ATTEMPTS):
                candidate = await self._revise_single(
                    system_prompt_text,
                    state,
                    context,
                    index,
                    previous_candidate,
                    attempt,
                )
                candidate, restored_qualifiers = self._restore_numeric_prefix_qualifiers(
                    candidate, state, index
                )
                if restored_qualifiers:
                    await events.running(
                        "revise_numeric_qualifier_restore",
                        {
                            "question_index": index + 1,
                            "expressions": restored_qualifiers,
                        },
                    )
                problems = self._generated_reply_problems(
                    candidate.best_reply, state, index
                )
                if not problems:
                    candidate, fallback_fields = self._with_safe_explanations(
                        candidate, state, index
                    )
                    targeted_results[index] = candidate
                    if fallback_fields:
                        await events.running(
                            "revise_explanation_fallback",
                            {
                                "question_index": index + 1,
                                "fields": fallback_fields,
                                "reason": (
                                    "본문은 검증을 통과했지만 설명 필드가 품질 검증을 "
                                    "통과하지 못해 안전한 설명으로 대체했습니다."
                                ),
                            },
                        )
                    break
                logger.warning(
                    "Per-question revision validation failed: questionIndex=%s attempt=%s problems=%s",
                    index + 1,
                    attempt + 1,
                    problems,
                )
                previous_candidate = candidate
                if attempt + 1 < _MAX_TARGETED_ATTEMPTS:
                    await events.running(
                        "revise_targeted_repair",
                        {"question_index": index + 1, "attempt": attempt + 2},
                    )
            if index not in targeted_results:
                targeted_results[index] = self._safe_fallback_candidate(state, index)
                await events.running(
                    "revise_safe_fallback",
                    {
                        "question_index": index + 1,
                        "reason": "생성 결과가 사실성 또는 품질 검증을 통과하지 못해 원문을 보존했습니다.",
                    },
                )

        validated_report = RevisedAnswerInfo(
            best_reply=[targeted_results[index].best_reply for index in range(expected_size)],
            reply_reason=[targeted_results[index].reply_reason for index in range(expected_size)],
            expectation=[targeted_results[index].expectation for index in range(expected_size)],
        )
        self._validate_final_report(validated_report, expected_size, state)

        state.revised_result = validated_report

        await events.completed("revise_result", validated_report)
        await events.completed("final_state", state)

        return state

    def _build_revision_context(self, state: AgentState) -> Dict[str, Any]:
        evaluation = state.evaluation_result
        return {
            "company": state.company,
            "job_position": state.job_position,
            "evaluation_editing_focus": [
                strategy.strategy_name for strategy in evaluation.improve_strategy
            ] if evaluation else [],
            "guidance_scope": (
                "편집 관점은 문장 구조와 강조점에만 적용합니다. 그 이름에서 새로운 경험, "
                "기술, 행동, KPI를 추론하지 않습니다. 지원자 사실의 유일한 출처는 "
                "target_pair의 original_answer입니다."
            ),
        }

    def _build_single_user_prompt(
        self,
        state: AgentState,
        context: Dict[str, Any],
        index: int,
        previous_candidate: Optional[SingleRevisedAnswer],
    ) -> str:
        problems = self._generated_reply_problems(
            previous_candidate.best_reply, state, index
        ) if previous_candidate is not None else []
        original_answer = (state.answer_list or [])[index]
        payload = {
            "revision_context": context,
            "target_pair": {
                "index": index + 1,
                "question": (state.question_list or [])[index],
                "original_answer": original_answer,
                "allowed_numeric_expressions": self._allowed_numeric_expressions(
                    state, index
                ),
                "required_numeric_expressions": self._required_numeric_expressions(
                    state, index
                ),
                "allowed_latin_tokens": self._allowed_latin_tokens(state, index),
                "required_latin_tokens": self._required_latin_tokens(state, index),
                "forbidden_claim_terms": self._forbidden_claim_terms(state, index),
                "original_answer_chars": len(original_answer.strip()),
                "target_answer_chars": {
                    "minimum": ceil(len(original_answer.strip()) * 0.9),
                    "maximum": ceil(len(original_answer.strip()) * 1.75),
                },
                "editing_plan": self._source_grounded_editing_plan(state, index),
            },
            "previous_candidate": self._bounded_candidate(previous_candidate),
            "problems_to_fix": problems,
        }
        return (
            "다음 한 항목만 완성도 높게 첨삭하세요. required_numeric_expressions와 "
            "required_latin_tokens는 빠짐없이 보존하고, allowed 목록에 없는 표현과 사실은 "
            "추가하지 마세요. forbidden_claim_terms는 best_reply에 절대 사용하지 마세요. "
            "editing_plan의 적용 가능한 작업을 최소 두 가지 실제 문장 구조에 "
            "반영하고 원문을 그대로 반환하거나 일부 어휘만 바꾸지 마세요. "
            "problems_to_fix가 있으면 모든 문제를 고치되 이전 후보의 올바른 사실은 유지하세요.\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    def _source_grounded_editing_plan(
        self, state: AgentState, index: int
    ) -> List[Dict[str, Any]]:
        evaluation = state.evaluation_result
        strategies = evaluation.improve_strategy if evaluation else []
        plan: List[Dict[str, Any]] = []
        for strategy_index, strategy in enumerate(strategies):
            source_text = " ".join(
                [strategy.strategy_name, *strategy.action_items]
            )
            operations = [
                operation
                for keywords, operation in _EDITING_OPERATION_RULES
                if any(keyword in source_text for keyword in keywords)
            ]
            operations = list(dict.fromkeys(operations))[
                :_MAX_EDITING_OPERATIONS_PER_STRATEGY
            ]
            if not operations:
                operations = [_DEFAULT_EDITING_OPERATION]
            plan.append(
                {
                    "strategy_name": self._safe_strategy_name(
                        strategy.strategy_name, state, index, strategy_index
                    ),
                    "source_grounded_operations": operations,
                }
            )
        return plan

    def _safe_strategy_name(
        self,
        value: str,
        state: AgentState,
        index: int,
        strategy_index: int,
    ) -> str:
        normalized = value.strip()
        if (
            not normalized
            or self._unsupported_numbers(normalized, state, index)
            or self._unsupported_latin_tokens(normalized, state, index)
            or self._unsupported_foreign_characters(normalized, state, index)
        ):
            return f"평가 전략 {strategy_index + 1}"
        return normalized

    async def _revise_single(
        self,
        system_prompt: str,
        state: AgentState,
        context: Dict[str, Any],
        index: int,
        previous_candidate: Optional[SingleRevisedAnswer],
        attempt: int,
    ) -> SingleRevisedAnswer:
        single_prompt = self._build_single_user_prompt(
            state, context, index, previous_candidate
        )
        return await parse_structured(
            self._client,
            system_prompt,
            single_prompt,
            SingleRevisedAnswer,
            options=_FIRST_PASS_OPTIONS if attempt == 0 else _SINGLE_OPTIONS,
        )

    def _invalid_indices(
        self,
        report: Optional[RevisedAnswerInfo],
        expected_size: int,
        state: Optional[AgentState] = None,
    ) -> List[int]:
        if report is None:
            return list(range(expected_size))

        invalid: List[int] = []
        for index in range(expected_size):
            best_reply = report.best_reply[index] if index < len(report.best_reply) else None
            reply_reason = report.reply_reason[index] if index < len(report.reply_reason) else None
            expectation = report.expectation[index] if index < len(report.expectation) else None
            candidate = SingleRevisedAnswer(
                best_reply=best_reply or "",
                reply_reason=reply_reason or "",
                expectation=expectation or "",
            )
            if self._single_is_invalid(candidate, state, index):
                invalid.append(index)
        return invalid

    def _validate_final_report(
        self,
        report: RevisedAnswerInfo,
        expected_size: int,
        state: AgentState,
    ) -> None:
        if not (
            len(report.best_reply)
            == len(report.reply_reason)
            == len(report.expectation)
            == expected_size
        ):
            raise RuntimeError("수정 결과의 질문별 항목 수가 일치하지 않습니다.")
        invalid_indices = self._invalid_indices(report, expected_size, state)
        if invalid_indices:
            raise RuntimeError(
                "수정 결과 검증에 실패했습니다. 문제 문항: "
                + ", ".join(str(index + 1) for index in invalid_indices)
            )

    def _single_is_invalid(
        self,
        candidate: SingleRevisedAnswer,
        state: AgentState,
        index: int,
    ) -> bool:
        return bool(self._single_problems(candidate, state, index))

    def _single_problems(
        self,
        candidate: SingleRevisedAnswer,
        state: AgentState,
        index: int,
    ) -> List[str]:
        problems = self._best_reply_problems(candidate.best_reply, state, index)
        for field_name, value in (
            ("reply_reason", candidate.reply_reason),
            ("expectation", candidate.expectation),
        ):
            problems.extend(
                f"{field_name}: {problem}"
                for problem in self._explanation_problems(value, state, index)
            )
        return problems

    def _best_reply_problems(
        self,
        best_reply: str,
        state: AgentState,
        index: int,
    ) -> List[str]:
        problems: List[str] = []
        if _is_invalid_text(best_reply, self._minimum_reply_chars(state, index)):
            problems.append("best_reply가 비어 있거나 원문에 비해 지나치게 짧습니다.")
        questions = state.question_list or []
        answers = state.answer_list or []
        is_preserved_original = (
            index < len(answers) and best_reply.strip() == answers[index].strip()
        )
        if (
            not is_preserved_original
            and index < len(questions)
            and questions[index].strip() in best_reply
        ):
            problems.append("best_reply에 질문 문장을 그대로 복사하지 마세요.")
        if not is_preserved_original and index < len(answers):
            original_chars = len(answers[index].strip())
            revised_chars = len(best_reply.strip())
            if original_chars >= 100:
                minimum_chars = ceil(original_chars * 0.9)
                maximum_chars = ceil(original_chars * 1.75)
                if not minimum_chars <= revised_chars <= maximum_chars:
                    problems.append(
                        "best_reply의 분량을 원문의 핵심 정보를 유지하는 범위로 조정하세요: "
                        f"현재 {revised_chars}자, 허용 {minimum_chars}~{maximum_chars}자"
                    )
        unsupported = self._unsupported_numbers(best_reply, state, index)
        if unsupported:
            problems.append(
                "원문에 없는 숫자 표현을 제거하세요: " + ", ".join(sorted(unsupported))
            )
        missing_numbers = self._missing_numbers(best_reply, state, index)
        if missing_numbers:
            problems.append(
                "원문의 핵심 숫자 표현을 모두 보존하세요: "
                + ", ".join(sorted(missing_numbers))
            )
        missing_numeric_qualifiers = self._missing_numeric_qualifiers(
            best_reply, state, index
        )
        if missing_numeric_qualifiers:
            problems.append(
                "숫자의 범위나 강도를 나타내는 원문 표현을 그대로 보존하세요: "
                + ", ".join(sorted(missing_numeric_qualifiers))
            )
        unsupported_latin = self._unsupported_latin_tokens(best_reply, state, index)
        if unsupported_latin:
            problems.append(
                "원문에 없는 영문 기술 표현을 제거하세요: "
                + ", ".join(sorted(unsupported_latin))
            )
        missing_latin = self._missing_latin_tokens(best_reply, state, index)
        if missing_latin:
            problems.append(
                "원문의 영문 기술명과 도구명을 모두 보존하세요: "
                + ", ".join(sorted(missing_latin))
            )
        unsupported_claim_terms = self._unsupported_claim_terms(
            best_reply, state, index
        )
        if unsupported_claim_terms:
            problems.append(
                "원문보다 사실의 강도를 높이거나 새 기술·행동을 만들지 마세요: "
                + ", ".join(sorted(unsupported_claim_terms))
            )
        unsupported_script = self._unsupported_foreign_characters(
            best_reply, state, index
        )
        if unsupported_script:
            problems.append(
                "원문에 없는 외국 문자를 제거하세요: "
                + " ".join(sorted(unsupported_script))
            )
        problems.extend(self._future_commitment_problems(best_reply, state, index))
        if not is_preserved_original:
            problems.extend(self._sentence_quality_problems(best_reply))
        return problems

    def _generated_reply_problems(
        self,
        best_reply: str,
        state: AgentState,
        index: int,
    ) -> List[str]:
        problems = self._best_reply_problems(best_reply, state, index)
        problems.extend(self._insufficient_revision_problems(best_reply, state, index))
        return problems

    @staticmethod
    def _insufficient_revision_problems(
        best_reply: str,
        state: AgentState,
        index: int,
    ) -> List[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return ["입력 범위를 벗어난 문항입니다."]

        original = " ".join(answers[index].split())
        revised = " ".join(best_reply.split())
        if revised == original:
            return [
                "원문을 그대로 반환하지 말고 editing_plan을 적용해 문장 구조와 근거 연결을 "
                "실제로 개선하세요."
            ]
        if len(original) < _MIN_NEAR_COPY_SOURCE_CHARS:
            return []

        similarity = SequenceMatcher(None, original, revised).ratio()
        if similarity > _MAX_NEAR_COPY_SIMILARITY:
            return [
                "수정안이 원문과 지나치게 유사합니다. 새로운 사실은 추가하지 말고, "
                "editing_plan에 따라 결론 위치·문장 순서·인과 연결 중 두 가지 이상을 "
                f"재구성하세요. 현재 문자열 유사도={similarity:.3f}"
            ]
        return []

    def _explanation_problems(
        self,
        value: str,
        state: AgentState,
        index: int,
    ) -> List[str]:
        problems: List[str] = []
        normalized = value.strip()
        if _is_invalid_text(value, _MIN_EXPLANATION_CHARS):
            problems.append("내용이 비어 있거나 지나치게 짧습니다.")
        if normalized in _GENERIC_EXPLANATION_VALUES:
            problems.append("출력 예시를 복사하지 말고 실제 수정 효과를 설명하세요.")
        copied_markers = [
            marker for marker in _INTERNAL_EXPLANATION_MARKERS if marker in value
        ]
        if copied_markers:
            problems.append(
                "입력 필드명이나 내부 처리 규칙을 설명하지 마세요: "
                + ", ".join(copied_markers)
            )
        unsupported_company_attributes = self._unsupported_company_attributes(
            value, state, index
        )
        if unsupported_company_attributes:
            problems.append(
                "입력에서 확인되지 않는 회사의 평가 기준이나 문화를 추정하지 마세요: "
                + ", ".join(sorted(unsupported_company_attributes))
            )
        unsupported_numbers = self._unsupported_numbers(value, state, index)
        if unsupported_numbers:
            problems.append(
                "입력에 없는 숫자 표현을 제거하세요: "
                + ", ".join(sorted(unsupported_numbers))
            )
        unsupported_latin = self._unsupported_latin_tokens(value, state, index)
        if unsupported_latin:
            problems.append(
                "입력에 없는 영문 표현을 자연스러운 한국어로 바꾸세요: "
                + ", ".join(sorted(unsupported_latin))
            )
        unsupported_script = self._unsupported_foreign_characters(value, state, index)
        if unsupported_script:
            problems.append(
                "원문에 없는 외국 문자를 제거하세요: "
                + " ".join(sorted(unsupported_script))
            )
        problems.extend(self._sentence_quality_problems(value))
        return problems

    @staticmethod
    def _unsupported_company_attributes(
        value: str, state: AgentState, index: int
    ) -> set[str]:
        company = (state.company or "").strip()
        if not company or company not in value:
            return set()
        source_text = ReviserNode._source_text(state, index)
        return {
            term
            for term in _COMPANY_ATTRIBUTE_TERMS
            if term in value and term not in source_text
        }

    def _with_safe_explanations(
        self,
        candidate: SingleRevisedAnswer,
        state: AgentState,
        index: int,
    ) -> tuple[SingleRevisedAnswer, List[str]]:
        fallback_fields: List[str] = []
        reply_reason = candidate.reply_reason
        expectation = candidate.expectation
        if self._explanation_problems(reply_reason, state, index):
            reply_reason = _SAFE_REPLY_REASON
            fallback_fields.append("reply_reason")
        if self._explanation_problems(expectation, state, index):
            expectation = _SAFE_EXPECTATION
            fallback_fields.append("expectation")
        return (
            SingleRevisedAnswer(
                best_reply=candidate.best_reply,
                reply_reason=reply_reason,
                expectation=expectation,
            ),
            fallback_fields,
        )

    @staticmethod
    def _future_commitment_problems(
        revised_answer: str, state: AgentState, index: int
    ) -> List[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return ["입력 범위를 벗어난 문항입니다."]
        original_answer = answers[index]
        has_tentative_plan = any(
            marker in original_answer
            for marker in ("싶습니다", "계획입니다", "예정입니다")
        )
        adds_stronger_commitment = (
            has_tentative_plan
            and "겠습니다" not in original_answer
            and "겠습니다" in revised_answer
        )
        if adds_stronger_commitment:
            return [
                "원문의 희망이나 계획을 확정된 수행 약속으로 강화하지 마세요. "
                "원문의 의지 수준을 유지하세요."
            ]
        return []

    def _unsupported_numbers(
        self,
        revised_answer: Optional[str],
        state: Optional[AgentState],
        index: int,
    ) -> set[str]:
        if revised_answer is None or state is None:
            return set()
        questions = state.question_list or []
        answers = state.answer_list or []
        if index >= len(questions) or index >= len(answers):
            return {"입력 범위를 벗어난 문항"}

        allowed_numbers = {
            self._normalize_number(value)
            for value in self._allowed_numeric_expressions(state, index)
        }
        generated_numbers = {
            self._normalize_number(value)
            for value in _NUMBER_PATTERN.findall(revised_answer)
        }
        return generated_numbers - allowed_numbers

    def _missing_numbers(
        self, revised_answer: str, state: AgentState, index: int
    ) -> set[str]:
        source = {
            self._normalize_number(value): value
            for value in self._required_numeric_expressions(state, index)
        }
        generated = {
            self._normalize_number(value)
            for value in _NUMBER_PATTERN.findall(revised_answer)
        }
        return {source[value] for value in source.keys() - generated}

    def _allowed_numeric_expressions(self, state: AgentState, index: int) -> List[str]:
        questions = state.question_list or []
        answers = state.answer_list or []
        if index >= len(questions) or index >= len(answers):
            return []
        allowed_text = f"{questions[index]}\n{answers[index]}"
        return list(dict.fromkeys(_NUMBER_PATTERN.findall(allowed_text)))

    def _missing_numeric_qualifiers(
        self, revised_answer: str, state: AgentState, index: int
    ) -> set[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return set()
        source_phrases = self._numeric_qualifier_phrases(answers[index])
        revised_normalized = self._normalize_number(revised_answer)
        return {
            phrase
            for phrase in source_phrases
            if self._normalize_number(phrase) not in revised_normalized
        }

    def _restore_numeric_prefix_qualifiers(
        self,
        candidate: SingleRevisedAnswer,
        state: AgentState,
        index: int,
    ) -> tuple[SingleRevisedAnswer, List[str]]:
        answers = state.answer_list or []
        if index >= len(answers):
            return candidate, []

        revised_answer = candidate.best_reply
        restored: List[str] = []
        for source_match in _NUMBER_PATTERN.finditer(answers[index]):
            source_prefix_window = answers[index][
                max(0, source_match.start() - 6):source_match.start()
            ]
            source_prefix = next(
                (
                    qualifier
                    for qualifier in _AUTO_RESTORE_NUMERIC_PREFIX_QUALIFIERS
                    if source_prefix_window.rstrip().endswith(qualifier)
                ),
                "",
            )
            if not source_prefix:
                continue

            source_separator = source_prefix_window[
                source_prefix_window.rfind(source_prefix) + len(source_prefix):
            ]
            source_number = self._normalize_number(source_match.group())
            for revised_match in list(_NUMBER_PATTERN.finditer(revised_answer)):
                if self._normalize_number(revised_match.group()) != source_number:
                    continue
                revised_prefix_window = revised_answer[
                    max(0, revised_match.start() - 6):revised_match.start()
                ]
                if revised_prefix_window.rstrip().endswith(source_prefix):
                    break
                restored_expression = (
                    f"{source_prefix}{source_separator}{revised_match.group()}"
                )
                revised_answer = (
                    revised_answer[:revised_match.start()]
                    + restored_expression
                    + revised_answer[revised_match.end():]
                )
                restored.append(restored_expression)
                break

        if revised_answer == candidate.best_reply:
            return candidate, restored
        return (
            SingleRevisedAnswer(
                best_reply=revised_answer,
                reply_reason=candidate.reply_reason,
                expectation=candidate.expectation,
            ),
            restored,
        )

    @staticmethod
    def _numeric_qualifier_phrases(value: str) -> List[str]:
        phrases: List[str] = []
        for match in _NUMBER_PATTERN.finditer(value):
            prefix_window = value[max(0, match.start() - 6):match.start()].rstrip()
            suffix_window = value[match.end():match.end() + 6].lstrip()
            prefix = next(
                (
                    qualifier
                    for qualifier in _NUMERIC_PREFIX_QUALIFIERS
                    if prefix_window.endswith(qualifier)
                ),
                "",
            )
            suffix = next(
                (
                    qualifier
                    for qualifier in _NUMERIC_SUFFIX_QUALIFIERS
                    if suffix_window.startswith(qualifier)
                ),
                "",
            )
            if prefix or suffix:
                phrases.append(f"{prefix} {match.group()} {suffix}".strip())
        return list(dict.fromkeys(phrases))

    def _required_numeric_expressions(
        self, state: AgentState, index: int
    ) -> List[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return []
        return list(dict.fromkeys(_NUMBER_PATTERN.findall(answers[index])))

    def _allowed_latin_tokens(self, state: AgentState, index: int) -> List[str]:
        source_text = "\n".join(
            [
                self._source_text(state, index),
                state.company or "",
                state.job_position or "",
            ]
        )
        return list(dict.fromkeys(_LATIN_TOKEN_PATTERN.findall(source_text)))

    def _unsupported_latin_tokens(
        self, revised_answer: str, state: AgentState, index: int
    ) -> set[str]:
        allowed = {value.lower() for value in self._allowed_latin_tokens(state, index)}
        generated = {value.lower() for value in _LATIN_TOKEN_PATTERN.findall(revised_answer)}
        return generated - allowed

    def _missing_latin_tokens(
        self, revised_answer: str, state: AgentState, index: int
    ) -> set[str]:
        source = {
            value.lower(): value for value in self._required_latin_tokens(state, index)
        }
        generated = {
            value.lower() for value in _LATIN_TOKEN_PATTERN.findall(revised_answer)
        }
        return {source[value] for value in source.keys() - generated}

    def _required_latin_tokens(self, state: AgentState, index: int) -> List[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return []
        return list(dict.fromkeys(_LATIN_TOKEN_PATTERN.findall(answers[index])))

    @staticmethod
    def _unsupported_claim_terms(
        revised_answer: str, state: AgentState, index: int
    ) -> set[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return {"입력 범위를 벗어난 문항"}
        original_answer = answers[index]
        return {
            term
            for term in _CLAIM_ESCALATION_TERMS
            if (
                term in revised_answer
                and term not in original_answer
                and not ReviserNode._is_grounded_claim_paraphrase(
                    term, original_answer, revised_answer
                )
            )
        }

    @staticmethod
    def _is_grounded_claim_paraphrase(
        term: str, original_answer: str, revised_answer: str
    ) -> bool:
        return (
            term == "운영"
            and "스터디 그룹" in original_answer
            and "조직" in original_answer
            and "스터디 그룹" in revised_answer
        )

    @staticmethod
    def _forbidden_claim_terms(state: AgentState, index: int) -> List[str]:
        answers = state.answer_list or []
        if index >= len(answers):
            return list(_CLAIM_ESCALATION_TERMS)
        original_answer = answers[index]
        return [
            term
            for term in _CLAIM_ESCALATION_TERMS
            if term not in original_answer
            and not (
                term == "운영"
                and "스터디 그룹" in original_answer
                and "조직" in original_answer
            )
        ]

    @staticmethod
    def _sentence_quality_problems(value: str) -> List[str]:
        normalized = " ".join(value.split())
        if not normalized or normalized[-1] not in ".!?":
            return ["best_reply의 마지막 문장을 완결된 문장부호로 끝내세요."]

        sentences = [
            sentence.strip()
            for sentence in _SENTENCE_SPLIT_PATTERN.split(normalized)
            if sentence.strip()
        ]
        fragments = []
        normalized_sentences = []
        for sentence in sentences:
            body = sentence.rstrip(".!?\"'”’)]} ")
            normalized_sentences.append(body.lower())
            if not re.search(r"(?:니다|요)$", body):
                fragments.append(sentence[:80])

        problems = []
        if fragments:
            problems.append(
                "모든 문장을 한국어 존댓말의 완결형으로 고치세요: "
                + " / ".join(fragments[:3])
            )
        duplicates = [
            sentence
            for sentence, count in Counter(normalized_sentences).items()
            if sentence and count > 1
        ]
        if duplicates:
            problems.append(
                "같은 문장을 반복하지 마세요: " + " / ".join(duplicates[:2])
            )
        return problems

    def _unsupported_foreign_characters(
        self, revised_answer: str, state: AgentState, index: int
    ) -> set[str]:
        source_characters = self._unexpected_script_characters(
            self._source_text(state, index)
        )
        generated_characters = self._unexpected_script_characters(revised_answer)
        return generated_characters - source_characters

    @staticmethod
    def _unexpected_script_characters(value: str) -> set[str]:
        unexpected = set()
        for character in value:
            codepoint = ord(character)
            expected_letter = (
                "A" <= character <= "Z"
                or "a" <= character <= "z"
                or 0x1100 <= codepoint <= 0x11FF
                or 0x3130 <= codepoint <= 0x318F
                or 0xAC00 <= codepoint <= 0xD7A3
            )
            if character == "\ufffd" or (
                unicodedata.category(character).startswith("L")
                and not expected_letter
            ):
                unexpected.add(character)
        return unexpected

    @staticmethod
    def _source_text(state: AgentState, index: int) -> str:
        questions = state.question_list or []
        answers = state.answer_list or []
        if index >= len(questions) or index >= len(answers):
            return ""
        return f"{questions[index]}\n{answers[index]}"

    def _minimum_reply_chars(self, state: Optional[AgentState], index: int) -> int:
        if state is None:
            return _DEFAULT_MIN_REPLY_CHARS
        answers = state.answer_list or []
        if index >= len(answers):
            return _DEFAULT_MIN_REPLY_CHARS
        original_length = len(answers[index].strip())
        if original_length == 0:
            return 1
        desired_minimum = min(
            120,
            max(_DEFAULT_MIN_REPLY_CHARS, round(original_length * 0.4)),
        )
        return min(original_length, desired_minimum)

    @staticmethod
    def _safe_fallback_candidate(state: AgentState, index: int) -> SingleRevisedAnswer:
        original_answer = (state.answer_list or [])[index].strip()
        if not original_answer:
            raise RuntimeError(
                f"{index + 1}번 문항의 원문 답변이 비어 있어 안전하게 보존할 수 없습니다."
            )
        return SingleRevisedAnswer(
            best_reply=original_answer,
            reply_reason=(
                "생성된 수정안에서 원문에 없는 표현이 감지되어, 검증되지 않은 내용을 "
                "추가하지 않고 원문의 사실을 그대로 보존했습니다."
            ),
            expectation=(
                "새로운 사실을 임의로 만들지 않아 답변의 사실성과 신뢰도를 유지할 수 있습니다."
            ),
        )

    @staticmethod
    def _bounded_candidate(
        candidate: Optional[SingleRevisedAnswer],
    ) -> Optional[Dict[str, str]]:
        if candidate is None:
            return None
        return {"best_reply": candidate.best_reply[:_MAX_PREVIOUS_CANDIDATE_CHARS]}

    @staticmethod
    def _normalize_number(value: str) -> str:
        return value.lower().replace(",", "").replace(" ", "")

    def decide_next_node(self, state: AgentState) -> str:
        return "END"

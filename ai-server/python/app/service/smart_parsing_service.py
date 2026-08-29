"""Port of ``pertineo.agent.service.SmartParsingService``."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import List, Optional

from app.config.smart_parsing_properties import SmartParsingProperties
from app.service.smart_parsing_client import SmartParsingClient
from app.service.smart_parsing_metrics_logger import SmartParsingMetricsLogger
from app.service.smart_parsing_models import ParseResult, SmartParsingMetric, SmartParsingResponse

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """하나의 텍스트로 이루어진 사용자의 지원서를 보고, 질문과 답변으로 구분하여 파싱하라.

규칙:
- 출력은 질문-답변 쌍만 명확하게 구분해 반환하라. 형식이 별도로 지정되지 않았다면 각 항목에서 질문과 답변이 무엇인지 일관되게 식별할 수 있도록 간결하게 정리하라.
- question_list와 answer_list의 길이는 반드시 같아야 한다.
- 최종 답변 전, 각 문장이 질문인지 답변인지 일관되게 분류되었는지 확인하라.
- 문맥이 불충분하거나 구분이 모호한 부분은 추측하지 말고, 모호하다고 명시하라
- 질문을 찾을 수 없으면 question_list와 answer_list를 빈 배열로 반환하라.
"""

_QUESTION_PREFIX = re.compile(r"^(?:Q|Question|질문|문항)\s*\d*\s*[:.)\-]\s*(.+)$", re.IGNORECASE)
_ANSWER_PREFIX = re.compile(r"^(?:A|Answer|답변|대답)\s*\d*\s*[:.)\-]\s*(.+)$", re.IGNORECASE)


class SmartParsingCallException(Exception):
    def __init__(self, model: str, latency_ms: int, cause: Exception) -> None:
        super().__init__(f"Smart parsing model call failed. model={model}, latencyMs={latency_ms}")
        self.model = model
        self.latency_ms = latency_ms
        self.cause = cause


@dataclass
class _TimedSmartParsingResponse:
    response: SmartParsingResponse
    latency_ms: int


class SmartParsingService:
    def __init__(
        self,
        client: SmartParsingClient,
        properties: SmartParsingProperties,
        metrics_logger: SmartParsingMetricsLogger,
    ) -> None:
        self._client = client
        self._properties = properties
        self._metrics_logger = metrics_logger

    async def parse_resume(self, input_data: Optional[str]) -> ParseResult:
        rule_result = self._parse_by_rule(input_data)
        input_length = self._input_length(input_data)

        if rule_result is not None:
            logger.info(
                "SmartParsingService rule-based parsing succeeded. questionCount=%s",
                len(rule_result.question_list),
            )
            self._log_rule_metric(input_length, rule_result)
            return rule_result

        primary_model = self._select_primary_model(input_length)
        logger.info(
            "SmartParsingService rule-based parsing did not match; using primary model=%s. "
            "inputChars=%s, thresholdChars=%s",
            primary_model,
            input_length,
            self._properties.fallback_max_chars,
        )
        return await self._parse_with_fallback(input_data, input_length, primary_model)

    async def _parse_with_fallback(self, input_data: str, input_length: int, primary_model: str) -> ParseResult:
        try:
            timed = await self._call_model(input_data, primary_model)
            result = self._require_usable_result(timed.response.result)
            logger.info(
                "SmartParsingService primary model parsing succeeded. model=%s, questionCount=%s",
                primary_model,
                len(result.question_list),
            )
            self._log_metric("primary", timed, False, input_length, True, None, result)
            return result
        except Exception as primary_failure:  # noqa: BLE001
            primary_error = self._unwrap_model_call_failure(primary_failure)
            if not self._should_use_fallback(input_length, primary_model):
                logger.warning(
                    "SmartParsingService primary model parsing failed; fallback skipped. "
                    "primaryModel=%s, inputChars=%s, fallbackEnabled=%s, thresholdChars=%s, reason=%s",
                    primary_model,
                    input_length,
                    self._properties.fallback_enabled,
                    self._properties.fallback_max_chars,
                    primary_error,
                )
                self._log_failure_metric("fail_fast", primary_model, False, input_length, primary_failure)
                raise primary_error

            logger.warning(
                "SmartParsingService primary model parsing failed; using fallback model=%s. "
                "primaryModel=%s, inputChars=%s, thresholdChars=%s, reason=%s",
                self._properties.fallback_model,
                primary_model,
                input_length,
                self._properties.fallback_max_chars,
                primary_error,
            )
            self._log_failure_metric("primary", primary_model, False, input_length, primary_failure)

            try:
                timed = await self._call_model(input_data, self._properties.fallback_model)
                result = self._require_usable_result(timed.response.result)
                logger.info(
                    "SmartParsingService fallback model parsing succeeded. model=%s, questionCount=%s",
                    self._properties.fallback_model,
                    len(result.question_list),
                )
                self._log_metric("fallback", timed, True, input_length, True, None, result)
                return result
            except Exception as fallback_failure:  # noqa: BLE001
                fallback_error = self._unwrap_model_call_failure(fallback_failure)
                logger.warning(
                    "SmartParsingService fallback model parsing failed. model=%s, reason=%s",
                    self._properties.fallback_model,
                    fallback_error,
                )
                self._log_failure_metric("fallback", self._properties.fallback_model, True, input_length, fallback_failure)
                raise fallback_error from primary_error

    async def _call_model(self, input_data: str, model: str) -> _TimedSmartParsingResponse:
        start = time.monotonic()
        try:
            response = await self._client.parse(_SYSTEM_PROMPT, input_data, model)
            latency_ms = int((time.monotonic() - start) * 1000)
            return _TimedSmartParsingResponse(response, latency_ms)
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.monotonic() - start) * 1000)
            raise SmartParsingCallException(model, latency_ms, exc) from exc

    def _log_rule_metric(self, input_length: int, result: ParseResult) -> None:
        self._metrics_logger.log_metric(
            SmartParsingMetric(
                selected_path="rule",
                model=None,
                fallback_used=False,
                input_chars=input_length,
                latency_ms=0,
                success=True,
                question_count=len(result.question_list),
                answer_count=len(result.answer_list),
            )
        )

    def _log_metric(
        self,
        selected_path: str,
        timed: _TimedSmartParsingResponse,
        fallback_used: bool,
        input_length: int,
        success: bool,
        error: Optional[Exception],
        result: Optional[ParseResult],
    ) -> None:
        response = timed.response
        cost = self._metrics_logger.estimate_cost_usd(response.model, response.input_tokens, response.output_tokens)
        self._metrics_logger.log_metric(
            SmartParsingMetric(
                selected_path=selected_path,
                model=response.model,
                fallback_used=fallback_used,
                input_chars=input_length,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
                estimated_cost_usd=cost,
                latency_ms=timed.latency_ms,
                success=success,
                error_type=type(error).__name__ if error else None,
                error_message=str(error) if error else None,
                question_count=len(result.question_list) if result else None,
                answer_count=len(result.answer_list) if result else None,
            )
        )

    def _log_failure_metric(
        self, selected_path: str, model: str, fallback_used: bool, input_length: int, error: Exception
    ) -> None:
        reported_error = self._unwrap_model_call_failure(error)
        self._metrics_logger.log_metric(
            SmartParsingMetric(
                selected_path=selected_path,
                model=model,
                fallback_used=fallback_used,
                input_chars=input_length,
                latency_ms=self._model_call_latency_ms(error),
                success=False,
                error_type=type(reported_error).__name__,
                error_message=str(reported_error),
            )
        )

    def _unwrap_model_call_failure(self, error: Exception) -> Exception:
        if isinstance(error, SmartParsingCallException) and isinstance(error.cause, Exception):
            return error.cause
        return error

    def _model_call_latency_ms(self, error: Exception) -> int:
        if isinstance(error, SmartParsingCallException):
            return error.latency_ms
        return 0

    def _select_primary_model(self, input_length: int) -> str:
        if input_length > self._properties.fallback_max_chars:
            return self._properties.fallback_model
        return self._properties.primary_model

    def _should_use_fallback(self, input_length: int, primary_model: str) -> bool:
        return (
            self._properties.fallback_enabled
            and input_length <= self._properties.fallback_max_chars
            and primary_model != self._properties.fallback_model
        )

    def _input_length(self, input_data: Optional[str]) -> int:
        return 0 if input_data is None else len(input_data)

    def _parse_by_rule(self, input_data: Optional[str]) -> Optional[ParseResult]:
        if input_data is None or not input_data.strip():
            return self._empty_result()

        questions: List[str] = []
        answers: List[str] = []
        current_question: Optional[str] = None
        current_answer_lines: Optional[List[str]] = None
        saw_question_marker = False
        saw_answer_marker = False

        for raw_line in re.split(r"\r\n|\r|\n", input_data):
            line = raw_line.strip()
            if not line:
                continue

            question_match = _QUESTION_PREFIX.match(line)
            if question_match:
                saw_question_marker = True
                if current_question is not None:
                    if current_answer_lines is None or not "\n".join(current_answer_lines).strip():
                        return None
                    questions.append(current_question)
                    answers.append("\n".join(current_answer_lines).strip())
                current_question = question_match.group(1).strip()
                current_answer_lines = None
                if not current_question:
                    return None
                continue

            answer_match = _ANSWER_PREFIX.match(line)
            if answer_match:
                saw_answer_marker = True
                if current_question is None:
                    continue
                current_answer_lines = [answer_match.group(1).strip()]
                continue

            if current_answer_lines is not None:
                current_answer_lines.append(line)

        if current_question is not None:
            if current_answer_lines is None or not "\n".join(current_answer_lines).strip():
                return None
            questions.append(current_question)
            answers.append("\n".join(current_answer_lines).strip())

        if saw_question_marker and len(questions) == len(answers) and questions:
            return ParseResult(question_list=list(questions), answer_list=list(answers))
        if not saw_question_marker and saw_answer_marker:
            return self._empty_result()
        return None

    def _require_usable_result(self, result: Optional[ParseResult]) -> ParseResult:
        if result is None or result.question_list is None or result.answer_list is None:
            raise ValueError("Smart parsing result is missing required lists")
        if len(result.question_list) != len(result.answer_list):
            raise ValueError("Smart parsing result has mismatched question/answer list sizes")
        for question, answer in zip(result.question_list, result.answer_list):
            if question is None or answer is None:
                raise ValueError("Smart parsing result contains null question/answer item")
            if not question.strip() or not answer.strip():
                raise ValueError("Smart parsing result contains blank question/answer item")
        return ParseResult(question_list=list(result.question_list), answer_list=list(result.answer_list))

    def _empty_result(self) -> ParseResult:
        return ParseResult(question_list=[], answer_list=[])

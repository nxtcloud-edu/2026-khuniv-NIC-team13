"""Port of ``pertineo.agent.workflow.nodes.SchemerNode``."""
from __future__ import annotations

import logging

from app.workflow.event import WorkflowEventSink
from app.workflow.errors import InvalidSubmissionError
from app.workflow.nodes.base import AgentNode
from app.workflow.nodes.schemer.client import SchemerClient
from app.workflow.nodes.schemer.models import SchemerResult
from app.workflow.state import AgentState

logger = logging.getLogger(__name__)


class SchemerNode(AgentNode):
    def __init__(self, schemer_client: SchemerClient) -> None:
        self._schemer_client = schemer_client

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        await events.running("schemer_start", "자기소개서 유효성 검사를 시작합니다.")
        result = await self._validate_with_self_consistency(events, state)

        await events.running("schemer_result", result.to_validation_event())
        await events.running("schemer_result_track", result.track.persistence_value())

        if not result.question_valid or not result.answer_valid:
            state.schema_result = False
            logger.warning("검증 실패 사유: %s", result.validation_reason)
            await events.failed("schemer_failed", f"지원서 내용이 부적절합니다: {result.validation_reason}")
            raise InvalidSubmissionError(f"지원서 내용이 부적절합니다: {result.validation_reason}")

        state.schema_result = True
        state.track = result.track.persistence_value()

        await events.running("schemer_end", "자기소개서 유효성 검사를 완료했습니다.")
        return state

    async def _validate_with_self_consistency(
        self,
        events: WorkflowEventSink,
        state: AgentState,
    ) -> SchemerResult:
        """Confirm a rejection once with full context and reasoning enabled."""
        result = await self._schemer_client.validate(state)
        if result.question_valid and result.answer_valid:
            return result

        logger.warning(
            "Schemer flagged invalid input, re-checking once before failing the workflow: %s",
            result.validation_reason,
        )
        await events.running("schemer_recheck", "부적절 판정의 오탐 여부를 다시 확인합니다.")
        retry_result = await self._schemer_client.validate(state, result.validation_reason)
        if retry_result.question_valid and retry_result.answer_valid:
            logger.info("Schemer re-check passed — treating the first rejection as a false positive.")
        return retry_result

    def decide_next_node(self, state: AgentState) -> str:
        if state.schema_result:
            return "WEBSEARCH"
        return "END"

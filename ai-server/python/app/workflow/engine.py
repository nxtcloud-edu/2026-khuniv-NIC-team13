"""Port of ``pertineo.agent.workflow.StateGraphEngine``."""
from __future__ import annotations

import logging
from typing import Dict

from app.trace.langsmith_tracer import LangSmithTracer
from app.workflow.errors import InvalidSubmissionError
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.base import AgentNode
from app.workflow.state import AgentState

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1


class StateGraphEngine:
    def __init__(
        self,
        schemer_node: AgentNode,
        web_search_node: AgentNode,
        evaluate_node: AgentNode,
        reviser_node: AgentNode,
        data_node: AgentNode,
        tracer: LangSmithTracer,
    ) -> None:
        self._nodes: Dict[str, AgentNode] = {
            "SCHEMER": schemer_node,
            "WEBSEARCH": web_search_node,
            "EVALUATE": evaluate_node,
            "REVISE": reviser_node,
            "DATA": data_node,
        }
        self._tracer = tracer

    async def run_workflow(self, events: WorkflowEventSink, state: AgentState) -> None:
        """Runs the full node graph to completion, streaming events as it
        goes. Intended to be scheduled as a background asyncio task from the
        controller — the async equivalent of Java's ``@Async`` method."""
        trace_id = await self._tracer.start_trace(state.user_id or "", "chain", state)
        current_node_name = "SCHEMER"
        current_node = self._nodes[current_node_name]
        try:
            while current_node_name != "END":
                retry_count = 0
                while True:
                    state_before_attempt = state.model_copy(deep=True)
                    span_id = await self._tracer.start_span(
                        current_node_name, "chain", state, trace_id, trace_id
                    )

                    try:
                        await current_node.execute(events, state)
                        next_node_name = current_node.decide_next_node(state)
                        await self._tracer.end_trace(span_id, state)
                        if retry_count:
                            logger.info(
                                "Workflow node retry recovered: node=%s successful_attempt=%s/%s",
                                current_node_name,
                                retry_count + 1,
                                _MAX_RETRIES + 1,
                            )
                        break
                    except InvalidSubmissionError as validation_exc:
                        await self._tracer.error_trace(span_id, str(validation_exc))
                        raise
                    except Exception as node_exc:  # noqa: BLE001
                        await self._tracer.error_trace(span_id, str(node_exc))
                        self._restore_state(state, state_before_attempt)
                        attempt_number = retry_count + 1
                        will_retry = attempt_number <= _MAX_RETRIES
                        logger.warning(
                            "Workflow node attempt failed: node=%s attempt=%s/%s "
                            "will_retry=%s error_type=%s error=%s",
                            current_node_name,
                            attempt_number,
                            _MAX_RETRIES + 1,
                            will_retry,
                            type(node_exc).__name__,
                            str(node_exc).splitlines()[0][:200],
                        )
                        retry_count += 1
                        if retry_count > _MAX_RETRIES:
                            raise
                        await events.running(
                            "workflow_retrying",
                            f"{current_node_name} 단계 오류로 재시도합니다. "
                            f"재시도 {retry_count}/{_MAX_RETRIES}",
                        )

                current_node_name = next_node_name

                if current_node_name == "END":
                    break
                if current_node_name not in self._nodes:
                    raise RuntimeError(f"알 수 없는 노드입니다: {current_node_name}")
                current_node = self._nodes[current_node_name]
            await events.completed("workflow_completed", "워크플로우를 완료했습니다.")
        except InvalidSubmissionError as exc:
            logger.warning("유효하지 않은 지원서로 워크플로우 종료: %s", exc)
            await self._tracer.error_trace(trace_id, str(exc))
            await events.failed("workflow_error", str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("워크플로우 실행 중 에러 발생", exc_info=exc)
            await self._tracer.error_trace(trace_id, str(exc))
            error_message = (
                f"{current_node_name} 단계에서 복구할 수 없는 오류가 발생했습니다. "
                "잠시 후 다시 시도해주세요."
            )
            await events.failed("workflow_error", error_message)
        finally:
            await self._tracer.end_trace(trace_id, state)

    @staticmethod
    def _restore_state(state: AgentState, snapshot: AgentState) -> None:
        for field_name in type(state).model_fields:
            setattr(state, field_name, getattr(snapshot, field_name))

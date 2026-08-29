import pytest

from app.workflow.event import WorkflowEvent, WorkflowEventSink
from app.workflow.errors import InvalidSubmissionError
from app.workflow.nodes.schemer.client import SchemerClient
from app.workflow.nodes.schemer.models import SchemerResult
from app.workflow.nodes.schemer_node import SchemerNode
from app.workflow.state import AgentState
from app.workflow.track import Track


class RecordingWorkflowEventSink(WorkflowEventSink):
    def __init__(self):
        self._events = []

    async def send(self, event: WorkflowEvent) -> None:
        self._events.append(event)

    @property
    def events(self):
        return self._events

    @property
    def types(self):
        return [e.type for e in self._events]


class FakeSchemerClient(SchemerClient):
    def __init__(self, *results: SchemerResult):
        self._results = results
        self.calls = []

    async def validate(self, state: AgentState, previous_rejection_reason=None) -> SchemerResult:
        self.calls.append(previous_rejection_reason)
        return self._results[min(len(self.calls) - 1, len(self._results) - 1)]


@pytest.mark.asyncio
async def test_execute_sets_normalized_track_from_single_structured_result():
    client = FakeSchemerClient(SchemerResult(
        question_valid=True, answer_valid=True, validation_reason="정상", track=Track.ENGINEERING
    ))
    node = SchemerNode(client)
    state = AgentState()
    events = RecordingWorkflowEventSink()

    result = await node.execute(events, state)

    assert result.schema_result is True
    assert result.track == "engineering"
    assert client.calls == [None]
    assert events.types == [
        "schemer_start",
        "schemer_result",
        "schemer_result_track",
        "schemer_end",
    ]


@pytest.mark.asyncio
async def test_execute_rejects_invalid_question_or_answer():
    client = FakeSchemerClient(SchemerResult(
        question_valid=False, answer_valid=True, validation_reason="질문이 부적절합니다", track=Track.BUSINESS
    ))
    node = SchemerNode(client)
    events = RecordingWorkflowEventSink()

    state = AgentState()
    with pytest.raises(InvalidSubmissionError) as exc_info:
        await node.execute(events, state)

    assert str(exc_info.value) == "지원서 내용이 부적절합니다: 질문이 부적절합니다"
    assert client.calls == [None, "질문이 부적절합니다"]
    assert state.schema_result is False
    assert "schemer_recheck" in events.types
    failed_event = events.events[-1]
    assert failed_event.type == "schemer_failed"
    from app.workflow.event import WorkflowEventStatus

    assert failed_event.status == WorkflowEventStatus.FAILED


@pytest.mark.asyncio
async def test_execute_accepts_reasoning_confirmation_after_initial_false_rejection():
    client = FakeSchemerClient(
        SchemerResult(
            question_valid=True,
            answer_valid=False,
            validation_reason="문장이 불완전합니다",
            track=Track.ENGINEERING,
        ),
        SchemerResult(
            question_valid=True,
            answer_valid=True,
            validation_reason="전체 문장을 확인한 결과 정상입니다",
            track=Track.ENGINEERING,
        ),
    )
    node = SchemerNode(client)
    state = AgentState()
    events = RecordingWorkflowEventSink()

    await node.execute(events, state)

    assert client.calls == [None, "문장이 불완전합니다"]
    assert state.schema_result is True
    assert state.track == "engineering"
    assert events.types[-1] == "schemer_end"

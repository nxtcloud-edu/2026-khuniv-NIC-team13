from pydantic import BaseModel
import pytest

from app.workflow.engine import StateGraphEngine
from app.workflow.errors import InvalidSubmissionError
from app.workflow.event import WorkflowEvent, WorkflowEventSink, WorkflowEventStatus
from app.workflow.state import AgentState


class RequiredInt(BaseModel):
    value: int


class RecordingSink(WorkflowEventSink):
    def __init__(self):
        self.events = []

    async def send(self, event: WorkflowEvent) -> None:
        self.events.append(event)


class NoOpTracer:
    async def start_trace(self, *args):
        return "root"

    async def start_span(self, *args):
        return "span"

    async def end_trace(self, *args):
        return None

    async def error_trace(self, *args):
        return None


class FlakyNode:
    def __init__(self, failures, next_node="END"):
        self.failures = failures
        self.next_node = next_node
        self.calls = 0

    async def execute(self, events, state):
        self.calls += 1
        if self.calls <= self.failures:
            RequiredInt.model_validate({"value": "invalid"})
        return state

    def decide_next_node(self, state):
        return self.next_node


class InvalidNode(FlakyNode):
    async def execute(self, events, state):
        self.calls += 1
        raise InvalidSubmissionError("확정된 입력 오류")


class MutatingFlakyNode(FlakyNode):
    async def execute(self, events, state):
        self.calls += 1
        state.context_web = f"실패한 시도 {self.calls}의 부분 상태"
        if self.calls <= self.failures:
            raise RuntimeError("일시 오류")
        state.context_web = "완료 상태"
        return state


@pytest.mark.asyncio
async def test_pydantic_validation_error_is_retried_and_not_emitted_as_failed(caplog):
    node = FlakyNode(failures=1)
    sink = RecordingSink()
    engine = StateGraphEngine(node, node, node, node, node, NoOpTracer())
    caplog.set_level("INFO", logger="app.workflow.engine")

    await engine.run_workflow(sink, AgentState())

    assert node.calls == 2
    retry_event = next(event for event in sink.events if event.type == "workflow_retrying")
    assert retry_event.status == WorkflowEventStatus.RUNNING
    assert sink.events[-1].type == "workflow_completed"
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "node=SCHEMER attempt=1/2 will_retry=True error_type=ValidationError"
        in message
        for message in messages
    )
    assert any(
        "node=SCHEMER successful_attempt=2/2" in message
        for message in messages
    )


@pytest.mark.asyncio
async def test_only_confirmed_invalid_submission_skips_retry():
    node = InvalidNode(failures=0)
    sink = RecordingSink()
    engine = StateGraphEngine(node, node, node, node, node, NoOpTracer())

    await engine.run_workflow(sink, AgentState())

    assert node.calls == 1
    assert all(event.type != "workflow_retrying" for event in sink.events)
    assert sink.events[-1].type == "workflow_error"
    assert sink.events[-1].status == WorkflowEventStatus.FAILED


@pytest.mark.asyncio
async def test_retry_budget_resets_for_each_node():
    schemer = FlakyNode(failures=1, next_node="WEBSEARCH")
    websearch = FlakyNode(failures=1, next_node="END")
    unused = FlakyNode(failures=0)
    sink = RecordingSink()
    engine = StateGraphEngine(schemer, websearch, unused, unused, unused, NoOpTracer())

    await engine.run_workflow(sink, AgentState())

    assert schemer.calls == 2
    assert websearch.calls == 2
    assert sink.events[-1].type == "workflow_completed"


@pytest.mark.asyncio
async def test_failed_attempt_state_is_restored_before_retry():
    node = MutatingFlakyNode(failures=1)
    sink = RecordingSink()
    engine = StateGraphEngine(node, node, node, node, node, NoOpTracer())
    state = AgentState(context_web="시작 상태")

    await engine.run_workflow(sink, state)

    assert node.calls == 2
    assert state.context_web == "완료 상태"
    retry_event = next(event for event in sink.events if event.type == "workflow_retrying")
    assert retry_event.data.endswith("재시도 1/1")

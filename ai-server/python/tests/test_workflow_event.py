import pytest

from app.workflow.event import WorkflowEvent, WorkflowEventStatus, WorkflowEventSink


class RecordingWorkflowEventSink(WorkflowEventSink):
    def __init__(self):
        self._events = []

    async def send(self, event: WorkflowEvent) -> None:
        self._events.append(event)

    @property
    def events(self):
        return self._events


@pytest.mark.asyncio
async def test_helper_methods_create_typed_workflow_events():
    sink = RecordingWorkflowEventSink()

    await sink.running("node_start", "시작")
    await sink.completed("node_end", "끝")
    await sink.failed("node_error", "실패")

    assert sink.events == [
        WorkflowEvent("node_start", WorkflowEventStatus.RUNNING, "시작"),
        WorkflowEvent("node_end", WorkflowEventStatus.COMPLETED, "끝"),
        WorkflowEvent("node_error", WorkflowEventStatus.FAILED, "실패"),
    ]

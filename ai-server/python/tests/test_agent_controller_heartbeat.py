import asyncio

import pytest

from app.controllers import agent_controller


@pytest.mark.asyncio
async def test_sse_stream_emits_heartbeat_while_workflow_is_quiet(monkeypatch):
    monkeypatch.setattr(agent_controller, "_HEARTBEAT_INTERVAL_SECONDS", 0.01)
    queue = asyncio.Queue()
    workflow_task = asyncio.create_task(asyncio.Event().wait())
    stream = agent_controller._stream_queue_with_heartbeat(
        queue, workflow_task, "synthetic-user"
    )

    heartbeat = await anext(stream)
    await stream.aclose()
    await asyncio.sleep(0)

    assert heartbeat == ": keep-alive\n\n"
    assert workflow_task.cancelled()


@pytest.mark.asyncio
async def test_sse_stream_forwards_event_and_stops_on_sentinel():
    queue = asyncio.Queue()
    await queue.put("data: test\n\n")
    await queue.put(None)

    async def completed_workflow():
        return None

    workflow_task = asyncio.create_task(completed_workflow())
    stream = agent_controller._stream_queue_with_heartbeat(
        queue, workflow_task, "synthetic-user"
    )

    assert await anext(stream) == "data: test\n\n"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)

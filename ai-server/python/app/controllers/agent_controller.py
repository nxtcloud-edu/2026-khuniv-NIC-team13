"""Port of ``pertineo.agent.controller.AgentController``."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.mappers.analyze_request_mapper import to_agent_state
from app.schemas.analyze_request import AnalyzeRequestDto
from app.workflow.event import SseWorkflowEventSink

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# 10 * 1000 * 60 ms in the Java version — 10 minutes.
_DEFAULT_TIMEOUT_SECONDS = 10 * 60
_HEARTBEAT_INTERVAL_SECONDS = 15


async def _stream_queue_with_heartbeat(
    queue: "asyncio.Queue[Optional[str]]",
    workflow_task: "asyncio.Task[None]",
    user_id: Optional[str],
) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    inactivity_deadline = loop.time() + _DEFAULT_TIMEOUT_SECONDS
    try:
        while True:
            remaining = inactivity_deadline - loop.time()
            if remaining <= 0:
                logger.warning("SSE stream timed out for userId=%s", user_id)
                break
            try:
                item = await asyncio.wait_for(
                    queue.get(),
                    timeout=min(_HEARTBEAT_INTERVAL_SECONDS, remaining),
                )
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue

            if item is None:
                break
            inactivity_deadline = loop.time() + _DEFAULT_TIMEOUT_SECONDS
            yield item
    finally:
        if not workflow_task.done():
            workflow_task.cancel()


@router.post("/analyze/stream")
async def start_analysis_and_subscribe(payload: AnalyzeRequestDto, request: Request) -> StreamingResponse:
    container = request.app.state.container
    state = to_agent_state(payload)

    queue: "asyncio.Queue[Optional[str]]" = asyncio.Queue()
    sink = SseWorkflowEventSink(queue)

    async def run_workflow_and_close() -> None:
        try:
            await container.state_graph_engine.run_workflow(sink, state)
        finally:
            await queue.put(None)  # sentinel: signals the generator to stop

    workflow_task = asyncio.create_task(run_workflow_and_close())

    return StreamingResponse(
        _stream_queue_with_heartbeat(queue, workflow_task, state.user_id),
        media_type="text/event-stream",
    )

"""Port of ``pertineo.agent.workflow.event.WorkflowEvent`` /
``WorkflowEventSink`` / ``SseWorkflowEventSink``."""
from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from app.util.json_utils import dumps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class WorkflowEventStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class WorkflowEvent(Generic[T]):
    type: str
    status: WorkflowEventStatus
    data: T

    @staticmethod
    def running(type_: str, data: T) -> "WorkflowEvent[T]":
        return WorkflowEvent(type_, WorkflowEventStatus.RUNNING, data)

    @staticmethod
    def completed(type_: str, data: T) -> "WorkflowEvent[T]":
        return WorkflowEvent(type_, WorkflowEventStatus.COMPLETED, data)

    @staticmethod
    def failed(type_: str, data: T) -> "WorkflowEvent[T]":
        return WorkflowEvent(type_, WorkflowEventStatus.FAILED, data)


class WorkflowEventSink(ABC):
    @abstractmethod
    async def send(self, event: WorkflowEvent) -> None: ...

    async def running(self, type_: str, data: Any) -> None:
        await self.send(WorkflowEvent.running(type_, data))

    async def completed(self, type_: str, data: Any) -> None:
        await self.send(WorkflowEvent.completed(type_, data))

    async def failed(self, type_: str, data: Any) -> None:
        await self.send(WorkflowEvent.failed(type_, data))


class SseWorkflowEventSink(WorkflowEventSink):
    """Pushes SSE-formatted payloads onto an asyncio.Queue that the FastAPI
    ``StreamingResponse`` generator drains, in place of Java's
    ``SseEmitter``."""

    def __init__(self, queue: "asyncio.Queue[Optional[str]]") -> None:
        self._queue = queue

    async def send(self, event: WorkflowEvent) -> None:
        if self._queue is None:
            return
        try:
            event_id = str(uuid.uuid4())
            body = dumps(
                {
                    "id": event_id,
                    "type": event.type,
                    "status": event.status.value,
                    "data": event.data,
                }
            )
            payload = f"id: {event_id}\ndata: {body}\n\n"
            await self._queue.put(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SSE 이벤트 전송 실패: %s", exc)

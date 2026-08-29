"""Port of ``pertineo.agent.controller.dto.SseEvent``."""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SseStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SseEvent(BaseModel, Generic[T]):
    id: str
    type: str
    status: SseStatus
    data: T

    @staticmethod
    def of(type_: str, status: SseStatus, data: T) -> "SseEvent[T]":
        return SseEvent(id=str(uuid.uuid4()), type=type_, status=status, data=data)

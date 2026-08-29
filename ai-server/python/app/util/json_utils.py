"""JSON helpers used to serialize arbitrary node payloads onto the SSE wire.

Node outputs can be pydantic models, dataclasses, enums, plain dicts/lists or
scalars (mirroring Jackson's ability to serialize any POJO in the Java
version). ``jsonable`` normalizes all of those into plain JSON-safe values.
"""
from __future__ import annotations

import dataclasses
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel


def jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, BaseModel):
        return jsonable(obj.model_dump(by_alias=True, mode="json"))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    # Fallback: best-effort string representation, matching Jackson's
    # behaviour of failing loudly being undesirable for SSE delivery.
    return str(obj)


def dumps(obj: Any) -> str:
    return json.dumps(jsonable(obj), ensure_ascii=False)

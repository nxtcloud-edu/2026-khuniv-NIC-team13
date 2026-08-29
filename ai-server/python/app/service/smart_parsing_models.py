"""Port of the small DTOs around smart parsing:
``SmartParsingResponse``, ``SmartParsingMetric``, and
``SmartParsingService.ParseResult``."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class ParseResult(BaseModel):
    question_list: List[str]
    answer_list: List[str]


class SmartParsingResponse(BaseModel):
    result: ParseResult
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    native_usage: Optional[Any] = None


class SmartParsingMetric(BaseModel):
    selected_path: Optional[str] = None
    model: Optional[str] = None
    fallback_used: bool = False
    input_chars: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[str] = None
    latency_ms: int = 0
    success: bool = False
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    question_count: Optional[int] = None
    answer_count: Optional[int] = None

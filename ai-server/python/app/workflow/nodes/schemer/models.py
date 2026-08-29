"""Port of ``pertineo.agent.workflow.nodes.schemer.SchemerResult``."""
from __future__ import annotations

from pydantic import BaseModel

from app.workflow.track import Track


class SchemerValidationEvent(BaseModel):
    is_question_valid: bool
    is_answer_valid: bool
    validation_reason: str


class SchemerResult(BaseModel):
    question_valid: bool
    answer_valid: bool
    validation_reason: str
    track: Track

    model_config = {"arbitrary_types_allowed": True}

    def to_validation_event(self) -> SchemerValidationEvent:
        return SchemerValidationEvent(
            is_question_valid=self.question_valid,
            is_answer_valid=self.answer_valid,
            validation_reason=self.validation_reason,
        )

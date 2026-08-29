"""Port of ``SchemerClient`` / ``SpringAiSchemerClient``."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config.resources import read_json
from app.service.openai_chat_client import (
    OPENAI_FAST,
    OPENAI_REASONING,
    create_openai_client,
    parse_structured,
)
from app.service.structured_output import json_schema_format_instructions
from app.util.template import render
from app.workflow.nodes.schemer.models import SchemerResult
from app.workflow.state import AgentState
from app.workflow.track import Track

logger = logging.getLogger(__name__)

_TRACK_CLASSIFICATION_INSTRUCTION = """

Track classification:
- Return `track` as `business` for 경영·영업·마케팅 계열.
- Return `track` as `engineering` for 이공계·연구개발·생산 계열.
- You must choose exactly one of: `business`, `engineering`.
"""


class _SchemerStructuredOutput(BaseModel):
    is_question_valid: bool
    is_answer_valid: bool
    validation_reason: str
    track: Track


class SchemerClient(ABC):
    @abstractmethod
    async def validate(
        self,
        state: AgentState,
        previous_rejection_reason: Optional[str] = None,
    ) -> SchemerResult: ...


class OpenAiSchemerClient(SchemerClient):
    def __init__(self, client: Optional[AsyncOpenAI] = None) -> None:
        self._client = client or create_openai_client()

    async def validate(
        self,
        state: AgentState,
        previous_rejection_reason: Optional[str] = None,
    ) -> SchemerResult:
        prompts = read_json("prompts", "schemer.json")["prompts"]
        system_template = prompts["system"] + _TRACK_CLASSIFICATION_INSTRUCTION
        user_template = prompts["user"]

        input_data_map = {
            "question_list": state.question_list,
            "answer_list": state.answer_list,
            "applying_to": state.company,
            "applying_as": state.job_position,
        }
        if previous_rejection_reason is not None:
            input_data_map["previous_rejection_reason"] = previous_rejection_reason
        applicant_input_data = json.dumps(input_data_map, ensure_ascii=False)
        logger.debug(
            "Schemer input prepared: question_count=%s answer_count=%s input_chars=%s confirmation=%s",
            len(state.question_list or []),
            len(state.answer_list or []),
            len(applicant_input_data),
            previous_rejection_reason is not None,
        )

        system_prompt = render(
            system_template, format=json_schema_format_instructions(_SchemerStructuredOutput)
        )
        user_prompt = render(user_template, applicant_input_data=applicant_input_data)

        if previous_rejection_reason is not None:
            system_prompt += (
                "\n\nThis is an independent confirmation review of a prior rejection. "
                "Read every original question and answer in full. Do not trust a quoted fragment "
                "or the prior reason unless the complete input supports it. Prefer valid when the "
                "content is understandable and evaluable."
            )

        output = await parse_structured(
            self._client,
            system_prompt,
            user_prompt,
            _SchemerStructuredOutput,
            options=OPENAI_REASONING if previous_rejection_reason is not None else OPENAI_FAST,
        )

        logger.info(
            "Schemer validation result: is_question_valid=%s is_answer_valid=%s track=%s reason=%s",
            output.is_question_valid,
            output.is_answer_valid,
            output.track,
            output.validation_reason,
        )

        return SchemerResult(
            question_valid=output.is_question_valid,
            answer_valid=output.is_answer_valid,
            validation_reason=output.validation_reason,
            track=output.track,
        )

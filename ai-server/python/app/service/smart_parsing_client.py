"""Port of ``SmartParsingClient`` / ``SpringAiSmartParsingClient``."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI

from app.service.openai_chat_client import create_openai_client
from app.service.smart_parsing_models import ParseResult, SmartParsingResponse


class SmartParsingClient(ABC):
    @abstractmethod
    async def parse(self, system_prompt: str, input_data: str, model: str) -> SmartParsingResponse: ...


class OpenAiSmartParsingClient(SmartParsingClient):
    """OpenAI Responses API structured-output client for smart parsing."""

    def __init__(self, client: Optional[AsyncOpenAI] = None) -> None:
        self._client = client or create_openai_client()

    async def parse(self, system_prompt: str, input_data: str, model: str) -> SmartParsingResponse:
        response = await self._client.responses.parse(
            model=model,
            instructions=system_prompt,
            input=input_data,
            text_format=ParseResult,
            max_output_tokens=4096,
            reasoning={"effort": "low"},
            store=False,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Smart parsing structured output was empty")
        usage = response.usage

        return SmartParsingResponse(
            result=parsed,
            model=model,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            native_usage=usage.model_dump() if usage else None,
        )

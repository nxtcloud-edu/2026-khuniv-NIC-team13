from types import SimpleNamespace

import pytest

from app.service.smart_parsing_client import OpenAiSmartParsingClient
from app.service.smart_parsing_models import ParseResult


class FakeResponses:
    def __init__(self, parsed=None):
        self.kwargs = None
        self._parsed = parsed

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        usage = SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            model_dump=lambda: {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
        )
        return SimpleNamespace(output_parsed=self._parsed, usage=usage)


@pytest.mark.asyncio
async def test_smart_parsing_uses_openai_responses_api():
    responses = FakeResponses(
        ParseResult(question_list=["질문"], answer_list=["답변"])
    )
    client = OpenAiSmartParsingClient(SimpleNamespace(responses=responses))

    result = await client.parse("system", "input", "gpt-5-nano")

    assert result.result.question_list == ["질문"]
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert responses.kwargs["model"] == "gpt-5-nano"
    assert responses.kwargs["instructions"] == "system"
    assert responses.kwargs["input"] == "input"
    assert responses.kwargs["text_format"] is ParseResult
    assert responses.kwargs["reasoning"] == {"effort": "low"}
    assert responses.kwargs["max_output_tokens"] == 4096
    assert responses.kwargs["store"] is False


@pytest.mark.asyncio
async def test_smart_parsing_rejects_empty_structured_output():
    client = OpenAiSmartParsingClient(
        SimpleNamespace(responses=FakeResponses())
    )

    with pytest.raises(RuntimeError, match="structured output was empty"):
        await client.parse("system", "input", "gpt-5-nano")

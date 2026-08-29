import json
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel

import app.service.openai_chat_client as openai_chat_client
from app.service.openai_chat_client import (
    OPENAI_FAST,
    OPENAI_REASONING,
    create_openai_client,
    parse_structured,
)


class Result(BaseModel):
    value: str


def test_create_openai_client_uses_only_openai_credentials(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        openai_chat_client,
        "get_settings",
        lambda: SimpleNamespace(openai_api_key="sk_test"),
    )
    monkeypatch.setattr(openai_chat_client, "AsyncOpenAI", fake_client)

    assert create_openai_client() is not None
    assert captured["api_key"] == "sk_test"
    assert "base_url" not in captured


def test_create_openai_client_rejects_missing_api_key(monkeypatch):
    monkeypatch.setattr(
        openai_chat_client,
        "get_settings",
        lambda: SimpleNamespace(openai_api_key=""),
    )

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        create_openai_client()


@pytest.mark.asyncio
async def test_parse_structured_serializes_and_parses_real_openai_sdk_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-5.6-luna"
        assert payload["instructions"] == "system"
        assert payload["input"] == "user"
        assert payload["text"]["format"]["type"] == "json_schema"
        assert payload["reasoning"] == {"effort": "low"}
        assert payload["store"] is False
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "created_at": 0.0,
                "model": "gpt-5.6-luna",
                "object": "response",
                "output": [
                    {
                        "id": "msg_test",
                        "content": [
                            {
                                "annotations": [],
                                "text": '{"value":"정상"}',
                                "type": "output_text",
                            }
                        ],
                        "role": "assistant",
                        "status": "completed",
                        "type": "message",
                    }
                ],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "status": "completed",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AsyncOpenAI(api_key="dummy", http_client=http_client)
        result = await parse_structured(
            client,
            "system",
            "user",
            Result,
            model="gpt-5.6-luna",
        )

    assert result == Result(value="정상")


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_parsed=Result(value="정상"),
            output_text='{"value":"정상"}',
            model="gpt-5.6-luna",
            status="completed",
            error=None,
            incomplete_details=None,
            usage=None,
        )


class ResponseFailure(RuntimeError):
    def __init__(self, response):
        super().__init__("response failed")
        self.response = response


class FailingResponses:
    async def parse(self, **kwargs):
        repeated_tail = '"반복 문장입니다.", ' * 40
        content = '{"value":[' + repeated_tail
        response = SimpleNamespace(
            id="response-test-id",
            output=[],
            output_text=content,
            status="incomplete",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=4096,
                total_tokens=4196,
                input_tokens_details=None,
            ),
        )
        raise ResponseFailure(response)


class RawResponse:
    def __init__(self, payload, parsed=None, error=None):
        self._payload = payload
        self._parsed = parsed
        self._error = error

    def json(self):
        return self._payload

    def parse(self):
        if self._error is not None:
            raise self._error
        return self._parsed


class LegacyRawResponse:
    def __init__(self, payload, error):
        import json

        self.text = json.dumps(payload, ensure_ascii=False)
        self._error = error

    def parse(self):
        raise self._error


class RawResponses:
    def __init__(self, raw_response):
        self.with_raw_response = SimpleNamespace(parse=self._parse)
        self.raw_response = raw_response
        self.kwargs = None

    async def _parse(self, **kwargs):
        self.kwargs = kwargs
        return self.raw_response


def _raw_payload(content: str, response_id: str = "response-validation-id"):
    return {
        "id": response_id,
        "object": "response",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": content}],
            }
        ],
        "usage": {
            "input_tokens": 110,
            "output_tokens": 17,
            "total_tokens": 127,
        },
    }


@pytest.mark.asyncio
async def test_parse_structured_uses_openai_responses_reasoning_controls():
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)

    result = await parse_structured(
        client,
        "system",
        "user",
        Result,
        model="gpt-5.6-luna",
        options=OPENAI_REASONING,
    )

    assert result.value == "정상"
    assert responses.kwargs["model"] == "gpt-5.6-luna"
    assert responses.kwargs["instructions"] == "system"
    assert responses.kwargs["input"] == "user"
    assert responses.kwargs["text_format"] is Result
    assert responses.kwargs["reasoning"] == {"effort": "medium"}
    assert responses.kwargs["max_output_tokens"] == 8192
    assert responses.kwargs["store"] is False
    assert "extra_body" not in responses.kwargs
    assert "temperature" not in responses.kwargs
    assert "top_p" not in responses.kwargs


@pytest.mark.asyncio
async def test_parse_structured_uses_configured_default_reasoning_effort():
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)

    await parse_structured(
        client,
        "system",
        "user",
        Result,
        model="gpt-5.6-luna",
        options=OPENAI_FAST,
    )

    assert responses.kwargs["reasoning"] == {"effort": "low"}


@pytest.mark.asyncio
async def test_parse_structured_logs_incomplete_response_diagnostics(caplog):
    client = SimpleNamespace(responses=FailingResponses())
    caplog.set_level("DEBUG", logger="app.service.openai_chat_client")

    with pytest.raises(ResponseFailure):
        await parse_structured(
            client,
            "system",
            "user",
            Result,
            model="gpt-5.6-luna",
            options=OPENAI_FAST,
        )

    messages = [record.getMessage() for record in caplog.records]
    warning = next(message for message in messages if "structured output failure" in message)
    assert "finish_reason=incomplete" in warning
    assert "completion_tokens=4096" in warning
    assert '"brace_balance":1' in warning
    assert '"content_sha256"' in warning
    assert any("failed content preview" in message for message in messages)


@pytest.mark.asyncio
async def test_parse_structured_logs_raw_content_when_validation_fails(caplog):
    raw_payload = _raw_payload('{"value":"깨진 결과 �"}')
    with pytest.raises(Exception) as validation:
        Result.model_validate({})
    responses = RawResponses(RawResponse(raw_payload, error=validation.value))
    client = SimpleNamespace(responses=responses)
    caplog.set_level("DEBUG", logger="app.service.openai_chat_client")

    with pytest.raises(Exception):
        await parse_structured(
            client,
            "system",
            "user",
            Result,
            model="gpt-5.6-luna",
            options=OPENAI_FAST,
        )

    warning = next(
        record.getMessage()
        for record in caplog.records
        if "structured output failure" in record.getMessage()
    )
    assert "finish_reason=completed" in warning
    assert "prompt_tokens=110" in warning
    assert "completion_tokens=17" in warning
    assert '"unexpected_character_codes":["U+FFFD"]' in warning


@pytest.mark.asyncio
async def test_parse_structured_reads_legacy_raw_response_text(caplog):
    raw_payload = _raw_payload('{"value":3}', "legacy-response-id")
    with pytest.raises(Exception) as validation:
        Result.model_validate({})
    client = SimpleNamespace(
        responses=RawResponses(LegacyRawResponse(raw_payload, validation.value))
    )
    caplog.set_level("WARNING", logger="app.service.openai_chat_client")

    with pytest.raises(Exception):
        await parse_structured(client, "system", "user", Result, model="gpt-5.6-luna")

    warning = next(
        record.getMessage()
        for record in caplog.records
        if "structured output failure" in record.getMessage()
    )
    assert "completion_id=legacy-response-id" in warning
    assert "prompt_tokens=110" in warning

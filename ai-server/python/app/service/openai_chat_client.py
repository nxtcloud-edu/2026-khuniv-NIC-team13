"""Shared OpenAI Responses API client for structured output.

Stand-in for Spring AI's ``ChatClient.Builder`` + ``BeanOutputConverter``
combo used across ``SchemerNode``, ``WebSearchNode``, ``EvaluateNode``,
``ReviserNode`` and ``SmartParsingService`` in the Java version.

All production LLM calls use OpenAI directly. The API key is read from
``OPENAI_API_KEY`` and is never accepted in an HTTP request or stored in the
repository.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import logging
import re
import unicodedata
import zlib
from dataclasses import dataclass
from typing import Any, Literal, Optional, Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_FAILURE_PREVIEW_CHARS = 500
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?요다])\s+|\n+")


@dataclass(frozen=True)
class GenerationOptions:
    """Per-task OpenAI Responses API generation controls."""

    max_tokens: int
    reasoning_effort: Optional[
        Literal["none", "low", "medium", "high", "xhigh", "max"]
    ] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


OPENAI_FAST = GenerationOptions(
    max_tokens=1024,
)

OPENAI_REASONING = GenerationOptions(
    max_tokens=8192,
    reasoning_effort="medium",
)


def create_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다. python/.env 또는 실행 환경변수에 설정하세요."
        )
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        max_retries=1,
        timeout=300.0,
    )


def _usage_value(usage: Any, field: str) -> Optional[int]:
    if isinstance(usage, dict):
        value = usage.get(field)
    else:
        value = getattr(usage, field, None) if usage is not None else None
    return value if isinstance(value, int) else None


def _cached_prompt_tokens(usage: Any) -> Optional[int]:
    details = (
        usage.get("input_tokens_details") or usage.get("prompt_tokens_details")
        if isinstance(usage, dict)
        else getattr(usage, "input_tokens_details", None)
        or getattr(usage, "prompt_tokens_details", None)
    )
    return _usage_value(details, "cached_tokens")


def _completion_details(exc: Exception) -> tuple[Any, Any, str]:
    completion = getattr(exc, "completion", None)
    if completion is None:
        completion = getattr(exc, "response", None)
    if completion is not None and hasattr(completion, "output"):
        return completion, None, getattr(completion, "output_text", "") or ""
    choices = getattr(completion, "choices", None) or []
    choice = choices[0] if choices else None
    message = getattr(choice, "message", None)
    content = getattr(message, "content", None) or ""
    return completion, choice, content


def _raw_payload_details(raw_payload: Any) -> tuple[Any, Any, str]:
    if not isinstance(raw_payload, dict):
        return None, None, ""
    if isinstance(raw_payload.get("output"), list):
        text_parts: list[str] = []
        for output_item in raw_payload["output"]:
            if not isinstance(output_item, dict):
                continue
            for content_item in output_item.get("content") or []:
                if isinstance(content_item, dict) and isinstance(content_item.get("text"), str):
                    text_parts.append(content_item["text"])
        return raw_payload, None, "".join(text_parts)
    choices = raw_payload.get("choices") or []
    choice = choices[0] if choices and isinstance(choices[0], dict) else None
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return raw_payload, choice, content if isinstance(content, str) else ""


def _unexpected_character_codes(content: str) -> list[str]:
    codes: list[str] = []
    for character in content:
        codepoint = ord(character)
        category = unicodedata.category(character)
        expected_letter = (
            "A" <= character <= "Z"
            or "a" <= character <= "z"
            or 0x1100 <= codepoint <= 0x11FF
            or 0x3130 <= codepoint <= 0x318F
            or 0xAC00 <= codepoint <= 0xD7A3
        )
        if character == "\ufffd" or (category.startswith("L") and not expected_letter):
            codes.append(f"U+{codepoint:04X}")
    return list(dict.fromkeys(codes))[:20]


def _tail_repeat(content: str) -> Optional[dict[str, Any]]:
    """Find an exact block repeated consecutively at the truncated tail."""
    best: Optional[dict[str, Any]] = None
    max_block = min(256, len(content) // 2)
    for block_chars in range(8, max_block + 1):
        block = content[-block_chars:]
        repeats = 1
        cursor = len(content) - block_chars
        while cursor >= block_chars and content[cursor - block_chars:cursor] == block:
            repeats += 1
            cursor -= block_chars
        if repeats < 2:
            continue
        repeated_chars = repeats * block_chars
        if best is None or repeated_chars > best["repeated_chars"]:
            best = {
                "block_chars": block_chars,
                "repeats": repeats,
                "repeated_chars": repeated_chars,
                "block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest()[:16],
            }
    return best


def _content_diagnostics(content: str) -> dict[str, Any]:
    if not content:
        return {
            "content_chars": 0,
            "content_sha256": None,
            "brace_balance": None,
            "bracket_balance": None,
            "duplicate_sentence_ratio": None,
            "compression_ratio": None,
            "tail_repeat": None,
            "unexpected_character_codes": [],
        }
    sentences = [
        " ".join(sentence.split()).lower()
        for sentence in _SENTENCE_SPLIT.split(content)
        if sentence.strip()
    ]
    duplicate_sentence_ratio = (
        round(1.0 - len(set(sentences)) / len(sentences), 4) if sentences else 0.0
    )
    compressed_bytes = len(zlib.compress(content.encode("utf-8")))
    return {
        "content_chars": len(content),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
        "brace_balance": content.count("{") - content.count("}"),
        "bracket_balance": content.count("[") - content.count("]"),
        "duplicate_sentence_ratio": duplicate_sentence_ratio,
        "compression_ratio": round(compressed_bytes / len(content.encode("utf-8")), 4),
        "tail_repeat": _tail_repeat(content),
        "unexpected_character_codes": _unexpected_character_codes(content),
    }


def _safe_validation_errors(exc: Exception) -> list[dict[str, Any]]:
    if not isinstance(exc, ValidationError):
        return []
    summarized: list[dict[str, Any]] = []
    for error in exc.errors(include_url=False):
        input_value = error.get("input")
        if isinstance(input_value, (int, float, bool)) or input_value is None:
            safe_input: Any = input_value
        elif isinstance(input_value, str):
            safe_input = {
                "type": "str",
                "chars": len(input_value),
                "sha256": hashlib.sha256(input_value.encode("utf-8")).hexdigest()[:16],
            }
        else:
            safe_input = {"type": type(input_value).__name__}
        summarized.append(
            {
                "location": list(error.get("loc", ())),
                "type": error.get("type"),
                "message": error.get("msg"),
                "input": safe_input,
            }
        )
    return summarized[:20]


def _log_structured_failure(
    *,
    exc: Exception,
    model: str,
    response_model: Type[BaseModel],
    options: GenerationOptions,
    prompt_sha256: str,
    raw_payload: Any = None,
) -> None:
    completion, choice, content = _completion_details(exc)
    if completion is None and raw_payload is not None:
        completion, choice, content = _raw_payload_details(raw_payload)
    usage = (
        completion.get("usage")
        if isinstance(completion, dict)
        else getattr(completion, "usage", None)
    )
    finish_reason = (
        choice.get("finish_reason")
        if isinstance(choice, dict)
        else getattr(choice, "finish_reason", None)
    )
    if finish_reason is None:
        finish_reason = (
            completion.get("status")
            if isinstance(completion, dict)
            else getattr(completion, "status", None)
        )
    completion_id = (
        completion.get("id")
        if isinstance(completion, dict)
        else getattr(completion, "id", None)
    )
    response_seed = (
        completion.get("seed")
        if isinstance(completion, dict)
        else getattr(completion, "seed", None)
    )
    diagnostics = _content_diagnostics(content)
    logger.warning(
        "LLM structured output failure: model=%s response_model=%s error_type=%s "
        "finish_reason=%s max_tokens=%s prompt_sha256=%s prompt_tokens=%s "
        "cached_tokens=%s completion_tokens=%s total_tokens=%s completion_id=%s "
        "response_seed=%s diagnostics=%s validation_errors=%s",
        model,
        response_model.__name__,
        type(exc).__name__,
        finish_reason,
        options.max_tokens,
        prompt_sha256,
        _usage_value(usage, "input_tokens") or _usage_value(usage, "prompt_tokens"),
        _cached_prompt_tokens(usage),
        _usage_value(usage, "output_tokens") or _usage_value(usage, "completion_tokens"),
        _usage_value(usage, "total_tokens"),
        completion_id,
        response_seed,
        json.dumps(diagnostics, ensure_ascii=False, separators=(",", ":")),
        json.dumps(_safe_validation_errors(exc), ensure_ascii=False, separators=(",", ":")),
    )
    if content:
        logger.debug(
            "LLM failed content preview: response_model=%s head=%r tail=%r",
            response_model.__name__,
            content[:_FAILURE_PREVIEW_CHARS],
            content[-_FAILURE_PREVIEW_CHARS:],
        )


async def _request_structured_completion(
    client: AsyncOpenAI,
    request_options: dict[str, Any],
) -> tuple[Any, Any]:
    """Return parsed completion plus optional raw JSON for failure diagnostics."""
    responses = client.responses
    raw_api = getattr(responses, "with_raw_response", None)
    if raw_api is None:
        return await responses.parse(**request_options), None

    raw_response = await raw_api.parse(**request_options)
    raw_payload: Any = None
    try:
        json_reader = getattr(raw_response, "json", None)
        if callable(json_reader):
            raw_payload = json_reader()
            if inspect.isawaitable(raw_payload):
                raw_payload = await raw_payload
        else:
            raw_text = getattr(raw_response, "text", "")
            if callable(raw_text):
                raw_text = raw_text()
                if inspect.isawaitable(raw_text):
                    raw_text = await raw_text
            if isinstance(raw_text, str) and raw_text:
                raw_payload = json.loads(raw_text)
    except Exception:  # noqa: BLE001 - diagnostics must not break the request
        logger.debug("Failed to decode raw structured response JSON", exc_info=True)
    try:
        parsed = raw_response.parse()
        if inspect.isawaitable(parsed):
            parsed = await parsed
    except Exception as exc:  # noqa: BLE001 - attach raw body before re-raising
        try:
            setattr(exc, "raw_payload", raw_payload)
        except Exception:  # noqa: BLE001 - some exception types may be immutable
            pass
        raise
    return parsed, raw_payload


async def parse_structured(
    client: AsyncOpenAI,
    system: str,
    user: str,
    response_model: Type[T],
    model: Optional[str] = None,
    options: GenerationOptions = OPENAI_FAST,
) -> T:
    settings = get_settings()
    resolved_model = model or settings.openai_chat_model
    reasoning_effort = options.reasoning_effort or settings.openai_reasoning_effort

    logger.debug(
        "LLM request -> model=%s response_model=%s system_chars=%s user_chars=%s",
        resolved_model,
        response_model.__name__,
        len(system),
        len(user),
    )

    request_options = {
        "model": resolved_model,
        "instructions": system,
        "input": user,
        "text_format": response_model,
        "max_output_tokens": options.max_tokens,
        "reasoning": {"effort": reasoning_effort},
        "store": False,
    }
    if options.temperature is not None:
        request_options["temperature"] = options.temperature
    if options.top_p is not None:
        request_options["top_p"] = options.top_p

    raw_payload: Any = None
    prompt_sha256 = hashlib.sha256(
        f"{system}\0{user}".encode("utf-8")
    ).hexdigest()[:16]
    try:
        completion, raw_payload = await _request_structured_completion(
            client,
            request_options,
        )
    except Exception as exc:  # noqa: BLE001 - preserve provider/validation exception
        if raw_payload is None:
            raw_payload = getattr(exc, "raw_payload", None)
        _log_structured_failure(
            exc=exc,
            model=resolved_model,
            response_model=response_model,
            options=options,
            prompt_sha256=prompt_sha256,
            raw_payload=raw_payload,
        )
        raise

    logger.debug(
        "LLM response <- model=%s status=%s error=%s content_chars=%s",
        completion.model,
        getattr(completion, "status", None),
        getattr(completion, "error", None),
        len(getattr(completion, "output_text", "") or ""),
    )

    parsed = completion.output_parsed
    if parsed is None:
        logger.warning(
            "Structured output parsing returned null: model=%s response_model=%s status=%s incomplete=%s",
            resolved_model,
            response_model.__name__,
            getattr(completion, "status", None),
            getattr(completion, "incomplete_details", None),
        )
        raise RuntimeError("Structured output parsing returned null")

    usage = completion.usage
    if usage is not None:
        input_details = getattr(usage, "input_tokens_details", None)
        logger.info(
            "LLM usage: model=%s response_model=%s reasoning_effort=%s input_tokens=%s "
            "cached_tokens=%s output_tokens=%s total_tokens=%s",
            completion.model,
            response_model.__name__,
            reasoning_effort,
            usage.input_tokens,
            getattr(input_details, "cached_tokens", None),
            usage.output_tokens,
            usage.total_tokens,
        )

    logger.debug("LLM parsed result -> response_model=%s", response_model.__name__)
    return parsed

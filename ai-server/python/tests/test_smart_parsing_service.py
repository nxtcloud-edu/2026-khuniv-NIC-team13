import pytest

from app.config.smart_parsing_properties import SmartParsingProperties
from app.service.smart_parsing_client import SmartParsingClient
from app.service.smart_parsing_metrics_logger import SmartParsingMetricsLogger
from app.service.smart_parsing_models import ParseResult, SmartParsingResponse
from app.service.smart_parsing_service import SmartParsingService


class FakeSmartParsingClient(SmartParsingClient):
    def __init__(self):
        self.results = []  # queue of ParseResult or Exception
        self.calls = []

    async def parse(self, system_prompt, input_data, model):
        self.calls.append(model)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return SmartParsingResponse(result=result, model=model, input_tokens=10, output_tokens=5, total_tokens=15)


def properties(**overrides) -> SmartParsingProperties:
    base = SmartParsingProperties(
        primary_model="gpt-5-nano",
        fallback_model="gpt-5-mini",
        fallback_enabled=True,
        fallback_max_chars=1000,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def new_service(client: FakeSmartParsingClient, props: SmartParsingProperties) -> SmartParsingService:
    return SmartParsingService(client, props, SmartParsingMetricsLogger())


@pytest.mark.asyncio
async def test_parse_resume_uses_rule_parser_when_explicit_question_and_answer_pairs_exist():
    client = FakeSmartParsingClient()
    service = new_service(client, properties())

    result = await service.parse_resume(
        "Q: 지원 동기는 무엇인가요?\n"
        "A: 고객 문제를 제품으로 해결하고 싶습니다.\n"
        "Q: 가장 큰 성과는 무엇인가요?\n"
        "A: 검색 응답 시간을 절반으로 줄였습니다.\n"
    )

    assert result.question_list == ["지원 동기는 무엇인가요?", "가장 큰 성과는 무엇인가요?"]
    assert result.answer_list == ["고객 문제를 제품으로 해결하고 싶습니다.", "검색 응답 시간을 절반으로 줄였습니다."]
    assert client.calls == []


@pytest.mark.asyncio
async def test_parse_resume_returns_empty_result_without_llm_when_only_answers_are_marked():
    client = FakeSmartParsingClient()
    service = new_service(client, properties())

    result = await service.parse_resume("답변: 저는 백엔드 개발자입니다.\n답변: 대규모 트래픽 개선 경험이 있습니다.\n")

    assert result.question_list == []
    assert result.answer_list == []
    assert client.calls == []


@pytest.mark.asyncio
async def test_parse_resume_calls_primary_model_when_rule_parser_cannot_parse_input():
    client = FakeSmartParsingClient()
    client.results.append(ParseResult(question_list=["지원 동기는 무엇인가요?"], answer_list=["문제 해결이 좋아서입니다."]))
    service = new_service(client, properties())

    result = await service.parse_resume("지원 동기\n문제 해결이 좋아서입니다.")

    assert result.question_list == ["지원 동기는 무엇인가요?"]
    assert result.answer_list == ["문제 해결이 좋아서입니다."]
    assert client.calls == ["gpt-5-nano"]


@pytest.mark.asyncio
async def test_parse_resume_calls_fallback_model_when_primary_throws():
    client = FakeSmartParsingClient()
    client.results.append(ValueError("primary failed"))
    client.results.append(ParseResult(question_list=["질문"], answer_list=["답변"]))
    service = new_service(client, properties())

    result = await service.parse_resume("모호한 입력")

    assert result.question_list == ["질문"]
    assert result.answer_list == ["답변"]
    assert client.calls == ["gpt-5-nano", "gpt-5-mini"]


@pytest.mark.asyncio
async def test_parse_resume_calls_fallback_model_when_primary_violates_contract():
    client = FakeSmartParsingClient()
    client.results.append(ParseResult(question_list=["질문1", "질문2"], answer_list=["답변1"]))
    client.results.append(ParseResult(question_list=["질문1"], answer_list=["답변1"]))
    service = new_service(client, properties())

    result = await service.parse_resume("모호한 입력")

    assert result.question_list == ["질문1"]
    assert result.answer_list == ["답변1"]
    assert client.calls == ["gpt-5-nano", "gpt-5-mini"]


@pytest.mark.asyncio
async def test_parse_resume_throws_fallback_failure_when_both_models_fail():
    client = FakeSmartParsingClient()
    client.results.append(ValueError("primary failed"))
    client.results.append(ValueError("fallback failed"))
    service = new_service(client, properties())

    with pytest.raises(ValueError) as exc_info:
        await service.parse_resume("모호한 입력")

    assert str(exc_info.value) == "fallback failed"
    assert exc_info.value.__cause__ is not None
    assert str(exc_info.value.__cause__) == "primary failed"
    assert client.calls == ["gpt-5-nano", "gpt-5-mini"]


@pytest.mark.asyncio
async def test_parse_resume_uses_fallback_model_as_primary_when_input_exceeds_fallback_max_chars():
    client = FakeSmartParsingClient()
    client.results.append(ParseResult(question_list=["긴 입력 질문"], answer_list=["긴 입력 답변"]))
    service = new_service(client, properties())
    long_input = "가" * 1001

    result = await service.parse_resume(long_input)

    assert result.question_list == ["긴 입력 질문"]
    assert result.answer_list == ["긴 입력 답변"]
    assert client.calls == ["gpt-5-mini"]


@pytest.mark.asyncio
async def test_parse_resume_does_not_fallback_again_when_long_input_fallback_model_primary_fails():
    client = FakeSmartParsingClient()
    client.results.append(ValueError("mini primary failed"))
    service = new_service(client, properties())
    long_input = "가" * 1001

    with pytest.raises(ValueError) as exc_info:
        await service.parse_resume(long_input)

    assert str(exc_info.value) == "mini primary failed"
    assert client.calls == ["gpt-5-mini"]


@pytest.mark.asyncio
async def test_parse_resume_skips_fallback_when_fallback_is_disabled():
    client = FakeSmartParsingClient()
    client.results.append(ValueError("primary failed"))
    props = properties(fallback_enabled=False)
    service = new_service(client, props)

    with pytest.raises(ValueError) as exc_info:
        await service.parse_resume("짧지만 모호한 입력")

    assert str(exc_info.value) == "primary failed"
    assert client.calls == ["gpt-5-nano"]


def test_estimate_cost_usd_calculates_known_smart_parsing_model_prices():
    logger = SmartParsingMetricsLogger()

    assert logger.estimate_cost_usd("gpt-5-nano", 1000, 500) == "0.000250000000"
    assert logger.estimate_cost_usd("gpt-5-mini", 1000, 500) == "0.001250000000"

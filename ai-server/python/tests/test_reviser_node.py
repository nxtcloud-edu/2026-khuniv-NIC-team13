from pathlib import Path

import pytest

from app.workflow.event import WorkflowEvent, WorkflowEventSink
from app.workflow.nodes.reviser_models import RevisedAnswerInfo, SingleRevisedAnswer
from app.workflow.nodes.reviser_node import (
    ReviserNode,
    _FIRST_PASS_OPTIONS,
    _MAX_TARGETED_ATTEMPTS,
    _SINGLE_OPTIONS,
)
from app.workflow.state import AgentState


def test_reviser_uses_low_reasoning_openai_responses_options():
    assert _FIRST_PASS_OPTIONS.reasoning_effort is None
    assert _FIRST_PASS_OPTIONS.temperature is None
    assert _FIRST_PASS_OPTIONS.max_tokens == 4096
    assert _SINGLE_OPTIONS.reasoning_effort == "low"
    assert _SINGLE_OPTIONS.temperature is None
    assert _SINGLE_OPTIONS.top_p is None
    assert _SINGLE_OPTIONS.max_tokens == 4096
    assert _MAX_TARGETED_ATTEMPTS == 5


@pytest.mark.asyncio
async def test_first_attempt_is_deterministic_and_repair_uses_sampling(monkeypatch):
    original = (
        "문제 상황을 확인한 뒤 로그를 분석했습니다. 반복 조회가 원인임을 파악하고 조회 "
        "순서를 조정했습니다. 그 결과 처리 흐름을 개선했고 근거 기반 문제 해결을 배웠습니다."
    )
    revised = (
        "근거를 바탕으로 원인을 끝까지 확인하는 것이 저의 문제 해결 방식입니다. 문제 상황이 "
        "발생하자 로그를 분석해 반복 조회를 원인으로 파악했습니다. 이후 조회 순서를 조정해 "
        "처리 흐름을 개선했고, 근거 기반 판단의 중요성을 배웠습니다."
    )
    candidates = [
        SingleRevisedAnswer(
            best_reply=original,
            reply_reason=_explanation("첫 후보"),
            expectation=_explanation("첫 후보 효과"),
        ),
        SingleRevisedAnswer(
            best_reply=revised,
            reply_reason=_explanation("교정 후보"),
            expectation=_explanation("교정 후보 효과"),
        ),
    ]
    options = []

    async def fake_parse(client, system, user, response_model, **kwargs):
        options.append(kwargs["options"])
        return candidates[len(options) - 1]

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["문제를 어떻게 해결했나요?"],
        answer_list=[original],
    )

    await ReviserNode(client=object()).execute(RecordingSink(), state)

    assert options == [_FIRST_PASS_OPTIONS, _SINGLE_OPTIONS]


def _reply(prefix: str) -> str:
    return (
        f"{prefix} 원본 사실을 근거로 질문의 핵심에 답했습니다. "
        "지원자가 맡은 역할과 당시 상황을 분명하게 설명했습니다. "
        "문제를 발견한 배경과 판단 기준을 자연스럽게 연결했습니다. "
        "실제로 수행한 행동을 시간 흐름에 맞춰 정리했습니다. "
        "기술을 선택한 이유와 적용 과정을 구체화했습니다. "
        "원문에 있는 결과를 빠짐없이 보존했습니다. "
        "경험을 통해 얻은 배움을 명확하게 전달했습니다. "
        "지원 직무와 연결되는 역량을 설득력 있게 강조했습니다."
    )


def _explanation(prefix: str) -> str:
    return (
        f"{prefix} 질문 의도와 원본 근거의 연결을 강화했습니다. "
        "핵심 행동과 결과가 자연스럽게 이어지도록 구조를 정리했습니다. "
        "평가자가 지원자의 역량을 명확히 이해하도록 표현을 다듬었습니다."
    )


class RecordingSink(WorkflowEventSink):
    def __init__(self):
        self.events = []

    async def send(self, event: WorkflowEvent) -> None:
        self.events.append(event)


def _state() -> AgentState:
    return AgentState(
        question_list=["지원 동기는?", "문제 해결 경험은?", "입사 후 목표는?"],
        answer_list=["지원 답변", "해결 답변", "목표 답변"],
        company="삼성전자",
        job_position="소프트웨어 개발",
        context_web="회사와 직무에 관한 검증된 맥락",
    )


@pytest.mark.asyncio
async def test_valid_results_use_one_isolated_call_per_question(monkeypatch):
    calls = []
    results = [
        SingleRevisedAnswer(
            best_reply=_reply(prefix),
            reply_reason=_explanation(prefix),
            expectation=_explanation(f"{prefix} 효과"),
        )
        for prefix in ["지원", "해결", "목표"]
    ]

    async def fake_parse(*args, **kwargs):
        calls.append((args, kwargs))
        return results[len(calls) - 1]

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    node = ReviserNode(client=object())
    state = _state()
    events = RecordingSink()

    await node.execute(events, state)

    assert len(calls) == 3
    assert all(call[0][3] is SingleRevisedAnswer for call in calls)
    assert state.revised_result.best_reply == [result.best_reply for result in results]
    assert all(event.type != "revise_targeted_repair" for event in events.events)


@pytest.mark.asyncio
async def test_only_invalid_question_is_repaired(monkeypatch):
    calls = []
    valid_first = SingleRevisedAnswer(
        best_reply=_reply("첫 번째"),
        reply_reason=_explanation("첫 번째"),
        expectation=_explanation("첫 번째 효과"),
    )
    invalid_second = SingleRevisedAnswer(
        best_reply="...",
        reply_reason=_explanation("두 번째"),
        expectation=_explanation("두 번째 효과"),
    )
    repaired = SingleRevisedAnswer(
        best_reply=_reply("두 번째 교정"),
        reply_reason=_explanation("두 번째 교정"),
        expectation=_explanation("두 번째 교정 효과"),
    )
    valid_third = SingleRevisedAnswer(
        best_reply=_reply("세 번째"),
        reply_reason=_explanation("세 번째"),
        expectation=_explanation("세 번째 효과"),
    )

    async def fake_parse(client, system, user, response_model, **kwargs):
        calls.append(user)
        if '"index": 1' in user:
            return valid_first
        if '"index": 2' in user:
            return invalid_second if sum('"index": 2' in call for call in calls) == 1 else repaired
        return valid_third

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    node = ReviserNode(client=object())
    state = _state()
    events = RecordingSink()

    await node.execute(events, state)

    assert len(calls) == 4
    assert state.revised_result.best_reply[0] == valid_first.best_reply
    assert state.revised_result.best_reply[1] == repaired.best_reply
    retry_event = next(event for event in events.events if event.type == "revise_targeted_repair")
    assert retry_event.data == {"question_index": 2, "attempt": 2}


@pytest.mark.asyncio
async def test_invalid_explanation_is_replaced_without_regenerating_valid_reply(monkeypatch):
    calls = []
    valid_reply = _reply("문제 해결")
    candidate = SingleRevisedAnswer(
        best_reply=valid_reply,
        reply_reason="required_latin_tokens 검증을 통과했습니다.",
        expectation="평가자에게 전달되는 역량과 설득 효과를 설명합니다.",
    )

    async def fake_parse(*args, **kwargs):
        calls.append((args, kwargs))
        return candidate

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["문제를 어떻게 해결했나요?"],
        answer_list=["문제의 원인을 확인하고 해결했습니다."],
    )
    sink = RecordingSink()

    await ReviserNode(client=object()).execute(sink, state)

    assert len(calls) == 1
    assert state.revised_result.best_reply == [valid_reply]
    assert "required_latin_tokens" not in state.revised_result.reply_reason[0]
    fallback_event = next(
        event for event in sink.events if event.type == "revise_explanation_fallback"
    )
    assert fallback_event.data["fields"] == ["reply_reason", "expectation"]
    assert all(event.type != "revise_safe_fallback" for event in sink.events)


def test_single_prompt_does_not_include_other_answers_or_web_context():
    node = ReviserNode(client=object())
    state = _state()
    state.context_web = "웹 맥락 " * 1000
    context = node._build_revision_context(state)

    prompt = node._build_single_user_prompt(state, context, 0, None)

    assert "지원 답변" in prompt
    assert "해결 답변" not in prompt
    assert "목표 답변" not in prompt
    assert "웹 맥락" not in prompt


def test_editing_plan_compiles_strategy_actions_without_copying_unsafe_details():
    from types import SimpleNamespace

    node = ReviserNode(client=object())
    state = _state()
    state.evaluation_result = SimpleNamespace(
        improve_overall=["KPI와 새 시스템을 추가합니다."],
        improve_strategy=[
            SimpleNamespace(
                strategy_name="인과관계 명확화",
                action_items=["원문에 없는 알고리즘을 추가합니다."],
            )
        ],
    )

    context = node._build_revision_context(state)
    prompt = node._build_single_user_prompt(state, context, 0, None)

    assert context["evaluation_editing_focus"] == ["인과관계 명확화"]
    assert "improve_overall" not in context
    assert '"strategy_name": "인과관계 명확화"' in prompt
    assert "선택·행동·결과 사이의 인과관계" in prompt
    assert "원문에 없는 알고리즘" not in prompt


def test_reviser_prompt_uses_python_field_names_and_forbids_fabrication():
    prompt_path = Path(__file__).parents[1] / "resources" / "prompts" / "revise" / "system.txt"
    prompt = prompt_path.read_text(encoding="utf-8")

    assert "best_reply" in prompt
    assert "reply_reason" in prompt
    assert "bestReply" not in prompt
    assert "새로운 경력이나 성과를 만들지 않습니다" in prompt
    assert "상위권 자기소개서" in prompt
    assert "결론 → 상황·문제 → 지원자의 행동과 선택 이유" in prompt
    assert "원문의 핵심 행동, 선택 이유, 성과, 기술, 목표를 누락하지 않습니다" in prompt
    assert "같은 문장이나 같은 내용을 반복하지 않습니다" in prompt
    assert "평가자가 제안한 전략을 원문 기반 편집 작업으로 변환한 것" in prompt
    assert "적용 가능한 작업을 최소 두 가지 선택" in prompt
    assert "원문 전체를 그대로 반환하거나 일부 어휘만 치환하지 않습니다" in prompt
    assert "원문의 표현보다 사실의 강도를 높이지 않습니다" in prompt
    assert "장애 복구" in prompt
    assert "알고리즘" in prompt


def test_exact_original_is_rejected_as_generated_revision():
    node = ReviserNode(client=object())
    original = "지원 직무에 필요한 경험을 쌓았으며, 이 경험을 바탕으로 회사에 기여하고 싶습니다."
    state = AgentState(question_list=["지원 동기는 무엇인가요?"], answer_list=[original])

    problems = node._generated_reply_problems(original, state, 0)

    assert any("원문을 그대로 반환하지 말고" in problem for problem in problems)
    assert node._best_reply_problems(original, state, 0) == []


def test_near_copy_is_rejected_but_meaningful_restructure_is_allowed():
    node = ReviserNode(client=object())
    original = (
        "로그를 분석해 문제의 원인을 확인했습니다. 반복 조회가 응답 지연의 원인임을 "
        "파악했고, 조회 순서를 조정해 처리 흐름을 개선했습니다. 이 경험을 통해 근거를 "
        "바탕으로 문제를 해결하는 태도를 배웠습니다."
    )
    state = AgentState(question_list=["문제 해결 경험을 설명해주세요."], answer_list=[original])
    near_copy = original.replace("태도를 배웠습니다", "자세를 배웠습니다")
    restructured = (
        "문제 해결에서 가장 중요하게 생각한 것은 추측보다 로그의 근거를 따르는 태도였습니다. "
        "응답 지연이 발생하자 로그를 분석했고, 반복 조회가 원인임을 확인했습니다. 이후 조회 "
        "순서를 조정해 처리 흐름을 개선하면서 근거 중심의 문제 해결 자세를 배웠습니다."
    )

    assert node._insufficient_revision_problems(near_copy, state, 0)
    assert node._insufficient_revision_problems(restructured, state, 0) == []


@pytest.mark.asyncio
async def test_unchanged_first_candidate_gets_targeted_revision_feedback(monkeypatch):
    original = (
        "문제 상황을 확인한 뒤 로그를 분석했습니다. 반복 조회가 원인임을 파악하고 조회 "
        "순서를 조정했습니다. 그 결과 처리 흐름을 개선했고 근거 기반 문제 해결을 배웠습니다."
    )
    revised = (
        "근거를 바탕으로 원인을 끝까지 확인하는 것이 저의 문제 해결 방식입니다. 문제 상황이 "
        "발생하자 로그를 분석해 반복 조회를 원인으로 파악했습니다. 이후 조회 순서를 조정해 "
        "처리 흐름을 개선했고, 근거 기반 판단의 중요성을 배웠습니다."
    )
    candidates = [
        SingleRevisedAnswer(
            best_reply=original,
            reply_reason=_explanation("첫 후보"),
            expectation=_explanation("첫 후보 효과"),
        ),
        SingleRevisedAnswer(
            best_reply=revised,
            reply_reason=_explanation("재구성"),
            expectation=_explanation("재구성 효과"),
        ),
    ]
    calls = []

    async def fake_parse(client, system, user, response_model, **kwargs):
        calls.append(user)
        return candidates[len(calls) - 1]

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["문제를 어떻게 해결했나요?"],
        answer_list=[original],
    )
    sink = RecordingSink()

    await ReviserNode(client=object()).execute(sink, state)

    assert len(calls) == 2
    assert "원문을 그대로 반환하지 말고" in calls[1]
    assert state.revised_result.best_reply == [revised]
    assert any(event.type == "revise_targeted_repair" for event in sink.events)


def test_new_numeric_claim_marks_only_that_question_for_targeted_retry():
    node = ReviserNode(client=object())
    state = _state()
    report = RevisedAnswerInfo(
        best_reply=[
            _reply("지원"),
            _reply("해결") + " 처리 시간을 420밀리초에서 95밀리초로 줄였습니다.",
            _reply("목표"),
        ],
        reply_reason=[_explanation("지원"), _explanation("해결"), _explanation("목표")],
        expectation=[_explanation("지원"), _explanation("해결"), _explanation("목표")],
    )

    assert node._invalid_indices(report, 3, state) == [1]


@pytest.mark.asyncio
async def test_targeted_retry_gets_numeric_feedback_and_repairs_only_bad_item(monkeypatch):
    calls = []
    invalid = SingleRevisedAnswer(
        best_reply=_reply("첫 생성") + " 처리 시간을 420밀리초로 줄였습니다.",
        reply_reason=_explanation("첫 생성"),
        expectation=_explanation("첫 생성 효과"),
    )
    repaired = SingleRevisedAnswer(
        best_reply=_reply("최종 교정"),
        reply_reason=_explanation("최종 교정"),
        expectation=_explanation("최종 교정 효과"),
    )

    async def fake_parse(client, system, user, response_model, **kwargs):
        calls.append((response_model, user))
        return invalid if len(calls) == 1 else repaired

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["문제를 어떻게 해결했나요?"],
        answer_list=["로그를 분석해 반복 조회를 줄였습니다."],
    )
    node = ReviserNode(client=object())

    await node.execute(RecordingSink(), state)

    assert [call[0] for call in calls] == [
        SingleRevisedAnswer,
        SingleRevisedAnswer,
    ]
    assert "420밀리초" in calls[1][1]
    assert state.revised_result.best_reply[0] == repaired.best_reply


def test_prompt_exposes_only_source_numeric_expressions():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["장애를 어떻게 해결했나요?"],
        answer_list=["응답 시간을 850밀리초에서 줄였습니다."],
    )
    prompt = node._build_single_user_prompt(
        state, node._build_revision_context(state), 0, None
    )

    assert '"allowed_numeric_expressions": ["850밀리초"]' in prompt
    assert '"required_numeric_expressions": ["850밀리초"]' in prompt
    assert '"allowed_latin_tokens": []' in prompt
    assert '"required_latin_tokens": []' in prompt
    assert '"forbidden_claim_terms"' in prompt
    assert '"운영"' in prompt
    assert '"original_answer_chars": 22' in prompt
    assert '"target_answer_chars"' in prompt
    assert "minimum_chars" not in prompt


def test_retry_prompt_keeps_only_previous_best_reply_and_body_problems():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["성과를 설명해주세요."],
        answer_list=["응답 시간을 약 85% 줄였습니다."],
    )
    previous = SingleRevisedAnswer(
        best_reply="응답 시간을 85% 줄였습니다.",
        reply_reason="required_latin_tokens 규칙을 설명했습니다.",
        expectation="깨진 설명입니다ध.",
    )

    prompt = node._build_single_user_prompt(
        state, node._build_revision_context(state), 0, previous
    )

    assert '"previous_candidate": {"best_reply": "응답 시간을 85% 줄였습니다."}' in prompt
    assert "약 85%" in prompt
    assert "required_latin_tokens 규칙을 설명했습니다" not in prompt
    assert "깨진 설명" not in prompt
    assert "reply_reason:" not in prompt
    assert "expectation:" not in prompt


def test_missing_source_number_and_latin_token_require_targeted_retry():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["API 성능을 어떻게 개선했나요?"],
        answer_list=["APM으로 분석해 응답 시간을 800ms에서 120ms로 줄였습니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply="로그를 분석해 응답 시간을 줄였습니다.",
        reply_reason=_explanation("문제 해결"),
        expectation=_explanation("문제 해결 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert any("800ms" in problem and "120ms" in problem for problem in problems)
    assert any("APM" in problem for problem in problems)
    assert all("API" not in problem for problem in problems if "보존하세요" in problem)


def test_missing_numeric_qualifiers_require_targeted_retry():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["성과를 설명해주세요."],
        answer_list=["초당 5,000건 이상의 이벤트를 처리해 응답 시간을 약 85% 줄였습니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply="5,000건의 이벤트를 처리해 응답 시간을 85% 줄였습니다.",
        reply_reason=_explanation("수치 보존"),
        expectation=_explanation("수치 보존 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    qualifier_problem = next(problem for problem in problems if "범위나 강도" in problem)
    assert "초당 5,000건 이상" in qualifier_problem
    assert "약 85%" in qualifier_problem


def test_source_numeric_prefix_qualifier_is_restored_before_validation():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["성과를 설명해주세요."],
        answer_list=["초당 5,000건 이상의 이벤트를 처리해 응답 시간을 약 85% 줄였습니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply="5,000건 이상의 이벤트를 처리해 응답 시간을 85% 줄였습니다.",
        reply_reason=_explanation("수치 보존"),
        expectation=_explanation("수치 보존 효과"),
    )

    restored, expressions = node._restore_numeric_prefix_qualifiers(
        candidate, state, 0
    )

    assert restored.best_reply == (
        "초당 5,000건 이상의 이벤트를 처리해 응답 시간을 약 85% 줄였습니다."
    )
    assert expressions == ["초당 5,000건", "약 85%"]
    assert all(
        "범위나 강도" not in problem
        for problem in node._single_problems(restored, state, 0)
    )


@pytest.mark.asyncio
async def test_numeric_qualifier_restore_avoids_targeted_retry(monkeypatch):
    calls = []
    candidate = SingleRevisedAnswer(
        best_reply="성과를 바탕으로 응답 시간을 85% 줄였다고 설명했습니다.",
        reply_reason=_explanation("수치 보존"),
        expectation=_explanation("수치 보존 효과"),
    )

    async def fake_parse(*args, **kwargs):
        calls.append((args, kwargs))
        return candidate

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["성과를 설명해주세요."],
        answer_list=["응답 시간을 약 85% 줄인 성과가 있습니다."],
    )
    sink = RecordingSink()

    await ReviserNode(client=object()).execute(sink, state)

    assert len(calls) == 1
    assert state.revised_result.best_reply == [
        "성과를 바탕으로 응답 시간을 약 85% 줄였다고 설명했습니다."
    ]
    assert any(
        event.type == "revise_numeric_qualifier_restore" for event in sink.events
    )
    assert all(event.type != "revise_targeted_repair" for event in sink.events)


def test_question_only_number_is_allowed_but_not_required_for_original_fallback():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["입사 후 5년 이내 목표는 무엇인가요?"],
        answer_list=["첫 2년은 기반 역량을 쌓고 이후 3년은 프로젝트를 주도하겠습니다."],
    )

    fallback = node._safe_fallback_candidate(state, 0)

    assert node._allowed_numeric_expressions(state, 0) == ["5년", "2년", "3년"]
    assert node._required_numeric_expressions(state, 0) == ["2년", "3년"]
    assert node._single_problems(fallback, state, 0) == []


@pytest.mark.parametrize(
    "reply",
    [
        "Kafka 기반 파이프라인을 설계. 안정성을 높였습니다.",
        "캐시 정책 개선을 통해. 응답 시간을 줄였습니다.",
        "문제를 분석해 해결했습니다",
    ],
)
def test_incomplete_sentence_requires_targeted_retry(reply):
    problems = ReviserNode._sentence_quality_problems(reply)

    assert problems


def test_duplicate_sentence_requires_targeted_retry():
    sentence = "로그를 분석해 원인을 확인했습니다."

    problems = ReviserNode._sentence_quality_problems(f"{sentence} {sentence}")

    assert any("같은 문장" in problem for problem in problems)


def test_revised_answer_outside_source_length_band_requires_retry():
    node = ReviserNode(client=object())
    original = "원문의 사실을 충분한 분량으로 설명했습니다. " * 8
    state = AgentState(question_list=["경험을 설명해주세요."], answer_list=[original])
    candidate = SingleRevisedAnswer(
        best_reply="원문의 사실을 설명했습니다.",
        reply_reason=_explanation("분량 검증"),
        expectation=_explanation("분량 검증 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert any("허용" in problem and "현재" in problem for problem in problems)


def test_foreign_script_in_explanation_requires_retry():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["경험을 설명해주세요."],
        answer_list=["로그를 분석해 문제의 원인을 확인하고 해결했습니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply="로그를 분석해 문제의 원인을 확인하고 해결했습니다.",
        reply_reason="구조를 개선했습니다ध.",
        expectation=_explanation("설득 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert any("reply_reason" in problem and "ध" in problem for problem in problems)


def test_internal_field_name_and_unknown_latin_in_explanation_require_retry():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["경험을 설명해주세요."],
        answer_list=["로그를 분석해 문제의 원인을 확인하고 해결했습니다."],
        company="테스트전자",
        job_position="소프트웨어 개발",
    )
    candidate = SingleRevisedAnswer(
        best_reply="로그를 분석해 문제의 원인을 확인하고 해결했습니다.",
        reply_reason="required_latin_tokens와 secrecy 표현을 제거했습니다.",
        expectation=_explanation("설득 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert any(
        "reply_reason" in problem
        and "required_latin_tokens" in problem
        and "secrecy" in problem
        for problem in problems
    )


def test_prompt_example_copied_into_explanation_is_invalid():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["경험을 설명해주세요."],
        answer_list=["로그를 분석해 문제의 원인을 확인하고 해결했습니다."],
    )

    problems = node._explanation_problems(
        "평가자에게 전달되는 역량과 설득 효과를 설명합니다.", state, 0
    )

    assert any("출력 예시" in problem for problem in problems)


@pytest.mark.parametrize("claim", ["평가 방식", "기술 중심 문화", "혁신 지향성"])
def test_unsupported_company_attribute_in_explanation_is_invalid(claim):
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["지원 동기를 설명해주세요."],
        answer_list=["데이터 처리 경험을 바탕으로 기여하고 싶습니다."],
        company="삼성전자",
    )

    problems = node._explanation_problems(
        f"이 답변은 삼성전자의 {claim}과 높은 일치성을 보여줍니다.", state, 0
    )

    assert any("회사" in problem and claim in problem for problem in problems)


@pytest.mark.parametrize(
    "new_claim",
    [
        "장애 복구 체계를 구축했습니다.",
        "이상 감지 알고리즘을 구현했습니다.",
        "시스템 가용성과 무결성을 확보했습니다.",
        "지속적 배포 인프라를 도입했습니다.",
    ],
)
def test_claim_escalation_absent_from_original_requires_retry(new_claim):
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["프로젝트 경험을 설명해주세요."],
        answer_list=["센서 이벤트 처리 파이프라인을 설계했습니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply=f"센서 이벤트 처리 파이프라인을 설계했습니다. {new_claim}",
        reply_reason=_explanation("사실 보존"),
        expectation=_explanation("사실 보존 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert any("사실의 강도" in problem for problem in problems)


def test_claim_term_already_in_original_is_allowed():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["프로젝트 경험을 설명해주세요."],
        answer_list=["이상 감지 알고리즘을 구현했습니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply="이상 감지 알고리즘을 구현했습니다.",
        reply_reason=_explanation("사실 보존"),
        expectation=_explanation("사실 보존 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert all("사실의 강도" not in problem for problem in problems)
    assert "알고리즘" not in node._forbidden_claim_terms(state, 0)
    assert "구축" in node._forbidden_claim_terms(state, 0)


def test_study_group_operation_is_allowed_only_when_source_has_group_organization():
    node = ReviserNode(client=object())
    grounded_state = AgentState(
        question_list=["입사 후 계획을 설명해주세요."],
        answer_list=["사내 스터디 그룹을 조직해 팀 역량에 기여할 계획입니다."],
    )
    ungrounded_state = AgentState(
        question_list=["입사 후 계획을 설명해주세요."],
        answer_list=["팀 역량에 기여할 계획입니다."],
    )

    grounded = node._unsupported_claim_terms(
        "사내 스터디 그룹을 운영해 팀 역량에 기여할 계획입니다.",
        grounded_state,
        0,
    )
    ungrounded = node._unsupported_claim_terms(
        "사내 스터디 그룹을 운영해 팀 역량에 기여할 계획입니다.",
        ungrounded_state,
        0,
    )

    assert "운영" not in grounded
    assert "운영" in ungrounded
    assert "운영" not in node._forbidden_claim_terms(grounded_state, 0)


def test_tentative_future_plan_cannot_be_strengthened_to_definite_commitment():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["입사 후 목표를 설명해주세요."],
        answer_list=["프로젝트를 주도하고 싶습니다. 역량 향상에 기여할 계획입니다."],
    )
    candidate = SingleRevisedAnswer(
        best_reply="프로젝트를 주도하겠습니다. 역량 향상에도 기여하겠습니다.",
        reply_reason=_explanation("미래 계획"),
        expectation=_explanation("미래 계획 효과"),
    )

    problems = node._single_problems(candidate, state, 0)

    assert any("의지 수준" in problem for problem in problems)


def test_foreign_script_and_unseen_latin_token_require_targeted_retry():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["문제를 어떻게 해결했나요?"],
        answer_list=["로그를 분석해 반복 조회를 줄였습니다."],
    )
    report = RevisedAnswerInfo(
        best_reply=[_reply("문제 해결") + " API 조회를 ารบ 개선했습니다."],
        reply_reason=[_explanation("문제 해결")],
        expectation=[_explanation("문제 해결 효과")],
    )

    assert node._invalid_indices(report, 1, state) == [0]


def test_source_latin_token_is_allowed():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["API 문제를 어떻게 해결했나요?"],
        answer_list=["API 로그를 분석해 반복 조회를 줄였습니다."],
    )
    report = RevisedAnswerInfo(
        best_reply=[_reply("API 문제 해결")],
        reply_reason=[_explanation("문제 해결")],
        expectation=[_explanation("문제 해결 효과")],
    )

    assert node._invalid_indices(report, 1, state) == []


def test_copying_full_question_requires_repair():
    node = ReviserNode(client=object())
    state = AgentState(
        question_list=["문제를 어떻게 해결했나요?"],
        answer_list=["로그를 분석해 반복 조회를 줄였습니다."],
    )
    report = RevisedAnswerInfo(
        best_reply=["문제를 어떻게 해결했나요? " + _reply("문제 해결")],
        reply_reason=[_explanation("문제 해결")],
        expectation=[_explanation("문제 해결 효과")],
    )

    assert node._invalid_indices(report, 1, state) == [0]


@pytest.mark.asyncio
async def test_exhausted_targeted_retries_preserve_original_instead_of_failing(monkeypatch):
    invalid_single = SingleRevisedAnswer(
        best_reply=_reply("교정") + " DB를 도입했습니다.",
        reply_reason=_explanation("교정"),
        expectation=_explanation("교정 효과"),
    )

    async def fake_parse(client, system, user, response_model, **kwargs):
        return invalid_single

    monkeypatch.setattr("app.workflow.nodes.reviser_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["지원 동기는 무엇인가요?"],
        answer_list=["사용자의 불편을 발견하고 팀과 해결한 경험을 바탕으로 지원했습니다."],
    )
    sink = RecordingSink()

    await ReviserNode(client=object()).execute(sink, state)

    assert state.revised_result.best_reply == state.answer_list
    fallback_event = next(event for event in sink.events if event.type == "revise_safe_fallback")
    assert fallback_event.data["question_index"] == 1

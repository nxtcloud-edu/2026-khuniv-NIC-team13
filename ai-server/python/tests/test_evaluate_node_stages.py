import pytest

from app.repository.models import PreviousAnalysisResult
from app.vector.vector_context_service import VectorEvaluationContext
from app.workflow.event import WorkflowEvent, WorkflowEventSink
from app.workflow.nodes.evaluate_models import (
    AxisEvaluation,
    AxisEvaluationReport,
    FitEvaluationReport,
    ImprovementEvaluationReport,
    ImprovementStrategyReport,
    ImprovementSummaryReport,
)
from app.workflow.nodes.evaluate_node import EvaluateNode, with_deterministic_compare_scores
from app.workflow.state import AgentState


class EmptyVectorContextService:
    async def build_evaluation_context(self, request):
        return VectorEvaluationContext.empty("test")


class RecordingSink(WorkflowEventSink):
    def __init__(self):
        self.events = []

    async def send(self, event: WorkflowEvent) -> None:
        self.events.append(event)


def _axis(score: float) -> AxisEvaluation:
    return AxisEvaluation(
        score=score,
        criteria=["평가 기준입니다."],
        basis=["원문 근거입니다."],
        summary="축 요약입니다.",
        compare_score="비교 대상 없음",
    )


def test_compare_scores_are_computed_from_applicant_and_pass_averages():
    axes = AxisEvaluationReport(x=_axis(4.3), y=_axis(4.1), z=_axis(3.9))
    baseline = PreviousAnalysisResult(x=4.2, y=4.1, z=3.98, overall=4.09)

    compared = with_deterministic_compare_scores(axes, baseline)

    assert compared.x.compare_score == (
        "지원자 4.30점으로 합격자 평균 4.20점보다 0.10점 높습니다."
    )
    assert compared.y.compare_score == (
        "지원자 4.10점으로 합격자 평균 4.10점과 동일합니다."
    )
    assert compared.z.compare_score == (
        "지원자 3.90점으로 합격자 평균 3.98점보다 0.08점 낮습니다."
    )


def test_compare_scores_use_no_target_only_when_pass_score_is_missing():
    axes = AxisEvaluationReport(x=_axis(4.3), y=_axis(4.1), z=_axis(3.9))

    compared = with_deterministic_compare_scores(axes, None)

    assert {compared.x.compare_score, compared.y.compare_score, compared.z.compare_score} == {
        "비교 대상 없음"
    }


@pytest.mark.asyncio
async def test_evaluation_uses_three_compact_stages_and_combines_result(monkeypatch):
    calls = []
    axes = AxisEvaluationReport(x=_axis(4.0), y=_axis(3.8), z=_axis(4.1))
    fit = FitEvaluationReport(
        role_fit="역할 적합성입니다.",
        domain_fit="도메인 적합성입니다.",
        culture_fit="문화 적합성입니다.",
        skill_fit="기술 적합성입니다.",
        compare_prob=["비교 설명입니다."],
        score_summary=["점수 설명입니다."],
        level="높음",
        job_summary="직무 요약입니다.",
        overall="종합 평가입니다.",
    )
    improvement_summary = ImprovementSummaryReport(
        strength=["강점입니다."],
        weakness=["약점입니다."],
        advice=["조언입니다."],
        improve_overall=["개선점입니다."],
        improve_expectation=["기대 효과입니다."],
    )
    improvement_strategy = ImprovementStrategyReport(
        improve_strategy=[
            {"strategy_name": "근거 강화", "action_items": ["행동과 결과를 연결합니다."]}
        ],
    )
    results = {
        AxisEvaluationReport: axes,
        FitEvaluationReport: fit,
        ImprovementSummaryReport: improvement_summary,
        ImprovementStrategyReport: improvement_strategy,
    }

    async def fake_parse(client, system, user, response_model, **kwargs):
        calls.append((system, user, response_model, kwargs["options"]))
        return results[response_model]

    monkeypatch.setattr("app.workflow.nodes.evaluate_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["지원 동기는 무엇인가요?"],
        answer_list=["사용자 문제를 해결한 경험을 바탕으로 지원했습니다."],
        company="테스트전자",
        job_position="소프트웨어 개발",
        track="engineering",
        context_db=PreviousAnalysisResult(x=3.9, y=3.8, z=4.2, overall=3.97),
    )
    sink = RecordingSink()

    await EvaluateNode(EmptyVectorContextService(), client=object()).execute(sink, state)

    assert [call[2] for call in calls] == [
        AxisEvaluationReport,
        FitEvaluationReport,
        ImprovementSummaryReport,
        ImprovementStrategyReport,
    ]
    assert calls[0][0].count("0. Pertineo 시스템") == 1
    assert "0. Pertineo 시스템" not in calls[1][0]
    assert "0. Pertineo 시스템" not in calls[2][0]
    assert '"web_context"' in calls[1][1]
    assert '"web_context"' not in calls[2][1]
    assert '"pass_score"' not in calls[2][1]
    assert '"improvement_summary"' in calls[3][1]
    assert '"web_context"' not in calls[3][1]
    assert '"questions"' not in calls[3][1]
    assert '"answers"' not in calls[3][1]
    assert all(call[3].reasoning_effort is None for call in calls)
    assert state.evaluation_result is not None
    assert state.evaluation_result.x.score == 4.0
    assert state.evaluation_result.x.compare_score == (
        "지원자 4.00점으로 합격자 평균 3.90점보다 0.10점 높습니다."
    )
    assert state.evaluation_result.y.compare_score == (
        "지원자 3.80점으로 합격자 평균 3.80점과 동일합니다."
    )
    assert state.evaluation_result.z.compare_score == (
        "지원자 4.10점으로 합격자 평균 4.20점보다 0.10점 낮습니다."
    )
    assert state.evaluation_result.level == "높음"
    assert state.evaluation_result.improve_strategy[0].strategy_name == "근거 강화"
    assert {event.type for event in sink.events} >= {
        "evaluate_vector_context",
        "evaluate_axes_completed",
        "evaluate_fit_completed",
        "evaluate_improvement_summary_completed",
        "evaluate_result",
    }
    vector_event = next(
        event for event in sink.events if event.type == "evaluate_vector_context"
    )
    assert vector_event.data == {
        "status": "test",
        "selected_key_count": 0,
        "document_count": 0,
    }


@pytest.mark.asyncio
async def test_invalid_strategy_uses_local_fallback_without_repeating_prior_stages(monkeypatch):
    calls = []
    axes = AxisEvaluationReport(x=_axis(4.0), y=_axis(3.8), z=_axis(4.1))
    fit = FitEvaluationReport(
        role_fit="역할 적합성입니다.", domain_fit="도메인 적합성입니다.",
        culture_fit="문화 적합성입니다.", skill_fit="기술 적합성입니다.",
        compare_prob=["비교 설명입니다."], score_summary=["점수 설명입니다."],
        level="보통", job_summary="직무 요약입니다.", overall="종합 평가입니다.",
    )
    summary = ImprovementSummaryReport(
        strength=["강점입니다."], weakness=["약점입니다."], advice=["조언입니다."],
        improve_overall=["개선점입니다."], improve_expectation=["기대 효과입니다."],
    )

    async def fake_parse(client, system, user, response_model, **kwargs):
        calls.append(response_model)
        if response_model is AxisEvaluationReport:
            return axes
        if response_model is FitEvaluationReport:
            return fit
        if response_model is ImprovementSummaryReport:
            return summary
        raise RuntimeError("invalid strategy")

    monkeypatch.setattr("app.workflow.nodes.evaluate_node.parse_structured", fake_parse)
    state = AgentState(
        question_list=["지원 동기는 무엇인가요?"], answer_list=["사용자 문제를 해결했습니다."],
        company="테스트전자", job_position="소프트웨어 개발", track="engineering",
    )
    sink = RecordingSink()

    await EvaluateNode(EmptyVectorContextService(), client=object()).execute(sink, state)

    assert calls == [
        AxisEvaluationReport, FitEvaluationReport, ImprovementSummaryReport,
        ImprovementStrategyReport,
    ]
    assert state.evaluation_result.improve_strategy
    assert any(event.type == "evaluate_strategy_fallback" for event in sink.events)

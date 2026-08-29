import pytest
from pydantic import ValidationError

from app.workflow.nodes.evaluate_models import (
    AxisEvaluation,
    AxisEvaluationReport,
    ImprovementEvaluationReport,
    ImprovementStrategyReport,
    ImprovementSummaryReport,
    ResumeEvaluation,
)


def _axis(score=4.0):
    return {
        "score": score,
        "criteria": ["평가 기준"],
        "basis": ["지원자 근거"],
        "summary": "축 요약입니다.",
        "compare_score": "비교 대상 없음",
    }


def _evaluation(**overrides):
    data = {
        "x": _axis(),
        "y": _axis(),
        "z": _axis(),
        "role_fit": "직무 적합성입니다.",
        "domain_fit": "도메인 적합성입니다.",
        "culture_fit": "문화 적합성입니다.",
        "skill_fit": "기술 적합성입니다.",
        "compare_prob": ["비교 설명입니다."],
        "score_summary": ["점수 설명입니다."],
        "level": "높음",
        "job_summary": "지원 직무 요약입니다.",
        "overall": "종합 평가입니다.",
        "strength": ["강점입니다."],
        "weakness": ["약점입니다."],
        "advice": ["조언입니다."],
        "improve_overall": ["개선점입니다."],
        "improve_strategy": [{"strategy_name": "전략", "action_items": ["실행합니다."]}],
        "improve_expectation": ["기대 효과입니다."],
    }
    data.update(overrides)
    return data


def test_evaluation_accepts_supported_score_and_level():
    result = ResumeEvaluation.model_validate(_evaluation())

    assert result.level == "높음"
    assert result.x.score == 4.0
    assert type(result.x.score) is float


def test_axis_score_schema_exposes_exact_tenth_step_enum():
    schema = AxisEvaluationReport.model_json_schema()
    score_schema = schema["$defs"]["AxisEvaluation"]["properties"]["score"]

    assert score_schema["type"] == "number"
    assert score_schema["enum"] == [value / 10 for value in range(10, 51)]
    assert "$ref" not in score_schema


@pytest.mark.parametrize("score", [0.9, 5.1, 4.25])
def test_axis_score_rejects_out_of_range_or_non_tenth_values(score):
    with pytest.raises(ValidationError):
        AxisEvaluation.model_validate(_axis(score))


def test_evaluation_rejects_unknown_level():
    with pytest.raises(ValidationError):
        ResumeEvaluation.model_validate(_evaluation(level="최상"))


def test_improvement_report_combines_two_small_structured_outputs():
    summary = ImprovementSummaryReport.model_validate({
        key: value
        for key, value in _evaluation().items()
        if key in {"strength", "weakness", "advice", "improve_overall", "improve_expectation"}
    })
    strategy = ImprovementStrategyReport(
        improve_strategy=[{"strategy_name": "전략", "action_items": ["실행합니다."]}]
    )

    combined = ImprovementEvaluationReport.combine(summary, strategy)

    assert combined.strength == ["강점입니다."]
    assert combined.improve_strategy[0].strategy_name == "전략"

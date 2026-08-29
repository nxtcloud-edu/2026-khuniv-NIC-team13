"""Port of ``pertineo.agent.workflow.nodes.EvaluateNode.ResumeEvaluation``
and nested records."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, field_validator


def _require_meaningful_strings(values: List[str]) -> List[str]:
    if not values or any(not value.strip() for value in values):
        raise ValueError("list must contain non-blank strings")
    return values


AxisScore = Literal[
    1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9,
    2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
    3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9,
    4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
    5.0,
]


class AxisEvaluation(BaseModel):
    score: AxisScore
    criteria: List[str]
    basis: List[str]
    summary: str
    compare_score: str

    @field_validator("criteria", "basis")
    @classmethod
    def _lists_are_meaningful(cls, values: List[str]) -> List[str]:
        return _require_meaningful_strings(values)

    @field_validator("summary", "compare_score")
    @classmethod
    def _strings_are_meaningful(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class ImprovementStrategy(BaseModel):
    strategy_name: str
    action_items: List[str]

    @field_validator("strategy_name")
    @classmethod
    def _name_is_meaningful(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("strategy_name must not be blank")
        return value

    @field_validator("action_items")
    @classmethod
    def _actions_are_meaningful(cls, values: List[str]) -> List[str]:
        values = _require_meaningful_strings(values)
        if any("예:" in value or "예시" in value for value in values):
            raise ValueError("action_items must not contain generated examples")
        return values


class AxisEvaluationReport(BaseModel):
    x: AxisEvaluation
    y: AxisEvaluation
    z: AxisEvaluation


class FitEvaluationReport(BaseModel):
    role_fit: str
    domain_fit: str
    culture_fit: str
    skill_fit: str
    compare_prob: List[str]
    score_summary: List[str]
    level: Literal["매우 높음", "높음", "보통", "낮음", "매우 낮음"]
    job_summary: str
    overall: str

    @field_validator(
        "role_fit",
        "domain_fit",
        "culture_fit",
        "skill_fit",
        "job_summary",
        "overall",
    )
    @classmethod
    def _strings_are_meaningful(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("compare_prob", "score_summary")
    @classmethod
    def _lists_are_meaningful(cls, values: List[str]) -> List[str]:
        return _require_meaningful_strings(values)


class ImprovementSummaryReport(BaseModel):
    strength: List[str]
    weakness: List[str]
    advice: List[str]
    improve_overall: List[str]
    improve_expectation: List[str]

    @field_validator(
        "strength",
        "weakness",
        "advice",
        "improve_overall",
        "improve_expectation",
    )
    @classmethod
    def _lists_are_meaningful(cls, values: List[str]) -> List[str]:
        return _require_meaningful_strings(values)


class ImprovementStrategyReport(BaseModel):
    improve_strategy: List[ImprovementStrategy]

    @field_validator("improve_strategy")
    @classmethod
    def _strategies_are_meaningful(
        cls, values: List[ImprovementStrategy]
    ) -> List[ImprovementStrategy]:
        if not values:
            raise ValueError("improve_strategy must not be empty")
        return values


class ImprovementEvaluationReport(ImprovementSummaryReport, ImprovementStrategyReport):
    @classmethod
    def combine(
        cls,
        summary: ImprovementSummaryReport,
        strategy: ImprovementStrategyReport,
    ) -> "ImprovementEvaluationReport":
        return cls.model_validate(
            summary.model_dump(mode="json") | strategy.model_dump(mode="json")
        )


class ResumeEvaluation(AxisEvaluationReport, FitEvaluationReport, ImprovementEvaluationReport):
    @classmethod
    def combine(
        cls,
        axes: AxisEvaluationReport,
        fit: FitEvaluationReport,
        improvement: ImprovementEvaluationReport,
    ) -> "ResumeEvaluation":
        return cls.model_validate(
            axes.model_dump(mode="json")
            | fit.model_dump(mode="json")
            | improvement.model_dump(mode="json")
        )

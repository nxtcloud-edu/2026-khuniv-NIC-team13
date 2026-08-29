"""Deterministic ranking for data-backed company recommendations."""
from __future__ import annotations

from statistics import mean
from typing import Dict

from app.career.models import ApplicantCompanyAssessment
from app.repository.models import HistoricalCompanyStats
from app.schemas.career import (
    AxisScoreGaps,
    CompanyFitScoreBreakdown,
    CompanyRecommendation,
    HistoricalAxisScores,
    JobRecommendation,
)


_AXIS_LABELS: Dict[str, Dict[str, str]] = {
    "engineering": {
        "x": "기술 문제 구조화·설계",
        "y": "직무 수행 적합성",
        "z": "성과·재현성",
    },
    "business": {
        "x": "시장·전략 구조화",
        "y": "직무 실행 적합성",
        "z": "성과·재현성",
    },
}


def _applicant_axis_scores(
    assessment: ApplicantCompanyAssessment,
) -> Dict[str, float]:
    return {
        "x": float(assessment.x.score),
        "y": float(assessment.y.score),
        "z": float(assessment.z.score),
    }


def _historical_axis_scores(stats: HistoricalCompanyStats) -> Dict[str, float]:
    return {"x": stats.x, "y": stats.y, "z": stats.z}


def historical_alignment_score(
    assessment: ApplicantCompanyAssessment, stats: HistoricalCompanyStats
) -> int:
    """Score threshold clearance without claiming an acceptance probability.

    Matching or exceeding a historical successful-applicant average earns the
    full axis score. Each full point below the average removes that axis's
    contribution, bounded at zero.
    """

    applicant = _applicant_axis_scores(assessment)
    historical = _historical_axis_scores(stats)
    clearances = [
        max(0.0, 1.0 - max(0.0, historical[axis] - applicant[axis]))
        for axis in ("x", "y", "z")
    ]
    return round(50 * mean(clearances))


def sample_confidence_score(sample_count: int) -> int:
    return min(10, round(10 * min(sample_count, 30) / 30))


def company_candidate_priority(
    assessment: ApplicantCompanyAssessment, stats: HistoricalCompanyStats
) -> tuple[int, int, float, str]:
    return (
        historical_alignment_score(assessment, stats)
        + sample_confidence_score(stats.sample_count),
        stats.sample_count,
        stats.overall,
        stats.company,
    )


def build_company_recommendation(
    assessment: ApplicantCompanyAssessment,
    stats: HistoricalCompanyStats,
    active_job: JobRecommendation,
    recommended_role: str,
) -> CompanyRecommendation:
    historical_alignment = historical_alignment_score(assessment, stats)
    active_job_fit = round(active_job.fit_score * 0.4)
    sample_confidence = sample_confidence_score(stats.sample_count)
    breakdown = CompanyFitScoreBreakdown(
        historical_alignment=historical_alignment,
        active_job_fit=active_job_fit,
        sample_confidence=sample_confidence,
    )
    fit_score = min(100, sum(breakdown.model_dump().values()))

    applicant = _applicant_axis_scores(assessment)
    historical = _historical_axis_scores(stats)
    gaps = {
        axis: round(applicant[axis] - historical[axis], 2)
        for axis in ("x", "y", "z")
    }
    axis_labels = _AXIS_LABELS[assessment.track.value]
    evidence = [
        f"동일 {assessment.track.value} 직군의 과거 합격 사례 {stats.sample_count}건을 기준으로 비교했습니다.",
        f"현재 모집 중인 공고의 이력 적합도는 {active_job.fit_score}점입니다.",
    ]
    for axis in ("x", "y", "z"):
        if gaps[axis] >= 0:
            evidence.append(
                f"{axis.upper()}축({axis_labels[axis]})은 합격 사례 평균보다 {gaps[axis]:.2f}점 높거나 같습니다."
            )

    missing = [
        f"{axis.upper()}축({axis_labels[axis]})이 합격 사례 평균보다 {abs(gaps[axis]):.2f}점 낮습니다."
        for axis in ("x", "y", "z")
        if gaps[axis] < 0
    ]
    missing.extend(active_job.missing_requirements[:3])

    confidence = (
        "high" if stats.sample_count >= 30 else "medium" if stats.sample_count >= 10 else "low"
    )
    return CompanyRecommendation(
        company=stats.company,
        recommended_role=recommended_role,
        fit_score=fit_score,
        confidence=confidence,
        historical_sample_count=stats.sample_count,
        historical_average_scores=HistoricalAxisScores(
            x=stats.x, y=stats.y, z=stats.z
        ),
        score_gaps=AxisScoreGaps(**gaps),
        score_breakdown=breakdown,
        recommendation_evidence=evidence,
        gaps=list(dict.fromkeys(missing)),
        active_job=active_job,
    )

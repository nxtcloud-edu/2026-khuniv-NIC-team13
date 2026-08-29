"""HTTP request and response contracts for career recommendations."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


class _CareerApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class CareerProfileDto(_CareerApiModel):
    user_id: str = Field(min_length=1, max_length=128)
    education: Optional[str] = Field(default=None, max_length=300)
    gpa: Optional[float] = Field(default=None, ge=0, le=5)
    major: Optional[str] = Field(default=None, max_length=200)
    experience_years: float = Field(default=0, ge=0, le=60)
    experience_summary: Optional[str] = Field(default=None, max_length=10_000)
    resume_text: Optional[str] = Field(default=None, max_length=30_000)
    skills: List[str] = Field(default_factory=list, max_length=50)
    projects: List[str] = Field(default_factory=list, max_length=30)
    certificates: List[str] = Field(default_factory=list, max_length=30)
    languages: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("skills", "certificates", "languages")
    @classmethod
    def _short_list_items(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        if any(len(value) > 200 for value in normalized):
            raise ValueError("list item must be 200 characters or fewer")
        return list(dict.fromkeys(normalized))

    @field_validator("projects")
    @classmethod
    def _project_items(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        if any(len(value) > 2_000 for value in normalized):
            raise ValueError("project item must be 2000 characters or fewer")
        return normalized


class JobRecommendationRequest(_CareerApiModel):
    profile: CareerProfileDto
    target_roles: List[str] = Field(default_factory=list, max_length=5)
    target_companies: List[str] = Field(default_factory=list, max_length=10)
    locations: List[str] = Field(default_factory=list, max_length=10)
    employment_types: List[str] = Field(default_factory=list, max_length=5)
    candidate_limit: int = Field(default=20, ge=10, le=20)
    result_limit: int = Field(default=3, ge=1, le=3)

    @field_validator(
        "target_roles", "target_companies", "locations", "employment_types"
    )
    @classmethod
    def _search_terms(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        if any(len(value) > 100 for value in normalized):
            raise ValueError("search term must be 100 characters or fewer")
        return list(dict.fromkeys(normalized))


class CompanyRecommendationRequest(_CareerApiModel):
    profile: CareerProfileDto
    question_list: List[str] = Field(min_length=1, max_length=20)
    answer_list: List[str] = Field(min_length=1, max_length=20)
    target_roles: List[str] = Field(default_factory=list, max_length=3)
    locations: List[str] = Field(default_factory=list, max_length=10)
    minimum_sample_count: int = Field(default=10, ge=3, le=100)
    company_candidate_limit: int = Field(default=10, ge=3, le=20)
    result_limit: int = Field(default=3, ge=1, le=3)

    @field_validator("question_list", "answer_list")
    @classmethod
    def _self_introduction_items(cls, values: List[str]) -> List[str]:
        if any(not value or not value.strip() for value in values):
            raise ValueError("question and answer items must not be blank")
        return [value.strip() for value in values]

    @field_validator("target_roles", "locations")
    @classmethod
    def _optional_search_terms(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def _question_answer_counts_match(self) -> "CompanyRecommendationRequest":
        if len(self.question_list) != len(self.answer_list):
            raise ValueError("questionList and answerList must have the same length")
        return self


class FitScoreBreakdown(_CareerApiModel):
    role: int = Field(ge=0, le=30)
    required: int = Field(ge=0, le=35)
    preferred: int = Field(ge=0, le=10)
    experience: int = Field(ge=0, le=10)
    location: int = Field(ge=0, le=10)
    verification: int = Field(ge=0, le=5)


class JobRecommendation(_CareerApiModel):
    company: str
    title: str
    url: str
    source_domain: str
    deadline: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    verification_status: Literal["verified_active", "inactive", "unknown"]
    fit_score: int = Field(ge=0, le=100)
    score_breakdown: FitScoreBreakdown
    required_requirements: List[str] = Field(default_factory=list)
    preferred_requirements: List[str] = Field(default_factory=list)
    matched_requirements: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    recommendation_reason: str
    checked_at: datetime


class RoleRecommendation(_CareerApiModel):
    role: str
    evidence: List[str]


class ApplicantAxisScores(_CareerApiModel):
    x: float = Field(ge=1, le=5)
    y: float = Field(ge=1, le=5)
    z: float = Field(ge=1, le=5)


class HistoricalAxisScores(_CareerApiModel):
    x: float = Field(ge=0, le=5)
    y: float = Field(ge=0, le=5)
    z: float = Field(ge=0, le=5)


class AxisScoreGaps(_CareerApiModel):
    x: float = Field(ge=-5, le=5)
    y: float = Field(ge=-5, le=5)
    z: float = Field(ge=-5, le=5)


class CompanyFitScoreBreakdown(_CareerApiModel):
    historical_alignment: int = Field(ge=0, le=50)
    active_job_fit: int = Field(ge=0, le=40)
    sample_confidence: int = Field(ge=0, le=10)


class CompanyRecommendation(_CareerApiModel):
    company: str
    recommended_role: str
    fit_score: int = Field(ge=0, le=100)
    confidence: Literal["high", "medium", "low"]
    historical_sample_count: int = Field(ge=1)
    historical_average_scores: HistoricalAxisScores
    score_gaps: AxisScoreGaps
    score_breakdown: CompanyFitScoreBreakdown
    recommendation_evidence: List[str]
    gaps: List[str]
    active_job: JobRecommendation


class CompanyRecommendationResponse(_CareerApiModel):
    generated_at: datetime
    resolved_track: Literal["business", "engineering"]
    resolved_target_roles: List[str]
    role_recommendations: List[RoleRecommendation]
    applicant_scores: ApplicantAxisScores
    considered_company_count: int = Field(ge=0)
    verified_company_count: int = Field(ge=0)
    companies: List[CompanyRecommendation]
    methodology_notice: str
    notice: Optional[str] = None


class JobRecommendationResponse(_CareerApiModel):
    generated_at: datetime
    resolved_target_roles: List[str]
    search_queries: List[str]
    searched_candidate_count: int
    verified_candidate_count: int
    jobs: List[JobRecommendation]
    notice: Optional[str] = None


class CareerRoadmapRequest(_CareerApiModel):
    profile: CareerProfileDto
    target_role: str = Field(min_length=1, max_length=100)
    target_company: Optional[str] = Field(default=None, max_length=100)
    locations: List[str] = Field(default_factory=list, max_length=10)
    employment_types: List[str] = Field(default_factory=list, max_length=5)
    candidate_limit: int = Field(default=15, ge=10, le=20)


class RequirementInsight(_CareerApiModel):
    requirement: str
    category: Literal["required", "preferred"]
    source_count: int = Field(ge=2)
    source_job_urls: List[str] = Field(min_length=2)


class RequirementGap(_CareerApiModel):
    requirement: str
    category: Literal["required", "preferred"]
    source_count: int = Field(ge=2)
    reason: str


class CareerMilestone(_CareerApiModel):
    horizon: Literal["1개월", "3개월", "6개월", "12개월"]
    objective: str
    actions: List[str]
    completion_criteria: List[str]


class CareerRoadmapResponse(_CareerApiModel):
    generated_at: datetime
    target_role: str
    target_company: Optional[str] = None
    current_fit_summary: str
    common_required_requirements: List[RequirementInsight]
    common_preferred_requirements: List[RequirementInsight]
    priority_gaps: List[RequirementGap]
    milestones: List[CareerMilestone]
    reference_jobs: List[JobRecommendation]
    notice: Optional[str] = None

"""Internal models for career job discovery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.workflow.nodes.evaluate_models import AxisScore
from app.workflow.track import Track


class JobDiscoveryPlan(BaseModel):
    target_roles: List[str] = Field(min_length=1, max_length=3)
    queries: List[str] = Field(min_length=4, max_length=6)

    @field_validator("target_roles", "queries")
    @classmethod
    def _distinct_non_blank_values(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        normalized = list(dict.fromkeys(normalized))
        if not normalized:
            raise ValueError("at least one non-blank value is required")
        if any(len(value) > 250 for value in normalized):
            raise ValueError("discovery plan values must be 250 characters or fewer")
        return normalized


class RoleRecommendationEvidence(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    evidence: List[str] = Field(min_length=1, max_length=6)

    @field_validator("evidence")
    @classmethod
    def _evidence_is_meaningful(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        if not normalized:
            raise ValueError("role evidence must not be empty")
        return list(dict.fromkeys(normalized))


class ApplicantAxisAssessment(BaseModel):
    score: AxisScore
    evidence: List[str] = Field(min_length=1, max_length=6)

    @field_validator("evidence")
    @classmethod
    def _axis_evidence_is_meaningful(cls, values: List[str]) -> List[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        if not normalized:
            raise ValueError("axis evidence must not be empty")
        return list(dict.fromkeys(normalized))


class ApplicantCompanyAssessment(BaseModel):
    track: Track
    role_recommendations: List[RoleRecommendationEvidence] = Field(
        min_length=1, max_length=3
    )
    x: ApplicantAxisAssessment
    y: ApplicantAxisAssessment
    z: ApplicantAxisAssessment

    @model_validator(mode="after")
    def _roles_are_distinct(self) -> "ApplicantCompanyAssessment":
        roles = [item.role.strip().lower() for item in self.role_recommendations]
        if len(roles) != len(set(roles)):
            raise ValueError("recommended roles must be distinct")
        return self


@dataclass(frozen=True)
class JobSearchHit:
    title: str
    url: str
    content: str
    query: str


@dataclass(frozen=True)
class VerifiedJobPage:
    candidate_id: str
    hit: JobSearchHit
    final_url: str
    source_domain: str
    page_text: str
    verification_status: Literal["verified_active", "inactive", "unknown"]


class ExtractedJob(BaseModel):
    candidate_id: str
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    deadline: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    required_requirements: List[str] = Field(default_factory=list, max_length=30)
    preferred_requirements: List[str] = Field(default_factory=list, max_length=30)


class ExtractedJobBatch(BaseModel):
    postings: List[ExtractedJob] = Field(default_factory=list, max_length=5)


class RoadmapMilestoneDraft(BaseModel):
    horizon: Literal["1개월", "3개월", "6개월", "12개월"]
    objective: str
    actions: List[str] = Field(min_length=1, max_length=6)
    completion_criteria: List[str] = Field(min_length=1, max_length=6)


class CareerRoadmapDraft(BaseModel):
    current_fit_summary: str
    milestones: List[RoadmapMilestoneDraft] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def _has_exact_ordered_horizons(self) -> "CareerRoadmapDraft":
        horizons = tuple(milestone.horizon for milestone in self.milestones)
        if horizons != ("1개월", "3개월", "6개월", "12개월"):
            raise ValueError("milestones must contain 1/3/6/12개월 in order")
        return self

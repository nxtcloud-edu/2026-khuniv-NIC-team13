"""Port of ``pertineo.agent.controller.dto.AnalyzeRequestDto``."""
from __future__ import annotations

from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


class AnalyzeRequestDto(BaseModel):
    # ==========================================
    # [1] initial user inputs
    # ==========================================
    user_id: str = Field(..., alias="userId", min_length=1)
    question_list: List[str] = Field(..., alias="questionList", min_length=1)
    answer_list: List[str] = Field(..., alias="answerList", min_length=1)

    # --- applicant specs / history (optional) ---
    education: Optional[str] = None
    gpa: Optional[float] = None
    major: Optional[str] = None
    background_career_award: Optional[str] = Field(default=None, alias="backgroundCareerAward")
    linguistic_ability: Optional[str] = Field(default=None, alias="linguisticAbility")
    certificates: Optional[str] = None

    # --- application target info ---
    # Java's default Jackson name is the camelCase field name ("company",
    # "jobPosition"), with "applying_to"/"applying_as" accepted as
    # @JsonAlias fallbacks. AliasChoices reproduces both accepted spellings.
    company: str = Field(
        ..., validation_alias=AliasChoices("company", "applying_to"), min_length=1
    )
    job_position: str = Field(
        ..., validation_alias=AliasChoices("jobPosition", "applying_as"), min_length=1
    )
    job_field: Optional[str] = Field(default=None, alias="jobField")
    division: Optional[str] = None
    apply_url: Optional[str] = Field(default=None, alias="applyUrl")

    model_config = {"populate_by_name": True}

    @field_validator("user_id")
    @classmethod
    def _user_id_not_blank(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("userId must not be blank")
        return v

    @field_validator("question_list", "answer_list")
    @classmethod
    def _list_not_empty_and_elements_not_blank(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("list must not be empty")
        for item in v:
            if item is None or not item.strip():
                raise ValueError("list elements must not be blank")
        return v

    @field_validator("company", "job_position")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("field must not be blank")
        return v

    @model_validator(mode="after")
    def _question_answer_count_matched(self) -> "AnalyzeRequestDto":
        if self.question_list is not None and self.answer_list is not None:
            if len(self.question_list) != len(self.answer_list):
                raise ValueError("questionList and answerList must have the same length")
        return self

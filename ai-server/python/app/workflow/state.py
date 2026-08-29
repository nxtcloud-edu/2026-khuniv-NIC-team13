"""Port of ``pertineo.agent.workflow.nodes.state.AgentState``.

A plain mutable pydantic model (mirroring the Lombok ``@Data`` class),
threaded through every workflow node.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.repository.models import PreviousAnalysisResult
from app.workflow.nodes.evaluate_models import ResumeEvaluation
from app.workflow.nodes.reviser_models import RevisedAnswerInfo


class AgentState(BaseModel):
    model_config = ConfigDict(validate_assignment=False)

    # ==========================================
    # [1] initial user inputs
    # ==========================================
    user_id: Optional[str] = None
    question_list: Optional[List[str]] = None
    answer_list: Optional[List[str]] = None

    # --- applicant specs / history (optional) ---
    education: Optional[str] = None
    gpa: Optional[float] = None
    major: Optional[str] = None
    background_career_award: Optional[str] = None
    linguistic_ability: Optional[str] = None
    certificates: Optional[str] = None

    # --- application target info ---
    company: Optional[str] = None
    job_position: Optional[str] = None
    job_field: Optional[str] = None
    division: Optional[str] = None
    apply_url: Optional[str] = None
    track: Optional[str] = None

    # --- retrieval-augmented context ---
    context_web: Optional[str] = None
    context_db: Optional[PreviousAnalysisResult] = None
    ref_document: Optional[List[str]] = None

    # ==========================================
    # [2] node outputs
    # ==========================================
    plan_result: Optional[bool] = None
    schema_result: Optional[bool] = None
    evaluation_result: Optional[ResumeEvaluation] = None
    revised_result: Optional[RevisedAnswerInfo] = None

    # ==========================================
    # [3] routing flags
    # ==========================================
    is_evaluation_passed: bool = False
    analyzer_retry_count: int = 0
